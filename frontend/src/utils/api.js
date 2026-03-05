/**
 * API 统一入口
 * =============
 * 支持真实后端和模拟模式自动切换
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
  mockFiles,
  mockHealth,
  generateMockTemperature,
  generateMockWebSocketData,
  mockDelay
} from './mockData'

// ==================== 配置 ====================

// 是否强制启用模拟模式（环境变量或手动设置）
const FORCE_MOCK = import.meta.env.VITE_MOCK_MODE === 'true' || false

// 是否在后端不可用时自动切换到模拟
const AUTO_MOCK_FALLBACK = true

// 后端地址
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// ==================== 后端检测 ====================

let backendAvailable = null
let checkPromise = null

async function checkBackend() {
  // 如果已检测过，直接返回结果
  if (backendAvailable !== null) return backendAvailable
  
  // 防止重复检测
  if (checkPromise) return checkPromise
  
  checkPromise = (async () => {
    try {
      await axios.get(`${API_BASE_URL}/`, { timeout: 2000 })
      backendAvailable = true
      console.log('[API] ✅ 后端连接成功，使用真实数据')
      return true
    } catch (e) {
      backendAvailable = false
      console.log('[API] ⚠️ 后端未启动，切换到模拟模式')
      return false
    }
  })()
  
  return checkPromise
}

// 重置检测（用于重新连接）
export function resetBackendCheck() {
  backendAvailable = null
  checkPromise = null
}

// ==================== Axios 实例 ====================

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 8000
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 只在非模拟模式下显示错误
    if (!error.config?.mock) {
      const message = error.response?.data?.detail || error.message || '请求失败'
      // 避免重复显示网络错误
      if (!message.includes('Network Error')) {
        ElMessage.error(message)
      }
    }
    return Promise.reject(error)
  }
)

// ==================== 模拟响应包装器 ====================

function createMockResponse(data) {
  return {
    data,
    status: 200,
    statusText: 'OK',
    headers: {},
    config: { mock: true },
    mock: true
  }
}

async function apiWithFallback(apiCall, mockData, delay = 200) {
  // 强制模拟模式
  if (FORCE_MOCK) {
    await mockDelay(delay)
    return createMockResponse(typeof mockData === 'function' ? mockData() : mockData)
  }
  
  // 自动回退模式
  if (AUTO_MOCK_FALLBACK) {
    const hasBackend = await checkBackend()
    
    if (!hasBackend) {
      // 后端不可用，使用模拟
      await mockDelay(delay)
      return createMockResponse(typeof mockData === 'function' ? mockData() : mockData)
    }
  }
  
  // 尝试调用真实 API
  try {
    return await apiCall()
  } catch (error) {
    // 如果配置了自动回退，出错时也使用模拟
    if (AUTO_MOCK_FALLBACK) {
      console.warn('[API] 后端请求失败，使用模拟数据:', error.message)
      await mockDelay(delay)
      return createMockResponse(typeof mockData === 'function' ? mockData() : mockData)
    }
    throw error
  }
}

// ==================== API 定义 ====================

// 打印机控制
export const printerApi = {
  getStatus: () => apiWithFallback(
    () => api.get('/api/printer/status'),
    mockPrinterStatus
  ),
  
  getTemperature: () => apiWithFallback(
    () => api.get('/api/printer/temperature'),
    generateMockTemperature
  ),
  
  getFiles: () => apiWithFallback(
    () => api.get('/api/printer/files'),
    mockFiles
  ),
  
  testConnection: () => apiWithFallback(
    () => api.get('/api/printer/test'),
    { success: true, simulation: true, message: '前端模拟模式运行中' }
  ),
  
  startPrint: (filename, location = 'local') => apiWithFallback(
    () => api.post('/api/printer/print', null, { 
      params: { filename, location },
      paramsSerializer: params => `filename=${encodeURIComponent(params.filename)}&location=${params.location}`
    }),
    { success: true, message: `模拟开始打印: ${filename}` }
  ),
  
  pauseJob: () => apiWithFallback(
    () => api.post('/api/printer/pause'),
    { success: true, message: '模拟暂停打印' }
  ),
  
  resumeJob: () => apiWithFallback(
    () => api.post('/api/printer/resume'),
    { success: true, message: '模拟恢复打印' }
  ),
  
  cancelJob: () => apiWithFallback(
    () => api.post('/api/printer/job/cancel'),
    { success: true, message: '模拟取消打印' }
  ),
  
  sendCommand: (command) => apiWithFallback(
    () => api.post('/api/printer/command', { command }),
    { success: true, message: `模拟发送命令: ${command}` }
  ),
  
  pausePrint: () => apiWithFallback(
    () => api.post('/api/printer/print/pause'),
    { success: true, message: '模拟暂停打印' }
  ),
  
  cancelPrint: () => apiWithFallback(
    () => api.post('/api/printer/print/cancel'),
    { success: true, message: '模拟取消打印' }
  ),
  
  emergencyStop: () => apiWithFallback(
    () => api.post('/api/printer/emergency'),
    { success: true, message: '模拟紧急停止' }
  )
}

// 相机控制
export const cameraApi = {
  getStatus: () => apiWithFallback(
    () => api.get('/api/camera/status'),
    mockCameraStatus
  ),
  
  snapshot: (type) => apiWithFallback(
    () => api.post(`/api/camera/snapshot/${type}`),
    { success: true, message: `模拟拍照: ${type}` }
  )
}

// 设备管理
export const deviceApi = {
  getStatus: () => apiWithFallback(
    () => api.get('/api/device/status'),
    mockDeviceStatus
  ),
  
  connect: (deviceType) => apiWithFallback(
    () => api.post('/api/device/connect', { device_type: deviceType }),
    { success: true, message: `模拟连接设备: ${deviceType}`, device: deviceType, connected: true }
  ),
  
  connectAll: () => apiWithFallback(
    () => api.post('/api/device/connect-all'),
    { success: true, message: '模拟连接所有设备', results: { ids: true, side_camera: true, fotric: true, m114: true } }
  ),
  
  disconnectAll: () => apiWithFallback(
    () => api.post('/api/device/disconnect-all'),
    { success: true, message: '模拟断开所有设备' }
  ),
  
  startAcquisition: () => apiWithFallback(
    () => api.post('/api/device/start-acquisition'),
    { success: true, message: '模拟启动采集', status: 'running' }
  ),
  
  stopAcquisition: () => apiWithFallback(
    () => api.post('/api/device/stop-acquisition'),
    { success: true, message: '模拟停止采集', status: 'stopped' }
  )
}

// 模型推理
export const inferenceApi = {
  getPrediction: () => apiWithFallback(
    () => api.get('/api/inference/prediction'),
    mockPrediction
  ),
  
  getStatus: () => apiWithFallback(
    () => api.get('/api/inference/status'),
    { loaded: true, model: 'PacNet (Mock)', device: 'cpu' }
  ),
  
  setConfig: (config) => apiWithFallback(
    () => api.post('/api/inference/config', config),
    { success: true, config }
  )
}

// 闭环控制
export const controlApi = {
  getStatus: () => apiWithFallback(
    () => api.get('/api/control/status'),
    mockControlStatus
  ),
  
  start: () => apiWithFallback(
    () => api.post('/api/control/start'),
    { success: true, message: '模拟启动闭环控制', status: 'monitoring' }
  ),
  
  stop: () => apiWithFallback(
    () => api.post('/api/control/stop'),
    { success: true, message: '模拟停止闭环控制', status: 'idle' }
  ),
  
  pause: () => apiWithFallback(
    () => api.post('/api/control/pause'),
    { success: true, message: '模拟暂停' }
  ),
  
  setThreshold: (threshold) => apiWithFallback(
    () => api.post('/api/control/threshold', { threshold }),
    { success: true, threshold }
  ),
  
  manualControl: (params) => apiWithFallback(
    () => api.post('/api/control/manual', params),
    { success: true, message: '模拟手动控制', params }
  ),
  
  getHistory: (limit = 100) => apiWithFallback(
    () => api.get(`/api/control/history?limit=${limit}`),
    { history: [], count: 0 }
  ),
  
  updateConfig: (config) => apiWithFallback(
    () => api.post('/api/control/config', config),
    { success: true, config }
  ),
  
  addPrediction: (cls, confidence) => apiWithFallback(
    () => api.post('/api/control/prediction', { class: cls, confidence }),
    { success: true }
  ),
  
  calculateAdjustment: () => apiWithFallback(
    () => api.get('/api/control/calculate'),
    { adjustment: null, should_regulate: false }
  ),
  
  clearHistory: () => apiWithFallback(
    () => api.post('/api/control/history/clear'),
    { success: true }
  )
}

// 数据管理
export const dataApi = {
  getRecordStatus: () => apiWithFallback(
    () => api.get('/api/data/record/status'),
    { recording: false, frame_count: 0, save_directory: '' }
  ),
  
  startRecord: (directory) => apiWithFallback(
    () => api.post('/api/data/record/start', { directory }),
    { success: true, message: '模拟开始录制', directory: directory || 'data/mock_session' }
  ),
  
  stopRecord: () => apiWithFallback(
    () => api.post('/api/data/record/stop'),
    { success: true, message: '模拟停止录制' }
  )
}

// 系统配置
export const systemApi = {
  getConfig: () => apiWithFallback(
    () => api.get('/api/system/config'),
    { 
      octoprint: { url: 'http://localhost:5000' },
      camera: { ids: { enabled: true }, side: { enabled: true } },
      inference: { model: 'PacNet', device: 'cpu' }
    }
  ),
  
  saveConfig: (section, config) => apiWithFallback(
    () => api.post(`/api/system/config/${section}`, config),
    { success: true, section, config }
  ),
  
  reloadModel: () => apiWithFallback(
    () => api.post('/api/system/model/reload'),
    { success: true, message: '模拟重新加载模型' }
  ),
  
  testConnection: () => apiWithFallback(
    () => api.get('/api/system/test'),
    { success: true, message: '前端模拟模式运行中' }
  )
}

// 健康检查
export const healthApi = {
  check: () => apiWithFallback(
    () => api.get('/api/health'),
    mockHealth
  )
}

// ==================== WebSocket 模拟 ====================

export function createWebSocket(url, onMessage, onError) {
  // 如果强制模拟或后端不可用，使用模拟 WebSocket
  if (FORCE_MOCK || backendAvailable === false) {
    console.log('[WebSocket] 使用模拟模式:', url)
    
    const interval = setInterval(() => {
      if (onMessage) {
        onMessage({ data: JSON.stringify(generateMockWebSocketData()) })
      }
    }, 1000)
    
    return {
      close: () => {
        clearInterval(interval)
        console.log('[WebSocket] 模拟连接已关闭')
      },
      send: (data) => {
        console.log('[WebSocket] 模拟发送:', data)
      },
      readyState: 1, // OPEN
      mock: true
    }
  }
  
  // 使用真实 WebSocket
  const ws = new WebSocket(url)
  
  ws.onmessage = onMessage
  ws.onerror = onError
  
  return ws
}

// ==================== 导出 ====================

export { 
  API_BASE_URL, 
  FORCE_MOCK, 
  AUTO_MOCK_FALLBACK,
  checkBackend, 
  backendAvailable 
}

// resetBackendCheck 已在上面导出

export default api
