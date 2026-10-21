import { afterEach, describe, expect, it, vi } from 'vitest'
import { resolveBackendWebSocketUrl } from '../utils/backendBase'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('实时连接随当前访问地址变化', () => {
  it.each([
    ['http://localhost:8000', 'ws://localhost:8000/api/slm/ws/data'],
    ['http://192.168.5.135:8000', 'ws://192.168.5.135:8000/api/slm/ws/data'],
    ['http://192.168.5.135:5173', 'ws://192.168.5.135:5173/api/slm/ws/data'],
    ['https://preview.example:9443', 'wss://preview.example:9443/api/slm/ws/data'],
    ['http://[::1]:8000', 'ws://[::1]:8000/api/slm/ws/data'],
  ])('保留 %s 的主机、端口并匹配协议', (origin, expected) => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    vi.stubGlobal('window', { location: { origin } })
    expect(resolveBackendWebSocketUrl('/api/slm/ws/data')).toBe(expected)
  })

  it('显式后端配置与 HTTP 接口保持一致', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://backend.example:8443/gateway/')
    vi.stubGlobal('window', { location: { origin: 'http://localhost:5173' } })
    expect(resolveBackendWebSocketUrl('/ws')).toBe('wss://backend.example:8443/gateway/ws')
  })
})
