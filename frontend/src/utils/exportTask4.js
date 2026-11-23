import { task4Api } from './task4Api'

// 浏览器之间的播放游标独立；导出时一次性固定当前游标，四个接口共用它。
export async function readCurrentTask4(deviceId, frame, options = {}) {
  if (!Number.isFinite(frame?.offset)) throw new Error('当前设备尚无可导出的播放快照')
  const selected = { deviceId, offset:frame.offset, layerNo:frame.layer,
    processingMode:frame.processing?.real ? 'real' : 'archive' }
  const [recognition, control, equipment, maintenance] = await Promise.all([
    task4Api('defect-recognition', {...selected, resultScope:'display'}),
    task4Api('quality-control', {...selected, ...options}),
    task4Api('equipment-diagnosis', {deviceIds:[deviceId], offset:selected.offset, processingMode:selected.processingMode, resultScope:'display'}),
    task4Api('maintenance-statistics', {deviceIds:[deviceId]})
  ])
  return {exportedAt:new Date().toISOString(), selection:selected, recognition, control, equipment, maintenance}
}

export function downloadTask4(data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json;charset=utf-8'})
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${data.selection.deviceId}-layer-${data.selection.layerNo}.json`
  link.click()
  // 给浏览器下载事件留出消费 Blob URL 的时间。
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
