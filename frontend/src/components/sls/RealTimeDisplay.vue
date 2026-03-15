<template>
  <el-card class="realtime-display-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">实时视频显示</span>
        <div class="header-actions">
          <el-tag v-if="!sensorStatus.camera_ch1?.enabled" type="info" size="small">CH1已禁用</el-tag>
          <el-tag v-if="!sensorStatus.camera_ch2?.enabled" type="info" size="small">CH2已禁用</el-tag>
          <el-tag v-if="!sensorStatus.thermal?.enabled" type="info" size="small">红外已禁用</el-tag>
        </div>
      </div>
    </template>
    
    <div class="video-grid">
      <!-- CH1 主摄像头 -->
      <div class="video-container" v-if="sensorStatus.camera_ch1?.enabled">
        <div class="video-header">
          <span class="video-title">CH1 主摄像头</span>
          <el-tag :type="sensorStatus.camera_ch1?.connected ? 'success' : 'danger'" size="small">
            {{ sensorStatus.camera_ch1?.connected ? '已连接' : '未连接' }}
          </el-tag>
        </div>
        <div class="video-wrapper">
          <img 
            v-if="sensorStatus.camera_ch1?.connected"
            :src="`/api/sls/stream/camera_ch1?t=${streamKey}`" 
            class="video-stream"
            @error="handleImageError('CH1')"
          />
          <div v-else class="video-placeholder">
            <el-icon :size="48"><VideoCamera /></el-icon>
            <span>CH1 未连接</span>
          </div>
        </div>
      </div>
      
      <!-- CH2 副摄像头 -->
      <div class="video-container" v-if="sensorStatus.camera_ch2?.enabled">
        <div class="video-header">
          <span class="video-title">CH2 副摄像头</span>
          <el-tag :type="sensorStatus.camera_ch2?.connected ? 'success' : 'danger'" size="small">
            {{ sensorStatus.camera_ch2?.connected ? '已连接' : '未连接' }}
          </el-tag>
        </div>
        <div class="video-wrapper">
          <img 
            v-if="sensorStatus.camera_ch2?.connected"
            :src="`/api/sls/stream/camera_ch2?t=${streamKey}`" 
            class="video-stream"
            @error="handleImageError('CH2')"
          />
          <div v-else class="video-placeholder">
            <el-icon :size="48"><VideoCamera /></el-icon>
            <span>CH2 未连接</span>
          </div>
        </div>
      </div>
      
      <!-- 红外热像仪 -->
      <div class="video-container" v-if="sensorStatus.thermal?.enabled">
        <div class="video-header">
          <span class="video-title">
            红外热像
            <el-tag size="small" type="info">
              {{ sensorStatus.thermal?.type === 'ir8062' ? 'IR8062' : 'Fotric' }}
            </el-tag>
          </span>
          <el-tag :type="sensorStatus.thermal?.connected ? 'success' : 'danger'" size="small">
            {{ sensorStatus.thermal?.connected ? '已连接' : '未连接' }}
          </el-tag>
        </div>
        <div class="video-wrapper thermal-wrapper">
          <img 
            v-if="sensorStatus.thermal?.connected"
            :src="`/api/sls/stream/thermal?t=${streamKey}`" 
            class="video-stream thermal-stream"
            @error="handleImageError('thermal')"
          />
          <div v-else class="video-placeholder">
            <el-icon :size="48"><MostlyCloudy /></el-icon>
            <span>红外未连接</span>
          </div>
          <!-- 温度数据显示 -->
          <div class="thermal-overlay" v-if="latestData.thermal">
            <div class="temp-item">
              <span class="temp-label">最高:</span>
              <span class="temp-value max">{{ latestData.thermal.temp_max?.toFixed(1) || '--' }}°C</span>
            </div>
            <div class="temp-item">
              <span class="temp-label">最低:</span>
              <span class="temp-value min">{{ latestData.thermal.temp_min?.toFixed(1) || '--' }}°C</span>
            </div>
            <div class="temp-item">
              <span class="temp-label">平均:</span>
              <span class="temp-value avg">{{ latestData.thermal.temp_avg?.toFixed(1) || '--' }}°C</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { VideoCamera, MostlyCloudy } from '@element-plus/icons-vue'

const props = defineProps({
  sensorStatus: {
    type: Object,
    required: true
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

const handleImageError = (channel) => {
  console.error(`[RealTimeDisplay] ${channel} 视频流加载失败`)
}
</script>

<style scoped>
.realtime-display-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
}

.video-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.video-title {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.video-wrapper {
  position: relative;
  aspect-ratio: 16/9;
  background: rgba(30, 41, 59, 0.8);
  border-radius: 8px;
  overflow: hidden;
}

.video-stream {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thermal-stream {
  filter: contrast(1.1) saturate(1.2);
}

.video-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #64748b;
}

.thermal-wrapper {
  position: relative;
}

.thermal-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.7);
  border-radius: 6px;
  backdrop-filter: blur(4px);
}

.temp-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.temp-label {
  color: #94a3b8;
  min-width: 32px;
}

.temp-value {
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.temp-value.max {
  color: #ef4444;
}

.temp-value.min {
  color: #3b82f6;
}

.temp-value.avg {
  color: #22c55e;
}

@media (max-width: 768px) {
  .video-grid {
    grid-template-columns: 1fr;
  }
}
</style>
