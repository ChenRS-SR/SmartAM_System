import { describe, expect, it } from 'vitest'
import { deviceSourceRow } from '../utils/slmDeviceSources'
import { REPLAY_CASES } from '../stores/replay'

describe('设备数据源列表', () => {
  it.each(REPLAY_CASES)('$name 不因缺少旧视频目录而显示未接入', entry => {
    const row = deviceSourceRow({ id: entry.deviceId, name: entry.name })
    expect(row.type).toBe('逐层案例')
    expect(row.status).toBe('已配置')
    expect(row.content).toContain(`${entry.layerCount} 层`)
  })
  it('同名真实采集设备与案例设备分开，配置不等于硬件已连接', () => {
    const row = deviceSourceRow({ id: 'huake-real', name: '华科 CRPBFM130', source: 'real' })
    expect(row.type).toBe('真实采集')
    expect(row.status).toBe('硬件连接由采集页确认')
  })
  it('目录视频按实际可用通道显示状态', () => {
    const device = { id: 'directory', dataDirectory: 'devices/directory' }
    expect(deviceSourceRow(device).status).toBe('待接入')
    device.mockVideo = { channels: {
      camera_ch1: { available: true, url: '/one.mp4', channel: 'CH1' },
      thermal: { available: false, channel: 'CH3' },
    } }
    expect(deviceSourceRow(device)).toMatchObject({ content: 'CH1', status: '部分通道可用' })
  })
})
