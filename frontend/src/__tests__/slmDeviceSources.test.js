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
  it('设备档案不再指向废弃的硬件设置入口', () => {
    const row = deviceSourceRow({ id: 'huake-real', name: '华科 CRPBFM130', source: 'real', parameters:[{value:10}] })
    expect(row.type).toBe('设备档案')
    expect(row.status).toBe('已配置')
    expect(row.location).not.toContain('连接设置')
  })
  it('仅报告工作区可展示的预矫正图像，不将原视频或侧轴计为可用通道', () => {
    const device = { id: 'directory', dataDirectory: 'devices/directory' }
    expect(deviceSourceRow(device).status).toBe('图像待接入')
    device.mockVideo = { channels: {camera_ch1:{available:true,url:'/raw.mp4'}}, correctedChannels: {
      camera_ch1: { available: true, url: '/one.mp4', media_type:'video' },
      camera_ch2: { available: true, url: '/side.png', media_type:'image' },
    } }
    expect(deviceSourceRow(device).type).toBe('设备档案')
    device.mockVideo.correctedChannels.camera_ch1.frameSequence={count:12}
    expect(deviceSourceRow(device)).toMatchObject({type:'预矫正图像', content:'可见光图像', status:'部分通道可用'})
    device.mockVideo.correctedChannels.thermal={available:true,url:'/thermal.jpg',media_type:'image'}
    expect(deviceSourceRow(device).status).toBe('通道齐全')
  })
})
