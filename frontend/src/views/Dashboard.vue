<template>
  <div class="dashboard">
    <!-- 骨架屏加载状态 -->
    <div v-if="!store.connected && !store.sensorData.printer" class="skeleton-status-cards">
      <SkeletonStatus v-for="i in 6" :key="i" />
    </div>
    
    <!-- 状态卡片行 -->
    <div v-else class="status-cards" :style="{ gridTemplateColumns: `repeat(${gridCols}, 1fr)` }">
      <StatusCard
        icon="Printer"
        label="打印机状态"
        :value="store.latestData.printer.state"
        :iconBg="statusColor"
        :iconColor="statusTextColor"
      />
      <StatusCard
        icon="Cpu"
        label="喷嘴温度"
        :value="currentTemps.nozzle.toFixed(1)"
        unit="°C"
        :subValue="'目标: ' + currentTemps.nozzleTarget.toFixed(0) + '°C'"
      />
      <StatusCard
        icon="FirstAidKit"
        label="热床温度"
        :value="currentTemps.bed.toFixed(1)"
        unit="°C"
        :subValue="'目标: ' + currentTemps.bedTarget.toFixed(0) + '°C'"
        :iconBg="'rgba(0, 255, 136, 0.2)'"
        :iconColor="'#00ff88'"
      />
      <StatusCard
        icon="VideoCamera"
        label="IDS 相机"
        :value="store.latestData.camera.ids_frame_count"
        unit="帧"
        :iconBg="store.latestData.camera.ids_available ? 'rgba(0, 255, 136, 0.2)' : 'rgba(255, 77, 79, 0.2)'"
        :iconColor="store.latestData.camera.ids_available ? '#00ff88' : '#ff4d4f'"
      />
      <StatusCard
        icon="Document"
        label="当前文件"
        :value="store.latestData.printer.filename || '无'"
        :subValue="printTimeLeft"
      />
      <StatusCard
        icon="View"
        label="打印进度"
        :value="store.latestData.printer.progress.toFixed(1)"
        unit="%"
        :subValue="printStatusText"
      />
      <!-- 采集状态卡片 -->
      <StatusCard
        icon="VideoPlay"
        label="采集状态"
        :value="acquisitionStateText"
        :subValue="acquisitionInfo"
        :iconBg="acquisitionStateColor"
        iconColor="#fff"
      />
      <!-- 当前参数卡片 -->
      <StatusCard
        icon="SetUp"
        label="打印参数"
        :value="currentZHeight"
        unit="mm"
        :subValue="printParamsText"
      />
    </div>
    
    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：视频流 -->
      <div class="video-section">
        <el-card class="video-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>实时监控</span>
              <div class="stream-selector">
                <el-radio-group v-model="currentStream" size="small">
                  <el-radio-button value="combined">组合画面</el-radio-button>
                  <el-radio-button value="ids">IDS相机</el-radio-button>
                  <el-radio-button value="side">旁轴相机</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <div class="video-container">
            <img 
              v-show="videoConnected"
              :src="streamUrl" 
              class="video-stream"
              alt="视频流"
              @load="videoConnected = true"
              @error="handleVideoError"
            />
            <div v-if="!videoConnected" class="video-error">
              <el-icon size="48" color="#666"><VideoCamera /></el-icon>
              <span>{{ videoError || '视频流加载中...' }}</span>
              <el-button 
                v-if="videoError" 
                type="primary" 
                size="small"
                @click="reconnectVideo"
              >
                <el-icon><Refresh /></el-icon>
                重新连接
              </el-button>
            </div>
          </div>
        </el-card>
        
        <!-- 温度图表 -->
        <TemperatureChart title="温度趋势" />
      </div>
      
      <!-- 右侧：预测和控制 -->
      <div class="side-section">
        <!-- 文件管理 -->
        <PrintFileManager />
        
        <!-- PacNet 预测结果 -->
        <PredictionPanel :prediction="store.latestData.prediction" />
        
        <!-- 控制面板 -->
        <ControlPanel />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useDataStore } from '../stores/data'
import { useResponsive } from '../composables/useResponsive'
import { useNotification } from '../composables/useNotification'
import { printerApi } from '../utils/api'
import StatusCard from '../components/StatusCard.vue'
import SkeletonStatus from '../components/SkeletonStatus.vue'
import PredictionPanel from '../components/PredictionPanel.vue'
import TemperatureChart from '../components/TemperatureChart.vue'
import ControlPanel from '../components/ControlPanel.vue'
import PrintFileManager from '../components/PrintFileManager.vue'

const store = useDataStore()

// 调试：监视 acquisition 数据变化
watch(() => store.sensorData.acquisition, (newVal, oldVal) => {
  console.log('[Dashboard Watch] acquisition changed:', {
    from: oldVal,
    to: newVal
  })
}, { deep: true })

// 调试：监视 printer.position 变化
watch(() => store.sensorData.printer?.position, (newVal, oldVal) => {
  console.log('[Dashboard Watch] printer.position changed:', {
    from: oldVal,
    to: newVal
  })
}, { deep: true })

const { gridCols, isMobile } = useResponsive()
const { handlePredictionAlert, handlePrintEvent } = useNotification()

// 当前温度
const currentTemps = ref({
  nozzle: 0,
  nozzleTarget: 0,
  bed: 0,
  bedTarget: 0
})

// 获取实时温度
const fetchTemperature = async () => {
  try {
    const res = await printerApi.getTemperature()
    if (res.data.success) {
      currentTemps.value = {
        nozzle: res.data.nozzle.actual,
        nozzleTarget: res.data.nozzle.target,
        bed: res.data.bed.actual,
        bedTarget: res.data.bed.target
      }
    }
  } catch (e) {
    console.log('获取温度失败:', e)
  }
}

// 视频流连接状态
const videoConnected = ref(false)
const videoError = ref('')
const videoRetryCount = ref(0)
const MAX_RETRY = 3

// 处理视频加载错误
const handleVideoError = () => {
  videoConnected.value = false
  videoRetryCount.value++
  
  if (videoRetryCount.value >= MAX_RETRY) {
    videoError.value = '视频流连接失败，请检查后端服务'
  } else {
    videoError.value = `连接失败，正在重试 (${videoRetryCount.value}/${MAX_RETRY})...`
    setTimeout(reconnectVideo, 2000)
  }
}

// 重新连接视频流
const reconnectVideo = () => {
  videoConnected.value = false
  videoError.value = ''
  videoRetryCount.value = 0
  // 强制刷新图片源（添加时间戳）
  const streamType = currentStream.value
  currentStream.value = ''
  setTimeout(() => {
    currentStream.value = streamType
  }, 100)
}

// 监听预测变化，触发告警
watch(() => store.latestData.prediction, (newVal, oldVal) => {
  if (newVal?.available && newVal !== oldVal) {
    handlePredictionAlert(newVal)
  }
}, { deep: true })

// 监听打印状态变化
watch(() => store.latestData.printer.state, (newState, oldState) => {
  if (newState !== oldState) {
    const eventMap = {
      'Printing': 'PrintStarted',
      'Operational': oldState === 'Printing' ? 'PrintDone' : null,
      'Paused': 'PrintPaused'
    }
    const eventType = eventMap[newState]
    if (eventType) {
      handlePrintEvent(eventType, {
        filename: store.latestData.printer.filename,
        progress: store.latestData.printer.progress
      })
    }
  }
})

const currentStream = ref('combined')
const streamTimestamp = ref(Date.now())

const streamUrl = computed(() => {
  const urls = {
    'combined': '/video_feed',
    'ids': '/video_feed/ids',
    'side': '/video_feed/side'
  }
  const baseUrl = urls[currentStream.value]
  return baseUrl ? `${baseUrl}?t=${streamTimestamp.value}` : ''
})

// 监听流类型变化，重置连接状态
watch(currentStream, () => {
  videoConnected.value = false
  videoError.value = ''
  videoRetryCount.value = 0
  streamTimestamp.value = Date.now()
})

const statusColor = computed(() => {
  const state = store.latestData.printer.state
  if (state === 'Operational') return 'rgba(0, 255, 136, 0.2)'
  if (state === 'Printing') return 'rgba(0, 212, 255, 0.2)'
  return 'rgba(255, 193, 7, 0.2)'
})

const statusTextColor = computed(() => {
  const state = store.latestData.printer.state
  if (state === 'Operational') return '#00ff88'
  if (state === 'Printing') return '#00d4ff'
  return '#ffc107'
})

// 打印状态文本
const printStatusText = computed(() => {
  const state = store.latestData.printer.state
  if (state === 'Printing') return '正在打印'
  if (state === 'Paused') return '已暂停'
  if (state === 'Operational') return '待机中'
  if (state === 'Offline') return '离线'
  return state || '未知'
})

// 剩余时间文本
const printTimeLeft = computed(() => {
  const seconds = store.latestData.printer.print_time_left
  if (!seconds || seconds <= 0) return ''
  
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  
  if (hours > 0) {
    return `剩余 ${hours}小时${mins}分钟`
  } else {
    return `剩余 ${mins}分钟`
  }
})

// 采集状态文本（包含详细区间信息）
const acquisitionStateText = computed(() => {
  // 直接从 store 获取原始数据
  const acq = store.sensorData.acquisition
  
  // 调试输出（每3秒一次）
  const now = Date.now()
  if (!window._lastAcqLog || now - window._lastAcqLog > 3000) {
    console.log('[Dashboard] acquisition raw:', store.sensorData.acquisition)
    console.log('[Dashboard] acquisition latestData:', store.latestData.acquisition)
    window._lastAcqLog = now
  }
  
  if (!acq) return '未连接'
  const state = acq.state
  if (state !== 'running') {
    if (state === 'paused') return '已暂停'
    if (state === 'idle') return '未开始'
    return state || '未知'
  }
  
  // 采集中：显示详细区间
  const z = acq.current_z || 0
  const mode = acq.param_mode || 'fixed'
  
  if (mode === 'tower') {
    if (z < 5.0) {
      return '开始0-5mm'
    } else if (z < 5.5) {
      return '5-5.5静默区'
    } else if (z < 9.5) {
      return '5.5-9.5记录区'
    } else if (z < 10.0) {
      return '9.5-10等待区'
    } else {
      // 计算当前是第几段
      const segment = Math.floor((z - 5) / 5) + 2  // 第2段开始
      const inSegment = (z - 5) % 5
      if (inSegment < 0.5) {
        return `${segment}段静默区`
      } else if (inSegment < 4.5) {
        return `${segment}段记录区`
      } else {
        return `${segment}段等待区`
      }
    }
  }
  
  return '采集中'
})

// 采集状态颜色
const acquisitionStateColor = computed(() => {
  // 直接使用原始数据
  const acq = store.sensorData.acquisition
  if (!acq) return 'rgba(128, 128, 128, 0.2)'
  const state = acq.state
  if (state === 'running') return 'rgba(0, 255, 136, 0.3)'
  if (state === 'paused') return 'rgba(255, 193, 7, 0.3)'
  return 'rgba(128, 128, 128, 0.2)'
})

// 采集信息（帧数/时长）
const acquisitionInfo = computed(() => {
  // 直接使用原始数据
  const acq = store.sensorData.acquisition
  if (!acq || !acq.state || acq.state === 'idle') return ''
  const frames = acq.frame_count || 0
  const duration = acq.duration || 0
  const mins = Math.floor(duration / 60)
  const secs = Math.floor(duration % 60)
  return `${frames}帧 / ${mins}分${secs}秒`
})

// 当前Z高度（优先从 printer.position 获取）
const currentZHeight = computed(() => {
  // 优先从原始数据获取
  const printerZ = store.sensorData.printer?.position?.z
  
  if (printerZ !== undefined && printerZ !== null && !isNaN(printerZ) && printerZ > 0) {
    return 'Z: ' + Number(printerZ).toFixed(2)
  }
  // 回退到 acquisition.current_z
  const acqZ = store.sensorData.acquisition?.current_z
  
  if (acqZ !== undefined && acqZ !== null && !isNaN(acqZ) && acqZ > 0) {
    return 'Z: ' + Number(acqZ).toFixed(2)
  }
  return 'Z: 0.00'
})

// 打印参数文本
const printParamsText = computed(() => {
  // 直接使用原始数据
  const acq = store.sensorData.acquisition
  if (!acq) return '未连接'
  const params = acq.current_params || {}
  const fr = params.flow_rate || 0
  const v = params.feed_rate || 0
  const th = params.target_hotend || 0
  const z_off = params.z_offset || 0
  return `FR:${fr}% V:${v}% T:${th}°C z_off:${z_off.toFixed(2)}mm`
})

// 当前采集区间信息（调试用）
const segmentInfo = computed(() => {
  const segment = store.sensorData.acquisition?.current_segment
  if (!segment) return ''
  return `塔${segment.tower_id} 区间${segment.segment_idx}/${segment.segment_total} (${segment.height_range})`
})

// 定时刷新温度
let tempInterval = null
onMounted(() => {
  fetchTemperature()
  tempInterval = setInterval(fetchTemperature, 5000)
})

onUnmounted(() => {
  if (tempInterval) {
    clearInterval(tempInterval)
  }
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.status-cards,
.skeleton-status-cards {
  display: grid;
  gap: 16px;
  margin-bottom: 20px;
}

.skeleton-status-cards {
  grid-template-columns: repeat(4, 1fr);
}

.status-cards {
  grid-template-columns: repeat(v-bind(gridCols), 1fr);
}

.main-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.video-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.video-card {
  border: none;
  background: rgba(15, 23, 42, 0.6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.video-container {
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.video-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-error {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #666;
  background: rgba(0, 0, 0, 0.5);
}

.side-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (max-width: 1200px) {
  .status-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .main-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .status-cards {
    grid-template-columns: 1fr;
  }
}
</style>
