<template>
  <div class="realtime-display">
    <!-- 通道状态指示器 -->
    <div class="channel-status-bar">
      <div class="status-item" :class="{ connected: sensorStatus.camera_ch1?.connected, waiting: !useMockMode, stored: isStoredMockSource }">
        <span class="status-dot"></span>
        <span>CH1 {{ channelStatusText('camera_ch1') }}</span>
      </div>
      <div class="status-item" :class="{ connected: sensorStatus.camera_ch2?.connected, waiting: !useMockMode, stored: isStoredMockSource }">
        <span class="status-dot"></span>
        <span>CH2 {{ channelStatusText('camera_ch2') }}</span>
      </div>
      <div class="status-item" :class="{ connected: sensorStatus.thermal?.connected, waiting: !useMockMode, stored: isStoredMockSource }">
        <span class="status-dot"></span>
        <span>CH3 {{ channelStatusText('thermal') }}</span>
      </div>
    </div>

    <!-- 视频流区域 - 三个并排 -->
    <div class="video-grid">
      <!-- CH1 主摄像头 -->
      <div class="video-panel" :class="{ disabled: useMockMode && !isStoredMockSource && !sensorStatus.camera_ch1?.enabled, connected: sensorStatus.camera_ch1?.connected }">
        <div class="panel-header">
          <span class="panel-title">CH1 主摄</span>
          <div class="panel-badges">
            <el-tag v-if="distortionCorrectionEnabled" type="warning" size="small">已校正</el-tag>
            <el-tag v-if="!useMockMode" type="info" size="small">{{ realtimeTagText }}</el-tag>
            <el-tag v-else-if="isStoredMockSource" type="info" size="small">存储数据</el-tag>
            <el-tag v-else-if="!sensorStatus.camera_ch1?.enabled" type="info" size="small">已禁用</el-tag>
            <el-tag v-else-if="!sensorStatus.camera_ch1?.connected" type="danger" size="small">未连接</el-tag>
            <el-tag v-else type="success" size="small">已连接</el-tag>
          </div>
        </div>
        <div class="video-container">
          <video
            v-if="sensorStatus.camera_ch1?.enabled && sensorStatus.camera_ch1?.connected && ch1HasStream && ch1MediaType === 'video'"
            :src="ch1StreamUrl"
            class="video-stream"
            :class="{ 'paused': displayPaused }"
            autoplay
            muted
            loop
            playsinline
            controls
            @error="onCh1Error"
          />
          <img 
            v-else-if="sensorStatus.camera_ch1?.enabled && sensorStatus.camera_ch1?.connected && ch1HasStream"
            :src="ch1StreamUrl" 
            class="video-stream"
            :class="{ 'paused': displayPaused }"
            alt="CH1 Stream"
            @error="onCh1Error"
          />
          <div v-else class="video-placeholder" :class="{ error: useMockMode && sensorStatus.camera_ch1?.enabled && !sensorStatus.camera_ch1?.connected }">
            <el-icon :size="40"><VideoCamera /></el-icon>
            <span>{{ placeholderText('camera_ch1') }}</span>
            <span class="sub-text">{{ placeholderHint('camera_ch1') }}</span>
          </div>
          <!-- 暂停遮罩 -->
          <div v-if="displayPaused && sensorStatus.camera_ch1?.enabled && sensorStatus.camera_ch1?.connected" class="pause-overlay">
            <el-icon :size="30"><VideoPause /></el-icon>
            <span>录制中</span>
          </div>
          <!-- ROI覆盖层 -->
          <template v-if="showROI && sensorStatus.camera_ch1?.enabled && sensorStatus.camera_ch1?.connected">
            <div 
              v-for="roi in roiList" 
              :key="roi.id"
              class="roi-overlay"
              :style="getROIStyle(roi)"
            />
            <div 
              v-for="roi in roiList" 
              :key="`label-${roi.id}`"
              class="roi-label"
              :style="getROILabelStyle(roi)"
            >
              {{ roi.name }}
            </div>
          </template>
        </div>
      </div>
      
      <!-- CH2 副摄像头 -->
      <div class="video-panel" :class="{ disabled: useMockMode && !isStoredMockSource && !sensorStatus.camera_ch2?.enabled, connected: sensorStatus.camera_ch2?.connected }">
        <div class="panel-header">
          <span class="panel-title">CH2 副摄</span>
          <div class="panel-badges">
            <el-tag v-if="distortionCorrectionEnabled" type="warning" size="small">已校正</el-tag>
            <el-tag v-if="!useMockMode" type="info" size="small">{{ realtimeTagText }}</el-tag>
            <el-tag v-else-if="isStoredMockSource" type="info" size="small">存储数据</el-tag>
            <el-tag v-else-if="!sensorStatus.camera_ch2?.enabled" type="info" size="small">已禁用</el-tag>
            <el-tag v-else-if="!sensorStatus.camera_ch2?.connected" type="danger" size="small">未连接</el-tag>
            <el-tag v-else type="success" size="small">已连接</el-tag>
          </div>
        </div>
        <div class="video-container">
          <video
            v-if="sensorStatus.camera_ch2?.enabled && sensorStatus.camera_ch2?.connected && ch2HasStream && ch2MediaType === 'video'"
            :src="ch2StreamUrl"
            class="video-stream"
            :class="{ 'paused': displayPaused }"
            autoplay
            muted
            loop
            playsinline
            controls
            @error="onCh2Error"
          />
          <img
            v-else-if="sensorStatus.camera_ch2?.enabled && sensorStatus.camera_ch2?.connected && ch2HasStream"
            :src="ch2StreamUrl" 
            class="video-stream"
            :class="{ 'paused': displayPaused }"
            alt="CH2 Stream"
            @error="onCh2Error"
          />
          <div v-else class="video-placeholder" :class="{ error: useMockMode && sensorStatus.camera_ch2?.enabled && !sensorStatus.camera_ch2?.connected }">
            <el-icon :size="40"><VideoCamera /></el-icon>
            <span>{{ placeholderText('camera_ch2') }}</span>
            <span class="sub-text">{{ placeholderHint('camera_ch2') }}</span>
          </div>
          <!-- 暂停遮罩 -->
          <div v-if="displayPaused && sensorStatus.camera_ch2?.enabled && sensorStatus.camera_ch2?.connected" class="pause-overlay">
            <el-icon :size="30"><VideoPause /></el-icon>
            <span>录制中</span>
          </div>
          <!-- ROI覆盖层 -->
          <template v-if="showROI && sensorStatus.camera_ch2?.enabled && sensorStatus.camera_ch2?.connected">
            <div 
              v-for="roi in roiList" 
              :key="roi.id"
              class="roi-overlay"
              :style="getROIStyle(roi)"
            />
            <div 
              v-for="roi in roiList" 
              :key="`label-${roi.id}`"
              class="roi-label"
              :style="getROILabelStyle(roi)"
            >
              {{ roi.name }}
            </div>
          </template>
        </div>
      </div>
      
      <!-- 红外热像 -->
      <div class="video-panel thermal-panel" :class="{ disabled: useMockMode && !isStoredMockSource && !sensorStatus.thermal?.enabled, connected: sensorStatus.thermal?.connected }">
        <div class="panel-header">
          <span class="panel-title">CH3 红外</span>
          <div class="panel-badges">
            <el-tag v-if="distortionCorrectionEnabled" type="warning" size="small">已校正</el-tag>
            <el-tag v-if="latestData?.thermal?.temp_max" type="warning" size="small">
              {{ latestData.thermal.temp_max.toFixed(1) }}°C
            </el-tag>
            <el-tag v-if="!useMockMode" type="info" size="small">{{ realtimeTagText }}</el-tag>
            <el-tag v-else-if="isStoredMockSource" type="info" size="small">存储数据</el-tag>
            <el-tag v-else-if="!sensorStatus.thermal?.enabled" type="info" size="small">已禁用</el-tag>
            <el-tag v-else-if="!sensorStatus.thermal?.connected" type="danger" size="small">未连接</el-tag>
            <el-tag v-else type="success" size="small">已连接</el-tag>
          </div>
        </div>
        <div class="video-container">
          <video
            v-if="sensorStatus.thermal?.enabled && sensorStatus.thermal?.connected && thermalHasStream && thermalMediaType === 'video'"
            :src="thermalStreamUrl"
            class="video-stream"
            :class="{ 'paused': displayPaused }"
            autoplay
            muted
            loop
            playsinline
            controls
            @error="onThermalError"
          />
          <img
            v-else-if="sensorStatus.thermal?.enabled && sensorStatus.thermal?.connected && thermalHasStream"
            :src="thermalStreamUrl" 
            class="video-stream"
            :class="{ 'paused': displayPaused }"
            alt="Thermal Stream"
            @error="onThermalError"
          />
          <div v-else class="video-placeholder" :class="{ error: useMockMode && sensorStatus.thermal?.enabled && !sensorStatus.thermal?.connected }">
            <el-icon :size="40"><HotWater /></el-icon>
            <span>{{ placeholderText('thermal') }}</span>
            <span class="sub-text">{{ placeholderHint('thermal') }}</span>
          </div>
          <!-- 暂停遮罩 -->
          <div v-if="displayPaused && sensorStatus.thermal?.enabled && sensorStatus.thermal?.connected" class="pause-overlay">
            <el-icon :size="30"><VideoPause /></el-icon>
            <span>录制中</span>
          </div>
          <!-- ROI覆盖层 -->
          <template v-if="showROI && sensorStatus.thermal?.enabled && sensorStatus.thermal?.connected">
            <div 
              v-for="roi in roiList" 
              :key="roi.id"
              class="roi-overlay"
              :style="getROIStyle(roi)"
            />
            <div 
              v-for="roi in roiList" 
              :key="`label-${roi.id}`"
              class="roi-label"
              :style="getROILabelStyle(roi)"
            >
              {{ roi.name }}
            </div>
          </template>
        </div>
        <!-- 温度信息 -->
        <div v-if="sensorStatus.thermal?.enabled && sensorStatus.thermal?.connected && latestData?.thermal" class="thermal-info">
          <div class="temp-item">
            <span class="temp-label">最高</span>
            <span class="temp-value temp-max">{{ latestData.thermal.temp_max?.toFixed(1) }}°C</span>
          </div>
          <div class="temp-item">
            <span class="temp-label">最低</span>
            <span class="temp-value temp-min">{{ latestData.thermal.temp_min?.toFixed(1) }}°C</span>
          </div>
          <div class="temp-item">
            <span class="temp-label">平均</span>
            <span class="temp-value temp-avg">{{ latestData.thermal.temp_avg?.toFixed(1) }}°C</span>
          </div>
        </div>
      </div>
    </div>
    
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { VideoCamera, HotWater, VideoPause } from '@element-plus/icons-vue'
import { useROIStore } from '../../stores/roiStore'

const props = defineProps({
  sensorStatus: {
    type: Object,
    default: () => ({})
  },
  latestData: {
    type: Object,
    default: () => ({})
  },
  streamKey: {
    type: Number,
    default: 0
  },
  displayPaused: {
    type: Boolean,
    default: false
  },
  // 视频容器尺寸（用于计算ROI位置）
  videoSize: {
    type: Object,
    default: () => ({ width: 640, height: 480 })
  },
  lastFrames: {
    type: Object,
    default: () => ({ CH1: null, CH2: null, thermal: null })
  },
  useMockMode: {
    type: Boolean,
    default: false
  },
  mockSourceType: {
    type: String,
    default: ''
  },
  waitingForRealtime: {
    type: Boolean,
    default: false
  },
  // 华科四台模拟设备在调控页固定展示ROI，不依赖全局ROI面板开关。
  forceShowROI: {
    type: Boolean,
    default: false
  },
  distortionCorrectionEnabled: {
    type: Boolean,
    default: false
  }
})

// Store
const roiStore = useROIStore()

// 视频流 URL 由设备详情页按当前设备注入；不再在显示层决定全局模拟源。
const mediaUrl = (media = {}) => media.data_url || media.url || ''
const detectMediaType = (media = {}) => {
  const explicitType = media.media_type || media.type || ''
  if (explicitType) return explicitType
  return /\.(mp4|webm|ogg|mov)(\?|$)/i.test(mediaUrl(media)) ? 'video' : 'image'
}

const ch1RealtimeMedia = computed(() => props.latestData?.camera_ch1 || {})
const ch2RealtimeMedia = computed(() => props.latestData?.camera_ch2 || {})
const thermalRealtimeMedia = computed(() => props.latestData?.thermal || {})
const ch1StreamUrl = computed(() => mediaUrl(ch1RealtimeMedia.value))
const ch2StreamUrl = computed(() => mediaUrl(ch2RealtimeMedia.value))
const thermalStreamUrl = computed(() => mediaUrl(thermalRealtimeMedia.value))
const ch1MediaType = computed(() => detectMediaType(ch1RealtimeMedia.value))
const ch2MediaType = computed(() => detectMediaType(ch2RealtimeMedia.value))
const thermalMediaType = computed(() => detectMediaType(thermalRealtimeMedia.value))
const ch1HasStream = computed(() => Boolean(ch1StreamUrl.value))
const ch2HasStream = computed(() => Boolean(ch2StreamUrl.value))
const thermalHasStream = computed(() => Boolean(thermalStreamUrl.value))
const realtimeTagText = computed(() => props.waitingForRealtime ? '等待数据' : '等待图像')
const isStoredMockSource = computed(() => props.useMockMode && props.mockSourceType === 'stored7103')

const channelStatusText = (key) => {
  if (!props.useMockMode) return props.waitingForRealtime ? '等待数据传输' : '等待图像数据'
  if (isStoredMockSource.value) return '存储数据'
  if (!props.sensorStatus[key]?.enabled) return '已禁用'
  return props.sensorStatus[key]?.connected ? '已连接' : '未连接'
}

const placeholderText = (key) => {
  if (!props.useMockMode) return props.waitingForRealtime ? '等待数据传输' : '等待图像数据'
  if (isStoredMockSource.value) return '暂不支持视频接入'
  return props.sensorStatus[key]?.enabled ? '未连接' : '已禁用'
}

const placeholderHint = (key) => {
  if (!props.useMockMode) return props.waitingForRealtime ? '外部接口推送后显示实时图像' : '本次实时事件未包含图像'
  if (isStoredMockSource.value) return '如需接入视频，请在设备目录下创建 mock_video/CH1..CH3'
  if (!props.sensorStatus[key]?.enabled) return ''
  return key === 'thermal' ? '请检查PIX Connect' : '请检查USB摄像头'
}

const onCh1Error = () => console.error('CH1视频流错误')
const onCh2Error = () => console.error('CH2视频流错误')
const onThermalError = () => console.error('热像视频流错误')

// ROI显示
const showROI = computed(() => props.forceShowROI || roiStore.showROIOnVideo)
const roiList = computed(() => roiStore.roiList)

// 计算ROI样式（将ROI坐标转换为CSS样式）
function getROIStyle(roi) {
  const coords = roi.coords || []
  const videoW = props.videoSize.width
  const videoH = props.videoSize.height
  
  if (roi.type === 'rectangle' && coords.length >= 4) {
    // 矩形: [x, y, width, height]
    const [x, y, w, h] = coords
    return {
      left: `${(x / videoW) * 100}%`,
      top: `${(y / videoH) * 100}%`,
      width: `${(w / videoW) * 100}%`,
      height: `${(h / videoH) * 100}%`,
      border: '2px solid #ef4444',
      position: 'absolute',
      pointerEvents: 'none',
      zIndex: 10
    }
  } else if (roi.type === 'circle' && coords.length >= 3) {
    // 圆形: [cx, cy, radius]
    const [cx, cy, r] = coords
    return {
      left: `${((cx - r) / videoW) * 100}%`,
      top: `${((cy - r) / videoH) * 100}%`,
      width: `${((r * 2) / videoW) * 100}%`,
      height: `${((r * 2) / videoH) * 100}%`,
      border: '2px solid #ef4444',
      borderRadius: '50%',
      position: 'absolute',
      pointerEvents: 'none',
      zIndex: 10
    }
  }
  return {}
}

// ROI标签样式
function getROILabelStyle(roi) {
  const style = getROIStyle(roi)
  return {
    left: style.left,
    top: `calc(${style.top} - 20px)`,
    position: 'absolute',
    background: '#ef4444',
    color: 'white',
    fontSize: '10px',
    padding: '2px 6px',
    borderRadius: '4px',
    pointerEvents: 'none',
    zIndex: 11,
    whiteSpace: 'nowrap'
  }
}


</script>

<style scoped>
.realtime-display {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 通道状态指示器 */
.channel-status-bar {
  display: flex;
  gap: 20px;
  padding: 12px 16px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 8px;
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #94a3b8;
}

.status-item.connected {
  color: #22c55e;
}

.status-item.waiting {
  color: #94a3b8;
}

.status-item.stored {
  color: #38bdf8;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
}

.status-item.connected .status-dot {
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}

.status-item.waiting .status-dot {
  background: #64748b;
  box-shadow: none;
}

.status-item.stored .status-dot {
  background: #38bdf8;
  box-shadow: 0 0 8px rgba(56, 189, 248, 0.8);
}

/* 视频网格 - 三个并排 */
.video-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.video-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.video-panel.disabled {
  opacity: 0.5;
}

.video-panel.connected {
  border-color: rgba(34, 197, 94, 0.5);
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.1);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: rgba(30, 41, 59, 0.5);
  border-bottom: 1px solid rgba(100, 116, 139, 0.2);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.panel-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.video-container {
  position: relative;
  aspect-ratio: 4/3;
  background: #0f172a;
  overflow: hidden;
}

.video-stream {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-stream.paused {
  filter: brightness(0.6);
}

.pause-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
}

.video-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #64748b;
}

.video-placeholder.error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.video-placeholder .sub-text {
  font-size: 11px;
  color: #94a3b8;
}

.video-placeholder.error .sub-text {
  color: #f87171;
}

/* ROI覆盖层 */
.roi-overlay {
  box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.5), 0 0 10px rgba(239, 68, 68, 0.3);
  animation: roi-pulse 2s ease-in-out infinite;
}

@keyframes roi-pulse {
  0%, 100% {
    box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.5), 0 0 10px rgba(239, 68, 68, 0.3);
  }
  50% {
    box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.7), 0 0 15px rgba(239, 68, 68, 0.5);
  }
}

.roi-label {
  font-weight: 500;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

/* 热像温度信息 */
.thermal-info {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.5);
  border-top: 1px solid rgba(100, 116, 139, 0.2);
}

.temp-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.temp-label {
  font-size: 10px;
  color: #94a3b8;
}

.temp-value {
  font-size: 13px;
  font-weight: 600;
}

.temp-max { color: #ef4444; }
.temp-min { color: #3b82f6; }
.temp-avg { color: #22c55e; }

@media (max-width: 1200px) {
  .video-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .video-grid {
    grid-template-columns: 1fr;
  }
  
  .channel-status-bar {
    flex-direction: column;
    gap: 8px;
  }
}
</style>
