/**
 * API 模块（支持模拟模式）
 * ======================
 * 当后端不可用时，自动使用模拟数据
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'
import {
  mockPrinterStatus,
  mockTemperatureHistory,
  mockDeviceStatus,
  mockCameraStatus,
  mockPrediction,
  mockControlStatus,
  mockSystemStatus,
  mockFiles,
  mockHealth,
  generateMockTemperature,
  generateMockPosition,
  generateMockWebSocketData,
  mockDelay
} from './mockData'

// 是否启用模拟模式
const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true' || false

// 创建 axios 实例
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 5000
})

// 后端可用性检测
let backendAvailable = null

async function checkBackend() {
  if (backendAvailable !== null) return backendAvailable
  
  try {
    await axios.get('http://localhost:8000/', { timeout: 2000 })
    backendAvailable = true
    console.log('[API] 后端连接成功，使用真实数据')
    return true
  } catch (e) {
    backendAvailable = false
    console.log('[API] 后端未启动，切换到模拟模式')
    return false
  }
}

// 创建模拟响应
function createMockResponse(data) {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: {},
    mock: true
  }
}

// 包装 API 调用，支持自动回退到模拟
async function apiCallWithMock(realCall, mockData, delay = 300) {
  // 如果强制启用模拟模式
  if (MOCK_MODE) {
    await mockDelay(delay)
    return createMockResponse(mockData)
  }
  
  // 检测后端是否可用
  const hasBackend = await checkBackend()
  
  if (hasBackend) {
    try {
      return await realCall()
    } catch (error) {
      // 后端出错时也回退到模拟
      console.warn('[API] 后端请求失败，使用模拟数据:', error.message)
      await mockDelay(delay)
      return createMockResponse(mockData)
    }
  } else {
    // 无后端，使用模拟数据
    await mockDelay(delay)
    return createMockResponse(mockData)
  }
}

// ========== 打印机 API ==========
export const printerApi = {
  getStatus: () => apiCallWithMock(
    () => api.get('/api/printer/status'),
    mockPrinterStatus
  ),
  
  getTemperature: () => apiCallWithMock(
    () => api.get('/api/printer/temperature'),
    generateMockTemperature()
  ),
  
  getFiles: () => apiCallWithMock(
    () => api.get('/api/printer/files'),
    mockFiles
  ),
  
  testConnection: () => apiCallWithMock(
    () => api.get('/api/printer/test'),
    { success: true, simulation: true, message: '前端模拟模式' }
  ),
  
  // 以下命令类操作返回成功但不实际执行
  startPrint: (filename, location = 'local') => apiCallWithMock(
    () => api.post('/api/printer/print', null, { params: { filename, location } }),
    { success: true, message: `模拟开始打印: ${filename}` }
  ),
  
  pauseJob: () => apiCallWithMock(
    () => api.post('/api/printer/pause'),
    { success: true, message: '模拟暂停' }
  ),
  
  resumeJob: () => apiCallWithMock(
    () => api.post('/api/printer/resume'),
    { success: true, message: '模拟恢复' }
  ),
  
  cancelJob: () => apiCallWithMock(
    () => api.post('/api/printer/job/cancel'),
    { success: true, message: '模拟取消' }
  ),
  
  sendCommand: (command) => apiCallWithMock(
    () => api.post('/api/printer/command', { command }),
    { success: true, message: `模拟发送命令: ${command}` }
  ),
  
  pausePrint: () => apiCallWithMock(
    () => api.post('/api/printer/pause'),
    { success: true, message: '模拟暂停打印' }
  ),
  
  cancelPrint: () => apiCallWithMock(
    () => api.post('/api/printer/print/cancel'),
    { success: true, message: '模拟取消打印' }
  ),
  
  emergencyStop: () => apiCallWithMock(
    () => api.post('/api/printer/emergency'),
    { success: true, message: '模拟紧急停止' }
  )
}

// ========== 相机 API ==========
export const cameraApi = {
  getStatus: () => apiCallWithMock(
    () => api.get('/api/camera/status'),
    mockCameraStatus
  ),
  
  snapshot: (type) => apiCallWithMock(
    () => api.post(`/api/camera/snapshot/${type}`),
    { success: true, message: `模拟拍照: ${type}` }
  )
}

// ========== 设备 API ==========
export const deviceApi = {
  getStatus: () => apiCallWithMock(
    () => api.get('/api/device/status'),
    mockDeviceStatus
  ),
  
  connect: (deviceType) => apiCallWithMock(
    () => api.post('/api/device/connect', { device_type: deviceType }),
    { success: true, message: `模拟连接设备: ${deviceType}` }
  ),
  
  connectAll: () => apiCallWithMock(
    () => api.post('/api/device/connect-all'),
    { success: true, message: '模拟连接所有设备', results: { ids: true, side_camera: true, fotric: true, m114: true } }
  ),
  
  disconnectAll: () => apiCallWithMock(
    () => api.post('/api/device/disconnect-all'),
    { success: true, message: '模拟断开所有设备' }
  ),
  
  startAcquisition: () => apiCallWithMock(
    () => api.post('/api/device/start-acquisition'),
    { success: true, message: '模拟启动采集', status: 'running' }
  ),
  
  stopAcquisition: () => apiCallWithMock(
    () => api.post('/api/device/stop-acquisition'),
    { success: true, message: '模拟停止采集', status: 'stopped' }
  )
}

// ========== 推理 API ==========
export const inferenceApi = {
  getPrediction: () => apiCallWithMock(
    () => api.get('/api/inference/prediction'),
    mockPrediction
  ),
  
  getStatus: () => apiCallWithMock(
    () => api.get('/api/inference/status'),
    { loaded: true, model: 'PacNet (Mock)', device: 'cpu' }
  ),
  
  setConfig: (config) => apiCallWithMock(
    () => api.post('/api/inference/config', config),
    { success: true, config }
  )
}

// ========== 控制 API ==========
export const controlApi = {
  getStatus: () => apiCallWithMock(
    () => api.get('/api/control/status'),
    mockControlStatus
  ),
  
  start: () => apiCallWithMock(
    () => api.post('/api/control/start'),
    { success: true, message: '模拟启动闭环控制', status: 'monitoring' }
  ),
  
  stop: () => apiCallWithMock(
    () => api.post('/api/control/stop'),
    { success: true, message: '模拟停止闭环控制', status: 'idle' }
  ),
  
  pause: () => apiCallWithMock(
    () => api.post('/api/control/pause'),
    { success: true, message: '模拟暂停' }
  ),
  
  setThreshold: (threshold) => apiCallWithMock(
    () => api.post('/api/control/threshold', { threshold }),
    { success: true, threshold }
  ),
  
  manualControl: (params) => apiCallWithMock(
    () => api.post('/api/control/manual', params),
    { success: true, message: '模拟手动控制', params }
  ),
  
  getHistory: (limit = 100) => apiCallWithMock(
    () => api.get(`/api/control/history?limit=${limit}`),
    { history: [], count: 0 }
  ),
  
  updateConfig: (config) => apiCallWithMock(
    () => api.post('/api/control/config', config),
    { success: true, config }
  ),
  
  addPrediction: (cls, confidence) => apiCallWithMock(
    () => api.post('/api/control/prediction', { class: cls, confidence }),
    { success: true }
  ),
  
  calculateAdjustment: () => apiCallWithMock(
    () => api.get('/api/control/calculate'),
    { adjustment: null, should_regulate: false }
  ),
  
  clearHistory: () => apiCallWithMock(
    () => api.post('/api/control/history/clear'),
    { success: true }
  )
}

// ========== 数据 API ==========
export const dataApi = {
  getRecordStatus: () => apiCallWithMock(
    () => api.get('/api/data/record/status'),
    { recording: false, frame_count: 0, save_directory: '' }
  ),
  
  startRecord: (directory) => apiCallWithMock(
    () => api.post('/api/data/record/start', { directory }),
    { success: true, message: '模拟开始录制', directory: directory || 'data/mock_session' }
  ),
  
  stopRecord: () => apiCallWithMock(
    () => api.post('/api/data/record/stop'),
    { success: true, message: '模拟停止录制' }
  )
}

// ========== 系统 API ==========
export const systemApi = {
  getConfig: () => apiCallWithMock(
    () => api.get('/api/system/config'),
    { 
      octoprint: { url: 'http://localhost:5000' },
      camera: { ids: { enabled: true }, side: { enabled: true } },
      inference: { model: 'PacNet', device: 'cpu' }
    }
  ),
  
  saveConfig: (section, config) => apiCallWithMock(
    () => api.post(`/api/system/config/${section}`, config),
    { success: true, section, config }
  ),
  
  reloadModel: () => apiCallWithMock(
    () => api.post('/api/system/model/reload'),
    { success: true, message: '模拟重新加载模型' }
  ),
  
  testConnection: () => apiCallWithMock(
    () => api.get('/api/system/test'),
    { success: true, message: '前端模拟模式运行中' }
  )
}

// ========== 健康检查 ==========
export const healthApi = {
  check: () => apiCallWithMock(
    () => api.get('/api/health'),
    mockHealth
  )
}

// ========== WebSocket 模拟 ==========
export function createMockWebSocket(url, onMessage) {
  console.log('[WebSocket] 使用模拟模式:', url)
  
  const interval = setInterval(() => {
    if (onMessage) {
      onMessage(generateMockWebSocketData())
    }
  }, 1000) // 每秒发送一次模拟数据
  
  return {
    close: () => {
      clearInterval(interval)
      console.log('[WebSocket] 模拟连接已关闭')
    },
    send: (data) => {
      console.log('[WebSocket] 模拟发送:', data)
    },
    mock: true
  }
}

// 导出配置
export { MOCK_MODE, checkBackend, backendAvailable }

export default {
  printer: printerApi,
  camera: cameraApi,
  device: deviceApi,
  inference: inferenceApi,
  control: controlApi,
  data: dataApi,
  system: systemApi,
  health: healthApi
}
