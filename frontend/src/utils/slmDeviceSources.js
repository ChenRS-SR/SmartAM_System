import { replayCaseForDevice } from '../stores/replay'

// 与设备工作区使用同一案例映射，不能用旧视频目录判断案例设备是否可用。
export function deviceSourceRow(device) {
  const row = { id: device.id, name: device.name, serial: device.serial }
  const replay = replayCaseForDevice(device.id)
  if (replay) return {
    ...row, type: '逐层案例', content: `${replay.layerCount} 层 · 图像、识别与溯源结果`,
    location: `backend/replay_cases/${replay.id}.part*.zip`, status: '已配置',
  }
  if (device.source === 'real') return {
    ...row, type: '真实采集', content: '可见光、红外与振动计层',
    location: '华科实验台连接设置', status: '硬件连接由采集页确认',
  }
  const channels = Object.values(device.mockVideo?.channels || {})
    .filter(channel => channel.available && channel.url)
    .map(channel => channel.channel)
  const directory = device.mockVideo?.dataDirectory || device.dataDirectory
  return {
    ...row, type: '目录视频', content: channels.length ? channels.join('、') : '未发现可用视频',
    location: directory ? `${directory}/mock_video` : '未配置目录',
    status: channels.length === 3 ? '通道齐全' : channels.length ? '部分通道可用' : '待接入',
  }
}
