import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useReplayStore } from '../stores/replay'

const manifest = { duration: 100, defaultOffset: 10, layers: [{ layer: 1, offset: 0 }, { layer: 2, offset: 50 }] }
const frame = offset => ({ offset, layer: offset < 50 ? 1 : 2, time: String(offset) })
const response = body => ({ ok: true, json: async () => body })

beforeEach(() => {
  vi.useFakeTimers()
  localStorage.clear()
  setActivePinia(createPinia())
  vi.stubGlobal('fetch', vi.fn(async url => response(url.endsWith('/manifest') ? manifest : frame(Number(new URL(url, 'http://localhost').searchParams.get('offset'))))))
})
afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals() })

describe('设备回放共享进度', () => {
  it('新会话忽略旧进度和倍速，从头以 1 倍速自动播放', async () => {
    localStorage.setItem('smartam-replay-blt-s430-20240828', JSON.stringify({ offset: 70, speed: 10, realProcessing: true }))
    const replay = useReplayStore()
    await replay.open()
    expect(replay.speed).toBe(1)
    expect(replay.snapshot.offset).toBe(0)
    expect(replay.playing).toBe(true)
    expect(replay.realProcessing).toBe(true)
    await vi.advanceTimersByTimeAsync(1000)
    expect(replay.snapshot.offset).toBeCloseTo(1)
  })
  it('末层展示后自动从头循环，并继续按当前倍速推进', async () => {
    const replay = useReplayStore()
    await replay.open()
    await replay.setSpeed(5)
    await replay.seek(99)
    await vi.advanceTimersByTimeAsync(250)
    expect(replay.snapshot.offset).toBe(100)
    expect(replay.playing).toBe(true)
    await vi.advanceTimersByTimeAsync(250)
    expect(replay.snapshot.offset).toBe(0)
    await vi.advanceTimersByTimeAsync(1000)
    expect(replay.snapshot.offset).toBeCloseTo(5)
  })
  it('在末帧暂停会取消循环，恢复播放从头开始', async () => {
    const replay = useReplayStore()
    await replay.open()
    await replay.seek(100)
    await replay.pause()
    await vi.advanceTimersByTimeAsync(1000)
    expect(replay.snapshot.offset).toBe(100)
    expect(replay.playing).toBe(false)
    await replay.play()
    expect(replay.snapshot.offset).toBe(0)
    expect(replay.playing).toBe(true)
  })
  it('进入自动播放，暂停后时间不再推进，重进工作区沿用进度', async () => {
    const replay = useReplayStore()
    await replay.open()
    expect(replay.playing).toBe(true)
    await replay.pause()
    const paused = replay.snapshot.offset
    await vi.advanceTimersByTimeAsync(10000)
    await replay.open()
    expect(replay.snapshot.offset).toBe(paused)
    expect(replay.playing).toBe(false)
  })
  it('跳转立即清除旧结果，延迟返回的旧请求不能覆盖新游标', async () => {
    const replay = useReplayStore()
    await replay.open()
    await replay.pause()
    let finishOld
    fetch.mockImplementationOnce(() => new Promise(resolve => { finishOld = resolve }))
    const oldRequest = replay.seek(70)
    expect(replay.snapshot).toBeNull()
    await replay.seek(5)
    finishOld(response(frame(70)))
    await oldRequest
    expect(replay.snapshot.offset).toBe(5)
    expect(replay.snapshot.layer).toBe(1)
  })
  it('没有接口数据时停止播放并报告错误，不伪造帧', async () => {
    const replay = useReplayStore()
    await replay.open()
    fetch.mockImplementationOnce(async () => ({ ok: false, status: 503 }))
    await replay.seek(60)
    expect(replay.snapshot).toBeNull()
    expect(replay.playing).toBe(false)
    expect(replay.error).toContain('503')
  })
})

describe('多设备进度隔离', () => {
  it('各案例的请求、快照与持久化位置独立，切换不复制另一台的结果', async () => {
    const first = useReplayStore('b10-20250509-07-47')
    const second = useReplayStore('b44-20250321-09-20')
    await first.open()
    await first.pause()
    await first.seek(60)
    await second.open()
    await second.pause()
    await second.seek(20)
    expect(first.snapshot.offset).toBe(60)
    expect(second.snapshot.offset).toBe(20)
    await first.setRealProcessing(true)
    expect(JSON.parse(localStorage.getItem('smartam-replay-b10-20250509-07-47')).realProcessing).toBe(true)
    expect(JSON.parse(localStorage.getItem('smartam-replay-b44-20250321-09-20')).realProcessing).toBe(false)
    expect(fetch.mock.calls.some(([url]) => url.includes('/cases/b10-20250509-07-47/'))).toBe(true)
    expect(fetch.mock.calls.some(([url]) => url.includes('/cases/b44-20250321-09-20/'))).toBe(true)
  })
})
