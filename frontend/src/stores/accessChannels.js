import { reactive } from 'vue'
import { defineStore } from 'pinia'

// 默认仅展开两路可见光图像；扭矩和设备状态继续显示。
const hiddenByDefault = new Set(['铺粉后红外图像', '熔化后红外图像', '可见光图像', '红外图像'])

// 新版默认关闭扩展图像通道；使用独立版本避免旧的全部显示设置覆盖默认值。
// 仅控制接入页展示；按设备/案例保存，不改变采集原始数据或识别模型输入。
export const useAccessChannels = defineStore('accessChannels', () => {
  const preferences = reactive({})
  function forDevice(key) {
    if (!preferences[key]) {
      const saved = localStorage.getItem(`smartam-access-channels:v2:${key}`)
      preferences[key] = saved ? JSON.parse(saved) : {}
    }
    return preferences[key]
  }
  function isVisible(key, name) {
    return forDevice(key)[name] ?? !hiddenByDefault.has(name)
  }
  function setVisible(key, names, visible) {
    const selected = forDevice(key)
    for (const name of names) selected[name] = visible
    localStorage.setItem(`smartam-access-channels:v2:${key}`, JSON.stringify(selected))
  }
  return { forDevice, isVisible, setVisible }
})
