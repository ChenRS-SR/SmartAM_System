<template>
  <div class="slm-dashboard">
    <!-- 页面标题 -->
    <div class="dashboard-header">
      <div class="title-block">
        <h1 class="page-title">{{ selectedDeviceName }} 设备状态监测</h1>
        <div class="device-subtitle">
          {{ selectedDevice?.dataTag || '7103设备' }} · {{ selectedDevice?.model || 'SLM 设备' }} · {{ selectedDevice?.location || '未设置位置' }}
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
            v-for="device in slmDeviceStore.devices"
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
        <span
          class="header-status-pill"
          :class="settings.use_mock ? 'warning' : 'success'"
        >
          {{ settings.use_mock ? '模拟模式' : '真实硬件' }}
        </span>
        <span
          v-if="settings.use_mock"
          class="header-status-pill"
          :class="selectedMockSourceReady ? 'success' : 'info'"
        >
          {{ selectedMockCaseStatusText }}
        </span>
        <span
          class="header-status-pill"
          :class="isRunning ? 'success' : 'info'"
        >
          {{ isRunning ? '采集中' : '已停止' }}
        </span>
        <el-button 
          :type="isRunning ? 'danger' : 'primary'"
          @click="toggleAcquisition"
          :loading="starting"
        >
          {{ isRunning ? '停止采集' : '开始采集' }}
        </el-button>
      </div>
    </div>

    <section class="device-workspace">
      <div class="subpage-header">
        <div>
          <h2>{{ activePanelTitle }}</h2>
          <p>{{ activePanelDescription }}</p>
        </div>
        <div class="subpage-tabs">
          <el-button
            v-for="panel in panelNavItems"
            :key="panel.key"
            :type="activePanel === panel.key ? 'primary' : 'default'"
            plain
            @click="switchPanel(panel.key)"
          >
            {{ panel.name }}
          </el-button>
        </div>
      </div>

      <template v-if="activePanel === 'status'">
        <section v-if="settings.use_mock && selectedMockSourceType === 'stored7103'" class="stored-source-panel">
          <div>
            <strong>7103存储数据模拟</strong>
            <span>当前设备使用已导入的7103参数和诊断结果，不要求连接实时图像通道。</span>
          </div>
          <el-tag type="success" size="small">在线</el-tag>
        </section>

        <!-- 当前设备实时参数 -->
        <section class="parameter-panel">
          <div class="panel-header">
            <span>实时参数</span>
            <el-tag size="small" :type="selectedDisplayOnline ? 'success' : 'info'">
              {{ selectedDisplayOnline ? '在线' : '离线' }}
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
      </template>

      <template v-else-if="activePanel === 'control'">
        <!-- 华科四台模拟设备专用视觉处理，真实硬件和7103存储数据不受影响。 -->
        <section v-if="isHuakeVideoMockDevice" class="mock-vision-panel">
          <div class="mock-vision-copy">
            <strong>华科模拟视觉处理</strong>
            <span>ROI叠加已应用到三路视频，畸变校正可在原始视频和校正视频之间切换。</span>
          </div>
          <div class="mock-vision-actions">
            <el-tag type="success" size="small">ROI已叠加</el-tag>
            <el-switch
              v-model="distortionCorrectionEnabled"
              active-text="畸变校正"
              inactive-text="原始视频"
              :disabled="!canUseDistortionCorrection"
            />
          </div>
        </section>

        <!-- CH1/CH2/CH3 连接状态和视频画面同页展示。 -->
        <SensorConnectionStatus
          v-if="!settings.use_mock || selectedMockSourceType !== 'stored7103'"
          :sensor-status="sensorStatus"
          @toggle-sensor="handleToggleSensor"
          @refresh="refreshStatus"
        />

        <!-- 闭环调控页同步展示三路视频，便于观察调控效果。 -->
        <div class="control-video-section">
          <RealTimeDisplay
            :sensor-status="sensorStatus"
            :latest-data="latestData"
            :stream-key="streamKey"
            :display-paused="displayPaused"
            :last-frames="lastFrames"
            :use-mock-mode="settings.use_mock"
            :mock-source-type="selectedMockSourceType"
            :waiting-for-realtime="waitingForRealtimeData"
            :distortion-correction-enabled="canUseDistortionCorrection && distortionCorrectionEnabled"
          />
        </div>

        <!-- 闭环调控和特征曲线只在闭环调控子页面显示 -->
        <div class="regulation-section">
          <RegulationControl
            ref="regulationControl"
            :use-mock-mode="settings.use_mock"
            :mock-case="selectedMockCase"
            :mock-case-available="selectedMockCaseAvailability.ready"
            :is-acquiring="isRunning"
            @layer-changed="onLayerChanged"
          />
        </div>

        <div class="feature-curve-section">
          <FeatureCurvePanel
            :current-layer="currentLayerInfo.number"
            :is-layer-start="currentLayerInfo.isStart"
            :is-layer-end="currentLayerInfo.isEnd"
            :is-running="isRunning"
          />
        </div>
      </template>

      <template v-else>
        <!-- 设备健康状态 -->
        <div class="health-section">
          <EquipmentHealthStatus
            :health-data="healthData"
            :is-running="isRunning"
            :is-mock-mode="settings.use_mock"
            :diagnosis-data="diagnosisData"
          />
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

import SensorConnectionStatus from '../../components/slm/SensorConnectionStatus.vue'
import RealTimeDisplay from '../../components/slm/RealTimeDisplay.vue'
import EquipmentHealthStatus from '../../components/slm/EquipmentHealthStatus.vue'
import RegulationControl from '../../components/slm/RegulationControl.vue'
import FeatureCurvePanel from '../../components/slm/FeatureCurvePanel.vue'
import { useSlmDeviceStore } from '../../stores/slmDevices'
import { useROIStore } from '../../stores/roiStore'
import { readSlmBenchSettings } from '../../utils/slmBenchSettings'
import {
  buildMockCaseHealthData,
  buildMockCaseMedia,
  buildMockCaseStatusText,
  checkMockCaseMedia,
  getDeviceMockCase
} from '../../utils/slmMockCases'

const route = useRoute()
const router = useRouter()
const slmDeviceStore = useSlmDeviceStore()
const roiStore = useROIStore()
const HUAKE_VIDEO_DEVICE_IDS = new Set(['huake-slm-01', 'huake-slm-02', 'huake-slm-03', 'huake-slm-04'])

const selectedDeviceId = ref(route.params.deviceId || '')
const selectedDevice = computed(() => slmDeviceStore.getDeviceById(selectedDeviceId.value) || slmDeviceStore.firstDevice)
const selectedDeviceName = computed(() => selectedDevice.value?.name || 'SLM设备')
const selectedMockCase = computed(() => getDeviceMockCase(selectedDevice.value))
const distortionCorrectionEnabled = ref(localStorage.getItem('slmHuakeDistortionCorrection') !== '0')

const cloneHealthData = (healthData = {}) => ({
  ...healthData,
  status_labels: [...(healthData.status_labels || [])],
  laser_system: { ...(healthData.laser_system || {}) },
  powder_system: { ...(healthData.powder_system || {}) },
  gas_system: { ...(healthData.gas_system || {}) }
})

const isStored7103MockDevice = (device) => !getDeviceMockCase(device) && device?.source === '7103'
const selectedStored7103MockDevice = computed(() => isStored7103MockDevice(selectedDevice.value))
const selectedMockSourceType = computed(() => {
  if (selectedMockCase.value) return 'video'
  if (selectedStored7103MockDevice.value) return 'stored7103'
  return 'none'
})
const isHuakeVideoMockDevice = computed(() => (
  settings.use_mock
  && selectedMockSourceType.value === 'video'
  && HUAKE_VIDEO_DEVICE_IDS.has(selectedDeviceId.value)
))
const canUseDistortionCorrection = computed(() => (
  isHuakeVideoMockDevice.value && selectedMockCase.value?.correctedSupported
))

const panelNavItems = [
  { key: 'status', name: '实时状态信息', description: '集中显示实时参数和设备状态。' },
  { key: 'control', name: '闭环调控', description: '展示层进度、调控状态和特征曲线。' },
  { key: 'health', name: '设备健康状态', description: '展示 SLM 设备健康诊断和子系统状态。' }
]
const panelKeys = panelNavItems.map((item) => item.key)
const activePanel = computed(() => {
  const tab = String(route.query.tab || 'status')
  return panelKeys.includes(tab) ? tab : 'status'
})
const activePanelMeta = computed(() => panelNavItems.find((item) => item.key === activePanel.value) || panelNavItems[0])
const activePanelTitle = computed(() => activePanelMeta.value.name)
const activePanelDescription = computed(() => activePanelMeta.value.description)

// 状态
const isRunning = ref(false)
const starting = ref(false)
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
  camera_ch2: { enabled: false, connected: false },
  thermal: { enabled: false, connected: false }
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

const realtimeState = reactive({
  hasData: false,
  eventTime: '',
  receivedAt: '',
  parameters: [],
  media: {},
  diagnosis: null,
  health: null
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

// 华科实验台连接设置在设置页维护，监测页启动采集时只读取已保存配置。
const settings = reactive(readSlmBenchSettings())
const selectedDeviceOnline = computed(() => selectedDevice.value?.online !== false)
const waitingForRealtimeData = computed(() => !settings.use_mock && selectedDeviceOnline.value && !realtimeState.hasData)
const selectedMockCaseAvailability = reactive({
  hasCase: false,
  ready: false,
  allReady: false,
  channels: {},
  missing: []
})
const selectedMockSourceReady = computed(() => {
  if (!settings.use_mock) return false
  return selectedMockCaseAvailability.ready || selectedStored7103MockDevice.value
})
const selectedMockCaseStatusText = computed(() => {
  if (selectedStored7103MockDevice.value) return '7103存储数据'
  return buildMockCaseStatusText(selectedMockCase.value, selectedMockCaseAvailability)
})
const selectedDisplayOnline = computed(() => settings.use_mock ? selectedMockSourceReady.value : selectedDeviceOnline.value)
const selectedMockHealthData = computed(() => buildMockCaseHealthData(selectedMockCase.value))
const selectedStored7103HealthData = computed(() => {
  if (!selectedStored7103MockDevice.value || !selectedDevice.value?.healthData) return null
  return cloneHealthData(selectedDevice.value.healthData)
})

// RegulationControl 引用
const regulationControl = ref(null)

// 当前层信息（用于特征曲线）
const currentLayerInfo = ref({
  number: 0,
  isStart: false,
  isEnd: false
})

const ensureSelectedDevice = (routeDeviceId = route.params.deviceId) => {
  if (!slmDeviceStore.devices.length) return
  const fallbackDeviceId = slmDeviceStore.firstDevice?.id
  const nextDeviceId = routeDeviceId && slmDeviceStore.getDeviceById(routeDeviceId)
    ? routeDeviceId
    : fallbackDeviceId
  selectedDeviceId.value = nextDeviceId
  if (nextDeviceId) {
    localStorage.setItem('slmSelectedDeviceId', nextDeviceId)
  }
  if (nextDeviceId && routeDeviceId !== nextDeviceId) {
    router.replace({ path: `/slm/device/${nextDeviceId}`, query: { tab: activePanel.value } })
  }
}

watch([() => route.params.deviceId, () => slmDeviceStore.devices.length], ([deviceId]) => {
  ensureSelectedDevice(deviceId)
}, { immediate: true })

const applySelectedMockHealth = () => {
  if (!settings.use_mock) return false
  if (selectedMockCase.value) {
    if (selectedMockCaseAvailability.ready && selectedMockHealthData.value) {
      applyHealthData(selectedMockHealthData.value)
      return true
    }
    resetHealthToWaiting('模拟用例未连接')
    return false
  }
  if (selectedStored7103HealthData.value) {
    applyHealthData(selectedStored7103HealthData.value)
    return true
  }
  resetHealthToWaiting('未配置模拟用例')
  return false
}

const syncMockHealthFromSelectedDevice = () => {
  if (settings.use_mock) {
    applySelectedMockHealth()
  } else {
    resetHealthToWaiting(selectedDeviceOnline.value ? '等待实时数据' : '离线')
  }
}

watch([selectedDevice, () => settings.use_mock, () => selectedMockCaseAvailability.ready], () => {
  syncMockHealthFromSelectedDevice()
}, { immediate: true })

const goToDeviceGroup = () => {
  router.push('/slm/dashboard')
}

const switchDevice = (deviceId) => {
  localStorage.setItem('slmSelectedDeviceId', deviceId)
  router.push({ path: `/slm/device/${deviceId}`, query: { tab: activePanel.value } })
}

const switchPanel = (panelKey) => {
  router.push({
    path: selectedDeviceId.value ? `/slm/device/${selectedDeviceId.value}` : '/slm/device',
    query: { tab: panelKey }
  })
}

const applySensorStatus = (status = {}, options = {}) => {
  const sensorKeys = ['camera_ch1', 'camera_ch2', 'thermal']
  sensorKeys.forEach((key) => {
    if (status[key]) {
      const nextStatus = { ...status[key] }
      if (!options.syncEnabled) {
        delete nextStatus.enabled
      }
      sensorStatus[key] = {
        ...sensorStatus[key],
        ...nextStatus
      }
    }
  })
}

const applyModeSensorDefaults = () => {
  sensorStatus.camera_ch1.enabled = true
  sensorStatus.camera_ch1.connected = false
  sensorStatus.camera_ch2.enabled = false
  sensorStatus.camera_ch2.connected = false
  sensorStatus.thermal.enabled = false
  sensorStatus.thermal.connected = false
}

const syncHealthDataToDevice = () => {
  if (settings.use_mock && selectedStored7103MockDevice.value) return
  if (selectedDeviceId.value) {
    slmDeviceStore.updateDeviceHealth(selectedDeviceId.value, {
      ...healthData,
      status_labels: [...(healthData.status_labels || [])],
      laser_system: { ...(healthData.laser_system || {}) },
      powder_system: { ...(healthData.powder_system || {}) },
      gas_system: { ...(healthData.gas_system || {}) }
    })
  }
}

function applyHealthData(nextHealth = {}) {
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

const resetRealtimeState = () => {
  realtimeState.hasData = false
  realtimeState.eventTime = ''
  realtimeState.receivedAt = ''
  realtimeState.parameters = []
  realtimeState.media = {}
  realtimeState.diagnosis = null
  realtimeState.health = null
  latestData.camera_ch1 = null
  latestData.camera_ch2 = null
  latestData.thermal = null
  lastFrames.CH1 = null
  lastFrames.CH2 = null
  lastFrames.thermal = null
  sensorStatus.camera_ch1.connected = false
  sensorStatus.camera_ch2.connected = false
  sensorStatus.thermal.connected = false
}

function resetHealthToWaiting(label = '等待实时数据') {
  healthData.status = 'power_off'
  healthData.status_code = -1
  healthData.status_labels = [label]
  healthData.laser_system = { status: 'unknown', message: label }
  healthData.powder_system = { status: 'unknown', message: label }
  healthData.gas_system = { status: 'unknown', message: label }
  Object.assign(latestData.health, healthData)
}

const applyRealtimeSample = (sample = {}) => {
  if (!selectedDeviceOnline.value) return
  realtimeState.hasData = Boolean(sample.hasData)
  realtimeState.eventTime = sample.eventTime || ''
  realtimeState.receivedAt = sample.receivedAt || ''
  realtimeState.parameters = Array.isArray(sample.parameters) ? sample.parameters : []
  realtimeState.media = sample.media || {}
  realtimeState.diagnosis = sample.diagnosis || null
  realtimeState.health = sample.health || null
  const mediaMap = {
    camera_ch1: realtimeState.media?.ch1 || realtimeState.media?.camera_ch1,
    camera_ch2: realtimeState.media?.ch2 || realtimeState.media?.camera_ch2,
    thermal: realtimeState.media?.ch3 || realtimeState.media?.thermal
  }
  Object.entries(mediaMap).forEach(([key, media]) => {
    const frameKey = key === 'camera_ch1' ? 'CH1' : key === 'camera_ch2' ? 'CH2' : 'thermal'
    const hasMedia = Boolean(media?.data_url || media?.url)
    latestData[key] = hasMedia ? { ...media, updated_at: realtimeState.eventTime } : null
    lastFrames[frameKey] = hasMedia ? (media.data_url || media.url) : null
    sensorStatus[key].enabled = hasMedia
    sensorStatus[key].connected = hasMedia
  })
  if (realtimeState.hasData && realtimeState.health) {
    applyHealthData(realtimeState.health)
  } else if (!settings.use_mock) {
    resetHealthToWaiting(selectedDeviceOnline.value ? '等待实时数据' : '离线')
  }
}

const resetMockCaseAvailability = (overrides = {}) => {
  Object.assign(selectedMockCaseAvailability, {
    hasCase: false,
    ready: false,
    allReady: false,
    channels: {},
    missing: [],
    ...overrides
  })
}

const clearMockMedia = () => {
  ;['camera_ch1', 'camera_ch2', 'thermal'].forEach((key) => {
    latestData[key] = null
    sensorStatus[key].enabled = true
    sensorStatus[key].connected = false
  })
  lastFrames.CH1 = null
  lastFrames.CH2 = null
  lastFrames.thermal = null
}

const clearStored7103Media = () => {
  ;['camera_ch1', 'camera_ch2', 'thermal'].forEach((key) => {
    latestData[key] = null
    sensorStatus[key].enabled = false
    sensorStatus[key].connected = false
  })
  lastFrames.CH1 = null
  lastFrames.CH2 = null
  lastFrames.thermal = null
}

const getMockVideoOptions = () => ({
  distortionCorrected: canUseDistortionCorrection.value && distortionCorrectionEnabled.value
})

const applyMockMediaUrls = () => {
  if (!settings.use_mock || !selectedMockCase.value) return
  const media = buildMockCaseMedia(selectedMockCase.value, streamKey.value, getMockVideoOptions())
  const frameKeyMap = {
    camera_ch1: 'CH1',
    camera_ch2: 'CH2',
    thermal: 'thermal'
  }

  ;['camera_ch1', 'camera_ch2', 'thermal'].forEach((key) => {
    const channelReady = Boolean(selectedMockCaseAvailability.channels?.[key])
    latestData[key] = channelReady ? media[key] : null
    lastFrames[frameKeyMap[key]] = channelReady ? media[key]?.url : null
    sensorStatus[key].enabled = true
    sensorStatus[key].connected = channelReady
  })
}

const applySelectedMockMedia = () => {
  if (!settings.use_mock) return
  if (selectedMockCase.value) {
    applyMockMediaUrls()
  } else if (selectedStored7103MockDevice.value) {
    clearStored7103Media()
  } else {
    clearMockMedia()
  }
}

let mockCaseProbeSerial = 0
const refreshSelectedMockCase = async () => {
  mockCaseProbeSerial += 1
  const serial = mockCaseProbeSerial

  if (!settings.use_mock) {
    resetMockCaseAvailability()
    return
  }

  clearMockMedia()
  if (!selectedMockCase.value) {
    if (selectedStored7103MockDevice.value) {
      clearStored7103Media()
    }
    resetMockCaseAvailability()
    return
  }

  const availability = await checkMockCaseMedia(selectedMockCase.value, getMockVideoOptions())
  if (serial !== mockCaseProbeSerial) return
  resetMockCaseAvailability(availability)
  applyMockMediaUrls()
}

let huakeRoiConfigLoaded = false
const loadHuakeRoiConfig = async () => {
  if (!isHuakeVideoMockDevice.value) return
  if (huakeRoiConfigLoaded && roiStore.hasConfig) return

  try {
    const response = await axios.get('/api/slm/roi/config')
    const config = response.data?.config
    if (!response.data?.success || !config?.rois || !Object.keys(config.rois).length) {
      ElMessage.warning('未读取到ROI配置')
      return
    }
    roiStore.setROIConfig(config)
    huakeRoiConfigLoaded = true
  } catch (error) {
    console.error('[Dashboard] 华科ROI配置加载失败:', error)
    ElMessage.warning('华科ROI配置加载失败')
  }
}

const formatRuntimeValue = (value, digits = 1) => {
  if (value === undefined || value === null || value === '') return '--'
  if (typeof value === 'number') return Number.isInteger(value) ? value : value.toFixed(digits)
  return value
}

const padNumber = (value) => String(value).padStart(2, '0')

const formatDateTime = (date = new Date()) => {
  const year = date.getFullYear()
  const month = padNumber(date.getMonth() + 1)
  const day = padNumber(date.getDate())
  const hours = padNumber(date.getHours())
  const minutes = padNumber(date.getMinutes())
  const seconds = padNumber(date.getSeconds())
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
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

watch([selectedDevice, () => settings.use_mock], () => {
  refreshSelectedMockCase()
}, { immediate: true })

watch(streamKey, () => {
  applySelectedMockMedia()
})

watch(isHuakeVideoMockDevice, (enabled) => {
  if (enabled) {
    loadHuakeRoiConfig()
  }
}, { immediate: true })

watch(distortionCorrectionEnabled, async (enabled) => {
  localStorage.setItem('slmHuakeDistortionCorrection', enabled ? '1' : '0')
  if (!isHuakeVideoMockDevice.value) return
  streamKey.value = Date.now()
  await refreshSelectedMockCase()
})

const emptyLiveParameters = () => fixedParameterSchema.map((schema) => ({ ...schema }))

const baseDeviceParameters = () => selectedDevice.value?.parameters?.length
  ? selectedDevice.value.parameters
  : fixedParameterSchema

const decimalPlaces = (value) => {
  const text = String(value)
  if (!text.includes('.')) return 0
  return Math.min(text.split('.')[1].length, 3)
}

const mockNumericValue = (schema, rawValue, index) => {
  const base = Number(rawValue)
  if (!Number.isFinite(base)) return rawValue ?? '--'
  const unit = schema.unit || ''
  const baseAmplitude = Math.abs(base) * 0.004
  const unitAmplitude = unit === '℃'
    ? 0.25
    : unit === 'Bar' || unit === 'mBar'
      ? 0.02
      : unit === '%' || unit === 'm3/h'
        ? 0.05
        : 0.1
  const amplitude = baseAmplitude + unitAmplitude
  const wave = Math.sin((mockRuntimeTick.value + index) * 0.71) * amplitude
  const nextValue = base + wave
  const digits = decimalPlaces(rawValue)
  return digits === 0 ? String(Math.round(nextValue)) : nextValue.toFixed(digits)
}

const buildMockLiveParameters = () => {
  const baseParameters = baseDeviceParameters()
  return fixedParameterSchema.map((schema, index) => {
    const matched = baseParameters.find((param) => param.id === schema.id || param.name === schema.name)
    const baseValue = matched?.value ?? schema.value
    let value = baseValue
    if (schema.id === 'current_layer') {
      value = isRunning.value ? formatRuntimeValue(runtimeBase.currentLayer + Math.floor(mockRuntimeTick.value / 4), 0) : baseValue
    } else if (schema.id === 'sequence') {
      value = isRunning.value ? formatRuntimeValue(runtimeBase.sequence + mockRuntimeTick.value * 3, 0) : baseValue
    } else if (schema.id === 'data_time') {
      value = isRunning.value ? formatDateTime() : baseValue
    } else if (schema.id === 'record_status') {
      value = currentStatusParameterText()
    } else if (isRunning.value && baseValue !== '--') {
      value = mockNumericValue(schema, baseValue, index)
    }
    return {
      ...schema,
      value: value ?? '--',
      unit: matched?.unit ?? schema.unit
    }
  })
}

const buildRealtimeLiveParameters = () => {
  if (!realtimeState.hasData) return emptyLiveParameters()
  const source = Array.isArray(realtimeState.parameters) ? realtimeState.parameters : []
  return fixedParameterSchema.map((schema) => {
    const matched = source.find((param) => param.id === schema.id || param.name === schema.name)
    return {
      ...schema,
      value: matched?.value ?? '--',
      unit: matched?.unit ?? schema.unit
    }
  })
}

const liveParameters = computed(() => {
  return settings.use_mock ? buildMockLiveParameters() : buildRealtimeLiveParameters()
})

const diagnosisData = computed(() => {
  if (settings.use_mock) {
    const diagnosis = selectedDevice.value?.diagnosis || {}
    const mockHealth = selectedMockHealthData.value || selectedStored7103HealthData.value
    const mockStatusCode = mockHealth?.status_code ?? selectedDevice.value?.healthData?.status_code ?? -1
    const mockStatusLabel = mockHealth?.status_labels?.join('、') || selectedDevice.value?.statusText || '模拟样本'
    return {
      enabled: true,
      modelVersion: selectedStored7103MockDevice.value ? '7103存储数据模拟' : '设备绑定模拟用例',
      statusCode: diagnosis.rawStatusCode ?? mockStatusCode,
      statusLabel: mockStatusLabel,
      frontendStatusCode: mockStatusCode,
      frontendStatusLabel: mockStatusLabel,
      confidence: diagnosis.confidence ?? null,
      confidenceText: diagnosis.confidence ? `${(diagnosis.confidence * 100).toFixed(1)}%` : '--',
      faultModes: diagnosis.categories || [],
      eventTime: isRunning.value ? formatDateTime() : selectedDevice.value?.updatedAt || '',
      modelLayer: 'mock_7103',
      input: { alarmCount: 0, parameterCount: liveParameters.value.filter((item) => item.value !== '--').length },
      evidence: diagnosis.evidence || []
    }
  }
  if (realtimeState.hasData && realtimeState.diagnosis) return realtimeState.diagnosis
  return {
    enabled: true,
    modelVersion: '',
    statusCode: -1,
    statusLabel: '等待实时数据',
    frontendStatusCode: -1,
    frontendStatusLabel: '等待实时数据',
    confidence: null,
    confidenceText: '--',
    faultModes: [],
    eventTime: '',
    modelLayer: 'waiting',
    input: { alarmCount: 0, parameterCount: 0 },
    evidence: []
  }
})

let lastParameterSignature = ''
watch(liveParameters, (parameters) => {
  if (selectedDeviceId.value && settings.use_mock) {
    const signature = JSON.stringify(parameters)
    if (signature === lastParameterSignature) return
    lastParameterSignature = signature
  }
}, { deep: true })

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
      if (settings.use_mock) {
        applySelectedMockMedia()
      } else {
        applyModeSensorDefaults()
      }
      
      // 模拟模式使用当前设备绑定的用例；真实模式等待外部实时接口事件。
      if (settings.use_mock) {
        applySelectedMockHealth()
  } else if (!settings.use_mock && !realtimeState.hasData) {
        resetHealthToWaiting(selectedDeviceOnline.value ? '等待实时数据' : '离线')
      }
      
      // 如果采集刚停止（wasRunning && !isRunning），立即重置健康状态为未开机
      if (wasRunning && !isRunning.value) {
        console.log('[Dashboard] 刷新状态：采集已停止，重置健康状态为未开机')
        if (settings.use_mock && selectedStored7103MockDevice.value) {
          applySelectedMockHealth()
        } else {
          healthData.status = 'power_off'
          healthData.status_code = -1
          healthData.status_labels = []
          healthData.laser_system = { status: 'unknown', message: '未检测' }
          healthData.powder_system = { status: 'unknown', message: '未检测' }
          healthData.gas_system = { status: 'unknown', message: '未检测' }
          syncHealthDataToDevice()
        }
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

const activateRunningView = async () => {
  resetRuntimeBase()
  mockRuntimeTick.value = 0
  resetRealtimeState()
  if (settings.use_mock) {
    closeWebSocket()
  }
  isRunning.value = true
  streamKey.value = Date.now()
  if (settings.use_mock) {
    await refreshSelectedMockCase()
    applySelectedMockMedia()
    applySelectedMockHealth()
  } else {
    applyModeSensorDefaults()
    resetHealthToWaiting(selectedDeviceOnline.value ? '等待实时数据' : '离线')
    if (selectedDeviceOnline.value) {
      connectWebSocket()
    }
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
      resetRealtimeState()
      
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      // 重置传感器状态为未连接
      Object.keys(sensorStatus).forEach(key => {
        if (sensorStatus[key]) sensorStatus[key].connected = false
      })
      
      // 重置健康状态为未开机（状态码-1）
      if (settings.use_mock && selectedStored7103MockDevice.value) {
        applySelectedMockMedia()
        applySelectedMockHealth()
      } else {
        healthData.status = 'power_off'
        healthData.status_code = -1
        healthData.status_labels = []
        healthData.laser_system = { status: 'unknown', message: '未检测' }
        healthData.powder_system = { status: 'unknown', message: '未检测' }
        healthData.gas_system = { status: 'unknown', message: '未检测' }
        syncHealthDataToDevice()
      }
      
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
    if (!settings.use_mock && !selectedDeviceOnline.value) {
      ElMessage.warning('当前设备在device.json中为online:false，已禁止真实数据接入')
      return
    }
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
        await activateRunningView()
        const modeText = settings.use_mock ? '模拟模式' : '真实硬件模式'
        ElMessage.success(`采集已启动 (${modeText})`)
      } else if (settings.use_mock && String(response.data.message || '').includes('采集已在运行中')) {
        // 后端已运行时仍刷新当前设备绑定的视频用例，避免前端停在“未加载视频”状态。
        await activateRunningView()
        ElMessage.success('采集已在运行，已刷新模拟视频')
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
      if (isRunning.value && selectedDeviceOnline.value) {
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
  if (settings.use_mock) {
    return
  }
  if (!selectedDeviceOnline.value) {
    return
  }

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

  if (settings.use_mock) {
    await refreshSelectedMockCase()
  }
  
  // 强制刷新视频流（更新streamKey使URL变化，防止缓存）
  streamKey.value = Date.now()
  applySelectedMockMedia()
  // 刷新闭环调控组件状态
  if (regulationControl.value && regulationControl.value.refresh) {
    regulationControl.value.refresh()
  }
  ElMessage.success('状态已刷新')
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

// WebSocket
let ws = null
let reconnectTimer = null
let mockParameterTimer = null
let realtimePollTimer = null

const refreshBenchSettings = () => {
  Object.assign(settings, readSlmBenchSettings())
}

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

const fetchRealtimeSample = async () => {
  if (settings.use_mock || !selectedDeviceId.value || !selectedDeviceOnline.value) return
  try {
    const response = await axios.get(`/api/slm/realtime/data/${encodeURIComponent(selectedDeviceId.value)}`)
    if (response.data.success && response.data.sample) {
      applyRealtimeSample(response.data.sample)
    }
  } catch (error) {
    console.error('[Dashboard] 获取实时参数失败:', error)
  }
}

const stopRealtimePoller = () => {
  if (realtimePollTimer) {
    clearInterval(realtimePollTimer)
    realtimePollTimer = null
  }
}

const refreshRealtimePoller = () => {
  stopRealtimePoller()
  if (settings.use_mock || !selectedDeviceId.value || !selectedDeviceOnline.value) {
    if (!settings.use_mock) resetRealtimeState()
    if (!settings.use_mock && !selectedDeviceOnline.value) resetHealthToWaiting('离线')
    return
  }
  fetchRealtimeSample()
  realtimePollTimer = setInterval(fetchRealtimeSample, 1000)
}

watch([isRunning, () => settings.use_mock, selectedDeviceId, selectedDeviceOnline], () => {
  if (isRunning.value) {
    resetRuntimeBase()
    if (settings.use_mock) {
      applySelectedMockHealth()
    } else if (!settings.use_mock) {
      resetHealthToWaiting(selectedDeviceOnline.value ? '等待实时数据' : '离线')
    }
  }
  refreshMockParameterTicker()
  refreshRealtimePoller()
}, { immediate: true })

watch(() => settings.use_mock, () => {
  applyModeSensorDefaults()
  if (settings.use_mock) {
    closeWebSocket()
    resetRealtimeState()
    applySelectedMockMedia()
    syncMockHealthFromSelectedDevice()
  } else {
    resetRealtimeState()
    resetHealthToWaiting(selectedDeviceOnline.value ? '等待实时数据' : '离线')
  }
})

onMounted(async () => {
  refreshBenchSettings()
  roiStore.loadFromStorage()
  applyModeSensorDefaults()

  try {
    await slmDeviceStore.loadDevicesFromBackend()
    ensureSelectedDevice()
    await loadHuakeRoiConfig()
  } catch (error) {
    ElMessage.error(error.message || '加载7103设备群数据失败')
  }

  fetchStatus()
  
  if (isRunning.value && !settings.use_mock && selectedDeviceOnline.value) {
    connectWebSocket()
  }
  
  window.addEventListener('focus', refreshBenchSettings)
  window.addEventListener('storage', refreshBenchSettings)
})

onUnmounted(() => {
  closeWebSocket()
  stopMockParameterTicker()
  stopRealtimePoller()
  window.removeEventListener('focus', refreshBenchSettings)
  window.removeEventListener('storage', refreshBenchSettings)
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

.header-actions :deep(.el-tag) {
  min-width: 72px;
  justify-content: center;
}

.header-status-pill {
  min-width: 72px;
  height: 32px;
  padding: 0 12px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #f8fafc;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.header-status-pill.success {
  background: rgba(34, 197, 94, 0.22);
  border: 1px solid rgba(34, 197, 94, 0.48);
}

.header-status-pill.warning {
  background: rgba(245, 158, 11, 0.24);
  border: 1px solid rgba(245, 158, 11, 0.5);
}

.header-status-pill.info {
  background: rgba(100, 116, 139, 0.26);
  border: 1px solid rgba(148, 163, 184, 0.32);
  color: #cbd5e1;
}

.device-switch {
  width: 220px;
}

.device-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.subpage-header {
  min-height: 72px;
  padding: 14px 16px;
  border: 1px solid rgba(100, 116, 139, 0.28);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.subpage-header h2 {
  margin: 0;
  color: #e2e8f0;
  font-size: 18px;
  font-weight: 600;
}

.subpage-header p {
  margin: 6px 0 0;
  color: #94a3b8;
  font-size: 13px;
}

.subpage-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.realtime-section,
.regulation-section,
.feature-curve-section,
.health-section {
  width: 100%;
}

.parameter-panel {
  padding: 16px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 8px;
}

.stored-source-panel {
  min-height: 76px;
  padding: 16px;
  background: rgba(14, 116, 144, 0.16);
  border: 1px solid rgba(56, 189, 248, 0.34);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.stored-source-panel div {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.stored-source-panel strong {
  color: #e0f2fe;
  font-size: 15px;
}

.stored-source-panel span {
  color: #bae6fd;
  font-size: 13px;
}

.mock-vision-panel {
  min-height: 76px;
  padding: 14px 16px;
  background: rgba(21, 128, 61, 0.14);
  border: 1px solid rgba(34, 197, 94, 0.32);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.mock-vision-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mock-vision-copy strong {
  color: #dcfce7;
  font-size: 15px;
}

.mock-vision-copy span {
  color: #bbf7d0;
  font-size: 13px;
}

.mock-vision-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
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

  .subpage-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .subpage-tabs {
    width: 100%;
  }

  .stored-source-panel {
    align-items: flex-start;
    flex-direction: column;
  }

  .mock-vision-panel {
    align-items: flex-start;
    flex-direction: column;
  }

  .mock-vision-actions {
    justify-content: flex-start;
  }
}
</style>
