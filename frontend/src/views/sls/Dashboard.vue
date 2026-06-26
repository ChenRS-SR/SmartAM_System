<template>
  <div class="slm-dashboard">
    <!-- 页面标题 -->
    <div class="dashboard-header">
      <div class="title-block">
        <h1 class="page-title">{{ selectedDeviceName }} 打印状态监测</h1>
        <div class="device-subtitle">
          {{ selectedDevice?.dataTag || 'SLS设备' }} · {{ selectedDevice?.model || 'SLS 设备' }} · {{ selectedDevice?.location || '未设置位置' }}
        </div>
      </div>
      <div class="header-actions">
        <el-select
          v-model="selectedDeviceId"
          class="device-switch"
          size="large"
          @change="switchDevice"
        >
          <el-option
            v-for="device in slsDeviceStore.devices"
            :key="device.id"
            :label="device.name"
            :value="device.id"
          />
        </el-select>
        <el-button @click="goToDeviceGroup">
          <el-icon><ArrowLeft /></el-icon>
          设备群
        </el-button>
        <!-- 模式指示器 -->
        <el-tag
          :type="settings.use_mock ? 'warning' : 'success'"
          size="large"
          effect="dark"
          class="mode-tag"
        >
          {{ settings.use_mock ? '模拟模式' : '真实硬件' }}
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
      @refresh="refreshStatus"
    />

    <!-- 当前设备实时参数 -->
    <section class="parameter-panel">
      <div class="panel-header">
        <span>实时参数</span>
        <el-tag size="small" :type="selectedDevice?.online ? 'success' : 'info'">
          {{ selectedDevice?.online ? '在线' : '离线' }}
        </el-tag>
      </div>
      <div class="parameter-grid">
        <div
          v-for="param in liveParameters"
          :key="param.id || param.name"
          class="parameter-item"
        >
          <span class="parameter-name">{{ param.name }}</span>
          <strong class="parameter-value">{{ param.value }}</strong>
          <span class="parameter-unit">{{ param.unit }}</span>
        </div>
      </div>
    </section>

    <!-- 实时数据显示 (包含CH1/CH2/CH3视频) -->
    <div class="realtime-section">
      <RealTimeDisplay
        :sensor-status="sensorStatus"
        :latest-data="latestData"
        :stream-key="streamKey"
        :display-paused="displayPaused"
        :last-frames="lastFrames"
      />
    </div>

    <!-- 闭环调控和视频控制 (放在视频下方) -->
    <div class="regulation-section">
      <RegulationControl
        ref="regulationControl"
        @video-source-changed="onVideoSourceChanged"
        @layer-changed="onLayerChanged"
      />
    </div>

    <!-- 区域特征曲线 (放在闭环调控下方) -->
    <div class="feature-curve-section">
      <FeatureCurvePanel
        :current-layer="currentLayerInfo.number"
        :is-layer-start="currentLayerInfo.isStart"
        :is-layer-end="currentLayerInfo.isEnd"
        :is-running="isRunning"
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
import { computed, ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Setting, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

import SensorConnectionStatus from '../../components/slm/SensorConnectionStatus.vue'
import RealTimeDisplay from '../../components/slm/RealTimeDisplay.vue'
import EquipmentHealthStatus from '../../components/slm/EquipmentHealthStatus.vue'
import RegulationControl from '../../components/slm/RegulationControl.vue'
import FeatureCurvePanel from '../../components/slm/FeatureCurvePanel.vue'
import { useSlsDeviceStore } from '../../stores/slsDevices'

const route = useRoute()
const router = useRouter()
const slsDeviceStore = useSlsDeviceStore()

const selectedDeviceId = ref(route.params.deviceId || '')
const selectedDevice = computed(() => slsDeviceStore.getDeviceById(selectedDeviceId.value) || slsDeviceStore.firstDevice)
const selectedDeviceName = computed(() => selectedDevice.value?.name || 'SLS设备')

// 状态
const isRunning = ref(false)
const starting = ref(false)
const showSettings = ref(false)
const wsConnected = ref(false)
const streamKey = ref(Date.now())  // 用于强制刷新视频流
const displayPaused = ref(false)   // 显示暂停状态（录制时节省带宽）
const lastFrames = reactive({      // 暂停时显示的最后一帧
  CH1: null,
  CH2: null,
  thermal: null
})

// 传感器状态
const sensorStatus = reactive({
  camera_ch1: { enabled: true, connected: false },
  camera_ch2: { enabled: true, connected: false },
  thermal: { enabled: true, connected: false }
})

// 最新数据
const latestData = reactive({
  timestamp: 0,
  frame_number: 0,
  camera_ch1: null,
  camera_ch2: null,
  thermal: null,
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

const fixedParameterSchema = [
  { id: 'current_layer', name: '当前层', value: '--', unit: '层' },
  { id: 'sequence', name: '数据序号', value: '--', unit: '' },
  { id: 'record_status', name: '状态参数', value: '--', unit: '' },
  { id: 'data_time', name: '采集时间', value: '--', unit: '' },
  { id: 'scraper_torque', name: '刮刀扭矩', value: '--', unit: '%' },
  { id: 'oxygen', name: '成形室氧含量', value: '--', unit: '%' },
  { id: 'ambient_oxygen', name: '环境氧含量', value: '--', unit: '%' },
  { id: 'chamber_temperature', name: '成形室温度', value: '--', unit: '℃' },
  { id: 'gas_flow', name: '循环气体流量', value: '--', unit: 'm3/h' },
  { id: 'fan_speed', name: '风机转速', value: '--', unit: '%' },
  { id: 'medium_filter_resistance', name: '中效滤芯阻力', value: '--', unit: 'mBar' },
  { id: 'high_filter_resistance', name: '高效滤芯阻力', value: '--', unit: 'mBar' },
  { id: 'gas_pressure', name: '气源压力', value: '--', unit: 'Bar' },
  { id: 'compressed_air_pressure', name: '压缩空气压力', value: '--', unit: 'Bar' },
  { id: 'servo_temperature_x', name: 'X轴伺服温度', value: '--', unit: '℃' },
  { id: 'servo_temperature_y', name: 'Y轴伺服温度', value: '--', unit: '℃' },
  { id: 'galvo_temperature_x', name: 'X轴振镜温度', value: '--', unit: '℃' },
  { id: 'galvo_temperature_y', name: 'Y轴振镜温度', value: '--', unit: '℃' },
  { id: 'output_current_x', name: 'X轴输出电流', value: '--', unit: 'mA' },
  { id: 'output_current_y', name: 'Y轴输出电流', value: '--', unit: 'mA' }
]
const mockRuntimeTick = ref(0)
const runtimeBase = reactive({
  deviceId: '',
  currentLayer: 0,
  sequence: 0
})

// 健康数据 - 初始状态为未开机（状态码-1）
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
  camera_ch1_index: 0,  // 默认自动检测
  camera_ch2_index: 1,  // 默认自动检测
  use_mock: false  // 默认使用真实硬件
})

// 可用摄像头列表
const availableCameras = ref([])
const camerasLoading = ref(false)

// RegulationControl 引用
const regulationControl = ref(null)

// 当前层信息（用于特征曲线）
const currentLayerInfo = ref({
  number: 0,
  isStart: false,
  isEnd: false
})

// 当前视频文件配置（用于检测变化）
const currentVideoConfig = ref({
  enabled: false,
  videoFilesHash: '',
  folder: ''
})

const ensureSelectedDevice = (routeDeviceId = route.params.deviceId) => {
  if (!slsDeviceStore.devices.length) return
  const fallbackDeviceId = slsDeviceStore.firstDevice?.id
  const nextDeviceId = routeDeviceId && slsDeviceStore.getDeviceById(routeDeviceId)
    ? routeDeviceId
    : fallbackDeviceId
  selectedDeviceId.value = nextDeviceId
  if (nextDeviceId && routeDeviceId !== nextDeviceId) {
    router.replace(`/sls/device/${nextDeviceId}`)
  }
}

watch([() => route.params.deviceId, () => slsDeviceStore.devices.length], ([deviceId]) => {
  ensureSelectedDevice(deviceId)
}, { immediate: true })

watch(selectedDevice, (device) => {
  if (device?.healthData) {
    Object.assign(healthData, device.healthData)
  }
}, { immediate: true })

const goToDeviceGroup = () => {
  router.push('/sls/dashboard')
}

const switchDevice = (deviceId) => {
  router.push(`/sls/device/${deviceId}`)
}

const applySensorStatus = (status = {}) => {
  const sensorKeys = ['camera_ch1', 'camera_ch2', 'thermal']
  sensorKeys.forEach((key) => {
    if (status[key]) {
      sensorStatus[key] = {
        ...sensorStatus[key],
        ...status[key]
      }
    }
  })
}

const syncHealthDataToDevice = () => {
  if (selectedDeviceId.value) {
    slsDeviceStore.updateDeviceHealth(selectedDeviceId.value, {
      ...healthData,
      status_labels: [...(healthData.status_labels || [])],
      laser_system: { ...(healthData.laser_system || {}) },
      powder_system: { ...(healthData.powder_system || {}) },
      gas_system: { ...(healthData.gas_system || {}) }
    })
  }
}

const applyHealthData = (nextHealth = {}) => {
  healthData.status = nextHealth.status || healthData.status
  healthData.status_code = nextHealth.status_code !== undefined ? nextHealth.status_code : healthData.status_code
  healthData.status_labels = nextHealth.status_labels || healthData.status_labels
  if (nextHealth.laser_system) {
    healthData.laser_system = { ...nextHealth.laser_system }
  }
  if (nextHealth.powder_system) {
    healthData.powder_system = { ...nextHealth.powder_system }
  }
  if (nextHealth.gas_system) {
    healthData.gas_system = { ...nextHealth.gas_system }
  }
  Object.assign(latestData.health, nextHealth)
  syncHealthDataToDevice()
}

const formatRuntimeValue = (value, digits = 1) => {
  if (value === undefined || value === null || value === '') return '--'
  if (typeof value === 'number') return Number.isInteger(value) ? value : value.toFixed(digits)
  return value
}

const numericValue = (value, fallback = 0) => {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

const resetRuntimeBase = () => {
  const params = selectedDevice.value?.parameters || []
  const layerParam = params.find((param) => param.id === 'current_layer')
  const sequenceParam = params.find((param) => param.id === 'sequence')
  runtimeBase.deviceId = selectedDeviceId.value || ''
  runtimeBase.currentLayer = numericValue(layerParam?.value, currentLayerInfo.value.number || 0)
  runtimeBase.sequence = numericValue(sequenceParam?.value, latestData.frame_number || 0)
}

const currentStatusParameterText = () => {
  const labels = Array.isArray(healthData.status_labels) ? healthData.status_labels.filter(Boolean) : []
  if (labels.length) return labels.join('、')
  return selectedDevice.value?.statusText || '--'
}

watch(selectedDevice, () => {
  resetRuntimeBase()
  mockRuntimeTick.value = 0
}, { immediate: true })

const liveParameters = computed(() => {
  const baseParameters = selectedDevice.value?.parameters?.length
    ? selectedDevice.value.parameters
    : fixedParameterSchema

  const normalized = fixedParameterSchema.map((schema) => {
    const matched = baseParameters.find((param) => param.id === schema.id || param.name === schema.name)
    return {
      ...schema,
      value: matched?.value ?? schema.value,
      unit: matched?.unit ?? schema.unit
    }
  })

  if (isRunning.value && settings.use_mock) {
    normalized[0].value = formatRuntimeValue(runtimeBase.currentLayer + Math.floor(mockRuntimeTick.value / 4), 0)
    normalized[1].value = formatRuntimeValue(runtimeBase.sequence + mockRuntimeTick.value * 3, 0)
  } else if (isRunning.value) {
    if (currentLayerInfo.value.number) {
      normalized[0].value = formatRuntimeValue(currentLayerInfo.value.number, 0)
    }
    if (latestData.frame_number) {
      normalized[1].value = formatRuntimeValue(latestData.frame_number, 0)
    }
  }

  normalized[2].value = currentStatusParameterText()
  return normalized
})

let lastParameterSignature = ''
watch(liveParameters, (parameters) => {
  if (selectedDeviceId.value) {
    const signature = JSON.stringify(parameters)
    if (signature === lastParameterSignature) return
    lastParameterSignature = signature
    slsDeviceStore.updateDeviceParameters(selectedDeviceId.value, parameters)
  }
}, { deep: true })

// 当设置对话框打开时自动检测硬件
watch(showSettings, (val) => {
  if (val) {
    // 对话框打开时自动检测
    fetchCameras()
  }
})

// 视频源改变时的处理
const onVideoSourceChanged = (sourceInfo) => {
  console.log('[Dashboard] 视频源已改变:', sourceInfo)
  // 强制刷新视频流
  streamKey.value = Date.now()

  // 如果正在运行，更新传感器状态为已连接
  if (sourceInfo.isPlaying) {
    sensorStatus.camera_ch1.connected = true
    sensorStatus.camera_ch2.connected = true
    sensorStatus.thermal.connected = true
  }
}

// 层变化时的处理
const onLayerChanged = (layerInfo) => {
  currentLayerInfo.value = layerInfo
  console.log('[Dashboard] 层变化:', layerInfo)
}

// 获取状态
const fetchStatus = async () => {
  try {
    const response = await axios.get('/api/slm/status')
    if (response.data) {
      const wasRunning = isRunning.value
      isRunning.value = response.data.is_running
      applySensorStatus(response.data.sensor_status || {})

      // 如果正在采集且当前状态为未开机(-1)，则更新为开机正常状态(0)
      if (isRunning.value && healthData.status_code === -1) {
        console.log('[Dashboard] 刷新状态：采集运行中，更新健康状态为开机正常')
        healthData.status = 'healthy'
        healthData.status_code = 0
        healthData.status_labels = ['系统健康']
        healthData.laser_system = { status: 'healthy', message: '健康' }
        healthData.powder_system = { status: 'healthy', message: '健康' }
        healthData.gas_system = { status: 'healthy', message: '健康' }
        syncHealthDataToDevice()

        // 通知后端更新健康状态
        await updateHealthStatusOnBackend(0, ['系统健康'])
      }

      // 如果采集刚停止（wasRunning && !isRunning），立即重置健康状态为未开机
      if (wasRunning && !isRunning.value) {
        console.log('[Dashboard] 刷新状态：采集已停止，重置健康状态为未开机')
        healthData.status = 'power_off'
        healthData.status_code = -1
        healthData.status_labels = []
        healthData.laser_system = { status: 'unknown', message: '未检测' }
        healthData.powder_system = { status: 'unknown', message: '未检测' }
        healthData.gas_system = { status: 'unknown', message: '未检测' }
        syncHealthDataToDevice()

        // 重置后端健康状态缓存
        lastBackendHealthCode = -1

        // 关闭WebSocket连接
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
    await axios.post('/api/slm/health/status', null, {
      params: {
        status_code: statusCode,
        labels: labels
      }
    })
    console.log(`[Dashboard] 后端健康状态已更新: ${statusCode}`)
  } catch (error) {
    console.error('[Dashboard] 更新后端健康状态失败:', error)
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

      // 重置传感器状态为未连接
      Object.keys(sensorStatus).forEach(key => {
        if (sensorStatus[key]) sensorStatus[key].connected = false
      })

      // 重置健康状态为未开机（状态码-1）
      healthData.status = 'power_off'
      healthData.status_code = -1
      healthData.status_labels = []
      healthData.laser_system = { status: 'unknown', message: '未检测' }
      healthData.powder_system = { status: 'unknown', message: '未检测' }
      healthData.gas_system = { status: 'unknown', message: '未检测' }
      syncHealthDataToDevice()

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
          use_mock: settings.use_mock
        }
      })
      console.log('[Dashboard] 启动响应:', response.data)

      if (response.data.success) {
        resetRuntimeBase()
        mockRuntimeTick.value = 0
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
    applySensorStatus(data.sensor_status)
  }

  // 更新最新数据
  if (data.thermal) {
    latestData.thermal = data.thermal
  }
  if (data.statistics) {
    latestData.statistics = data.statistics
  }
  // 更新健康状态
  if (data.health) {
    console.log('[Dashboard] 收到健康状态:', data.health)
    applyHealthData(data.health)
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

// 刷新状态
const refreshStatus = async () => {
  fetchStatus()

  // 检查视频文件模式配置是否变化
  try {
    const response = await axios.get('/api/slm/video_file_mode/config')
    if (response.data.success) {
      const config = response.data
      // 生成视频文件配置的简单哈希（路径拼接）
      const videoFilesStr = JSON.stringify(config.video_files || {})

      // 检测配置是否变化
      const configChanged = (
        config.enabled !== currentVideoConfig.value.enabled ||
        videoFilesStr !== currentVideoConfig.value.videoFilesHash
      )

      if (configChanged) {
        console.log('[Dashboard] 检测到视频文件配置变化，需要重启采集')
        // 更新当前配置
        currentVideoConfig.value = {
          enabled: config.enabled,
          videoFilesHash: videoFilesStr,
          folder: config.video_files ? Object.values(config.video_files)[0] : ''
        }

        // 自动重启采集以应用新配置（无论是否正在运行）
        ElMessage.info('检测到视频源变化，正在重启采集...')
        await restartAcquisitionWithNewVideoConfig()
      }
    }
  } catch (error) {
    console.error('[Dashboard] 检查视频文件配置失败:', error)
  }

  // 强制刷新视频流（更新streamKey使URL变化，防止缓存）
  streamKey.value = Date.now()
  // 刷新闭环调控组件状态
  if (regulationControl.value && regulationControl.value.refresh) {
    regulationControl.value.refresh()
  }
  ElMessage.success('状态已刷新')
}

// 使用新视频配置重启采集
const restartAcquisitionWithNewVideoConfig = async () => {
  try {
    // 1. 如果正在运行，停止当前采集
    if (isRunning.value) {
      await axios.post('/api/slm/stop')
      isRunning.value = false
      closeWebSocket()
      // 等待资源释放
      await new Promise(resolve => setTimeout(resolve, 1500))
    }

    // 2. 重新启动采集（使用视频文件模式）
    const response = await axios.post('/api/slm/start', null, {
      params: {
        camera_ch1_index: settings.camera_ch1_index,
        camera_ch2_index: settings.camera_ch2_index,
        use_mock: true  // 视频文件模式使用模拟模式
      }
    })

    if (response.data.success) {
      isRunning.value = true
      streamKey.value = Date.now()
      connectWebSocket()
      console.log('[Dashboard] 采集已使用新视频配置重启')
      ElMessage.success('视频源已更新')
    }
  } catch (error) {
    console.error('[Dashboard] 重启采集失败:', error)
    ElMessage.error('重启采集失败: ' + (error.response?.data?.message || error.message))
  }
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

// 处理诊断结果
const handleDiagnosisComplete = (result) => {
  console.log('[Dashboard] 诊断结果:', result)

  // 更新健康状态
  healthData.status_code = result.status_code
  healthData.status = getStatusFromCode(result.status_code)
  healthData.status_labels = [result.status_label]

  // 更新子系统状态
  if (result.status_code === 0) {
    healthData.laser_system = { status: 'healthy', message: '健康' }
    healthData.powder_system = { status: 'healthy', message: '健康' }
    healthData.gas_system = { status: 'healthy', message: '健康' }
  } else if (result.status_code === 1) {
    healthData.laser_system = { status: 'healthy', message: '健康' }
    healthData.powder_system = { status: 'fault', message: '刮刀磨损' }
    healthData.gas_system = { status: 'healthy', message: '健康' }
  } else if (result.status_code === 2) {
    healthData.laser_system = { status: 'fault', message: '激光功率异常' }
    healthData.powder_system = { status: 'healthy', message: '健康' }
    healthData.gas_system = { status: 'healthy', message: '健康' }
  } else if (result.status_code === 3) {
    healthData.laser_system = { status: 'healthy', message: '健康' }
    healthData.powder_system = { status: 'healthy', message: '健康' }
    healthData.gas_system = { status: 'fault', message: '保护气体异常' }
  } else if (result.status_code === 4) {
    healthData.laser_system = { status: 'fault', message: '需检查' }
    healthData.powder_system = { status: 'fault', message: '需检查' }
    healthData.gas_system = { status: 'fault', message: '需检查' }
  }
  syncHealthDataToDevice()

  ElMessage.success(`诊断完成: ${result.status_label}`)
}

const getStatusFromCode = (code) => {
  const map = {
    '-1': 'power_off',
    '0': 'healthy',
    '1': 'powder_fault',
    '2': 'laser_fault',
    '3': 'gas_fault',
    '4': 'compound_fault'
  }
  return map[String(code)] || 'power_off'
}

// 后端健康状态缓存
let lastBackendHealthCode = -1
let healthCheckTimer = null

// 从后端获取健康状态（用于检测诊断模块输出）
const fetchBackendHealthStatus = async () => {
  // 只有在采集运行中才获取
  if (!isRunning.value) return

  try {
    const response = await axios.get('/api/slm/health/status')
    if (response.data.success && response.data.health) {
      const backendCode = response.data.health.status_code

      // 只有状态码变化时才更新前端显示
      if (backendCode !== lastBackendHealthCode) {
        console.log(`[Dashboard] 后端健康状态变化: ${lastBackendHealthCode} -> ${backendCode}`)
        lastBackendHealthCode = backendCode

        // 更新前端健康状态，并同步到设备群卡片。
        applyHealthData(response.data.health)

        // 如果状态码表示故障，提示用户
        if (backendCode > 0) {
          const statusLabels = response.data.health.status_labels || ['异常']
          ElMessage.warning(`检测到设备异常: ${statusLabels.join(', ')}`)
        }
      }
    }
  } catch (error) {
    console.error('[Dashboard] 获取后端健康状态失败:', error)
  }
}

// 获取视频文件模式配置
const fetchVideoFileModeConfig = async () => {
  try {
    const response = await axios.get('/api/slm/video_file_mode/config')
    if (response.data.success) {
      const config = response.data
      // 保存当前配置
      currentVideoConfig.value = {
        enabled: config.enabled,
        videoFilesHash: JSON.stringify(config.video_files || {}),
        folder: config.video_files ? Object.values(config.video_files)[0] : ''
      }

      if (config.enabled) {
        // 如果视频文件模式已启用，自动切换到模拟模式
        settings.use_mock = true
        console.log('[Dashboard] 检测到视频文件模式已启用，自动切换到模拟模式')
      }
    }
  } catch (error) {
    console.error('[Dashboard] 获取视频文件模式配置失败:', error)
  }
}

// WebSocket
let ws = null
let reconnectTimer = null
let mockParameterTimer = null

const stopMockParameterTicker = () => {
  if (mockParameterTimer) {
    clearInterval(mockParameterTimer)
    mockParameterTimer = null
  }
}

const refreshMockParameterTicker = () => {
  stopMockParameterTicker()
  if (!isRunning.value || !settings.use_mock) return
  mockParameterTimer = setInterval(() => {
    mockRuntimeTick.value += 1
    currentLayerInfo.value = {
      ...currentLayerInfo.value,
      number: runtimeBase.currentLayer + Math.floor(mockRuntimeTick.value / 4)
    }
    latestData.frame_number = runtimeBase.sequence + mockRuntimeTick.value * 3
  }, 1000)
}

watch([isRunning, () => settings.use_mock, selectedDeviceId], () => {
  if (isRunning.value) {
    resetRuntimeBase()
  }
  refreshMockParameterTicker()
})

onMounted(async () => {
  try {
    await slsDeviceStore.loadDevicesFromBackend()
    ensureSelectedDevice()
  } catch (error) {
    ElMessage.error(error.message || '加载SLS设备群数据失败')
  }

  fetchStatus()
  fetchCameras()
  fetchVideoFileModeConfig()  // 获取视频文件模式配置

  if (isRunning.value) {
    connectWebSocket()
  }

  // 启动健康状态定期检查（每3秒检查一次，仅状态变化时刷新）
  healthCheckTimer = setInterval(() => {
    fetchBackendHealthStatus()
  }, 3000)
})

onUnmounted(() => {
  closeWebSocket()
  stopMockParameterTicker()
  // 清理健康状态检查定时器
  if (healthCheckTimer) {
    clearInterval(healthCheckTimer)
    healthCheckTimer = null
  }
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

.title-block {
  min-width: 240px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.device-subtitle {
  margin-top: 6px;
  color: #94a3b8;
  font-size: 13px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.device-switch {
  width: 220px;
}

.realtime-section,
.health-section {
  width: 100%;
}

.parameter-panel {
  padding: 16px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 8px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  color: #e2e8f0;
  font-weight: 600;
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.parameter-item {
  min-height: 76px;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid rgba(100, 116, 139, 0.22);
  background: rgba(30, 41, 59, 0.5);
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto 1fr;
  column-gap: 8px;
  align-items: end;
}

.parameter-name {
  grid-column: 1 / -1;
  color: #94a3b8;
  font-size: 12px;
}

.parameter-value {
  min-width: 0;
  color: #f8fafc;
  font-size: 22px;
  line-height: 1.1;
  overflow-wrap: anywhere;
}

.parameter-unit {
  color: #64748b;
  font-size: 12px;
  padding-bottom: 2px;
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

  .device-switch {
    width: 100%;
  }
}
</style>
