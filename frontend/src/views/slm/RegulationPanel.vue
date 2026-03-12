<template>
  <el-card class="regulation-panel">
    <template #header>
      <div class="header">
        <span>🎛️ 激光功率闭环调控</span>
        <div>
          <el-tag :type="modeType" class="mode-tag">{{ isSimulation ? '模拟模式' : '真实模式' }}</el-tag>
          <el-tag :type="diagnosisType">{{ diagnosisText }}</el-tag>
        </div>
      </div>
    </template>
    
    <!-- 模式切换 -->
    <div class="mode-switch">
      <el-radio-group v-model="isSimulation" @change="onModeChange">
        <el-radio-button :label="false">真实模式</el-radio-button>
        <el-radio-button :label="true">模拟演示</el-radio-button>
      </el-radio-group>
      
      <!-- 模拟场景选择 -->
      <el-select 
        v-if="isSimulation" 
        v-model="currentSceneId" 
        placeholder="选择演示场景" 
        @change="loadScene"
        style="width: 250px"
      >
        <el-option 
          v-for="scene in sceneList" 
          :key="scene.id" 
          :label="scene.name" 
          :value="scene.id"
        >
          <span>{{ scene.name }}</span>
          <span style="float: right; color: #8492a6; font-size: 13px">
            {{ scene.parameters.recoverable ? '可恢复' : '不可恢复' }}
          </span>
        </el-option>
      </el-select>
    </div>
    
    <!-- 场景描述 -->
    <div v-if="currentScene && isSimulation" class="scene-info">
      <el-alert :title="currentScene.description" type="info" :closable="false" show-icon />
    </div>
    
    <!-- 标准参数显示 -->
    <div class="standard-params">
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="激光功率">
          <span :class="{ 'text-danger': isPowerAbnormal }">{{ currentPower }} W</span>
          <span v-if="isPowerAbnormal" class="deviation">
            (标准: {{ standardParams.power }}W)
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="扫描速度">{{ standardParams.speed }} mm/s</el-descriptions-item>
        <el-descriptions-item label="填充间距">{{ standardParams.spacing }} mm</el-descriptions-item>
      </el-descriptions>
    </div>
    
    <el-divider />
    
    <!-- 当前状态 -->
    <div class="current-status">
      <div class="status-item">
        <label>当前层数</label>
        <el-tag size="large" type="primary">{{ currentLayer }}</el-tag>
      </div>
      <div class="status-item">
        <label>当前帧</label>
        <el-tag size="large">{{ currentFrame }} / {{ totalFrames }}</el-tag>
      </div>
      <div class="status-item" v-if="isSimulation && currentScene">
        <label>进度</label>
        <el-progress :percentage="progressPercent" style="width: 150px" />
      </div>
    </div>
    
    <!-- 层进度条（场景2显示） -->
    <div v-if="isSimulation && currentScene?.timeline?.layers" class="layer-progress">
      <el-divider content-position="left">📊 打印层进度</el-divider>
      <div class="layer-timeline">
        <div 
          v-for="(layerData, layerNum) in currentScene.timeline.layers" 
          :key="layerNum"
          class="layer-item"
          :class="{
            'active': currentLayer === parseInt(layerNum),
            'fault': layerData.fault,
            'regulation': layerData.regulation,
            'recovered': layerData.recovered
          }"
        >
          <div class="layer-num">{{ layerNum }}</div>
          <div class="layer-name">{{ layerData.name }}</div>
          <div class="layer-power">{{ layerData.power }}W</div>
        </div>
      </div>
    </div>
    
    <!-- 视频播放器（模拟模式） -->
    <div v-if="isSimulation && currentScene" class="video-players">
      <el-divider content-position="left">🎬 模拟视频流</el-divider>
      <div class="video-grid">
        <div class="video-item">
          <label>CH1 主摄</label>
          <video 
            ref="videoCh1"
            :src="videoUrls.ch1" 
            @timeupdate="onVideoTimeUpdate"
            @loadedmetadata="onVideoLoaded"
            controls
            muted
          />
        </div>
        <div class="video-item">
          <label>CH2 副摄</label>
          <video 
            ref="videoCh2"
            :src="videoUrls.ch2" 
            controls
            muted
          />
        </div>
        <div class="video-item">
          <label>CH3 红外</label>
          <video 
            ref="videoCh3"
            :src="videoUrls.ch3" 
            controls
            muted
          />
        </div>
      </div>
    </div>
    
    <!-- 诊断结果 -->
    <div v-if="diagnosisResult" class="diagnosis-section" :class="diagnosisResult.status">
      <el-divider content-position="left">🔍 诊断结果</el-divider>
      
      <el-alert 
        :type="diagnosisResult.status === 'normal' ? 'success' : 'error'"
        :closable="false"
        show-icon
        :title="diagnosisResult.status === 'normal' ? '✅ 打印质量正常' : `🔴 检测到异常: ${diagnosisResult.abnormalType}`"
      >
        <div v-if="diagnosisResult.status === 'abnormal'">
          <p><strong>异常原因:</strong> {{ diagnosisResult.reason }}</p>
          <p v-if="!isSimulation"><strong>置信度:</strong> {{ diagnosisResult.confidence }}%</p>
          <p v-if="diagnosisResult.recoverable !== undefined">
            <strong>可恢复性:</strong> 
            <el-tag :type="diagnosisResult.recoverable ? 'success' : 'danger'" size="small">
              {{ diagnosisResult.recoverable ? '✅ 可调回' : '❌ 可能不可逆' }}
            </el-tag>
          </p>
        </div>
      </el-alert>
      
      <!-- 调控建议 -->
      <div v-if="diagnosisResult.status === 'abnormal' && !diagnosisResult.regulated" class="regulation-action">
        <el-divider />
        <div class="suggestion-box">
          <p class="suggestion-title">💡 调控建议</p>
          <p class="suggestion-content">
            激光功率: <span class="text-danger">{{ currentPower }}W</span> 
            → <span class="text-success">{{ standardParams.power }}W</span>
          </p>
          <p v-if="diagnosisResult.recoverLayers" class="recover-info">
            预计 <strong>{{ diagnosisResult.recoverLayers }}</strong> 层后可恢复
          </p>
        </div>
        <el-button 
          type="success" 
          size="large" 
          @click="executeRegulation"
          :loading="isRegulating"
          :disabled="!diagnosisResult.recoverable && isSimulation"
        >
          ⚡ 执行自动调控
        </el-button>
      </div>
    </div>
    
    <!-- 调控执行中 -->
    <div v-if="isRegulating" class="regulating-section">
      <el-divider content-position="left">⏳ 调控执行</el-divider>
      <el-progress 
        :percentage="regulationProgress" 
        :status="regulationStatus"
        :stroke-width="20"
        striped
        striped-flow
      />
      <p class="regulation-message">{{ regulationMessage }}</p>
    </div>
    
    <!-- 调控历史 -->
    <div v-if="regulationHistory.length > 0" class="history-section">
      <el-divider content-position="left">📊 调控记录</el-divider>
      <el-timeline>
        <el-timeline-item 
          v-for="(record, index) in regulationHistory" 
          :key="index"
          :type="record.result === 'success' ? 'success' : 'danger'"
          :timestamp="record.time"
          :icon="record.result === 'success' ? 'Check' : 'Close'"
        >
          <el-card size="small">
            <p><strong>层 {{ record.layer }}</strong></p>
            <p>功率: {{ record.from }}W → {{ record.to }}W</p>
            <p>异常: {{ record.abnormalType }}</p>
            <el-tag :type="record.result === 'success' ? 'success' : 'danger'" size="small">
              {{ record.result === 'success' ? '✅ 恢复成功' : '❌ 恢复失败' }}
            </el-tag>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>
    
    <!-- 模拟控制（仅模拟模式） -->
    <div v-if="isSimulation && currentScene" class="simulation-control">
      <el-divider content-position="left">🎮 播放控制</el-divider>
      
      <div class="control-bar">
        <el-button-group>
          <el-button @click="seekFrame(0)">⏮ 开头</el-button>
          <el-button @click="prevFrame">◀ 上一帧</el-button>
          <el-button type="primary" @click="togglePlay" size="large">
            {{ isPlaying ? '⏸ 暂停' : '▶ 播放' }}
          </el-button>
          <el-button @click="nextFrame">▶ 下一帧</el-button>
        </el-button-group>
        
        <el-button-group>
          <el-button @click="changeSpeed(0.5)">0.5x</el-button>
          <el-button @click="changeSpeed(1)">1x</el-button>
          <el-button @click="changeSpeed(2)">2x</el-button>
        </el-button-group>
      </div>
      
      <!-- 帧进度条 -->
      <div class="frame-slider">
        <el-slider 
          v-model="currentFrame" 
          :max="totalFrames" 
          :step="1"
          show-stops
          :marks="frameMarks"
          @change="onFrameSliderChange"
        />
        <div class="frame-labels">
          <span>0</span>
          <span v-if="currentScene?.timeline?.layers">115层</span>
          <span v-else-if="currentScene">故障:{{ currentScene.timeline.faultFrame }}</span>
          <span v-if="currentScene?.timeline?.layers">126层</span>
          <span v-else-if="currentScene">诊断:{{ currentScene.timeline.diagnosisFrame }}</span>
          <span>{{ totalFrames }}</span>
        </div>
      </div>
      
      <!-- 当前播放速度 -->
      <div class="playback-info">
        播放速度: {{ playbackSpeed }}x | 
        当前时间: {{ formatTime(currentTime) }} / {{ formatTime(totalTime) }}
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Check, Close } from '@element-plus/icons-vue'

// ==================== 基础配置 ====================
const standardParams = {
  power: 120,
  speed: 1000,
  spacing: 0.08
}

// ==================== 模式与场景 ====================
const isSimulation = ref(false)
const currentSceneId = ref('')
const currentScene = ref(null)
const sceneList = ref([])

// 加载场景配置
const loadSceneConfig = async () => {
  try {
    const response = await fetch('/simulation_record/scenes.json')
    const data = await response.json()
    sceneList.value = data.scenes
  } catch (error) {
    console.error('加载场景配置失败:', error)
    // 使用默认配置
    sceneList.value = [
      {
        id: 'scene_overpower',
        name: '场景1: 激光功率过高（可恢复）',
        description: '功率调至300W，5层后调回标准值可恢复',
        folder: 'scene_overpower',
        videos: { ch1: 'CH1_segment029_20260310_180512.mp4', ch2: 'CH2_segment029_20260310_180512.mp4', ch3: 'CH3_segment029_20260310_180512.mp4' },
        timeline: { totalFrames: 600, framesPerLayer: 30, faultFrame: 150, diagnosisFrame: 155, regulationFrame: 160 },
        parameters: { faultPower: 300, standardPower: 120, abnormalType: '激光功率过高', reason: '功率300W超出标准150%', recoverable: true, recoverLayers: 5 }
      },
      {
        id: 'scene_underpower',
        name: '场景2: 激光功率过低（可恢复）- 实测数据',
        description: '115-119层功率55W，120层开始调控，126层完全恢复',
        folder: 'scene_underpower',
        videos: { ch1: 'ch1_main.mp4', ch2: 'ch2_side.mp4', ch3: 'ch3_thermal.mp4' },
        timeline: {
          totalFrames: 3600,
          fps: 30,
          startLayer: 115,
          layers: {
            '115': { name: '故障注入层', ch1Range: [545, 753], ch2Range: [544, 752], ch3Range: [573, 781], fault: true, power: 55 },
            '116': { name: '异常持续', ch1Range: [786, 968], ch2Range: [785, 967], ch3Range: [814, 996], power: 55 },
            '117': { name: '异常持续', ch1Range: [1026, 1208], ch2Range: [1025, 1207], ch3Range: [1054, 1236], power: 55 },
            '118': { name: '异常持续', ch1Range: [1267, 1448], ch2Range: [1266, 1447], ch3Range: [1295, 1476], power: 55 },
            '119': { name: '异常持续', ch1Range: [1509, 1712], ch2Range: [1508, 1711], ch3Range: [1537, 1740], power: 55 },
            '120': { name: '闭环调控开始', ch1Range: [1748, 1958], ch2Range: [1747, 1957], ch3Range: [1776, 1986], regulation: true, power: 120 },
            '121': { name: '恢复中', ch1Range: [2012, 2191], ch2Range: [2011, 2190], ch3Range: [2040, 2219], power: 120 },
            '122': { name: '恢复中', ch1Range: [2242, 2431], ch2Range: [2241, 2430], ch3Range: [2270, 2459], power: 120 },
            '123': { name: '恢复中', ch1Range: [2489, 2672], ch2Range: [2488, 2671], ch3Range: [2517, 2700], power: 120 },
            '124': { name: '恢复中', ch1Range: [2727, 2912], ch2Range: [2726, 2911], ch3Range: [2755, 2940], power: 120 },
            '125': { name: '恢复中', ch1Range: [2968, 3181], ch2Range: [2967, 3180], ch3Range: [2996, 3209], power: 120 },
            '126': { name: '完全恢复', ch1Range: [3216, 3392], ch2Range: [3215, 3391], ch3Range: [3244, 3420], recovered: true, power: 120 }
          },
          faultFrame: 545,
          diagnosisFrame: 1748,
          regulationFrame: 1748,
          recoveredFrame: 3216
        },
        parameters: { faultPower: 55, standardPower: 120, abnormalType: '激光功率过低', reason: '功率55W低于标准54%，导致未完全熔化', recoverable: true, faultLayers: 5, recoverLayers: 6 }
      },
      {
        id: 'scene_underpower_critical',
        name: '场景3: 激光功率过低（不可恢复）',
        description: '功率调至55W持续4-5层，造成不可逆缺陷',
        folder: 'scene_underpower_critical',
        videos: { ch1: 'ch1_main.mp4', ch2: 'ch2_side.mp4', ch3: 'ch3_thermal.mp4' },
        timeline: { totalFrames: 600, framesPerLayer: 30, faultFrame: 500, diagnosisFrame: 503, regulationFrame: 506 },
        parameters: { faultPower: 55, standardPower: 120, abnormalType: '激光功率过低（临界）', reason: '功率55W持续4-5层，已造成不可逆缺陷', recoverable: false, recoverLayers: null }
      }
    ]
  }
}

// ==================== 视频播放 ====================
const videoCh1 = ref(null)
const videoCh2 = ref(null)
const videoCh3 = ref(null)
const videoUrls = ref({ ch1: '', ch2: '', ch3: '' })
const isPlaying = ref(false)
const playbackSpeed = ref(1)
const currentTime = ref(0)
const totalTime = ref(0)
// 动态FPS，根据场景配置
const fps = computed(() => currentScene.value?.timeline?.fps || 10)

// 计算属性
const currentFrame = ref(0)
const totalFrames = computed(() => currentScene.value?.timeline.totalFrames || 600)
const framesPerLayer = computed(() => currentScene.value?.timeline.framesPerLayer || 30)

// 当前层数计算（支持详细层配置）
const currentLayer = computed(() => {
  if (currentScene.value?.timeline?.layers) {
    const frame = currentFrame.value
    for (const [layerNum, layerData] of Object.entries(currentScene.value.timeline.layers)) {
      const [startFrame, endFrame] = layerData.ch1Range || [0, 0]
      if (frame >= startFrame && frame <= endFrame) {
        return parseInt(layerNum)
      }
    }
    return currentScene.value.timeline.startLayer || 115
  }
  return Math.floor(currentFrame.value / framesPerLayer.value) + 1
})
const progressPercent = computed(() => Math.round((currentFrame.value / totalFrames.value) * 100))
const isPowerAbnormal = computed(() => currentPower.value !== standardParams.power)

// 帧标记
const frameMarks = computed(() => {
  if (!currentScene.value) return {}
  
  const { layers, faultFrame, diagnosisFrame } = currentScene.value.timeline
  const marks = {}
  
  // 如果有详细层信息，标记关键层
  if (layers) {
    for (const [layerNum, layerData] of Object.entries(layers)) {
      if (layerData.fault) {
        marks[layerData.ch1Range[0]] = { style: { color: '#f56c6c' }, label: `${layerNum}层故障` }
      } else if (layerData.regulation) {
        marks[layerData.ch1Range[0]] = { style: { color: '#e6a23c' }, label: `${layerNum}层调控` }
      } else if (layerData.recovered) {
        marks[layerData.ch1Range[0]] = { style: { color: '#67c23a' }, label: `${layerNum}层恢复` }
      }
    }
  } else {
    // 简单标记
    marks[faultFrame] = { style: { color: '#f56c6c' }, label: '故障' }
    marks[diagnosisFrame] = { style: { color: '#e6a23c' }, label: '诊断' }
  }
  
  return marks
})

// ==================== 状态管理 ====================
const currentPower = ref(120)
const diagnosisResult = ref(null)
const isRegulating = ref(false)
const regulationProgress = ref(0)
const regulationStatus = ref('')
const regulationMessage = ref('')
const regulationHistory = ref([])

// 诊断状态标签
const modeType = computed(() => isSimulation.value ? 'warning' : 'primary')
const diagnosisType = computed(() => {
  if (!diagnosisResult.value) return 'info'
  return diagnosisResult.value.status === 'normal' ? 'success' : 'danger'
})
const diagnosisText = computed(() => {
  if (!diagnosisResult.value) return '等待诊断'
  return diagnosisResult.value.status === 'normal' ? '正常' : '异常'
})

// ==================== 方法 ====================
const onModeChange = () => {
  reset()
  if (isSimulation.value) {
    currentSceneId.value = sceneList.value[0]?.id || ''
    loadScene(currentSceneId.value)
  }
}

const loadScene = (sceneId) => {
  const scene = sceneList.value.find(s => s.id === sceneId)
  if (!scene) return
  
  currentScene.value = scene
  currentPower.value = standardParams.power
  currentFrame.value = 0
  regulationHistory.value = []
  diagnosisResult.value = null
  
  // 设置视频源
  const baseUrl = `/simulation_record/${scene.folder}`
  videoUrls.value = {
    ch1: `${baseUrl}/${scene.videos.ch1}`,
    ch2: `${baseUrl}/${scene.videos.ch2}`,
    ch3: `${baseUrl}/${scene.videos.ch3}`
  }
  
  console.log('加载场景:', scene.name)
}

const onVideoLoaded = () => {
  if (videoCh1.value) {
    totalTime.value = videoCh1.value.duration
  }
}

const onVideoTimeUpdate = () => {
  if (videoCh1.value) {
    currentTime.value = videoCh1.value.currentTime
    currentFrame.value = Math.floor(currentTime.value * fps.value)
    
    // 同步CH2和CH3（如果它们没有自动同步）
    syncOtherChannels()
    
    checkTimeline()
  }
}

// 同步其他通道
const syncOtherChannels = () => {
  if (!currentScene.value?.sync) return
  
  const sync = currentScene.value.sync
  const ch1Time = videoCh1.value?.currentTime || 0
  const currentFps = fps.value
  
  // CH2同步
  if (videoCh2.value && sync.ch2?.offset !== undefined) {
    const targetTime = ch1Time + sync.ch2.offset / currentFps
    if (Math.abs(videoCh2.value.currentTime - targetTime) > 0.1) {
      videoCh2.value.currentTime = targetTime
    }
  }
  
  // CH3同步
  if (videoCh3.value && sync.ch3?.offset !== undefined) {
    const targetTime = ch1Time + sync.ch3.offset / currentFps
    if (Math.abs(videoCh3.value.currentTime - targetTime) > 0.1) {
      videoCh3.value.currentTime = targetTime
    }
  }
}

// 检查时间线事件
const checkTimeline = () => {
  if (!currentScene.value || !isSimulation.value) return
  
  const { layers, faultFrame, diagnosisFrame } = currentScene.value.timeline
  const { faultPower, standardPower, abnormalType, reason, recoverable, recoverLayers } = currentScene.value.parameters
  
  // 基于层的详细时间线（场景2）
  if (layers) {
    const frame = currentFrame.value
    
    // 查找当前所在层
    for (const [layerNum, layerData] of Object.entries(layers)) {
      const [startFrame, endFrame] = layerData.ch1Range || [0, 0]
      
      if (frame >= startFrame && frame <= endFrame) {
        // 更新当前层
        currentLayer.value = parseInt(layerNum)
        
        // 故障注入层
        if (layerData.fault && currentPower.value === standardPower) {
          currentPower.value = layerData.power || faultPower
          console.log(`[模拟] 第${layerNum}层(${frame}帧): 注入故障，功率调至${currentPower.value}W`)
        }
        
        // 调控层
        if (layerData.regulation && !diagnosisResult.value) {
          diagnosisResult.value = {
            layer: parseInt(layerNum),
            status: 'abnormal',
            abnormalType,
            reason,
            recoverable,
            recoverLayers,
            regulated: false
          }
          console.log(`[模拟] 第${layerNum}层(${frame}帧): 诊断出异常 - ${abnormalType}，建议调控至${standardPower}W`)
        }
        
        // 完全恢复层
        if (layerData.recovered && diagnosisResult.value?.regulated) {
          console.log(`[模拟] 第${layerNum}层(${frame}帧): 完全恢复`)
        }
        
        break
      }
    }
  } else {
    // 简单时间线（场景1和3）
    // 故障注入点
    if (currentFrame.value === faultFrame && currentPower.value === standardParams.power) {
      currentPower.value = faultPower
      console.log(`[模拟] 第${faultFrame}帧: 注入故障，功率调至${faultPower}W`)
    }
    
    // 诊断点
    if (currentFrame.value === diagnosisFrame && !diagnosisResult.value) {
      diagnosisResult.value = {
        layer: currentLayer.value,
        status: 'abnormal',
        abnormalType,
        reason,
        recoverable,
        recoverLayers,
        regulated: false
      }
      console.log(`[模拟] 第${diagnosisFrame}帧: 诊断出异常 - ${abnormalType}`)
    }
  }
}

// 播放控制
const togglePlay = () => {
  if (!videoCh1.value) return
  
  if (isPlaying.value) {
    videoCh1.value.pause()
    videoCh2.value?.pause()
    videoCh3.value?.pause()
  } else {
    // 先同步时间再播放
    if (currentScene.value?.sync) {
      const ch1Time = videoCh1.value.currentTime
      const currentFps = fps.value
      
      if (videoCh2.value && currentScene.value.sync.ch2?.offset !== undefined) {
        videoCh2.value.currentTime = ch1Time + currentScene.value.sync.ch2.offset / currentFps
      }
      if (videoCh3.value && currentScene.value.sync.ch3?.offset !== undefined) {
        videoCh3.value.currentTime = ch1Time + currentScene.value.sync.ch3.offset / currentFps
      }
    }
    
    videoCh1.value.play()
    videoCh2.value?.play()
    videoCh3.value?.play()
  }
  isPlaying.value = !isPlaying.value
}

const changeSpeed = (speed) => {
  playbackSpeed.value = speed
  if (videoCh1.value) videoCh1.value.playbackRate = speed
  if (videoCh2.value) videoCh2.value.playbackRate = speed
  if (videoCh3.value) videoCh3.value.playbackRate = speed
}

const seekFrame = (frame) => {
  currentFrame.value = frame
  const currentFps = fps.value
  
  // 根据同步信息计算各通道的时间
  if (currentScene.value?.sync) {
    // 使用sync配置计算偏移
    const sync = currentScene.value.sync
    const ch1Time = frame / currentFps
    
    if (videoCh1.value) videoCh1.value.currentTime = ch1Time
    
    // CH2和CH3根据sync偏移计算
    if (sync.ch2?.offset !== undefined && videoCh2.value) {
      videoCh2.value.currentTime = Math.max(0, ch1Time + sync.ch2.offset / currentFps)
    } else if (videoCh2.value) {
      videoCh2.value.currentTime = ch1Time
    }
    
    if (sync.ch3?.offset !== undefined && videoCh3.value) {
      videoCh3.value.currentTime = Math.max(0, ch1Time + sync.ch3.offset / currentFps)
    } else if (videoCh3.value) {
      videoCh3.value.currentTime = ch1Time
    }
  } else if (currentScene.value?.timeline?.layers && currentScene.value.timeline.layers['115']) {
    // 使用CH1作为基准
    const ch1Time = frame / currentFps
    if (videoCh1.value) videoCh1.value.currentTime = ch1Time
    
    // CH2和CH3根据同步偏移计算
    const layer115 = currentScene.value.timeline.layers['115']
    const ch1Start = layer115.ch1Range[0] / currentFps
    const ch2Start = layer115.ch2Range[0] / currentFps
    const ch3Start = layer115.ch3Range[0] / currentFps
    
    const ch2Offset = ch2Start - ch1Start
    const ch3Offset = ch3Start - ch1Start
    
    if (videoCh2.value) videoCh2.value.currentTime = Math.max(0, ch1Time + ch2Offset)
    if (videoCh3.value) videoCh3.value.currentTime = Math.max(0, ch1Time + ch3Offset)
  } else {
    // 简单同步
    const time = frame / fps
    if (videoCh1.value) videoCh1.value.currentTime = time
    if (videoCh2.value) videoCh2.value.currentTime = time
    if (videoCh3.value) videoCh3.value.currentTime = time
  }
}

const prevFrame = () => seekFrame(Math.max(0, currentFrame.value - 1))
const nextFrame = () => seekFrame(Math.min(totalFrames.value, currentFrame.value + 1))
const onFrameSliderChange = (frame) => seekFrame(frame)

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 执行调控
const executeRegulation = async () => {
  isRegulating.value = true
  regulationProgress.value = 0
  regulationStatus.value = ''
  regulationMessage.value = '正在调整激光功率...'
  
  const fromPower = currentPower.value
  const toPower = standardParams.power
  
  // 模拟调控过程
  for (let i = 0; i <= 100; i += 10) {
    regulationProgress.value = i
    currentPower.value = Math.round(fromPower + (toPower - fromPower) * i / 100)
    await new Promise(r => setTimeout(r, 200))
  }
  
  // 验证恢复
  const isSuccess = !isSimulation.value || diagnosisResult.value?.recoverable !== false
  
  if (isSuccess) {
    regulationStatus.value = 'success'
    regulationMessage.value = diagnosisResult.value?.recoverLayers 
      ? `✅ 调控成功，预计${diagnosisResult.value.recoverLayers}层后完全恢复`
      : '✅ 调控成功'
  } else {
    regulationStatus.value = 'exception'
    regulationMessage.value = '❌ 调控失败：缺陷已不可逆'
  }
  
  // 记录
  regulationHistory.value.unshift({
    time: new Date().toLocaleString(),
    layer: currentLayer.value,
    from: fromPower,
    to: toPower,
    abnormalType: diagnosisResult.value?.abnormalType,
    result: isSuccess ? 'success' : 'failed'
  })
  
  if (diagnosisResult.value) {
    diagnosisResult.value.regulated = true
  }
  
  setTimeout(() => {
    isRegulating.value = false
    if (isSuccess) diagnosisResult.value = null
  }, 2000)
}

const reset = () => {
  currentPower.value = standardParams.power
  currentFrame.value = 0
  currentTime.value = 0
  diagnosisResult.value = null
  isRegulating.value = false
  regulationHistory.value = []
  if (videoCh1.value) {
    videoCh1.value.pause()
    videoCh1.value.currentTime = 0
  }
  isPlaying.value = false
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadSceneConfig()
})
</script>

<style scoped>
.regulation-panel { margin-top: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; }
.mode-tag { margin-right: 10px; }
.mode-switch { margin-bottom: 20px; display: flex; gap: 15px; align-items: center; flex-wrap: wrap; }
.scene-info { margin-bottom: 15px; }
.standard-params { margin: 15px 0; }
.text-danger { color: #f56c6c; font-weight: bold; }
.text-success { color: #67c23a; font-weight: bold; }
.deviation { color: #999; font-size: 12px; margin-left: 10px; }
.current-status { display: flex; gap: 30px; margin: 20px 0; flex-wrap: wrap; }
.status-item { display: flex; align-items: center; gap: 10px; }
.status-item label { color: #666; min-width: 60px; }

/* 层进度样式 */
.layer-progress { margin: 20px 0; }
.layer-timeline { display: flex; gap: 8px; overflow-x: auto; padding: 10px 0; }
.layer-item { 
  min-width: 80px; 
  padding: 10px; 
  border-radius: 8px; 
  text-align: center;
  background: #f5f7fa;
  border: 2px solid transparent;
  transition: all 0.3s;
}
.layer-item.active { 
  border-color: #409eff; 
  background: #ecf5ff;
  transform: scale(1.05);
}
.layer-item.fault { background: #fef0f0; }
.layer-item.fault.active { border-color: #f56c6c; }
.layer-item.regulation { background: #fdf6ec; }
.layer-item.regulation.active { border-color: #e6a23c; }
.layer-item.recovered { background: #f0f9eb; }
.layer-item.recovered.active { border-color: #67c23a; }
.layer-num { font-size: 18px; font-weight: bold; margin-bottom: 5px; }
.layer-name { font-size: 12px; color: #666; margin-bottom: 3px; }
.layer-power { font-size: 14px; font-weight: bold; }

.video-players { margin: 20px 0; }
.video-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
.video-item { text-align: center; }
.video-item label { display: block; margin-bottom: 5px; font-weight: bold; color: #666; }
.video-item video { width: 100%; max-height: 200px; border-radius: 8px; background: #000; }

.diagnosis-section { padding: 15px; border-radius: 8px; margin: 15px 0; }
.diagnosis-section.abnormal { background: #fef0f0; border: 1px solid #f56c6c; }
.regulation-action { margin-top: 20px; text-align: center; }
.suggestion-box { background: #f5f7fa; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
.suggestion-title { font-weight: bold; margin-bottom: 10px; }
.suggestion-content { font-size: 18px; margin: 10px 0; }
.recover-info { color: #666; margin-top: 10px; }

.regulating-section { text-align: center; padding: 20px; }
.regulation-message { margin-top: 15px; font-size: 16px; }

.history-section { max-height: 400px; overflow-y: auto; }

.simulation-control { margin-top: 20px; }
.control-bar { display: flex; gap: 15px; justify-content: center; margin-bottom: 20px; flex-wrap: wrap; }
.frame-slider { padding: 0 20px; }
.frame-labels { display: flex; justify-content: space-between; color: #999; font-size: 12px; margin-top: 5px; }
.playback-info { text-align: center; color: #666; margin-top: 10px; }
</style>
