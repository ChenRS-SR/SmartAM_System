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
            <!-- 模拟视频流 Canvas -->
            <canvas
              ref="mockCanvas"
              class="video-stream"
              :width="canvasWidth"
              :height="canvasHeight"
            />
            <div class="mock-label">[MOCK MODE] 模拟视频流</div>
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
const { gridCols, isMobile } = useResponsive()
const { handlePredictionAlert, handlePrintEvent } = useNotification()

// ========== 模拟视频流 ==========
const mockCanvas = ref(null)
let mockAnimationId = null
const currentStream = ref('combined')

const canvasWidth = computed(() => currentStream.value === 'combined' ? 960 : 640)
const canvasHeight = computed(() => currentStream.value === 'combined' ? 540 : 480)

const startMockAnimation = () => {
  if (!mockCanvas.value) {
    console.warn('[Mock] Canvas not ready')
    return
  }
  
  stopMockAnimation()
  const ctx = mockCanvas.value.getContext('2d')
  const type = currentStream.value
  
  console.log('[Mock] Starting animation:', type)
  
  const animate = () => {
    const t = Date.now() / 1000
    const w = canvasWidth.value
    const h = canvasHeight.value
    
    // 背景
    ctx.fillStyle = '#1a1a2e'
    ctx.fillRect(0, 0, w, h)
    
    // 网格
    ctx.strokeStyle = '#333'
    ctx.lineWidth = 1
    for (let i = 0; i < w; i += 40) {
      ctx.beginPath()
      ctx.moveTo(i, 0)
      ctx.lineTo(i, h)
      ctx.stroke()
    }
    for (let i = 0; i < h; i += 40) {
      ctx.beginPath()
      ctx.moveTo(0, i)
      ctx.lineTo(w, i)
      ctx.stroke()
    }
    
    // 根据类型绘制
    if (type === 'ids') {
      // IDS 视角
      const x = w / 2 + Math.sin(t) * 50
      const y = h / 2 + Math.cos(t * 0.7) * 30
      
      ctx.fillStyle = '#ff6b6b'
      ctx.beginPath()
      ctx.arc(x, y, 20, 0, Math.PI * 2)
      ctx.fill()
      
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, 40)
      gradient.addColorStop(0, 'rgba(255, 100, 100, 0.6)')
      gradient.addColorStop(1, 'rgba(255, 100, 100, 0)')
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(x, y, 40, 0, Math.PI * 2)
      ctx.fill()
    } else if (type === 'side') {
      // 旁轴视角
      const x = w / 2 + Math.sin(t * 0.5) * 100
      const nozzleY = h / 3
      
      ctx.strokeStyle = '#666'
      ctx.lineWidth = 3
      ctx.strokeRect(w / 4, h / 6, w / 2, h * 0.6)
      
      ctx.fillStyle = '#4ecdc4'
      ctx.fillRect(w / 2 - 30, h * 0.6, 60, 80)
      
      ctx.fillStyle = '#ff6b6b'
      ctx.fillRect(x - 15, nozzleY - 20, 30, 40)
    } else {
      // 组合画面
      ctx.strokeStyle = '#00d4ff'
      ctx.strokeRect(10, 10, w / 2 - 20, h - 20)
      ctx.fillStyle = '#00d4ff'
      ctx.font = '14px Arial'
      ctx.fillText('[MOCK] IDS', 20, 35)
      
      ctx.strokeStyle = '#00ff88'
      ctx.strokeRect(w / 2 + 10, 10, w / 2 - 20, h - 20)
      ctx.fillStyle = '#00ff88'
      ctx.fillText('[MOCK] Side', w / 2 + 20, 35)
      
      ctx.fillStyle = '#fff'
      ctx.font = 'bold 24px Arial'
      ctx.textAlign = 'center'
      ctx.fillText('SIMULATION MODE', w / 2, h / 2)
      ctx.font = '16px Arial'
      ctx.fillText('No Backend Required', w / 2, h / 2 + 30)
    }
    
    // 标识
    ctx.textAlign = 'left'
    ctx.fillStyle = '#00ff00'
    ctx.font = 'bold 16px Arial'
    ctx.fillText(`[MOCK] ${type.toUpperCase()}`, 10, 25)
    ctx.fillStyle = '#aaa'
    ctx.font = '12px Arial'
    ctx.fillText('Frontend Only Mode', 10, 45)
    ctx.fillText(`FPS: ${(Math.random() * 2 + 28).toFixed(1)}`, 10, 65)
    
    mockAnimationId = requestAnimationFrame(animate)
  }
  
  animate()
}

const stopMockAnimation = () => {
  if (mockAnimationId) {
    cancelAnimationFrame(mockAnimationId)
    mockAnimationId = null
  }
}

// 监听流类型变化
watch(currentStream, () => {
  setTimeout(startMockAnimation, 50)
})

// ========== 温度数据 ==========
const currentTemps = ref({
  nozzle: 200,
  nozzleTarget: 200,
  bed: 60,
  bedTarget: 60
})

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

let tempInterval = null

// ========== 视频流状态 ==========
const videoConnected = ref(true)

// ========== 计算属性 ==========
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

const printStatusText = computed(() => {
  const state = store.latestData.printer.state
  if (state === 'Printing') return '正在打印'
  if (state === 'Paused') return '已暂停'
  if (state === 'Operational') return '待机中'
  if (state === 'Offline') return '离线'
  return state || '未知'
})

const printTimeLeft = computed(() => {
  const seconds = store.latestData.printer.print_time_left
  if (!seconds || seconds <= 0) return ''
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return hours > 0 ? `剩余 ${hours}小时${mins}分钟` : `剩余 ${mins}分钟`
})

const acquisitionStateText = computed(() => {
  const acq = store.sensorData.acquisition
  if (!acq) return '未连接'
  const state = acq.state
  if (state !== 'running') {
    if (state === 'paused') return '已暂停'
    if (state === 'idle') return '未开始'
    return state || '未知'
  }
  const z = acq.current_z || 0
  const mode = acq.param_mode || 'fixed'
  if (mode === 'tower') {
    if (z < 5.0) return '开始0-5mm'
    if (z < 5.5) return '5-5.5静默区'
    if (z < 9.5) return '5.5-9.5记录区'
    const segment = Math.floor((z - 5) / 5) + 2
    return `${segment}段记录区`
  }
  return '采集中'
})

const acquisitionInfo = computed(() => {
  const acq = store.sensorData.acquisition
  if (!acq || acq.state !== 'running') return ''
  return `Z: ${(acq.current_z || 0).toFixed(2)}mm | 帧: ${acq.frame_count || 0}`
})

const acquisitionStateColor = computed(() => {
  const state = store.sensorData.acquisition?.state
  if (state === 'running') return 'rgba(0, 255, 136, 0.3)'
  if (state === 'paused') return 'rgba(255, 193, 7, 0.3)'
  return 'rgba(128, 128, 128, 0.3)'
})

const currentZHeight = computed(() => {
  const z = store.sensorData.acquisition?.current_z
  return z ? z.toFixed(2) : '0.00'
})

const printParamsText = computed(() => {
  const params = store.sensorData.acquisition?.current_params
  if (!params) return ''
  return `F:${params.flow_rate || 0}% E:${params.feed_rate || 0}% T:${params.target_hotend || 0}°C`
})

// ========== 生命周期 ==========
onMounted(() => {
  fetchTemperature()
  tempInterval = setInterval(fetchTemperature, 5000)
  
  // 启动模拟视频流
  setTimeout(() => {
    console.log('[Dashboard] 启动模拟视频流')
    videoConnected.value = true
    startMockAnimation()
  }, 100)
})

onUnmounted(() => {
  if (tempInterval) clearInterval(tempInterval)
  stopMockAnimation()
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
  background: #1a1a2e;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.video-stream {
  width: 100%;
  height: 100%;
  display: block;
}

.mock-label {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 255, 0, 0.8);
  color: #000;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
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
