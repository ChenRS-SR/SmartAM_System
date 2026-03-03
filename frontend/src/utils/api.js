import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 10000
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
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 打印机控制
export const printerApi = {
  getStatus: () => api.get('/api/printer/status'),
  getTemperature: () => api.get('/api/printer/temperature'),
  getFiles: () => api.get('/api/printer/files'),
  startPrint: (filename, location = 'local') => api.post('/api/printer/print', null, { 
    params: { filename, location },
    paramsSerializer: params => {
      // 确保文件名编码正确
      return `filename=${encodeURIComponent(params.filename)}&location=${params.location}`
    }
  }),
  pauseJob: () => api.post('/api/printer/pause'),
  resumeJob: () => api.post('/api/printer/resume'),
  cancelJob: () => api.post('/api/printer/job/cancel'),
  connect: (port, baudrate) => api.post('/api/printer/connect', { port, baudrate }),
  disconnect: () => api.post('/api/printer/disconnect'),
  home: () => api.post('/api/printer/home'),
  sendCommand: (command) => api.post('/api/printer/command', { command })
}

// 相机控制
export const cameraApi = {
  getStatus: () => api.get('/api/camera/status'),
  snapshot: (type) => api.post(`/api/camera/snapshot/${type}`)
}

// 推理接口
export const inferenceApi = {
  getPrediction: () => api.get('/api/inference/prediction'),
  getStatus: () => api.get('/api/inference/status'),
  setConfig: (config) => api.post('/api/inference/config', config)
}

// 闭环控制
export const controlApi = {
  getStatus: () => api.get('/api/control/status'),
  start: () => api.post('/api/control/start'),
  stop: () => api.post('/api/control/stop'),
  pause: () => api.post('/api/control/pause'),
  setThreshold: (threshold) => api.post('/api/control/threshold', { threshold }),
  manualControl: (params) => api.post('/api/control/manual', params),
  getHistory: (limit = 100) => api.get(`/api/control/history?limit=${limit}`)
}

// 数据管理
export const dataApi = {
  getRecordStatus: () => api.get('/api/data/record/status'),
  startRecord: (directory) => api.post('/api/data/record/start', { directory }),
  stopRecord: () => api.post('/api/data/record/stop')
}

// 系统配置
export const systemApi = {
  getConfig: () => api.get('/api/system/config'),
  saveConfig: (section, config) => api.post(`/api/system/config/${section}`, config),
  reloadModel: () => api.post('/api/system/model/reload'),
  testConnection: () => api.get('/api/system/test')
}

// 设备管理
export const deviceApi = {
  getStatus: () => api.get('/api/device/status'),
  connect: (deviceType) => api.post('/api/device/connect', { device_type: deviceType }),
  connectAll: () => api.post('/api/device/connect-all'),
  disconnectAll: () => api.post('/api/device/disconnect-all'),
  startAcquisition: () => api.post('/api/device/start-acquisition'),
  stopAcquisition: () => api.post('/api/device/stop-acquisition')
}

// 扩展 printerApi
printerApi.getFiles = () => api.get('/api/printer/files')
printerApi.startPrint = (file) => api.post('/api/printer/print/start', { file })
printerApi.pausePrint = () => api.post('/api/printer/print/pause')
printerApi.cancelPrint = () => api.post('/api/printer/print/cancel')
printerApi.emergencyStop = () => api.post('/api/printer/emergency')
printerApi.testConnection = () => api.get('/api/printer/test')

// 扩展 controlApi
controlApi.updateConfig = (config) => api.post('/api/control/config', config)
controlApi.addPrediction = (cls, confidence) => api.post('/api/control/prediction', { class: cls, confidence })
controlApi.calculateAdjustment = () => api.get('/api/control/calculate')
controlApi.clearHistory = () => api.post('/api/control/history/clear')

export default api
