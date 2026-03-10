<template>
  <el-card class="image-capture-panel" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">
          <el-icon><Camera /></el-icon>
          振动触发图像采集
        </span>
        <div class="header-tags">
          <el-tag 
            :type="captureStatus.is_capturing ? 'success' : 'info'" 
            size="small"
            effect="dark"
          >
            {{ captureStatus.is_capturing ? '采集中' : '未采集' }}
          </el-tag>
          <el-tag 
            v-if="captureStatus.layer_count > 0"
            type="warning" 
            size="small"
            effect="dark"
          >
            层数: {{ captureStatus.layer_count }}
          </el-tag>
        </div>
      </div>
    </template>

    <!-- 振动强度实时显示 -->
    <div class="vibration-display">
      <el-divider content-position="left">
        <el-icon><Histogram /></el-icon>
        实时振动监测
      </el-divider>
      
      <div class="vibration-values">
        <div class="vib-item">
          <span class="vib-label">X轴</span>
          <el-progress 
            :percentage="Math.min(100, (currentVibration.vx / 1.0) * 100)" 
            :color="getVibrationColor(currentVibration.vx, config.threshold)"
            :stroke-width="8"
            :show-text="false"
          />
          <span class="vib-value">{{ currentVibration.vx.toFixed(3) }}</span>
        </div>
        <div class="vib-item">
          <span class="vib-label">Y轴</span>
          <el-progress 
            :percentage="Math.min(100, (currentVibration.vy / 1.0) * 100)" 
            :color="getVibrationColor(currentVibration.vy, config.threshold)"
            :stroke-width="8"
            :show-text="false"
          />
          <span class="vib-value">{{ currentVibration.vy.toFixed(3) }}</span>
        </div>
        <div class="vib-item">
          <span class="vib-label">Z轴</span>
          <el-progress 
            :percentage="Math.min(100, (currentVibration.vz / 1.0) * 100)" 
            :color="getVibrationColor(currentVibration.vz, config.threshold)"
            :stroke-width="8"
            :show-text="false"
          />
          <span class="vib-value">{{ currentVibration.vz.toFixed(3) }}</span>
        </div>
        <div class="vib-item magnitude">
          <span class="vib-label">综合强度</span>
          <el-progress 
            :percentage="Math.min(100, (currentVibration.magnitude / 1.0) * 100)" 
            :color="getVibrationColor(currentVibration.magnitude, config.threshold)"
            :stroke-width="12"
            status="exception"
          />
          <span class="vib-value" :class="{ 'over-threshold': currentVibration.magnitude > config.threshold }">
            {{ currentVibration.magnitude.toFixed(3) }}
          </span>
        </div>
      </div>
      
      <!-- 阈值指示线 -->
      <div class="threshold-indicator">
        <span>触发阈值: {{ config.threshold }}</span>
        <span v-if="currentVibration.magnitude > config.threshold" class="trigger-status high">高于阈值</span>
        <span v-else class="trigger-status low">低于阈值</span>
      </div>
    </div>

    <!-- 采集设置 -->
    <div class="capture-settings">
      <el-divider content-position="left">
        <el-icon><Setting /></el-icon>
        采集设置
      </el-divider>
      
      <el-form :model="config" label-width="120px" size="small">
        <!-- 保存目录 -->
        <el-form-item label="保存目录">
          <div class="directory-input">
            <el-input 
              v-model="config.saveDir" 
              readonly
              size="small"
            >
              <template #append>
                <el-button @click="selectDirectory" size="small" :loading="checkingDirectory">
                  <el-icon><Folder /></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>
          <div class="directory-hint">
            结构: {{ config.saveDir }}/时间戳/CH1,CH2,CH3/LayerX_before/after_时间戳.jpg
          </div>
        </el-form-item>
        
        <!-- 振动阈值 -->
        <el-form-item label="振动阈值">
          <el-slider 
            v-model="config.threshold" 
            :min="0.01" 
            :max="1.0" 
            :step="0.01"
            show-input
            @change="onThresholdChange"
          />
          <span class="form-hint">振动强度低于此值时触发采集（下降沿触发）</span>
        </el-form-item>
        
        <!-- 防抖时间 -->
        <el-form-item label="防抖时间">
          <el-slider 
            v-model="config.debounceTime" 
            :min="0.1" 
            :max="2.0" 
            :step="0.1"
            :marks="{0.1: '0.1s', 1.0: '1s', 2.0: '2s'}"
            @change="onDebounceChange"
          />
          <span class="form-hint">{{ config.debounceTime }} 秒 - 避免同一事件重复触发</span>
        </el-form-item>
        
        <!-- 层数计数 -->
        <el-form-item label="当前层数">
          <div class="layer-display">
            <el-statistic :value="captureStatus.layer_count" title="已完成层数">
              <template #suffix>层</template>
            </el-statistic>
            <el-button 
              size="small" 
              @click="resetLayerCount"
              :disabled="captureStatus.is_capturing"
            >
              重置计数
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- 采集控制 -->
    <div class="capture-control">
      <el-divider content-position="left">
        <el-icon><VideoCamera /></el-icon>
        采集控制
      </el-divider>
      
      <div class="control-buttons">
        <el-button
          :type="captureStatus.is_capturing ? 'danger' : 'primary'"
          size="large"
          @click="toggleCapture"
          :disabled="!isRunning || !isDirectoryValid"
          :loading="controlLoading"
        >
          <el-icon><VideoCamera /></el-icon>
          {{ captureStatus.is_capturing ? '停止采集' : '开始采集' }}
        </el-button>
        
        <el-button
          type="info"
          size="large"
          @click="fetchStatus"
          :loading="statusLoading"
        >
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>
      </div>
      
      <!-- 采集状态信息 -->
      <div v-if="captureStatus.is_capturing" class="capture-info">
        <el-alert
          type="success"
          :closable="false"
          show-icon
        >
          <template #title>
            采集中 - 等待振动触发
          </template>
          <template #default>
            <div class="status-detail">
              <p>状态: {{ captureStatus.state }}</p>
              <p>已采集: {{ captureStatus.total_captures }} 张图像</p>
              <p>当前层: {{ captureStatus.layer_count }}</p>
              <p v-if="lastCaptureInfo">
                上次触发: {{ lastCaptureInfo.type }} (层{{ lastCaptureInfo.layer }})
              </p>
            </div>
          </template>
        </el-alert>
      </div>
      
      <!-- 上次会话信息 -->
      <div v-else-if="lastSessionInfo" class="last-session">
        <el-tag type="success" size="large">
          上次采集: {{ lastSessionInfo.total_captures }} 张图像, {{ lastSessionInfo.layer_count }} 层
        </el-tag>
      </div>
    </div>

    <!-- 采集历史 -->
    <div v-if="captureHistory.length > 0" class="history-section">
      <el-divider content-position="left">
        <el-icon><Timer /></el-icon>
        采集历史
      </el-divider>
      
      <el-table :data="captureHistory" size="small" max-height="200">
        <el-table-column prop="layer" label="层数" width="70">
          <template #default="{ row }">
            <el-tag size="small" type="primary">Layer{{ row.layer }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.type === 'before' ? 'warning' : 'success'" size="small">
              {{ row.type === 'before' ? 'Before' : 'After' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="时间" width="150" />
        <el-table-column prop="channels" label="通道" />
      </el-table>
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { Camera, Histogram, Setting, Folder, VideoCamera, Refresh, Timer } from '@element-plus/icons-vue'
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

// 配置
const config = reactive({
  saveDir: 'E:/SmartAM_recordings',
  threshold: 0.1,
  debounceTime: 0.5
})

// 状态
const captureStatus = reactive({
  is_capturing: false,
  state: 'idle',
  layer_count: 0,
  trigger_count: 0,
  total_captures: 0,
  threshold: 0.1,
  current_vibration: {
    vx: 0,
    vy: 0,
    vz: 0,
    magnitude: 0
  }
})

// 当前振动值（从父组件实时数据获取）
const currentVibration = computed(() => {
  if (props.latestData?.vibration) {
    const v = props.latestData.vibration
    return {
      vx: Math.abs(v.x || 0),
      vy: Math.abs(v.y || 0),
      vz: Math.abs(v.z || 0),
      magnitude: v.amplitude || 0
    }
  }
  return captureStatus.current_vibration
})

// 加载状态
const controlLoading = ref(false)
const statusLoading = ref(false)
const checkingDirectory = ref(false)
const isDirectoryValid = ref(true)

// 历史记录
const captureHistory = ref([])
const lastCaptureInfo = ref(null)
const lastSessionInfo = ref(null)

// 状态轮询
let statusPoller = null

// 获取振动颜色
const getVibrationColor = (value, threshold) => {
  if (value > threshold) return '#f56c6c'  // 红色 - 高于阈值
  if (value > threshold * 0.7) return '#e6a23c'  // 橙色 - 接近阈值
  return '#67c23a'  // 绿色 - 正常
}

// 获取采集状态
const fetchStatus = async () => {
  statusLoading.value = true
  try {
    const response = await axios.get('/api/slm/capture/status')
    if (response.data.success) {
      Object.assign(captureStatus, response.data)
      config.threshold = response.data.threshold || config.threshold
      if (response.data.save_directory) {
        config.saveDir = response.data.save_directory
      }
    }
  } catch (error) {
    console.error('获取采集状态失败:', error)
  } finally {
    statusLoading.value = false
  }
}

// 阈值变更
const onThresholdChange = async (val) => {
  try {
    await axios.post('/api/slm/capture/threshold', null, { params: { threshold: val } })
    ElMessage.success(`阈值已设置为 ${val}`)
  } catch (error) {
    ElMessage.error('设置阈值失败')
  }
}

// 防抖时间变更（仅前端记录，实际在采集器初始化时设置）
const onDebounceChange = (val) => {
  ElMessage.success(`防抖时间已设置为 ${val} 秒`)
}

// 选择目录
const selectDirectory = async () => {
  const newDir = prompt('请输入保存目录路径:', config.saveDir)
  if (newDir && newDir !== config.saveDir) {
    checkingDirectory.value = true
    try {
      const response = await axios.post('/api/slm/capture/directory', null, {
        params: { save_dir: newDir }
      })
      if (response.data.success) {
        config.saveDir = response.data.path
        isDirectoryValid.value = true
        ElMessage.success('目录设置成功')
      } else {
        isDirectoryValid.value = false
        ElMessage.error(response.data.message || '目录设置失败')
      }
    } catch (error) {
      ElMessage.error('设置目录失败')
    } finally {
      checkingDirectory.value = false
    }
  }
}

// 重置层数计数
const resetLayerCount = () => {
  // 实际层数由后端管理，这里仅做提示
  ElMessage.info('层数计数将在下次采集时自动重置')
}

// 切换采集
const toggleCapture = async () => {
  controlLoading.value = true
  try {
    if (captureStatus.is_capturing) {
      // 停止采集
      const response = await axios.post('/api/slm/capture/stop')
      if (response.data.success) {
        captureStatus.is_capturing = false
        clearInterval(statusPoller)
        statusPoller = null
        
        lastSessionInfo.value = {
          total_captures: response.data.total_captures,
          layer_count: response.data.layer_count,
          session_dir: response.data.session_dir
        }
        
        ElMessage.success(`采集已停止，共 ${response.data.total_captures} 张图像`)
      }
    } else {
      // 开始采集
      const response = await axios.post('/api/slm/capture/start')
      if (response.data.success) {
        captureStatus.is_capturing = true
        
        // 启动状态轮询
        statusPoller = setInterval(fetchStatus, 1000)
        
        ElMessage.success('采集已启动')
      } else {
        ElMessage.error(response.data.message || '启动采集失败')
      }
    }
  } catch (error) {
    ElMessage.error('操作失败: ' + error.message)
  } finally {
    controlLoading.value = false
  }
}

// 监听实时数据变化，检测触发事件
watch(() => props.latestData, (newData) => {
  if (newData?.capture_event) {
    const evt = newData.capture_event
    lastCaptureInfo.value = {
      layer: evt.layer,
      type: evt.type,
      timestamp: new Date().toLocaleTimeString()
    }
    
    // 添加到历史
    captureHistory.value.unshift({
      layer: evt.layer,
      type: evt.type,
      timestamp: new Date().toLocaleString(),
      channels: 'CH1, CH2, CH3'
    })
    
    // 限制历史数量
    if (captureHistory.value.length > 50) {
      captureHistory.value = captureHistory.value.slice(0, 50)
    }
    
    emit('capture-triggered', evt)
  }
}, { deep: true })

onMounted(() => {
  fetchStatus()
})

onUnmounted(() => {
  if (statusPoller) {
    clearInterval(statusPoller)
  }
})
</script>

<style scoped>
.image-capture-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
  margin-top: 16px;
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

.header-tags {
  display: flex;
  gap: 8px;
}

/* 振动显示 */
.vibration-display {
  padding: 0 10px;
  margin-bottom: 16px;
}

.vibration-values {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.vib-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.vib-item.magnitude {
  padding-top: 8px;
  border-top: 1px solid rgba(100, 116, 139, 0.2);
}

.vib-label {
  width: 60px;
  font-size: 13px;
  color: #94a3b8;
}

.vib-value {
  width: 60px;
  text-align: right;
  font-size: 13px;
  font-weight: 500;
  color: #e2e8f0;
  font-family: monospace;
}

.vib-value.over-threshold {
  color: #f56c6c;
}

:deep(.el-progress) {
  flex: 1;
}

.threshold-indicator {
  margin-top: 16px;
  padding: 10px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #94a3b8;
}

.trigger-status {
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
}

.trigger-status.high {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

.trigger-status.low {
  color: #67c23a;
  background: rgba(103, 194, 58, 0.1);
}

/* 设置区域 */
.capture-settings {
  padding: 0 10px;
}

.directory-input {
  display: flex;
  gap: 8px;
}

.directory-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
}

.form-hint {
  margin-left: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.layer-display {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 控制区域 */
.capture-control {
  margin-top: 20px;
  padding: 0 10px;
}

.control-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.capture-info {
  margin-top: 16px;
}

.status-detail {
  font-size: 13px;
  line-height: 1.8;
}

.status-detail p {
  margin: 4px 0;
}

.last-session {
  margin-top: 16px;
  text-align: center;
}

/* 历史记录 */
.history-section {
  margin-top: 20px;
}

:deep(.el-divider__text) {
  background: rgba(15, 23, 42, 0.8);
  color: #94a3b8;
}
</style>
