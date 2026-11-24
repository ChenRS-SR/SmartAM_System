import { replayCaseForDevice } from '../stores/replay'

// 列表仅说明当前工作区实际读取的资源，不提供已废弃的硬件配置入口。
export function deviceSourceRow(device) {
  const row = { id: device.id, name: device.name, serial: device.serial }
  const replay = replayCaseForDevice(device.id)
  if (replay) return {
    ...row, type: '逐层案例', content: `${replay.layerCount} 层 · 图像、识别与溯源结果`,
    location: `backend/replay_cases/${replay.id}.part*.zip`, status: '已配置',
  }
  const corrected = device.mockVideo?.correctedChannels || {}
  const channels = [['camera_ch1', '可见光图像'], ['thermal', '红外图像']]
    .filter(([key]) => corrected[key]?.available && corrected[key].url
      && (corrected[key].media_type === 'image' || corrected[key].frameSequence?.count > 0))
    .map(([, label]) => label)
  const directory = device.mockVideo?.dataDirectory || device.dataDirectory
  if (channels.length) return {
    ...row, type: '预矫正图像', content: channels.join('、'),
    location: `${directory}/mock_video_corrected`, status: channels.length === 2 ? '通道齐全' : '部分通道可用',
  }
  const hasRecords = !!device.realData?.preview_csv || device.parameters?.some(p => p.value != null && p.value !== '--')
  return {
    ...row, type: '设备档案', content: hasRecords ? '设备状态参数与故障记录' : '设备基础信息',
    location: directory || 'slm_device_data/manifest.json', status: hasRecords ? '已配置' : '图像待接入',
  }
}
