<template>
  <div class="realtime-display">
    <!-- 通道状态指示器 -->
    <div class="channel-status-bar">
      <div class="status-item" :class="{ 'connected': sensorStatus.camera_ch1?.connected }">
        <span class="status-dot"></span>
        <span>CH1 {{ sensorStatus.camera_ch1?.connected ? '已连接' : '未连接' }}</span>
      </div>
      <div class="status-item" :class="{ 'connected': sensorStatus.camera_ch2?.connected }">
        <span class="status-dot"></span>
        <span>CH2 {{ sensorStatus.camera_ch2?.connected ? '已连接' : '未连接' }}</span>
      </div>
      <div class="status-item" :class="{ 'connected': sensorStatus.thermal?.connected }">
        <span class="status-dot"></span>
        <span>CH3 {{ sensorStatus.thermal?.connected ? '已连接' : '未连接' }}</span>
      </div>
    </div>

    <!-- 视频流区域 - 三个并排 -->
    <div class="video-grid">
      <!-- CH1 主摄像头 -->
      <div class="video-panel" :class="{ 'disabled': !sensorStatus.camera_ch1?.enabled, 'connected': sensorStatus.camera_ch1?.connected }">
        <div class="panel-header">
          <span class="panel-title">CH1 主摄</span>
          <div class="panel-badges">
            <el-tag v-if="!sensorStatus.camera_ch1?.enabled" type="info" size="small">已禁用</el-tag>
            <el-tag v-else-if="!sensorStatus.camera_ch1?.connected" type="danger" size="small">未连接</el-tag>
            <el-tag v-else type="success" size="small">已连接</el-tag>
          </div>
        </div>
        <div class="video-container">
          <img 
            v-if="sensorStatus.camera_ch1?.enabled && sensorStatus.camera_ch1?.connected"
            :src="ch1StreamUrl" 
            class="video-stream"
            alt="CH1 Stream"
            @error="onCh1Error"
          />
          <div v-else class="video-placeholder" :class="{ 'error': sensorStatus.camera_ch1?.enabled && !sensorStatus.camera_ch1?.connected }">
            <el-icon :size="40"><VideoCamera /></el-icon>
            <span>{{ sensorStatus.camera_ch1?.enabled ? '未连接' : '已禁用' }}</span>
            <span v-if="sensorStatus.camera_ch1?.enabled && !sensorStatus.camera_ch1?.connected" class="sub-text">请检查USB摄像头</span>
          </div>
        </div>
      </div>
      
      <!-- CH2 副摄像头 -->
      <div class="video-panel" :class="{ 'disabled': !sensorStatus.camera_ch2?.enabled, 'connected': sensorStatus.camera_ch2?.connected }">
        <div class="panel-header">
          <span class="panel-title">CH2 副摄</span>
          <div class="panel-badges">
            <el-tag v-if="!sensorStatus.camera_ch2?.enabled" type="info" size="small">已禁用</el-tag>
            <el-tag v-else-if="!sensorStatus.camera_ch2?.connected" type="danger" size="small">未连接</el-tag>
            <el-tag v-else type="success" size="small">已连接</el-tag>
          </div>
        </div>
        <div class="video-container">
          <img 
            v-if="sensorStatus.camera_ch2?.enabled && sensorStatus.camera_ch2?.connected"
            :src="ch2StreamUrl" 
            class="video-stream"
            alt="CH2 Stream"
            @error="onCh2Error"
          />
          <div v-else class="video-placeholder" :class="{ 'error': sensorStatus.camera_ch2?.enabled && !sensorStatus.camera_ch2?.connected }">
            <el-icon :size="40"><VideoCamera /></el-icon>
            <span>{{ sensorStatus.camera_ch2?.enabled ? '未连接' : '已禁用' }}</span>
            <span v-if="sensorStatus.camera_ch2?.enabled && !sensorStatus.camera_ch2?.connected" class="sub-text">请检查USB摄像头</span>
          </div>
        </div>
      </div>
      
      <!-- 红外热像 -->
      <div class="video-panel thermal-panel" :class="{ 'disabled': !sensorStatus.thermal?.enabled, 'connected': sensorStatus.thermal?.connected }">
        <div class="panel-header">
          <span class="panel-title">CH3 红外</span>
          <div class="panel-badges">
            <el-tag v-if="latestData?.thermal?.temp_max" type="warning" size="small">
              {{ latestData.thermal.temp_max.toFixed(1) }}°C
            </el-tag>
            <el-tag v-if="!sensorStatus.thermal?.enabled" type="info" size="small">已禁用</el-tag>
            <el-tag v-else-if="!sensorStatus.thermal?.connected" type="danger" size="small">未连接</el-tag>
            <el-tag v-else type="success" size="small">已连接</el-tag>
          </div>
        </div>
        <div class="video-container">
          <img 
            v-if="sensorStatus.thermal?.enabled && sensorStatus.thermal?.connected"
            :src="thermalStreamUrl" 
            class="video-stream"
            alt="Thermal Stream"
            @error="onThermalError"
          />
          <div v-else class="video-placeholder" :class="{ 'error': sensorStatus.thermal?.enabled && !sensorStatus.thermal?.connected }">
            <el-icon :size="40"><HotWater /></el-icon>
            <span>{{ sensorStatus.thermal?.enabled ? '未连接' : '已禁用' }}</span>
            <span v-if="sensorStatus.thermal?.enabled && !sensorStatus.thermal?.connected" class="sub-text">请检查PIX Connect</span>
          </div>
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
    
    <!-- 振动波形图 -->
    <div class="vibration-section">
      <VibrationWaveform 
        :waveform-data="vibrationWaveform"
        :latest-vibration="latestData?.vibration"
        :enabled="sensorStatus.vibration?.enabled"
        :connected="sensorStatus.vibration?.connected"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { VideoCamera, HotWater } from '@element-plus/icons-vue'
import VibrationWaveform from './VibrationWaveform.vue'

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
  }
})

// 视频流URL - 添加streamKey强制刷新
const ch1StreamUrl = computed(() => `/api/slm/stream/camera/CH1?t=${props.streamKey}`)
const ch2StreamUrl = computed(() => `/api/slm/stream/camera/CH2?t=${props.streamKey}`)
const thermalStreamUrl = computed(() => `/api/slm/stream/thermal?t=${props.streamKey}`)

const onCh1Error = () => console.error('CH1视频流错误')
const onCh2Error = () => console.error('CH2视频流错误')
const onThermalError = () => console.error('热像视频流错误')

// 振动波形数据
const vibrationWaveform = computed(() => {
  return props.latestData?.vibration_waveform || { x: [], y: [], z: [], sample_count: 0 }
})
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

/* 振动波形区域 */
.vibration-section {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 8px;
  padding: 16px;
}

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
