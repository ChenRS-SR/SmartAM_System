<template>
  <div class="sls-dashboard">
    <div class="header">
      <h1>SLS 粉末烧结监控系统</h1>
      <el-button @click="backToDeviceSelect">切换设备</el-button>
    </div>
    
    <!-- 状态概览 -->
    <div class="status-cards">
      <el-card class="status-card">
        <template #header>
          <span>采集状态</span>
        </template>
        <div class="status-content">
          <el-tag :type="acquisitionStatus.type">{{ acquisitionStatus.text }}</el-tag>
          <p>当前层数: {{ currentLayer }}</p>
          <p>总周期: {{ totalCycles }}</p>
        </div>
      </el-card>
      
      <el-card class="status-card">
        <template #header>
          <span>振动监测</span>
        </template>
        <div class="status-content">
          <div class="vibration-value" :class="vibrationClass">
            {{ vibrationMagnitude.toFixed(3) }}
          </div>
          <p>检测状态: {{ powderState }}</p>
        </div>
      </el-card>
      
      <el-card class="status-card">
        <template #header>
          <span>设备状态</span>
        </template>
        <div class="device-list">
          <div v-for="(status, name) in deviceStatus" :key="name" class="device-item">
            <span>{{ deviceNames[name] }}:</span>
            <el-tag :type="status.connected ? 'success' : 'danger'" size="small">
              {{ status.connected ? '已连接' : '未连接' }}
            </el-tag>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 控制面板 -->
    <el-card class="control-panel">
      <template #header>
        <span>采集控制</span>
      </template>
      
      <div class="control-row">
        <el-input-number v-model="startLayer" :min="0" label="起始层数" />
        
        <el-button 
          type="primary" 
          @click="startAcquisition" 
          :disabled="isRunning"
          :loading="starting"
        >
          开始采集
        </el-button>
        
        <el-button 
          type="danger" 
          @click="stopAcquisition" 
          :disabled="!isRunning"
        >
          停止采集
        </el-button>
        
        <el-button @click="resetState">重置状态</el-button>
      </div>
      
      <div class="control-row">
        <span>振动阈值:</span>
        <el-slider v-model="threshold" :min="0.01" :max="1" :step="0.01" style="width: 200px" />
        <el-input-number v-model="threshold" :min="0.01" :max="1" :step="0.01" size="small" />
        <el-button size="small" @click="applyThreshold">应用</el-button>
      </div>
      
      <div class="control-row">
        <span>当前层数:</span>
        <el-input-number v-model="currentLayer" :min="0" @change="setLayer" />
      </div>
    </el-card>
    
    <!-- 实时图像 -->
    <el-card class="camera-panel">
      <template #header>
        <span>实时图像</span>
      </template>
      <div class="camera-grid">
        <div class="camera-view">
          <h4>主摄像头 (CH1)</h4>
          <div class="camera-placeholder">摄像头画面</div>
        </div>
        <div class="camera-view">
          <h4>副摄像头 (CH2)</h4>
          <div class="camera-placeholder">摄像头画面</div>
        </div>
        <div class="camera-view">
          <h4>热像仪 (CH3)</h4>
          <div class="camera-placeholder">热像画面</div>
        </div>
      </div>
    </el-card>
    
    <!-- 激光功率闭环调控 -->
    <RegulationControl ref="regulationControl" />
    
    <!-- 日志输出 -->
    <el-card class="log-panel">
      <template #header>
        <span>系统日志</span>
        <el-button size="small" @click="clearLogs">清空</el-button>
      </template>
      <div class="log-content" ref="logContainer">
        <div v-for="(log, index) in logs" :key="index" class="log-line">
          <span class="log-time">{{ log.time }}</span>
          <span :class="['log-level', log.level]">{{ log.level }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import RegulationControl from '../../components/slm/RegulationControl.vue'

const router = useRouter()

// API基础URL
const API_BASE = 'http://localhost:8000/api/sls'

// 状态
const isRunning = ref(false)
const starting = ref(false)
const startLayer = ref(0)
const currentLayer = ref(0)
const totalCycles = ref(0)
const vibrationMagnitude = ref(0)
const powderState = ref('idle')
const threshold = ref(0.05)
const logs = ref([])

// 设备状态
const deviceStatus = ref({
  vibration: { connected: false },
  main_camera: { connected: false },
  secondary_camera: { connected: false },
  thermal: { connected: false }
})

const deviceNames = {
  vibration: '振动传感器',
  main_camera: '主摄像头',
  secondary_camera: '副摄像头',
  thermal: '热像仪'
}

// 计算属性
const acquisitionStatus = computed(() => {
  if (isRunning.value) {
    return { type: 'success', text: '采集中' }
  }
  return { type: 'info', text: '未开始' }
})

const vibrationClass = computed(() => {
  if (vibrationMagnitude.value > threshold.value) {
    return 'high'
  } else if (vibrationMagnitude.value > threshold.value * 0.5) {
    return 'medium'
  }
  return 'low'
})

// 方法
const addLog = (message, level = 'INFO') => {
  const now = new Date()
  const time = now.toLocaleTimeString()
  logs.value.push({ time, level, message })
  // 限制日志数量
  if (logs.value.length > 100) {
    logs.value.shift()
  }
}

const clearLogs = () => {
  logs.value = []
}

const startAcquisition = async () => {
  try {
    starting.value = true
    const response = await axios.post(`${API_BASE}/start`, {
      layer: startLayer.value
    })
    
    if (response.data.success) {
      isRunning.value = true
      currentLayer.value = startLayer.value
      addLog(`采集已启动: ${response.data.message}`, 'SUCCESS')
      ElMessage.success('采集已启动')
    } else {
      addLog(`启动失败: ${response.data.message}`, 'ERROR')
      ElMessage.error(response.data.message)
    }
  } catch (error) {
    addLog(`启动错误: ${error.message}`, 'ERROR')
    ElMessage.error('启动失败')
  } finally {
    starting.value = false
  }
}

const stopAcquisition = async () => {
  try {
    await axios.post(`${API_BASE}/stop`)
    isRunning.value = false
    addLog('采集已停止', 'INFO')
    ElMessage.success('采集已停止')
  } catch (error) {
    addLog(`停止错误: ${error.message}`, 'ERROR')
    ElMessage.error('停止失败')
  }
}

const setLayer = async () => {
  try {
    await axios.post(`${API_BASE}/control/layer`, {
      layer: currentLayer.value
    })
    addLog(`层数设置为: ${currentLayer.value}`, 'INFO')
  } catch (error) {
    addLog(`设置层数错误: ${error.message}`, 'ERROR')
  }
}

const applyThreshold = async () => {
  try {
    await axios.post(`${API_BASE}/control/threshold`, {
      threshold: threshold.value
    })
    addLog(`振动阈值设置为: ${threshold.value}`, 'INFO')
    ElMessage.success('阈值已应用')
  } catch (error) {
    addLog(`设置阈值错误: ${error.message}`, 'ERROR')
  }
}

const backToDeviceSelect = async () => {
  try {
    // 停止当前设备
    await axios.post('/api/device-type/stop')
    // 清除设备类型
    localStorage.removeItem('deviceType')
    // 跳转
    router.push('/')
  } catch (error) {
    console.error('切换设备失败:', error)
    // 即使后端失败，也要跳转
    localStorage.removeItem('deviceType')
    router.push('/')
  }
}

const resetState = async () => {
  try {
    await axios.post(`${API_BASE}/control/reset`)
    addLog('状态机已重置', 'INFO')
    ElMessage.success('状态已重置')
  } catch (error) {
    addLog(`重置错误: ${error.message}`, 'ERROR')
  }
}

// 获取状态
const fetchStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE}/status`)
    const data = response.data
    
    isRunning.value = data.is_running
    currentLayer.value = data.current_layer
    totalCycles.value = data.stats?.total_cycles || 0
    
    if (data.vibration) {
      vibrationMagnitude.value = data.vibration.magnitude || 0
    }
    
    if (data.powder_detector) {
      powderState.value = data.powder_detector.state || 'idle'
    }
  } catch (error) {
    console.error('获取状态失败:', error)
  }
}

// 获取设备状态
const fetchDeviceStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE}/status/devices`)
    deviceStatus.value = response.data
  } catch (error) {
    console.error('获取设备状态失败:', error)
  }
}

// 定时器
let statusTimer = null
let deviceStatusTimer = null

onMounted(() => {
  addLog('SLS Dashboard 已加载', 'INFO')
  fetchStatus()
  fetchDeviceStatus()
  
  // 定时刷新运行状态 (2秒一次，用于振动监测)
  statusTimer = setInterval(() => {
    fetchStatus()
  }, 2000)
  
  // 定时刷新设备状态 (5秒一次，设备连接状态变化较慢)
  deviceStatusTimer = setInterval(() => {
    fetchDeviceStatus()
  }, 5000)
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
  }
  if (deviceStatusTimer) {
    clearInterval(deviceStatusTimer)
  }
})
</script>

<style scoped>
.sls-dashboard {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h1 {
  margin: 0;
}

.status-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.status-card {
  min-height: 150px;
}

.status-content {
  text-align: center;
}

.vibration-value {
  font-size: 48px;
  font-weight: bold;
  margin: 20px 0;
}

.vibration-value.low {
  color: #67c23a;
}

.vibration-value.medium {
  color: #e6a23c;
}

.vibration-value.high {
  color: #f56c6c;
}

.device-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.device-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.control-panel {
  margin-bottom: 20px;
}

.control-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.camera-panel {
  margin-bottom: 20px;
}

.camera-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.camera-view h4 {
  margin-bottom: 10px;
}

.camera-placeholder {
  width: 100%;
  height: 300px;
  background: #1a1a1a;
  border: 1px solid #333;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
}

.log-panel {
  margin-bottom: 20px;
}

.log-content {
  height: 200px;
  overflow-y: auto;
  background: #1a1a1a;
  padding: 10px;
  font-family: monospace;
  font-size: 12px;
}

.log-line {
  margin-bottom: 4px;
}

.log-time {
  color: #888;
  margin-right: 10px;
}

.log-level {
  display: inline-block;
  width: 60px;
  margin-right: 10px;
  font-weight: bold;
}

.log-level.INFO {
  color: #409eff;
}

.log-level.SUCCESS {
  color: #67c23a;
}

.log-level.WARNING {
  color: #e6a23c;
}

.log-level.ERROR {
  color: #f56c6c;
}

.log-message {
  color: #ccc;
}
</style>
