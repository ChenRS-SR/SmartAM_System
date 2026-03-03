/**
 * API 测试工具
 * 用于测试后端 API 和 WebSocket 连接
 */

import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 测试结果类型
export const TestResult = {
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
  SKIPPED: 'skipped'
}

// API 测试类
export class APITester {
  constructor() {
    this.results = []
    this.wsConnection = null
  }

  // 添加测试结果
  addResult(name, status, message, details = null) {
    const result = {
      id: Date.now() + Math.random(),
      name,
      status,
      message,
      details,
      timestamp: new Date().toISOString()
    }
    this.results.push(result)
    return result
  }

  // 清空结果
  clearResults() {
    this.results = []
  }

  // 测试根路径
  async testRoot() {
    try {
      const response = await axios.get(`${API_BASE_URL}/`, { timeout: 5000 })
      return this.addResult(
        '根路径访问',
        TestResult.SUCCESS,
        '后端服务运行正常',
        { status: response.status, data: response.data }
      )
    } catch (error) {
      return this.addResult(
        '根路径访问',
        TestResult.ERROR,
        '无法连接到后端服务',
        { error: error.message }
      )
    }
  }

  // 测试打印机 API
  async testPrinterAPI() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/printer/status`, { timeout: 5000 })
      return this.addResult(
        '打印机状态 API',
        TestResult.SUCCESS,
        '打印机接口正常',
        { status: response.status, state: response.data?.state }
      )
    } catch (error) {
      const status = error.response?.status
      if (status === 404) {
        return this.addResult(
          '打印机状态 API',
          TestResult.ERROR,
          '接口不存在 (404)',
          { error: error.message }
        )
      }
      return this.addResult(
        '打印机状态 API',
        TestResult.ERROR,
        '接口访问失败',
        { status, error: error.message }
      )
    }
  }

  // 测试相机 API
  async testCameraAPI() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/camera/status`, { timeout: 5000 })
      return this.addResult(
        '相机状态 API',
        TestResult.SUCCESS,
        '相机接口正常',
        { status: response.status, data: response.data }
      )
    } catch (error) {
      return this.addResult(
        '相机状态 API',
        TestResult.ERROR,
        '接口访问失败',
        { error: error.message }
      )
    }
  }

  // 测试推理 API
  async testInferenceAPI() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/inference/status`, { timeout: 5000 })
      return this.addResult(
        '推理服务 API',
        TestResult.SUCCESS,
        '推理接口正常',
        { status: response.status, data: response.data }
      )
    } catch (error) {
      return this.addResult(
        '推理服务 API',
        TestResult.ERROR,
        '接口访问失败',
        { error: error.message }
      )
    }
  }

  // 测试闭环控制 API
  async testControlAPI() {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/control/status`, { timeout: 5000 })
      return this.addResult(
        '闭环控制 API',
        TestResult.SUCCESS,
        '控制接口正常',
        { status: response.status, data: response.data }
      )
    } catch (error) {
      return this.addResult(
        '闭环控制 API',
        TestResult.ERROR,
        '接口访问失败',
        { error: error.message }
      )
    }
  }

  // 测试视频流
  async testVideoFeed() {
    try {
      const response = await axios.get(`${API_BASE_URL}/video_feed`, { 
        timeout: 5000,
        responseType: 'blob'
      })
      const contentType = response.headers['content-type']
      if (contentType && contentType.includes('multipart')) {
        return this.addResult(
          '视频流 (MJPEG)',
          TestResult.SUCCESS,
          '视频流正常',
          { contentType, size: response.data?.size }
        )
      }
      return this.addResult(
        '视频流 (MJPEG)',
        TestResult.WARNING,
        '响应正常但内容类型异常',
        { contentType }
      )
    } catch (error) {
      return this.addResult(
        '视频流 (MJPEG)',
        TestResult.ERROR,
        '无法访问视频流',
        { error: error.message }
      )
    }
  }

  // 测试 WebSocket
  testWebSocket() {
    return new Promise((resolve) => {
      const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws/sensor_data'
      
      try {
        const ws = new WebSocket(wsUrl)
        const timeout = setTimeout(() => {
          ws.close()
          resolve(this.addResult(
            'WebSocket 连接',
            TestResult.ERROR,
            '连接超时 (5s)',
            { url: wsUrl }
          ))
        }, 5000)

        ws.onopen = () => {
          clearTimeout(timeout)
          ws.close()
          resolve(this.addResult(
            'WebSocket 连接',
            TestResult.SUCCESS,
            'WebSocket 连接正常',
            { url: wsUrl }
          ))
        }

        ws.onerror = (error) => {
          clearTimeout(timeout)
          resolve(this.addResult(
            'WebSocket 连接',
            TestResult.ERROR,
            'WebSocket 连接失败',
            { url: wsUrl, error: 'Connection error' }
          ))
        }
      } catch (error) {
        resolve(this.addResult(
          'WebSocket 连接',
          TestResult.ERROR,
          'WebSocket 初始化失败',
          { error: error.message }
        ))
      }
    })
  }

  // 运行所有测试
  async runAllTests() {
    this.clearResults()
    
    // 顺序执行测试
    await this.testRoot()
    await this.testPrinterAPI()
    await this.testCameraAPI()
    await this.testInferenceAPI()
    await this.testControlAPI()
    await this.testVideoFeed()
    await this.testWebSocket()
    
    return this.getSummary()
  }

  // 获取测试摘要
  getSummary() {
    const total = this.results.length
    const success = this.results.filter(r => r.status === TestResult.SUCCESS).length
    const warning = this.results.filter(r => r.status === TestResult.WARNING).length
    const error = this.results.filter(r => r.status === TestResult.ERROR).length
    
    return {
      total,
      success,
      warning,
      error,
      passRate: total > 0 ? ((success / total) * 100).toFixed(1) : 0,
      allPassed: error === 0 && total > 0
    }
  }

  // 获取所有结果
  getResults() {
    return this.results
  }
}

// 创建单例
export const apiTester = new APITester()

// 快速测试函数
export async function quickTest() {
  return await apiTester.runAllTests()
}

export default apiTester
