<template>
  <div class="sls-dashboard">
    <!-- 页面标题 -->
    <div class="dashboard-header">
      <h1 class="page-title">SLS 设备监控仪表盘</h1>
      <div class="header-actions">
        <!-- 模式指示器 -->
        <el-tag 
          :type="settings.use_mock ? 'warning' : 'success'" 
          size="large" 
          effect="dark"
          class="mode-tag"
        >
          {{ settings.use_mock ? '🔶 模拟模式' : '🔷 真实硬件' }}
        </el-tag>
        <el-tag :type="isRunning ? 'success' : 'info'" size="large" effect="dark">
          {{ isRunning ? '采集中' : '已停止' }}
        </el-tag>
        <el-button 
          :type="isRunning ? 'danger' : 'primary'"
          @click="toggleAcquisition"
          :loading="starting"
        >
          {{ isRunning ? '停止采集' : '开始采集' }}
        </el-button>
        <el-button @click="showSettings = true">
          <el-icon><Setting /></el-icon>
          设置
        </el-button>
      </div>
    </div>
    
    <!-- 传感器连接状态 -->
    <SensorConnectionStatus
      :sensor-status="sensorStatus"
      @toggle-sensor="handleToggleSensor"
      @change-com-port="handleChangeComPort"
      @refresh="refreshStatus"
    />
    
    <!-- 实时数据显示 (包含CH1/CH2/红外视频) -->
    <div class="realtime-section">
      <RealTimeDisplay
        :sensor-status="sensorStatus"
        :latest-data="latestData"
        :stream-key="streamKey"
        :display-paused="displayPaused"
        :last-frames="lastFrames"
      />
    </div>
    
    <!-- 舵机控制面板 (SLS特有) -->
    <div class="servo-section">
      <ServoControlPanel
        :is-running="isRunning"
        :servo-status="servoStatus"
        @servo-move="handleServoMove"
        @servo-toggle="handleServoToggle"
      />
    </div>
    
    <!-- 振动波形监测 -->
    <div class="vibration-section">
      <VibrationWaveform 
        :waveform-data="latestData.vibration_waveform"
        :latest-vibration="latestData.vibration"
        :enabled="sensorStatus.vibration?.enabled"
        :connected="sensorStatus.vibration?.connected"
      />
    </div>
    
    <!-- 设备健康状态 -->
    <div class="health-section">
      <EquipmentHealthStatus
        :health-data="healthData"
        :is-running="isRunning"
      />
    </div>
    
    <!-- 振动触发图像采集 -->
    <div class="capture-section">
      <ImageCapturePanel
        :is-running="isRunning"
        :latest-data="latestData"
        @capture-triggered="handleCaptureTriggered"
      />
    </div>
    
    <!-- 设置对话框 -->
    <el-dialog
      v-model="showSettings"
      title="采集设置"
      width="600px"
      destroy-on-close
    >
      <el-form :model="settings" label-width="140px">
        <!-- 摄像头设置 -->
        <el-divider content-position="left">摄像头设置 (USB)</el-divider>
        <el-form-item label="CH1主摄像头">
          <el-select v-model="settings.camera_ch1_index" style="width: 200px" :loading="camerasLoading">
            <el-option
              v-for="cam in availableCameras"
              :key="cam.index"
              :label="`摄像头 ${cam.index} (${cam.resolution?.[0] || '?'}x${cam.resolution?.[1] || '?'})`"
              :value="cam.index"
            />
            <el-option v-if="availableCameras.length === 0 && !camerasLoading" label="未检测到摄像头" :value="-1" disabled />
            <el-option v-if="camerasLoading" label="正在检测..." :value="-1" disabled />
          </el-select>
          <el-button type="primary" size="small" @click="fetchCameras" style="margin-left: 10px" :loading="camerasLoading">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </el-form-item>
        <el-form-item label="CH2副摄像头">
          <el-select v-model="settings.camera_ch2_index" style="width: 200px" :loading="camerasLoading">
            <el-option
              v-for="cam in availableCameras"
              :key="cam.index"
              :label="`摄像头 ${cam.index} (${cam.resolution?.[0] || '?'}x${cam.resolution?.[1] || '?'})`"
              :value="cam.index"
            />
            <el-option v-if="availableCameras.length === 0 && !camerasLoading" label="未检测到摄像头" :value="-1" disabled />
            <el-option v-if="camerasLoading" label="正在检测..." :value="-1" disabled />
          </el-select>
        </el-form-item>
        
        <!-- 红外热像仪 (SLS使用Fotric/IR8062) -->
        <el-divider content-position="left">红外热像仪 (Fotric/IR8062)</el-divider>
        <el-form-item label="热像仪类型">
          <el-radio-group v-model="settings.thermal_type">
            <el-radio label="fotric">Fotric 628CH</el-radio>
            <el-radio label="ir8062">IR8062</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="设备索引">
          <el-input-number v-model="settings.thermal_index" :min="0" :max="10" style="width: 120px" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">
            多设备连接时的设备编号
          </span>
        </el-form-item>
        
        <!-- 振动传感器 -->
        <el-divider content-position="left">振动传感器 (COM口)</el-divider>
        <el-form-item label="COM端口">
          <el-select v-model="settings.vibration_com" style="width: 200px">
            <el-option
              v-for="port in availableComPorts"
              :key="port.device"
              :label="`${port.device} - ${port.description}`"
              :value="port.device"
            />
          </el-select>
          <el-button type="primary" size="small" @click="fetchComPorts" style="margin-left: 10px">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </el-form-item>
        
        <!-- 舵机控制 (SLS特有) -->
        <el-divider content-position="left">舵机控制 (挡板控制)</el-divider>
        <el-form-item label="启用舵机">
          <el-switch v-model="settings.servo_enabled" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">
            控制红外摄像头保护挡板
          </span>
        </el-form-item>
        <el-form-item label="舵机COM口" v-if="settings.servo_enabled">
          <el-select v-model="settings.servo_com" style="width: 200px">
            <el-option
              v-for="port in availableComPorts"
              :key="port.device"
              :label="`${port.device} - ${port.description}`"
              :value="port.device"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="舵机ID" v-if="settings.servo_enabled">
          <el-input-number v-model="settings.servo_id" :min="1" :max="16" style="width: 120px" />
        </el-form-item>
        
        <!-- 模拟模式 -->
        <el-divider content-position="left">调试模式</el-divider>
        <el-form-item label="使用模拟数据">
          <el-switch v-model="settings.use_mock" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">
            开启后无需连接真实硬件，用于界面测试
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="saveSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { Setting, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

import SensorConnectionStatus from '../../components/sls/SensorConnectionStatus.vue'
import RealTimeDisplay from '../../components/sls/RealTimeDisplay.vue'
import EquipmentHealthStatus from '../../components/sls/EquipmentHealthStatus.vue'
import ImageCapturePanel from '../../components/sls/ImageCapturePanel.vue'
import VibrationWaveform from '../../components/sls/VibrationWaveform.vue'
import ServoControlPanel from '../../components/sls/ServoControlPanel.vue'

// 状态
const isRunning = ref(false)
const starting = ref(false)
const showSettings = ref(false)
const wsConnected = ref(false)
const streamKey = ref(Date.now())
const displayPaused = ref(false)
const lastFrames = reactive({
  CH1: null,
  CH2: null,
  thermal: null
})

// 传感器状态
const sensorStatus = reactive({
  camera_ch1: { enabled: true, connected: false },
  camera_ch2: { enabled: true, connected: false },
  thermal: { enabled: true, connected: false, type: 'fotric' },
  vibration: { enabled: true, connected: false, com_port: 'COM5' },
  servo: { enabled: true, connected: false, com_port: 'COM16' }
})

// 舵机状态
const servoStatus = reactive({
  position: 1500,  // 当前位置
  target: 1500,    // 目标位置
  isOpen: false,   // 是否开启（挡板移开）
  isMoving: false  // 是否正在运动
})

// 最新数据
const latestData = reactive({
  timestamp: 0,
  frame_number: 0,
  camera_ch1: null,
  camera_ch2: null,
  thermal: null,
  vibration: null,
  vibration_waveform: { x: [], y: [], z: [], sample_count: 0 },
  statistics: {},
  health: {
    status: 'power_off',
    status_code: 0,
    status_labels: [],
    laser_system: { status: 'unknown', message: '未检测' },
    powder_system: { status: 'unknown', message: '未检测' },
    gas_system: { status: 'unknown', message: '未检测' }
  }
})

// 健康数据
const healthData = reactive({
  status: 'power_off',
  status_code: -1,
  status_labels: [],
  laser_system: { status: 'unknown', message: '未检测' },
  powder_system: { status: 'unknown', message: '未检测' },
  gas_system: { status: 'unknown', message: '未检测' }
})

// 设置
const settings = reactive({
  camera_ch1_index: 0,
  camera_ch2_index: 1,
  vibration_com: 'COM5',
  thermal_type: 'fotric',  // fotric 或 ir8062
  thermal_index: 0,
  servo_enabled: true,
  servo_com: 'COM16',
  servo_id: 1,
  use_mock: false
})

// 可用设备列表
const availableCameras = ref([])
const camerasLoading = ref(false)
const availableComPorts = ref([])

// WebSocket
let ws = null
let reconnectTimer = null
let healthCheckTimer = null
let lastBackendHealthCode = -1

// 获取状态
const fetchStatus = async () => {
  try {
    const response = await axios.get('/api/sls/status')
    if (response.data) {
      const wasRunning = isRunning.value
      isRunning.value = response.data.is_running
      Object.assign(sensorStatus, response.data.sensor_status || {})
      
      // 更新舵机状态
      if (response.data.servo_status) {
        Object.assign(servoStatus, response.data.servo_status)
      }
      
      // 采集状态处理（同SLM）
      if (isRunning.value && healthData.status_code === -1) {
        healthData.status = 'healthy'
        healthData.status_code = 0
        healthData.status_labels = ['系统健康']
        healthData.laser_system = { status: 'healthy', message: '健康' }
        healthData.powder_system = { status: 'healthy', message: '健康' }
        healthData.gas_system = { status: 'healthy', message: '健康' }
        await updateHealthStatusOnBackend(0, ['系统健康'])
      }
      
      if (wasRunning && !isRunning.value) {
        healthData.status = 'power_off'
        healthData.status_code = -1
        healthData.status_labels = []
        healthData.laser_system = { status: 'unknown', message: '未检测' }
        healthData.powder_system = { status: 'unknown', message: '未检测' }
        healthData.gas_system = { status: 'unknown', message: '未检测' }
        lastBackendHealthCode = -1
        closeWebSocket()
      }
    }
  } catch (error) {
    console.error('获取状态失败:', error)
  }
}

// 通知后端更新健康状态
const updateHealthStatusOnBackend = async (statusCode, labels) => {
  try {
    await axios.post('/api/sls/health/status', null, {
      params: {
        status_code: statusCode,
        labels: labels
      }
    })
  } catch (error) {
    console.error('更新后端健康状态失败:', error)
  }
}

// 获取COM口列表
const fetchComPorts = async () => {
  try {
    const response = await axios.get('/api/sls/com_ports')
    if (response.data.success) {
      availableComPorts.value = response.data.ports
      // 自动检测振动传感器COM口
      const ch340 = response.data.ports.find(p => 
        p.description.includes('CH340') || p.description.includes('USB-SERIAL')
      )
      if (ch340 && !isRunning.value) {
        settings.vibration_com = ch340.device
      }
      // 自动检测舵机COM口
      const servoPort = response.data.ports.find(p => 
        p.description.includes('舵机') || p.description.includes('Servo')
      )
      if (servoPort && !isRunning.value) {
        settings.servo_com = servoPort.device
      }
    }
  } catch (error) {
    console.error('获取COM口失败:', error)
  }
}

// 获取可用摄像头
const fetchCameras = async () => {
  camerasLoading.value = true
  try {
    const response = await axios.get('/api/sls/cameras')
    if (response.data.success) {
      availableCameras.value = response.data.cameras
      const availableIndices = response.data.cameras.map(c => c.index)
      if (!isRunning.value) {
        if (response.data.cameras.length >= 2) {
          settings.camera_ch1_index = response.data.cameras[0].index
          settings.camera_ch2_index = response.data.cameras[1].index
        } else if (response.data.cameras.length === 1) {
          settings.camera_ch1_index = response.data.cameras[0].index
        }
      }
    }
  } catch (error) {
    console.error('获取摄像头失败:', error)
    ElMessage.error('摄像头检测失败')
  } finally {
    camerasLoading.value = false
  }
}

// 舵机控制
const handleServoMove = async (position) => {
  try {
    const response = await axios.post('/api/sls/servo/move', {
      position: position,
      duration: 100,
      servo_id: settings.servo_id
    })
    if (response.data.success) {
      servoStatus.position = position
      servoStatus.isOpen = position > 2000
      ElMessage.success(`舵机移动到 ${position}`)
    }
  } catch (error) {
    ElMessage.error('舵机控制失败')
  }
}

const handleServoToggle = async () => {
  const targetPosition = servoStatus.isOpen ? 1500 : 2500
  await handleServoMove(targetPosition)
}

// 开始/停止采集
const toggleAcquisition = async () => {
  if (starting.value) return
  
  if (isRunning.value) {
    starting.value = true
    try {
      await axios.post('/api/sls/stop')
      isRunning.value = false
      streamKey.value = Date.now()
      closeWebSocket()
      ElMessage.success('采集已停止')
    } catch (error) {
      ElMessage.error('停止采集失败')
    } finally {
      starting.value = false
    }
  } else {
    starting.value = true
    try {
      const response = await axios.post('/api/sls/start', null, {
        params: {
          camera_ch1_index: settings.camera_ch1_index,
          camera_ch2_index: settings.camera_ch2_index,
          vibration_com: settings.vibration_com,
          thermal_type: settings.thermal_type,
          thermal_index: settings.thermal_index,
          servo_enabled: settings.servo_enabled,
          servo_com: settings.servo_com,
          servo_id: settings.servo_id,
          use_mock: settings.use_mock
        }
      })
      
      if (response.data.success) {
        isRunning.value = true
        streamKey.value = Date.now()
        connectWebSocket()
        ElMessage.success('采集已启动')
      } else {
        ElMessage.error(response.data.message || '启动失败')
      }
    } catch (error) {
      ElMessage.error('启动采集失败')
    } finally {
      starting.value = false
    }
  }
}

// WebSocket连接
const connectWebSocket = () => {
  const wsUrl = `ws://${window.location.host}/api/sls/ws/data`
  try {
    ws = new WebSocket(wsUrl)
    ws.onopen = () => { wsConnected.value = true }
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleWebSocketData(data)
      } catch (error) {
        console.error('解析WebSocket数据失败:', error)
      }
    }
    ws.onerror = () => { wsConnected.value = false }
    ws.onclose = () => {
      wsConnected.value = false
      if (isRunning.value) {
        reconnectTimer = setTimeout(() => connectWebSocket(), 3000)
      }
    }
  } catch (error) {
    console.error('连接WebSocket失败:', error)
  }
}

const closeWebSocket = () => {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
}

// 处理WebSocket数据
const handleWebSocketData = (data) => {
  if (data.sensor_status) {
    Object.assign(sensorStatus, data.sensor_status)
  }
  if (data.vibration) {
    latestData.vibration = data.vibration
  }
  if (data.vibration_waveform) {
    latestData.vibration_waveform = data.vibration_waveform
  }
  if (data.thermal) {
    latestData.thermal = data.thermal
  }
  if (data.statistics) {
    latestData.statistics = data.statistics
  }
  if (data.health) {
    Object.assign(healthData, data.health)
    Object.assign(latestData.health, data.health)
  }
  if (data.servo_status) {
    Object.assign(servoStatus, data.servo_status)
  }
  latestData.timestamp = data.timestamp
  latestData.frame_number = data.frame_number
}

// 切换传感器
const handleToggleSensor = async (sensor, enabled) => {
  try {
    await axios.post(`/api/sls/sensor/${sensor}/enable?enabled=${enabled}`)
    sensorStatus[sensor].enabled = enabled
    ElMessage.success(`${sensor} 已${enabled ? '启用' : '禁用'}`)
  } catch (error) {
    ElMessage.error('切换传感器失败')
    sensorStatus[sensor].enabled = !enabled
  }
}

// 切换COM口
const handleChangeComPort = async (port) => {
  try {
    await axios.post(`/api/sls/vibration/com_port?port=${port}`)
    settings.vibration_com = port
    ElMessage.success(`COM口已切换到 ${port}`)
  } catch (error) {
    ElMessage.error('切换COM口失败')
  }
}

// 刷新状态
const refreshStatus = async () => {
  fetchStatus()
  fetchComPorts()
  streamKey.value = Date.now()
  ElMessage.success('状态已刷新')
}

// 保存设置
const saveSettings = async () => {
  if (isRunning.value) {
    ElMessage.warning('设置已更改，正在重启采集...')
    try {
      await axios.post('/api/sls/stop')
      isRunning.value = false
      closeWebSocket()
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      const response = await axios.post('/api/sls/start', null, {
        params: {
          camera_ch1_index: settings.camera_ch1_index,
          camera_ch2_index: settings.camera_ch2_index,
          vibration_com: settings.vibration_com,
          thermal_type: settings.thermal_type,
          thermal_index: settings.thermal_index,
          servo_enabled: settings.servo_enabled,
          servo_com: settings.servo_com,
          servo_id: settings.servo_id,
          use_mock: settings.use_mock
        }
      })
      
      if (response.data.success) {
        isRunning.value = true
        streamKey.value = Date.now()
        connectWebSocket()
        ElMessage.success('采集已重启')
      }
    } catch (error) {
      ElMessage.error('重启采集失败')
    }
  } else {
    ElMessage.success('设置已保存')
  }
  showSettings.value = false
}

// 图像采集触发
const handleCaptureTriggered = (event) => {
  if (event.type === 'after') {
    ElMessage.success(`第 ${event.layer} 层采集完成`)
  }
}

// 从后端获取健康状态
const fetchBackendHealthStatus = async () => {
  if (!isRunning.value) return
  try {
    const response = await axios.get('/api/sls/health/status')
    if (response.data.success && response.data.health) {
      const backendCode = response.data.health.status_code
      if (backendCode !== lastBackendHealthCode) {
        lastBackendHealthCode = backendCode
        Object.assign(healthData, response.data.health)
        if (backendCode > 0) {
          const statusLabels = response.data.health.status_labels || ['异常']
          ElMessage.warning(`检测到设备异常: ${statusLabels.join(', ')}`)
        }
      }
    }
  } catch (error) {
    console.error('获取后端健康状态失败:', error)
  }
}

// 设置对话框打开时自动检测硬件
watch(showSettings, (val) => {
  if (val) {
    fetchCameras()
    fetchComPorts()
  }
})

onMounted(() => {
  fetchStatus()
  fetchComPorts()
  fetchCameras()
  
  if (isRunning.value) {
    connectWebSocket()
  }
  
  healthCheckTimer = setInterval(() => {
    fetchBackendHealthStatus()
  }, 3000)
})

onUnmounted(() => {
  closeWebSocket()
  if (healthCheckTimer) {
    clearInterval(healthCheckTimer)
    healthCheckTimer = null
  }
})
</script>

<style scoped>
.sls-dashboard {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.realtime-section,
.servo-section,
.vibration-section,
.health-section,
.capture-section {
  width: 100%;
}

@media (max-width: 768px) {
  .sls-dashboard {
    padding: 12px;
  }
  
  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .page-title {
    font-size: 20px;
  }
  
  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
