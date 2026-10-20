import { describe, expect, it } from 'vitest'
import { layerWindow, torqueWindow } from '../views/slm/forming/rollingWindow'

describe('曲线滚动窗口', () => {
  it('两路扭矩同步保留最后 50 点，模型输入保持完整', () => {
    const source = { t: [], scraper: [], platform: [] }
    for (let i = 0; i < 224; i++) {
      source.t.push(i / 10)
      source.scraper.push(-i)
      source.platform.push(i * 2)
    }
    const window = torqueWindow(source)
    expect(window.t).toHaveLength(50)
    expect(window.scraper[0]).toBe(-174)
    expect(window.platform[49]).toBe(446)
    expect(window.min).toBe(17.4)
    expect(window.max).toBe(22.3)
    expect(source.t).toHaveLength(224)
  })

  it('稀疏采样时横轴贴合首尾点，新点到达才推进，不拉长空白或展示未来采样', () => {
    const source = { t: [10, 10, 15, 25], scraper: [0, -3, 8, 9], platform: [4, 5, 6, 7], cursor: 20 }
    const first = torqueWindow(source)
    const next = torqueWindow({ ...source, cursor: 20.25 })
    expect(first.t).toEqual([10, 10, 15])
    expect(next.t).toEqual(first.t)
    expect(next.scraper).toEqual([0, -3, 8])
    expect([first.min, first.max]).toEqual([10, 15])
    expect([next.min, next.max]).toEqual([10, 15])
    const arrived = torqueWindow({ ...source, cursor: 25 })
    expect(arrived.max).toBe(25)
    expect(arrived.scraper.at(-1)).toBe(9)
    expect(torqueWindow({ ...source, cursor: 70 }).t).toEqual([25])
  })

  it('每秒两点时 50 点铺满实际时间范围，不额外留出 50 秒空窗', () => {
    const t = Array.from({ length: 50 }, (_, i) => 100 + Math.floor(i / 2))
    const window = torqueWindow({ t, scraper: t, platform: t, cursor: 124.8 })
    expect(window.t).toHaveLength(50)
    expect(window.min).toBe(100)
    expect(window.max).toBe(124)
  })

  it('回跳立即切换窗口；空序列和同秒采样有有效坐标范围', () => {
    const source = { t: [100, 100, 105], scraper: [1, 2, 3], platform: [4, 5, 6] }
    expect(torqueWindow({ ...source, cursor: 102 }).t).toEqual([100, 100])
    expect(torqueWindow({ ...source, cursor: 99 }).t).toEqual([])
    const empty = torqueWindow({ t: [], scraper: [], platform: [] })
    expect(empty.max).toBeGreaterThan(empty.min)
    const same = torqueWindow({ t: [1, 1], scraper: [0, 1], platform: [0, 2] })
    expect(same.max).toBeGreaterThan(same.min)
  })

  it('溯源独立保留 40 层，新层到达移出最旧层，不连接未来结果或早期区段', () => {
    const rows = Array.from({ length: 120 }, (_, i) => ({ layer: i + 1 }))
    expect(layerWindow(rows, 100)).toEqual(rows.slice(60, 100))
    expect(layerWindow(rows, 101)).toEqual(rows.slice(61, 101))
    expect(layerWindow(rows, 3)).toEqual(rows.slice(0, 3))
    expect(layerWindow([{ layer: 900 }, { layer: 2500 }], 2500)).toEqual([{ layer: 2500 }])
  })
})
