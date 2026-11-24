// 各通道共用进入设备后的时间轴；循环只更新图像，不改模型结果或层号。
export function updateMonitorFrames(images, elapsedMs) {
  for (const image of Object.values(images || {})) {
    const sequence = image.frameSequence
    if (!sequence) continue
    const index = Math.floor(elapsedMs / sequence.intervalMs) % sequence.count + 1
    image.url = `${sequence.baseUrl}/${String(index).padStart(6, '0')}.jpg`
  }
}
