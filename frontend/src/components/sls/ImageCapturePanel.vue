<template>
  <el-card class="capture-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">
          <el-icon><Camera /></el-icon>
          振动触发图像采集
        </span>
        <el-tag :type="isCapturing ? 'success' : 'info'" size="small">
          {{ isCapturing ? '采集中' : '待机' }}
        </el-tag>
      </div>
    </template>
    
    <div class="capture-content">
      <div class="capture-stats">
        <div class="stat-box">
          <div class="stat-value">{{ layerCount }}</div>
          <div class="stat-label">已采集层数</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">{{ totalCaptures }}</div>
          <div class="stat-label">总采集次数</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">{{ lastTriggerTime || '--' }}</div>
          <div class="stat-label">上次触发</div>
        </div>
      </div>
      
      <div class="capture-controls">
        <el-button 
          :type="isCapturing ? 'danger' : 'primary'"
          size="large"
          :disabled="!isRunning"
          @click="toggleCapture"
        >
          <el-icon><Camera /></el-icon>
          {{ isCapturing ? '停止采集' : '开始采集' }}
        </el-button>
        
        <el-button 
          type="warning"
          size="large"
          :disabled="!isRunning"
          @click="manualTrigger"
        >
          <el-icon><Aim /></el-icon>
          手动触发
        </el-button>
        
        <el-button 
          type="info"
          size="large"
          @click="resetCounter"
        >
          <el-icon><RefreshRight /></el-icon>
          重置计数
        </el-button>
      </div>
      
      <div class="capture-settings">
        <el-divider content-position="left">采集设置</el-divider>
        <div class="settings-row">
          <div class="setting-item">
            <span class="setting-label">振动阈值:</span>
            <el-slider v-model="threshold" :min="0.01" :max="1" :step="0.01" style="width: 150px" />
            <span class="setting-value">{{ threshold.toFixed(2) }}</span>
          </div>
          <div class="setting-item">
            <span class="setting-label">保存路径:</span>
            <el-input v-model="savePath" placeholder="采集保存路径" style="width: 250px" />
            <el-button type="primary" size="small" @click="browsePath">浏览</el-button>
          </div>
        </div>
      </div>
      
      <div class="capture-log">
        <el-divider content-position="left">采集日志</el-divider>
        <div class="log-container" ref="logContainer">
          <div 
            v-for="(log, index) in captureLogs" 
            :key="index"
            class="log-item"
            :class="log.type"
          >
            <span class="log-time">{{ log.time }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
          <div v-if="captureLogs.length === 0" class="log-empty">
            暂无采集记录
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { Camera, Aim, RefreshRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const props = defineProps({
  isRunning: {
    type: Boolean,
    default: false
  },
  latestData: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['capture-triggered'])

const isCapturing = ref(false)
const layerCount = ref(0)
const totalCaptures = ref(0)
const lastTriggerTime = ref('')
const threshold = ref(0.1)
const savePath = ref('F:/SLS_recordings')
const captureLogs = ref([])
const logContainer = ref(null)

// 监听振动数据，自动触发
watch(() => props.latestData.vibration, (vibration) => {
  if (!isCapturing.value || !vibration) return
  
  const magnitude = Math.sqrt(
    Math.pow(vibration.x || 0, 2) +
    Math.pow(vibration.y || 0, 2) +
    Math.pow(vibration.z || 0, 2)
  )
  
  if (magnitude > threshold.value) {
    handleVibrationTrigger(magnitude)
  }
}, { deep: true })

const handleVibrationTrigger = (magnitude) => {
  const now = new Date()
  const timeStr = now.toLocaleTimeString()
  
  layerCount.value++
  totalCaptures.value++
  lastTriggerTime.value = timeStr
  
  addLog('trigger', `振动触发采集，幅度: ${magnitude.toFixed(4)}`)
  
  emit('capture-triggered', {
    type: 'vibration',
    layer: layerCount.value,
    magnitude: magnitude,
    timestamp: now.toISOString()
  })
}

const toggleCapture = async () => {
  try {
    if (isCapturing.value) {
      await axios.post('/api/sls/capture/stop')
      isCapturing.value = false
      addLog('info', '停止振动触发采集')
      ElMessage.success('采集已停止')
    } else {
      await axios.post('/api/sls/capture/start', {
        threshold: threshold.value,
        save_path: savePath.value
      })
      isCapturing.value = true
      addLog('info', '开始振动触发采集')
      ElMessage.success('采集已启动')
    }
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const manualTrigger = async () => {
  try {
    await axios.post('/api/sls/capture/trigger')
    layerCount.value++
    totalCaptures.value++
    lastTriggerTime.value = new Date().toLocaleTimeString()
    addLog('success', '手动触发采集')
    emit('capture-triggered', {
      type: 'manual',
      layer: layerCount.value,
      timestamp: new Date().toISOString()
    })
    ElMessage.success('手动触发成功')
  } catch (error) {
    ElMessage.error('触发失败')
  }
}

const resetCounter = () => {
  layerCount.value = 0
  totalCaptures.value = 0
  lastTriggerTime.value = ''
  captureLogs.value = []
  ElMessage.success('计数已重置')
}

const browsePath = () => {
  // 实际应用中这里会打开文件夹选择对话框
  ElMessage.info('请选择保存路径')
}

const addLog = (type, message) => {
  const now = new Date()
  captureLogs.value.unshift({
    type,
    time: now.toLocaleTimeString(),
    message
  })
  
  // 限制日志数量
  if (captureLogs.value.length > 50) {
    captureLogs.value = captureLogs.value.slice(0, 50)
  }
  
  // 滚动到顶部
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = 0
    }
  })
}
</script>

<style scoped>
.capture-card {
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
  display: flex;
  align-items: center;
  gap: 8px;
}

.capture-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.capture-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.stat-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  font-family: 'Courier New', monospace;
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.capture-controls {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.capture-settings {
  padding: 0 16px;
}

.settings-row {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.setting-label {
  font-size: 13px;
  color: #94a3b8;
  min-width: 60px;
}

.setting-value {
  font-size: 13px;
  color: #e2e8f0;
  font-family: 'Courier New', monospace;
  min-width: 40px;
}

.capture-log {
  padding: 0 16px;
}

.log-container {
  max-height: 200px;
  overflow-y: auto;
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
}

.log-item {
  display: flex;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid rgba(100, 116, 139, 0.2);
  font-size: 12px;
}

.log-item:last-child {
  border-bottom: none;
}

.log-time {
  color: #64748b;
  font-family: 'Courier New', monospace;
  min-width: 60px;
}

.log-message {
  color: #e2e8f0;
}

.log-item.trigger .log-message {
  color: #22c55e;
}

.log-item.success .log-message {
  color: #3b82f6;
}

.log-item.error .log-message {
  color: #ef4444;
}

.log-empty {
  text-align: center;
  color: #64748b;
  padding: 20px;
}

@media (max-width: 768px) {
  .capture-stats {
    grid-template-columns: 1fr;
  }
  
  .capture-controls {
    flex-direction: column;
  }
  
  .settings-row {
    flex-direction: column;
  }
  
  .setting-item {
    flex-wrap: wrap;
  }
}
</style>
