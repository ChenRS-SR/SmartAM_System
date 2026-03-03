import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { ElNotification } from 'element-plus'

// 通知辅助函数
const notify = (options) => {
  ElNotification({
    position: 'top-right',
    duration: 4000,
    ...options
  })
}

export const useDataStore = defineStore('data', () => {
  // ============ State ============
  const ws = ref(null)
  const connected = ref(false)
  const connecting = ref(false)
  
  // 传感器数据（包含默认值）
  const sensorData = ref({
    printer: null,
    thermal: null,
    camera: null,
    acquisition: {
      state: 'idle',
      frame_count: 0,
      duration: 0,
      fps: 0,
      current_params: {
        flow_rate: 0,
        feed_rate: 0,
        z_offset: 0,
        target_hotend: 0
      },
      current_z: 0,
      param_mode: 'fixed'
    }
  })
  const prediction = ref({})
  
  // 历史数据
  const historyData = ref({
    timestamps: [],
    nozzleTemps: [],
    bedTemps: [],
    nozzleTargetTemps: [],  // 喷嘴目标温度
    bedTargetTemps: [],     // 热床目标温度
    meltPoolTemps: [],
    flowRateClasses: [],
    feedRateClasses: [],
    zOffsetClasses: [],
    hotendClasses: []
  })
  
  // 闭环控制状态
  const closedLoopStatus = ref({
    status: 'idle',
    windowSize: 0,
    regulationCount: 0
  })
  
  // 告警列表
  const alerts = ref([])
  
  // 最新数据（聚合）
  const latestData = computed(() => ({
    printer: sensorData.value.printer || {
      state: 'Unknown',
      progress: 0,
      filename: '',
      print_time: 0,
      print_time_left: 0,
      temperature: { nozzle: 0, bed: 0 },
      position: { x: 0, y: 0, z: 0 }
    },
    thermal: sensorData.value.thermal || {
      nozzle_temp: 0,
      melt_pool_max: 0
    },
    camera: sensorData.value.camera || {
      ids_available: false,
      ids_frame_count: 0,
      side_available: false,
      thermal_available: false
    },
    acquisition: sensorData.value.acquisition || {
      state: 'idle',
      frame_count: 0,
      current_z: 0
    },
    prediction: prediction.value
  }))
  
  // ============ Actions ============
  
  function connectWebSocket() {
    if (ws.value || connecting.value) return
    
    connecting.value = true
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//localhost:8000/ws/sensor_data`
    
    ws.value = new WebSocket(wsUrl)
    
    ws.value.onopen = () => {
      connected.value = true
      connecting.value = false
      console.log('WebSocket 连接成功')
      notify({
        type: 'success',
        title: '系统已连接',
        message: '实时数据流已建立',
        duration: 2000
      })
    }
    
    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleWebSocketData(data)
      } catch (e) {
        console.error('WebSocket 数据解析失败:', e)
      }
    }
    
    ws.value.onclose = () => {
      const wasConnected = connected.value
      connected.value = false
      connecting.value = false
      ws.value = null
      if (wasConnected) {
        notify({
          type: 'warning',
          title: '连接已断开',
          message: '正在尝试重新连接...',
          duration: 3000
        })
      }
      // 3秒后重连
      setTimeout(connectWebSocket, 3000)
    }
    
    ws.value.onerror = (error) => {
      console.error('WebSocket 错误:', error)
      ws.value?.close()
    }
  }
  
  function disconnectWebSocket() {
    ws.value?.close()
    ws.value = null
    connected.value = false
  }
  
  function handleWebSocketData(data) {
    // 调试输出（每3秒一次）
    const now = Date.now()
    if (!window._lastWsLog || now - window._lastWsLog > 3000) {
      console.log('[WebSocket] Received data:', {
        hasPrinter: !!data.printer,
        hasAcquisition: !!data.acquisition,
        acqState: data.acquisition?.state,
        acqZ: data.acquisition?.current_z,
        acqParams: data.acquisition?.current_params,
        printerZ: data.printer?.position?.z,
        sensorDataAcq: sensorData.value.acquisition?.state
      })
      window._lastWsLog = now
    }
    
    // 更新传感器数据 - 使用 Object.assign 确保响应式更新
    if (data.printer) {
      sensorData.value.printer = { ...sensorData.value.printer, ...data.printer }
    }
    if (data.thermal) {
      sensorData.value.thermal = { ...sensorData.value.thermal, ...data.thermal }
    }
    if (data.camera) {
      sensorData.value.camera = { ...sensorData.value.camera, ...data.camera }
    }
    if (data.acquisition) {
      // 重要：确保 acquisition 对象完全替换，触发响应式更新
      sensorData.value.acquisition = { 
        state: data.acquisition.state || 'idle',
        frame_count: data.acquisition.frame_count || 0,
        duration: data.acquisition.duration || 0,
        fps: data.acquisition.fps || 0,
        save_directory: data.acquisition.save_directory || '',
        current_params: data.acquisition.current_params || {},
        current_z: data.acquisition.current_z || 0,
        param_mode: data.acquisition.param_mode || 'fixed',
        current_segment: data.acquisition.current_segment || null
      }
    }
    
    // 更新预测
    if (data.prediction) {
      prediction.value = data.prediction
      updateHistory(data)
    }
    
    // 更新闭环状态
    if (data.closed_loop) {
      closedLoopStatus.value = data.closed_loop
    }
    
    // 处理告警
    if (data.alerts) {
      alerts.value = data.alerts
    }
  }
  
  function updateHistory(data) {
    const now = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    
    // 获取熔池温度，如果没有数据则使用 null（图表不会显示）
    const meltPoolTemp = data.thermal?.melt_pool_max
    
    // 获取目标温度（从 printer 数据）
    const nozzleTarget = data.printer?.temperature?.nozzle_target || 0
    const bedTarget = data.printer?.temperature?.bed_target || 0
    
    historyData.value.timestamps.push(now)
    historyData.value.nozzleTemps.push(data.printer?.temperature?.nozzle || 0)
    historyData.value.bedTemps.push(data.printer?.temperature?.bed || 0)
    historyData.value.nozzleTargetTemps.push(nozzleTarget)
    historyData.value.bedTargetTemps.push(bedTarget)
    historyData.value.meltPoolTemps.push(meltPoolTemp > 0 ? meltPoolTemp : null)
    
    // 预测类别映射: Low=-1, Normal=0, High=1
    const labelMap = { 'Low': -1, 'Normal': 0, 'High': 1 }
    
    if (data.prediction) {
      historyData.value.flowRateClasses.push(labelMap[data.prediction.flow_rate_label] || 0)
      historyData.value.feedRateClasses.push(labelMap[data.prediction.feed_rate_label] || 0)
      historyData.value.zOffsetClasses.push(labelMap[data.prediction.z_offset_label] || 0)
      historyData.value.hotendClasses.push(labelMap[data.prediction.hot_end_label] || 0)
    }
    
    // 限制历史数据长度（保存更多点以显示更长时间范围，约30分钟 @ 1秒/点 = 1800点）
    const maxLength = 600  // 10分钟 @ 1秒/点
    if (historyData.value.timestamps.length > maxLength) {
      Object.keys(historyData.value).forEach(key => {
        historyData.value[key] = historyData.value[key].slice(-maxLength)
      })
    }
  }
  
  function clearHistory() {
    historyData.value = {
      timestamps: [],
      nozzleTemps: [],
      bedTemps: [],
      nozzleTargetTemps: [],
      bedTargetTemps: [],
      meltPoolTemps: [],
      flowRateClasses: [],
      feedRateClasses: [],
      zOffsetClasses: [],
      hotendClasses: []
    }
  }
  
  function setClosedLoopStatus(status) {
    closedLoopStatus.value = { ...closedLoopStatus.value, ...status }
  }
  
  function addAlert(alert) {
    alerts.value.unshift({
      id: Date.now(),
      timestamp: new Date().toISOString(),
      ...alert
    })
    // 限制告警数量
    if (alerts.value.length > 50) {
      alerts.value = alerts.value.slice(0, 50)
    }
  }
  
  function dismissAlert(id) {
    alerts.value = alerts.value.filter(a => a.id !== id)
  }
  
  function clearAlerts() {
    alerts.value = []
  }
  
  return {
    // State
    connected,
    sensorData,
    prediction,
    historyData,
    closedLoopStatus,
    alerts,
    latestData,
    
    // Actions
    connectWebSocket,
    disconnectWebSocket,
    clearHistory,
    setClosedLoopStatus,
    addAlert,
    dismissAlert,
    clearAlerts
  }
})
