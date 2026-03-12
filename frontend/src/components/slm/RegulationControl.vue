<template>
  <div class="regulation-control">
    <!-- 闭环调控面板 -->
    <div class="control-panel">
      <div class="panel-header">
        <span class="panel-title">🎛️ 闭环调控</span>
        <div class="header-actions">
          <el-tag :type="isVideoFileMode ? 'success' : 'info'" effect="dark" size="small">
            {{ isVideoFileMode ? '模拟模式' : '真实模式' }}
          </el-tag>
          <el-tag v-if="currentSceneName" type="warning" effect="dark" size="small">
            {{ currentSceneName }}
          </el-tag>
          <el-tag v-if="injectionStatus" :type="injectionStatus.type" effect="dark" size="small">
            {{ injectionStatus.text }}
          </el-tag>
        </div>
      </div>
      
      <!-- 状态概览 -->
      <div class="status-overview">
        <div class="status-box">
          <div class="status-label">当前层数</div>
          <div class="status-value layer">{{ displayLayer }}</div>
        </div>
        <div class="status-box">
          <div class="status-label">激光功率</div>
          <div class="status-value" :class="{ 'text-danger': isPowerAbnormal }">{{ currentPower }} W</div>
        </div>
        <div class="status-box">
          <div class="status-label">诊断状态</div>
          <div class="status-value" :class="diagnosisStatusClass">{{ diagnosisStatusText }}</div>
        </div>
        <div class="status-box">
          <div class="status-label">调控指令</div>
          <div class="status-value" :class="regulationCommandClass">{{ regulationCommandText }}</div>
        </div>
      </div>
      
      <!-- 视频时间信息（调试用） -->
      <div v-if="isVideoFileMode && isRunning" class="video-time-info">
        <span>场景: {{ detectedScene }}</span>
        <span>视频时间: {{ formatVideoTime(currentVideoTime) }}</span>
        <span>当前层: {{ currentLayer }}</span>
      </div>
      
      <!-- 异常注入提示 -->
      <div v-if="injectionAlert.show" class="injection-alert" :class="injectionAlert.type">
        <el-alert
          :title="injectionAlert.title"
          :type="injectionAlert.type"
          :description="injectionAlert.description"
          show-icon
          effect="dark"
          :closable="false"
        />
      </div>
      
      <!-- 标准参数 -->
      <div class="params-section">
        <div class="param-item">
          <span class="param-label">激光功率</span>
          <span class="param-value" :class="{ 'text-danger': isPowerAbnormal }">{{ currentPower }} W</span>
          <span v-if="isPowerAbnormal" class="param-std">(标准: {{ standardParams.power }}W)</span>
        </div>
        <div class="param-item">
          <span class="param-label">扫描速度</span>
          <span class="param-value">{{ standardParams.speed }} mm/s</span>
        </div>
        <div class="param-item">
          <span class="param-label">填充间距</span>
          <span class="param-value">{{ standardParams.spacing }} mm</span>
        </div>
      </div>
      
      <!-- 层进度 -->
      <div v-if="showLayerProgress" class="layer-progress">
        <div class="section-title">📊 打印层进度</div>
        <div class="layer-timeline">
          <div 
            v-for="layerNum in visibleLayerRange" 
            :key="layerNum"
            class="layer-item"
            :class="{
              'active': currentLayer === layerNum,
              'fault': isFaultLayer(layerNum),
              'diagnosis': isDiagnosisLayer(layerNum),
              'regulation': isRegulationLayer(layerNum),
              'recovered': isRecoveredLayer(layerNum)
            }"
          >
            <div class="layer-num">{{ layerNum }}</div>
            <div class="layer-badge" v-if="getLayerBadge(layerNum)">{{ getLayerBadge(layerNum) }}</div>
          </div>
        </div>
      </div>
      
      <!-- 调控执行中 -->
      <div v-if="isRegulating" class="regulating-section">
        <el-progress :percentage="regulationProgress" striped striped-flow />
        <p>{{ regulationMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// ==================== 视频裁剪偏移配置 ====================
const VIDEO_OFFSET_SECONDS = 2 + 7/30
const VIDEO_FPS = 30

// 视频长度（秒）- 用于检测轮播
const VIDEO_DURATION = {
  normal: 46 + 6/30,
  scene_underpower: 113 + 2/30 - VIDEO_OFFSET_SECONDS
}

// ==================== 场景检测 ====================
function detectSceneFromVideoFiles(videoFiles) {
  if (!videoFiles || Object.keys(videoFiles).length === 0) return 'normal'
  const firstPath = Object.values(videoFiles)[0]
  if (!firstPath) return 'normal'
  const path = firstPath.toLowerCase()
  if (path.includes('underpower')) return 'scene_underpower'
  if (path.includes('overpower')) return 'scene_overpower'
  return 'normal'
}

// ==================== 层配置 ====================
const normalLayerConfig = [
  { layer: 1, startSec: 0, startFrame: 0, endSec: 7, endFrame: 9 },
  { layer: 2, startSec: 9, startFrame: 4, endSec: 17, endFrame: 2 },
  { layer: 3, startSec: 18, startFrame: 7, endSec: 26, endFrame: 5 },
  { layer: 4, startSec: 27, startFrame: 9, endSec: 35, endFrame: 3 },
  { layer: 5, startSec: 37, startFrame: 2, endSec: 44, endFrame: 16 }
]

const underpowerLayerConfig = [
  { layer: 113, startSec: 2, startFrame: 7, endSec: 8, endFrame: 5 },
  { layer: 114, startSec: 10, startFrame: 6, endSec: 16, endFrame: 4 },
  { layer: 115, startSec: 18, startFrame: 5, endSec: 25, endFrame: 3 },
  { layer: 116, startSec: 26, startFrame: 7, endSec: 32, endFrame: 9 },
  { layer: 117, startSec: 34, startFrame: 7, endSec: 40, endFrame: 9 },
  { layer: 118, startSec: 42, startFrame: 8, endSec: 48, endFrame: 9 },
  { layer: 119, startSec: 51, startFrame: 0, endSec: 57, endFrame: 2 },
  { layer: 120, startSec: 58, startFrame: 9, endSec: 65, endFrame: 9 },
  { layer: 121, startSec: 67, startFrame: 2, endSec: 73, endFrame: 3 },
  { layer: 122, startSec: 74, startFrame: 7, endSec: 81, endFrame: 3 },
  { layer: 123, startSec: 83, startFrame: 0, endSec: 89, endFrame: 0 },
  { layer: 124, startSec: 90, startFrame: 9, endSec: 97, endFrame: 2 },
  { layer: 125, startSec: 98, startFrame: 9, endSec: 106, endFrame: 1 },
  { layer: 126, startSec: 107, startFrame: 2, endSec: 113, endFrame: 2 }
]

// ==================== 状态 ====================
const isVideoFileMode = ref(false)
const detectedScene = ref('normal')
const isRunning = ref(false)
const currentVideoTime = ref(0)
const currentVideoFrame = ref(0)
const videoStartTime = ref(null)
const pausedTime = ref(0)
const videoFiles = ref({})

// ==================== 层数和状态 ====================
const currentLayer = ref(1)
const displayLayer = ref(1)
const currentPower = ref(120)

// ==================== 层数累加状态 ====================
const completedCycles = ref(0)
const lastVideoTime = ref(0)
const totalLayers = ref(5)

// ==================== 故障注入和诊断状态 ====================
const injectionStatus = ref(null)
const diagnosisStatus = ref('normal')
const regulationStatus = ref('none')

// ==================== 基础配置 ====================
const standardParams = { power: 120, speed: 1000, spacing: 0.08 }

// ==================== 调控相关 ====================
const isRegulating = ref(false)
const regulationProgress = ref(0)
const regulationMessage = ref('')

// ==================== 计算属性 ====================
const currentSceneName = computed(() => {
  const names = { 'normal': '场景1: 正常打印', 'scene_underpower': '场景2: 欠功率', 'scene_overpower': '场景3: 过功率' }
  return names[detectedScene.value] || ''
})

const isPowerAbnormal = computed(() => currentPower.value !== standardParams.power)

const diagnosisStatusClass = computed(() => diagnosisStatus.value === 'abnormal' ? 'abnormal' : 'normal')
const diagnosisStatusText = computed(() => diagnosisStatus.value === 'abnormal' ? '激光功率异常' : '正常')

const regulationCommandClass = computed(() => {
  if (regulationStatus.value === 'regulating') return 'regulating'
  if (regulationStatus.value === 'completed') return 'completed'
  return 'none'
})

const regulationCommandText = computed(() => {
  if (regulationStatus.value === 'regulating') return '调整激光功率'
  if (regulationStatus.value === 'completed') return '已完成'
  return '无'
})

const injectionAlert = computed(() => {
  if (!isVideoFileMode.value || detectedScene.value !== 'scene_underpower') {
    return { show: true, type: 'success', title: '✅ 系统正常', description: '激光功率正常，打印过程稳定' }
  }
  
  // 115-117层：异常注入
  if (currentLayer.value >= 115 && currentLayer.value <= 117) {
    return { show: true, type: 'error', title: '🔴 异常注入', description: '检测到激光功率过低 (55W)，低于标准值54%' }
  }
  
  // 118-119层：诊断异常，无调控
  if (currentLayer.value >= 118 && currentLayer.value <= 119) {
    return { show: true, type: 'warning', title: '⚠️ 诊断异常', description: '激光功率异常，等待调控指令' }
  }
  
  // 120-124层：诊断异常，调控中
  if (currentLayer.value >= 120 && currentLayer.value <= 124) {
    return { show: true, type: 'info', title: '🎛️ 闭环调控', description: '正在调整激光功率 55W → 120W' }
  }
  
  // 125-126层：恢复正常
  return { show: true, type: 'success', title: '✅ 系统恢复', description: '激光功率已恢复正常，打印过程稳定' }
})

const showLayerProgress = computed(() => isVideoFileMode.value && detectedScene.value === 'scene_underpower')

const visibleLayerRange = computed(() => {
  if (detectedScene.value === 'scene_underpower') return Array.from({ length: 14 }, (_, i) => 113 + i)
  return [1, 2, 3, 4, 5]
})

// ==================== 辅助函数 ====================
function toTotalSeconds(sec, frame) { return sec + frame / VIDEO_FPS }

function formatVideoTime(totalSeconds) {
  const videoDuration = VIDEO_DURATION[detectedScene.value] || VIDEO_DURATION.normal
  const displayTime = totalSeconds % videoDuration
  const min = Math.floor(displayTime / 60)
  const sec = Math.floor(displayTime % 60)
  const frame = Math.floor((displayTime - Math.floor(displayTime)) * VIDEO_FPS)
  return min > 0 ? `${min}分${sec}秒${frame}帧` : `${sec}秒${frame}帧`
}

// 层状态判断函数
function isFaultLayer(layer) { return detectedScene.value === 'scene_underpower' && layer >= 115 && layer <= 117 }
function isDiagnosisLayer(layer) { return detectedScene.value === 'scene_underpower' && layer >= 118 && layer <= 124 }
function isRegulationLayer(layer) { return detectedScene.value === 'scene_underpower' && layer >= 120 && layer <= 124 }
function isRecoveredLayer(layer) { return detectedScene.value === 'scene_underpower' && layer >= 125 }

// 获取层徽章
function getLayerBadge(layer) {
  if (detectedScene.value !== 'scene_underpower') return null
  if (layer >= 115 && layer <= 117) return '注'
  if (layer >= 118 && layer <= 119) return '诊'
  if (layer >= 120 && layer <= 124) return '调'
  if (layer >= 125) return '恢'
  return null
}

// ==================== 层数计算 ====================
function calculateLayerByTime(timeInSeconds) {
  if (detectedScene.value === 'scene_underpower') {
    const originalTime = timeInSeconds + VIDEO_OFFSET_SECONDS
    for (const config of underpowerLayerConfig) {
      const startTime = toTotalSeconds(config.startSec, config.startFrame)
      const endTime = toTotalSeconds(config.endSec, config.endFrame)
      if (originalTime >= startTime && originalTime <= endTime) return config.layer
    }
    for (let i = 0; i < underpowerLayerConfig.length - 1; i++) {
      const currEnd = toTotalSeconds(underpowerLayerConfig[i].endSec, underpowerLayerConfig[i].endFrame)
      const nextStart = toTotalSeconds(underpowerLayerConfig[i + 1].startSec, underpowerLayerConfig[i + 1].startFrame)
      if (originalTime > currEnd && originalTime < nextStart) {
        const mid = (currEnd + nextStart) / 2
        return originalTime < mid ? underpowerLayerConfig[i].layer : underpowerLayerConfig[i + 1].layer
      }
    }
    if (originalTime < toTotalSeconds(underpowerLayerConfig[0].startSec, underpowerLayerConfig[0].startFrame)) return 113
    return 126
  } else {
    for (const config of normalLayerConfig) {
      const startTime = toTotalSeconds(config.startSec, config.startFrame)
      const endTime = toTotalSeconds(config.endSec, config.endFrame)
      if (timeInSeconds >= startTime && timeInSeconds <= endTime) return config.layer
    }
    for (let i = 0; i < normalLayerConfig.length - 1; i++) {
      const currEnd = toTotalSeconds(normalLayerConfig[i].endSec, normalLayerConfig[i].endFrame)
      const nextStart = toTotalSeconds(normalLayerConfig[i + 1].startSec, normalLayerConfig[i + 1].startFrame)
      if (timeInSeconds > currEnd && timeInSeconds < nextStart) {
        const mid = (currEnd + nextStart) / 2
        return timeInSeconds < mid ? normalLayerConfig[i].layer : normalLayerConfig[i + 1].layer
      }
    }
    if (timeInSeconds < toTotalSeconds(normalLayerConfig[0].startSec, normalLayerConfig[0].startFrame)) return 1
    return 5
  }
}

// ==================== 状态更新 ====================
function updateStatusByLayer(layer) {
  if (detectedScene.value === 'scene_underpower') {
    // 功率：115-119层显示55W，其他层显示120W
    currentPower.value = (layer >= 115 && layer <= 119) ? 55 : 120
    
    // 故障注入：115-117层
    injectionStatus.value = (layer >= 115 && layer <= 117) ? { type: 'danger', text: '异常注入' } : null
    
    // 诊断状态：117-124层异常
    diagnosisStatus.value = (layer >= 117 && layer <= 124) ? 'abnormal' : 'normal'
    
    // 调控状态：120-124层调控中
    regulationStatus.value = (layer >= 120 && layer <= 124) ? 'regulating' : 'none'
  } else {
    currentPower.value = standardParams.power
    diagnosisStatus.value = 'normal'
    regulationStatus.value = 'none'
    injectionStatus.value = null
  }
}

// ==================== 视频文件模式检测 ====================
let statusCheckInterval = null

async function checkVideoFileMode() {
  try {
    const response = await axios.get('/api/slm/video_file_mode/config')
    if (response.data.success) {
      const config = response.data
      const wasVideoFileMode = isVideoFileMode.value
      isVideoFileMode.value = config.enabled
      
      if (config.enabled && config.video_files) {
        const newScene = detectSceneFromVideoFiles(config.video_files)
        const sceneChanged = newScene !== detectedScene.value
        detectedScene.value = newScene
        videoFiles.value = config.video_files
        
        if (sceneChanged || !wasVideoFileMode) resetLayerState()
      }
    }
  } catch (error) {
    console.error('检查视频文件模式失败:', error)
  }
}

function resetLayerState() {
  stopTimeTracking()
  currentVideoTime.value = 0
  currentVideoFrame.value = 0
  pausedTime.value = 0
  videoStartTime.value = null
  lastVideoTime.value = 0
  completedCycles.value = 0
  
  if (detectedScene.value === 'scene_underpower') {
    currentLayer.value = 113
    displayLayer.value = 113
    totalLayers.value = 14
  } else {
    currentLayer.value = 1
    displayLayer.value = 1
    totalLayers.value = 5
  }
  
  currentPower.value = standardParams.power
  diagnosisStatus.value = 'normal'
  regulationStatus.value = 'none'
  injectionStatus.value = null
}

// ==================== 采集状态检测 ====================
async function checkAcquisitionStatus() {
  try {
    const response = await axios.get('/api/slm/status')
    if (response.data) {
      const wasRunning = isRunning.value
      isRunning.value = response.data.is_running
      
      if (!wasRunning && isRunning.value && isVideoFileMode.value) {
        videoStartTime.value = Date.now()
        startTimeTracking()
      }
      
      if (wasRunning && !isRunning.value) {
        stopTimeTracking()
        pausedTime.value = 0
        completedCycles.value = 0
        lastVideoTime.value = 0
      }
    }
  } catch (error) {
    console.error('检查采集状态失败:', error)
  }
}

// ==================== 时间追踪 ====================
let timeTrackingInterval = null

function startTimeTracking() {
  stopTimeTracking()
  
  timeTrackingInterval = setInterval(() => {
    if (!isRunning.value || !videoStartTime.value) return
    
    const elapsed = (Date.now() - videoStartTime.value) / 1000 + pausedTime.value
    const videoDuration = VIDEO_DURATION[detectedScene.value] || VIDEO_DURATION.normal
    const videoTimeInCycle = elapsed % videoDuration
    const videoLayer = calculateLayerByTime(videoTimeInCycle)
    
    const lastLayer = detectedScene.value === 'scene_underpower' ? 126 : 5
    const firstLayer = detectedScene.value === 'scene_underpower' ? 113 : 1
    
    if (currentLayer.value === lastLayer && videoLayer === firstLayer && elapsed > videoDuration * 0.5) {
      completedCycles.value++
    }
    
    const targetDisplayLayer = completedCycles.value * totalLayers.value + (videoLayer - firstLayer + 1)
    
    if (videoLayer !== currentLayer.value) {
      currentLayer.value = videoLayer
      updateStatusByLayer(videoLayer)
    }
    
    displayLayer.value = targetDisplayLayer
    lastVideoTime.value = elapsed
    currentVideoTime.value = videoTimeInCycle
    currentVideoFrame.value = Math.floor(videoTimeInCycle * VIDEO_FPS)
  }, 100)
}

function stopTimeTracking() {
  if (timeTrackingInterval) {
    clearInterval(timeTrackingInterval)
    timeTrackingInterval = null
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  checkVideoFileMode()
  checkAcquisitionStatus()
  statusCheckInterval = setInterval(() => {
    checkVideoFileMode()
    checkAcquisitionStatus()
  }, 2000)
})

onUnmounted(() => {
  stopTimeTracking()
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval)
    statusCheckInterval = null
  }
})
</script>

<style scoped>
.regulation-control { display: flex; flex-direction: column; gap: 16px; }
.control-panel { background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 8px; overflow: hidden; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: rgba(30, 41, 59, 0.5); border-bottom: 1px solid rgba(100, 116, 139, 0.2); }
.panel-title { font-size: 14px; font-weight: 600; color: #e2e8f0; }
.header-actions { display: flex; align-items: center; gap: 8px; }
.status-overview { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 16px; border-bottom: 1px solid rgba(100, 116, 139, 0.2); }
.status-box { text-align: center; padding: 12px; background: rgba(30, 41, 59, 0.5); border-radius: 6px; border: 1px solid rgba(100, 116, 139, 0.2); }
.status-label { font-size: 12px; color: #94a3b8; margin-bottom: 8px; }
.status-value { font-size: 20px; font-weight: 600; color: #e2e8f0; }
.status-value.layer { color: #22c55e; }
.status-value.abnormal { color: #ef4444; }
.status-value.normal { color: #22c55e; }
.status-value.regulating { color: #f59e0b; animation: pulse 1.5s infinite; }
.status-value.none { color: #64748b; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
.video-time-info { display: flex; gap: 20px; padding: 8px 16px; background: rgba(30, 41, 59, 0.3); font-size: 12px; color: #94a3b8; border-bottom: 1px solid rgba(100, 116, 139, 0.2); }
.injection-alert { padding: 12px 16px; border-bottom: 1px solid rgba(100, 116, 139, 0.2); }
.injection-alert.error :deep(.el-alert) { background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.5); }
.injection-alert.warning :deep(.el-alert) { background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.5); }
.injection-alert.info :deep(.el-alert) { background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.5); }
.injection-alert.success :deep(.el-alert) { background: rgba(34, 197, 94, 0.2); border: 1px solid rgba(34, 197, 94, 0.5); }
.params-section { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 12px 16px; border-bottom: 1px solid rgba(100, 116, 139, 0.2); }
.param-item { display: flex; flex-direction: column; gap: 4px; padding: 8px; background: rgba(30, 41, 59, 0.3); border-radius: 4px; }
.param-label { font-size: 11px; color: #94a3b8; }
.param-value { font-size: 14px; font-weight: 600; color: #e2e8f0; }
.param-value.text-danger { color: #ef4444; }
.param-std { font-size: 11px; color: #64748b; }
.section-title { font-size: 13px; font-weight: 600; color: #94a3b8; padding: 12px 16px 8px; }
.layer-progress { border-bottom: 1px solid rgba(100, 116, 139, 0.2); }
.layer-timeline { display: flex; gap: 6px; overflow-x: auto; padding: 8px 16px 16px; }
.layer-item { min-width: 50px; padding: 6px; border-radius: 4px; text-align: center; background: rgba(30, 41, 59, 0.5); border: 2px solid transparent; transition: all 0.3s; color: #e2e8f0; position: relative; }
.layer-item.active { border-color: #22c55e; background: rgba(34, 197, 94, 0.1); transform: scale(1.05); }
.layer-item.fault { background: rgba(239, 68, 68, 0.3); }
.layer-item.fault.active { border-color: #ef4444; }
.layer-item.diagnosis { background: rgba(245, 158, 11, 0.3); }
.layer-item.diagnosis.active { border-color: #f59e0b; }
.layer-item.regulation { background: rgba(59, 130, 246, 0.3); }
.layer-item.regulation.active { border-color: #3b82f6; }
.layer-item.recovered { background: rgba(34, 197, 94, 0.3); }
.layer-item.recovered.active { border-color: #22c55e; }
.layer-num { font-size: 13px; font-weight: 600; }
.layer-badge { position: absolute; top: -4px; right: -4px; font-size: 9px; background: #ef4444; color: white; border-radius: 50%; width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; }
.regulating-section { text-align: center; padding: 16px; color: #e2e8f0; }
.text-danger { color: #ef4444; }
@media (max-width: 1200px) { .status-overview, .params-section { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px) { .status-overview, .params-section { grid-template-columns: 1fr; } .layer-timeline { flex-wrap: wrap; } }
</style>
