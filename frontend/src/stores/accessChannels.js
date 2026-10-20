import { reactive } from 'vue'
import { defineStore } from 'pinia'

// 仅控制接入页展示；按设备/案例保存，不改变采集原始数据或识别模型输入。
export const useAccessChannels = defineStore('accessChannels', () => {
  const preferences = reactive({})
  function forDevice(key) {
    if (!preferences[key]) {
      const saved = localStorage.getItem(`smartam-access-channels:${key}`)
      preferences[key] = saved ? JSON.parse(saved) : {}
    }
    return preferences[key]
  }
  function setVisible(key, names, visible) {
    const selected = forDevice(key)
    for (const name of names) selected[name] = visible
    localStorage.setItem(`smartam-access-channels:${key}`, JSON.stringify(selected))
  }
  return { forDevice, setVisible }
})
