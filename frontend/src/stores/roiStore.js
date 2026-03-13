import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useROIStore = defineStore('roi', () => {
  // ROI配置
  const roiConfig = ref({
    rois: {},
    features: ['mean', 'std'],
    update_mode: 'layer'
  })
  
  // 是否在视频上显示ROI区域
  const showROIOnVideo = ref(false)
  
  // 计算属性
  const hasConfig = computed(() => Object.keys(roiConfig.value.rois).length > 0)
  const roiList = computed(() => {
    return Object.entries(roiConfig.value.rois).map(([id, roi]) => ({
      id,
      ...roi
    }))
  })
  
  // 设置ROI配置
  function setROIConfig(config) {
    roiConfig.value = {
      ...roiConfig.value,
      ...config
    }
    // 保存到localStorage
    localStorage.setItem('roi_config', JSON.stringify(roiConfig.value))
  }
  
  // 设置显示开关
  function setShowROIOnVideo(show) {
    showROIOnVideo.value = show
    localStorage.setItem('roi_show_on_video', show ? '1' : '0')
  }
  
  // 从localStorage加载
  function loadFromStorage() {
    const saved = localStorage.getItem('roi_config')
    if (saved) {
      try {
        roiConfig.value = JSON.parse(saved)
      } catch (e) {
        console.error('加载ROI配置失败:', e)
      }
    }
    
    const showSaved = localStorage.getItem('roi_show_on_video')
    if (showSaved !== null) {
      showROIOnVideo.value = showSaved === '1'
    }
  }
  
  // 清除配置
  function clearConfig() {
    roiConfig.value = {
      rois: {},
      features: ['mean', 'std'],
      update_mode: 'layer'
    }
    localStorage.removeItem('roi_config')
  }
  
  return {
    roiConfig,
    showROIOnVideo,
    hasConfig,
    roiList,
    setROIConfig,
    setShowROIOnVideo,
    loadFromStorage,
    clearConfig
  }
})
