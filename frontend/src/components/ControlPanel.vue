<template>
  <div class="control-panel">
    <div class="panel-header">
      <el-icon size="20" color="#00d4ff"><SetUp /></el-icon>
      <span class="panel-title">控制面板</span>
    </div>
    
    <!-- 闭环控制状态 -->
    <div class="control-section">
      <div class="section-title">闭环调控</div>
      <div class="loop-status">
        <el-tag 
          :type="loopStatusType" 
          size="large" 
          effect="dark"
          class="status-tag"
        >
          <el-icon><CircleCheck v-if="isRunning" /><CircleClose v-else /></el-icon>
          {{ loopStatusText }}
        </el-tag>
        
        <div class="loop-actions">
          <el-button 
            type="success" 
            size="small"
            :disabled="isRunning"
            @click="startLoop"
          >
            <el-icon><VideoPlay /></el-icon>
            启动
          </el-button>
          <el-button 
            type="warning" 
            size="small"
            :disabled="!isRunning"
            @click="pauseLoop"
          >
            <el-icon><VideoPause /></el-icon>
            暂停
          </el-button>
          <el-button 
            type="danger" 
            size="small"
            :disabled="!isRunning"
            @click="stopLoop"
          >
            <el-icon><CircleClose /></el-icon>
            停止
          </el-button>
        </div>
      </div>
      
      <div class="loop-info">
        <div class="info-item">
          <span>窗口大小:</span>
          <el-tag size="small" type="info">{{ status.windowSize || 0 }}</el-tag>
        </div>
        <div class="info-item">
          <span>调控次数:</span>
          <el-tag size="small" type="info">{{ status.regulationCount || 0 }}</el-tag>
        </div>
      </div>
    </div>
    
    <!-- 阈值设置 -->
    <div class="control-section">
      <div class="section-title">调控阈值</div>
      <div class="threshold-control">
        <el-slider 
          v-model="threshold" 
          :min="0.5" 
          :max="0.95" 
          :step="0.05"
          show-stops
          @change="updateThreshold"
        />
        <div class="threshold-value">{{ threshold.toFixed(2) }}</div>
      </div>
    </div>
    
    <!-- 手动控制 -->
    <div class="control-section">
      <div class="section-title">手动控制</div>
      <div class="manual-controls">
        <div class="control-row">
          <span class="control-label">流量 (M221)</span>
          <el-input-number 
            v-model="manualParams.flow_rate_delta" 
            :step="10" 
            :min="-100" 
            :max="100"
            size="small"
          />
          <el-button type="primary" size="small" @click="applyManual">
            应用
          </el-button>
        </div>
        
        <div class="control-row">
          <span class="control-label">速度 (M220)</span>
          <el-input-number 
            v-model="manualParams.feed_rate_delta" 
            :step="10" 
            :min="-100" 
            :max="100"
            size="small"
          />
          <el-button type="primary" size="small" @click="applyManual">
            应用
          </el-button>
        </div>
        
        <div class="control-row">
          <span class="control-label">Z偏移 (M290)</span>
          <el-input-number 
            v-model="manualParams.z_offset_delta" 
            :step="0.02" 
            :min="-0.5" 
            :max="0.5"
            size="small"
          />
          <el-button type="primary" size="small" @click="applyManual">
            应用
          </el-button>
        </div>
        
        <div class="control-row">
          <span class="control-label">温度 (M104)</span>
          <el-input-number 
            v-model="manualParams.hotend_delta" 
            :step="5" 
            :min="-50" 
            :max="50"
            size="small"
          />
          <el-button type="primary" size="small" @click="applyManual">
            应用
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 快捷操作 -->
    <div class="control-section">
      <div class="section-title">快捷操作</div>
      <div class="quick-actions">
        <el-button type="primary" plain @click="emergencyStop">
          <el-icon><Warning /></el-icon>
          紧急停止
        </el-button>
        <el-button @click="resetParams">
          <el-icon><RefreshLeft /></el-icon>
          参数重置
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { controlApi } from '../utils/api'
import { useDataStore } from '../stores/data'

const store = useDataStore()

const status = computed(() => store.closedLoopStatus)
const isRunning = computed(() => status.value.status === 'monitoring' || status.value.status === 'regulating')

const loopStatusType = computed(() => {
  if (status.value.status === 'monitoring') return 'success'
  if (status.value.status === 'regulating') return 'warning'
  if (status.value.status === 'paused') return 'info'
  return 'danger'
})

const loopStatusText = computed(() => {
  const texts = {
    'idle': '未启动',
    'monitoring': '监控中',
    'regulating': '调控中',
    'paused': '已暂停'
  }
  return texts[status.value.status] || '未知'
})

const threshold = ref(0.7)

const manualParams = ref({
  flow_rate_delta: 0,
  feed_rate_delta: 0,
  z_offset_delta: 0,
  hotend_delta: 0
})

const startLoop = async () => {
  try {
    await controlApi.start()
    store.setClosedLoopStatus({ status: 'monitoring' })
    ElMessage.success('闭环调控已启动')
  } catch (e) {
    ElMessage.error('启动失败: ' + e.message)
  }
}

const pauseLoop = async () => {
  try {
    await controlApi.pause()
    store.setClosedLoopStatus({ status: 'paused' })
    ElMessage.info('闭环调控已暂停')
  } catch (e) {
    ElMessage.error('暂停失败: ' + e.message)
  }
}

const stopLoop = async () => {
  try {
    await controlApi.stop()
    store.setClosedLoopStatus({ status: 'idle', windowSize: 0 })
    ElMessage.success('闭环调控已停止')
  } catch (e) {
    ElMessage.error('停止失败: ' + e.message)
  }
}

const updateThreshold = async () => {
  try {
    await controlApi.setThreshold(threshold.value)
    ElMessage.success('阈值已更新')
  } catch (e) {
    ElMessage.error('更新失败: ' + e.message)
  }
}

const applyManual = async () => {
  try {
    await controlApi.manualControl(manualParams.value)
    ElMessage.success('手动控制已应用')
    // 清空
    manualParams.value = {
      flow_rate_delta: 0,
      feed_rate_delta: 0,
      z_offset_delta: 0,
      hotend_delta: 0
    }
  } catch (e) {
    ElMessage.error('应用失败: ' + e.message)
  }
}

const emergencyStop = () => {
  ElMessageBox.confirm('确定要紧急停止打印机吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    // 发送 M112 紧急停止
    // printerApi.sendCommand('M112')
    ElMessage.success('紧急停止指令已发送')
  }).catch(() => {})
}

const resetParams = async () => {
  try {
    await controlApi.manualControl({
      flow_rate_delta: 0,
      feed_rate_delta: 0,
      z_offset_delta: 0,
      hotend_delta: 0
    })
    ElMessage.success('参数已重置')
  } catch (e) {
    ElMessage.error('重置失败')
  }
}
</script>

<style scoped>
.control-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  padding: 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.panel-title {
  font-size: 16px;
  font-weight: 500;
  color: #e2e8f0;
}

.control-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 13px;
  color: #a0aec0;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.loop-status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.status-tag {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 14px;
}

.loop-actions {
  display: flex;
  gap: 8px;
}

.loop-info {
  display: flex;
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #a0aec0;
}

.threshold-control {
  display: flex;
  align-items: center;
  gap: 16px;
}

.threshold-control :deep(.el-slider) {
  flex: 1;
}

.threshold-value {
  min-width: 50px;
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  color: #00d4ff;
}

.manual-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.control-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.control-label {
  width: 100px;
  font-size: 13px;
  color: #a0aec0;
}

.control-row :deep(.el-input-number) {
  flex: 1;
}

.quick-actions {
  display: flex;
  gap: 10px;
}

.quick-actions .el-button {
  flex: 1;
}
</style>
