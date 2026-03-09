<template>
  <div class="slm-dashboard">
    <!-- 页面标题 -->
    <div class="dashboard-header">
      <h1 class="page-title">SLM 设备监控仪表盘</h1>
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
    
    <!-- 实时数据显示 -->
    <div class="realtime-section">
      <RealTimeDisplay
        :sensor-status="sensorStatus"
        :latest-data="latestData"
        :stream-key="streamKey"
      />
    </div>
    
    <!-- 设备健康状态 -->
    <div class="health-section">
      <EquipmentHealthStatus
        :health-data="healthData"
        :is-running="isRunning"
      />
    </div>
    
    <!-- 设置对话框 -->
    <el-dialog
      v-model="showSettings"
      title="采集设置"
      width="550px"
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
        
        <!-- 红外热像仪 -->
        <el-divider content-position="left">红外热像仪</el-divider>
        <el-form-item>
          <el-alert
            type="info"
            :closable="false"
            show-icon
          >
            <template #title>
              红外热像仪通过PIX Connect SDK连接，不需要COM口
            </template>
            <template #default>
              请确保：<br>
              1. PIX Connect软件已安装并启动<br>
              2. 热像仪设备已连接<br>
              3. 在PIX Connect中启用IPC通信
            </template>
          </el-alert>
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

import SensorConnectionStatus from '../../components/slm/SensorConnectionStatus.vue'
import RealTimeDisplay from '../../components/slm/RealTimeDisplay.vue'
import EquipmentHealthStatus from '../../components/slm/EquipmentHealthStatus.vue'

// 状态
const isRunning = ref(false)
const starting = ref(false)
const showSettings = ref(false)
const wsConnected = ref(false)
const streamKey = ref(Date.now())  // 用于强制刷新视频流

// 传感器状态
const sensorStatus = reactive({
  camera_ch1: { enabled: true, connected: false },
  camera_ch2: { enabled: true, connected: false },
  thermal: { enabled: true, connected: false },
  vibration: { enabled: true, connected: false, com_port: 'COM5' }
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
  status_code: 0,
  status_labels: [],
  laser_system: { status: 'unknown', message: '未检测' },
  powder_system: { status: 'unknown', message: '未检测' },
  gas_system: { status: 'unknown', message: '未检测' }
})

// 设置
const settings = reactive({
  camera_ch1_index: 0,  // 默认自动检测
  camera_ch2_index: 1,  // 默认自动检测
  vibration_com: 'COM5',
  use_mock: false  // 默认使用真实硬件
})

// 可用摄像头列表
const availableCameras = ref([])
const camerasLoading = ref(false)

const availableComPorts = ref([])

// 当设置对话框打开时自动检测硬件
watch(showSettings, (val) => {
  if (val) {
    // 对话框打开时自动检测
    fetchCameras()
    fetchComPorts()
  }
})

// WebSocket
let ws = null
let reconnectTimer = null

// 获取状态
const fetchStatus = async () => {
  try {
    const response = await axios.get('/api/slm/status')
    if (response.data) {
      isRunning.value = response.data.is_running
      Object.assign(sensorStatus, response.data.sensor_status || {})
    }
  } catch (error) {
    console.error('获取状态失败:', error)
  }
}

// 获取COM口列表
const fetchComPorts = async () => {
  try {
    const response = await axios.get('/api/slm/com_ports')
    if (response.data.success) {
      availableComPorts.value = response.data.ports
      // 自动检测振动传感器COM口
      const ch340 = response.data.ports.find(p => p.description.includes('CH340') || p.description.includes('USB-SERIAL'))
      if (ch340 && !isRunning.value) {
        settings.vibration_com = ch340.device
        console.log('自动检测到振动传感器:', ch340.device)
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
    const response = await axios.get('/api/slm/cameras')
    if (response.data.success) {
      availableCameras.value = response.data.cameras
      
      // 检查当前选择是否有效，无效则自动设置
      const availableIndices = response.data.cameras.map(c => c.index)
      const ch1Valid = availableIndices.includes(settings.camera_ch1_index)
      const ch2Valid = availableIndices.includes(settings.camera_ch2_index)
      
      // 自动设置摄像头索引（仅在未运行时且当前选择无效）
      if (!isRunning.value) {
        if (response.data.cameras.length >= 2) {
          if (!ch1Valid) settings.camera_ch1_index = response.data.cameras[0].index
          if (!ch2Valid) settings.camera_ch2_index = response.data.cameras[1].index
        } else if (response.data.cameras.length === 1) {
          if (!ch1Valid) settings.camera_ch1_index = response.data.cameras[0].index
        }
      }
      
      if (response.data.cameras.length > 0) {
        console.log('检测到摄像头:', response.data.cameras)
      }
    } else {
      ElMessage.warning(response.data.message || '摄像头检测失败')
    }
  } catch (error) {
    console.error('获取摄像头失败:', error)
    ElMessage.error('摄像头检测失败: ' + (error.response?.data?.message || error.message))
  } finally {
    camerasLoading.value = false
  }
}

// 开始/停止采集
const toggleAcquisition = async () => {
  console.log(`[Dashboard] toggleAcquisition 调用, isRunning=${isRunning.value}, starting=${starting.value}`)
  
  if (starting.value) {
    console.log('[Dashboard] 正在处理中，忽略点击')
    return
  }
  
  if (isRunning.value) {
    // 停止
    console.log('[Dashboard] 停止采集...')
    starting.value = true
    try {
      const response = await axios.post('/api/slm/stop')
      console.log('[Dashboard] 停止响应:', response.data)
      isRunning.value = false
      streamKey.value = Date.now()
      closeWebSocket()
      
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      Object.keys(sensorStatus).forEach(key => {
        if (sensorStatus[key]) sensorStatus[key].connected = false
      })
      
      ElMessage.success('采集已停止')
    } catch (error) {
      console.error('[Dashboard] 停止失败:', error)
      ElMessage.error('停止采集失败: ' + (error.response?.data?.message || error.message))
    } finally {
      starting.value = false
      console.log('[Dashboard] 停止处理完成')
    }
  } else {
    // 开始
    console.log('[Dashboard] 开始采集...')
    starting.value = true
    try {
      console.log('[Dashboard] 发送启动请求, 参数:', settings)
      const response = await axios.post('/api/slm/start', null, {
        params: {
          camera_ch1_index: settings.camera_ch1_index,
          camera_ch2_index: settings.camera_ch2_index,
          vibration_com: settings.vibration_com,
          use_mock: settings.use_mock
        }
      })
      console.log('[Dashboard] 启动响应:', response.data)
      
      if (response.data.success) {
        isRunning.value = true
        streamKey.value = Date.now()
        const modeText = settings.use_mock ? '模拟模式' : '真实硬件模式'
        ElMessage.success(`采集已启动 (${modeText})`)
        connectWebSocket()
      } else {
        ElMessage.error(response.data.message || '启动失败')
      }
    } catch (error) {
      console.error('[Dashboard] 启动失败:', error)
      ElMessage.error('启动采集失败: ' + (error.response?.data?.message || error.message))
    } finally {
      starting.value = false
      console.log('[Dashboard] 启动处理完成')
    }
  }
}

// 连接WebSocket
const connectWebSocket = () => {
  const wsUrl = `ws://${window.location.host}/api/slm/ws/data`
  
  try {
    ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      console.log('WebSocket已连接')
      wsConnected.value = true
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleWebSocketData(data)
      } catch (error) {
        console.error('解析WebSocket数据失败:', error)
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
      wsConnected.value = false
    }
    
    ws.onclose = () => {
      console.log('WebSocket已关闭')
      wsConnected.value = false
      
      // 尝试重连
      if (isRunning.value) {
        reconnectTimer = setTimeout(() => {
          connectWebSocket()
        }, 3000)
      }
    }
  } catch (error) {
    console.error('连接WebSocket失败:', error)
  }
}

// 关闭WebSocket
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
  // 更新传感器状态
  if (data.sensor_status) {
    Object.assign(sensorStatus, data.sensor_status)
  }
  
  // 更新最新数据
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
  
  latestData.timestamp = data.timestamp
  latestData.frame_number = data.frame_number
}

// 切换传感器
const handleToggleSensor = async (sensor, enabled) => {
  try {
    await axios.post(`/api/slm/sensor/${sensor}/enable?enabled=${enabled}`)
    sensorStatus[sensor].enabled = enabled
    ElMessage.success(`${sensor} 已${enabled ? '启用' : '禁用'}`)
  } catch (error) {
    ElMessage.error('切换传感器失败')
    // 恢复状态
    sensorStatus[sensor].enabled = !enabled
  }
}

// 切换COM口
const handleChangeComPort = async (port) => {
  try {
    await axios.post(`/api/slm/vibration/com_port?port=${port}`)
    settings.vibration_com = port
    ElMessage.success(`COM口已切换到 ${port}`)
  } catch (error) {
    ElMessage.error('切换COM口失败')
  }
}

// 刷新状态
const refreshStatus = () => {
  fetchStatus()
  fetchComPorts()
  ElMessage.success('状态已刷新')
}

// 保存设置
const saveSettings = async () => {
  // 如果正在采集，需要先停止再重新启动以应用新设置
  if (isRunning.value) {
    ElMessage.warning('设置已更改，正在重启采集以应用新配置...')
    
    try {
      // 停止当前采集
      await axios.post('/api/slm/stop')
      isRunning.value = false  // 更新状态
      streamKey.value = Date.now()  // 强制刷新视频流
      closeWebSocket()
      
      // 等待资源释放
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      // 重新启动采集
      const response = await axios.post('/api/slm/start', null, {
        params: {
          camera_ch1_index: settings.camera_ch1_index,
          camera_ch2_index: settings.camera_ch2_index,
          vibration_com: settings.vibration_com,
          use_mock: settings.use_mock
        }
      })
      
      if (response.data.success) {
        isRunning.value = true  // 更新状态
        streamKey.value = Date.now()  // 更新streamKey强制刷新视频流
        connectWebSocket()
        ElMessage.success('采集已重启，新设置已生效')
      }
    } catch (error) {
      ElMessage.error('重启采集失败: ' + (error.response?.data?.message || error.message))
      isRunning.value = false
    }
  } else {
    ElMessage.success('设置已保存，将在下次启动采集时生效')
  }
  
  showSettings.value = false
}

onMounted(() => {
  fetchStatus()
  fetchComPorts()
  fetchCameras()  // 自动检测摄像头
  
  // 如果正在运行，连接WebSocket
  if (isRunning.value) {
    connectWebSocket()
  }
})

onUnmounted(() => {
  closeWebSocket()
})
</script>

<style scoped>
.slm-dashboard {
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
.health-section {
  width: 100%;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .slm-dashboard {
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
