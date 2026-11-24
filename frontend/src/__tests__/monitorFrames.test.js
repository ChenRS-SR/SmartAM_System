import { describe, it, expect } from 'vitest'
import { updateMonitorFrames } from '../views/slm/workspace/monitorFrames'

describe('监测图像序列', () => {
  it('按同一时间更新两路帧、循环回首帧，静态图片保持原样', () => {
    const images = {
      visible: {frameSequence: {baseUrl:'/visible', count:3, intervalMs:1000}},
      thermal: {frameSequence: {baseUrl:'/thermal', count:3, intervalMs:1000}},
      before: {url:'/layer.jpg'},
    }
    updateMonitorFrames(images, 0)
    expect(images.visible.url).toBe('/visible/000001.jpg')
    updateMonitorFrames(images, 2100)
    expect(images.visible.url).toBe('/visible/000003.jpg')
    expect(images.thermal.url).toBe('/thermal/000003.jpg')
    updateMonitorFrames(images, 3000)
    expect(images.visible.url).toBe('/visible/000001.jpg')
    expect(images.before.url).toBe('/layer.jpg')
  })
})
