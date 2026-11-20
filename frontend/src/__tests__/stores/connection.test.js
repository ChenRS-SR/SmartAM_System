import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDataStore } from '../../stores/data'
import { generateMockWebSocketData } from '../../utils/mockData'
vi.mock('element-plus', () => ({ ElNotification: vi.fn() }))
vi.mock('../../utils/api', () => ({ FORCE_MOCK: false }))
vi.mock('../../utils/mockData', () => ({ generateMockWebSocketData: vi.fn(() => ({ printer: { state: 'Printing' } })) }))
let sockets
beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  sockets = []
  setActivePinia(createPinia())
  vi.stubGlobal('WebSocket', class {
    constructor() { sockets.push(this) }
    close() { this.onclose?.() }
  })
})
afterEach(() => { vi.clearAllTimers(); vi.useRealTimers(); vi.unstubAllGlobals() })
describe('演示数据通道生命周期', () => {
  it('连接失败自动接续模拟数据，并保持采集状态', async () => {
    const store = useDataStore()
    store.connectWebSocket()
    sockets[0].onerror()
    expect(store.connected).toBe(true)
    expect(store.sensorData.printer.state).toBe('Printing')
    await vi.advanceTimersByTimeAsync(3000)
    expect(generateMockWebSocketData).toHaveBeenCalledTimes(4)
    expect(sockets).toHaveLength(1)
    store.disconnectWebSocket()
  })
  it('正常连接中断也切换模拟，重复事件和进入页面只保留一条数据流', async () => {
    const store = useDataStore()
    store.connectWebSocket()
    sockets[0].onopen()
    sockets[0].onclose()
    sockets[0].onclose()
    store.connectWebSocket()
    await vi.advanceTimersByTimeAsync(1000)
    expect(generateMockWebSocketData).toHaveBeenCalledTimes(2)
    expect(sockets).toHaveLength(1)
    store.disconnectWebSocket()
    await vi.advanceTimersByTimeAsync(10000)
    expect(generateMockWebSocketData).toHaveBeenCalledTimes(2)
    expect(store.connected).toBe(false)
  })
  it('主动断开不启动模拟，仍允许下一次重新连接', () => {
    const store = useDataStore()
    store.connectWebSocket()
    store.connectWebSocket()
    expect(sockets).toHaveLength(1)
    store.disconnectWebSocket()
    expect(generateMockWebSocketData).not.toHaveBeenCalled()
    store.connectWebSocket()
    expect(sockets).toHaveLength(2)
    store.disconnectWebSocket()
  })
})
