<template>
  <el-card class="sensor-status-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">传感器连接状态</span>
        <el-tag :type="allConnected ? 'success' : 'warning'" size="small">
          {{ allConnected ? '全部连接' : '部分未连接' }}
        </el-tag>
      </div>
    </template>
    
    <div class="sensor-grid">
      <!-- CH1 摄像头 -->
      <div class="sensor-item" :class="{ 'disabled': !sensorStatus.camera_ch1?.enabled }">
        <div class="sensor-header">
          <div class="sensor-icon" :class="getStatusClass(sensorStatus.camera_ch1)">
            <el-icon><VideoCamera /></el-icon>
          </div>
          <div class="sensor-info">
            <span class="sensor-name">主摄像头 CH1</span>
            <span class="sensor-status">{{ getStatusText(sensorStatus.camera_ch1) }}</span>
          </div>
        </div>
        <el-switch
          v-model="localStatus.camera_ch1.enabled"
          @change="(val) => toggleSensor('camera_ch1', val)"
          active-text="开启"
          inactive-text="关闭"
          size="small"
        />
      </div>
      
      <!-- CH2 摄像头 -->
      <div class="sensor-item" :class="{ 'disabled': !sensorStatus.camera_ch2?.enabled }">
        <div class="sensor-header">
          <div class="sensor-icon" :class="getStatusClass(sensorStatus.camera_ch2)">
            <el-icon><VideoCamera /></el-icon>
          </div>
          <div class="sensor-info">
            <span class="sensor-name">副摄像头 CH2</span>
            <span class="sensor-status">{{ getStatusText(sensorStatus.camera_ch2) }}</span>
          </div>
        </div>
        <el-switch
          v-model="localStatus.camera_ch2.enabled"
          @change="(val) => toggleSensor('camera_ch2', val)"
          active-text="开启"
          inactive-text="关闭"
          size="small"
        />
      </div>
      
      <!-- 红外热像仪 -->
      <div class="sensor-item" :class="{ 'disabled': !sensorStatus.thermal?.enabled }">
        <div class="sensor-header">
          <div class="sensor-icon" :class="getStatusClass(sensorStatus.thermal)">
            <el-icon><HotWater /></el-icon>
          </div>
          <div class="sensor-info">
            <span class="sensor-name">红外热像仪 (CH3)</span>
            <span class="sensor-status">{{ getStatusText(sensorStatus.thermal) }}</span>
            <span class="sensor-hint">PIX Connect SDK</span>
          </div>
        </div>
        <el-tooltip placement="top">
          <template #content>
            <div style="max-width: 250px;">
              红外热像仪通过PIX Connect软件连接，不需要COM口。<br>
              请确保PIX Connect已启动并启用IPC通信。
            </div>
          </template>
          <el-switch
            v-model="localStatus.thermal.enabled"
            @change="(val) => toggleSensor('thermal', val)"
            active-text="开启"
            inactive-text="关闭"
            size="small"
          />
        </el-tooltip>
      </div>
      
      <!-- 振动传感器 -->
      <div class="sensor-item" :class="{ 'disabled': !sensorStatus.vibration?.enabled }">
        <div class="sensor-header">
          <div class="sensor-icon" :class="getStatusClass(sensorStatus.vibration)">
            <el-icon><Odometer /></el-icon>
          </div>
          <div class="sensor-info">
            <span class="sensor-name">振动传感器</span>
            <span class="sensor-status">{{ getStatusText(sensorStatus.vibration) }}</span>
          </div>
        </div>
        <div class="vibration-controls">
          <el-switch
            v-model="localStatus.vibration.enabled"
            @change="(val) => toggleSensor('vibration', val)"
            active-text="开启"
            inactive-text="关闭"
            size="small"
          />
          <el-select 
            v-model="selectedComPort" 
            size="small" 
            style="width: 100px; margin-left: 10px;"
            @change="changeComPort"
            :disabled="!sensorStatus.vibration?.enabled"
          >
            <el-option
              v-for="port in availableComPorts"
              :key="port.device"
              :label="port.device"
              :value="port.device"
            />
          </el-select>
        </div>
      </div>
    </div>
    
    <!-- 快速操作 -->
    <div class="quick-actions">
      <el-button 
        type="primary" 
        size="small" 
        @click="refreshStatus"
        :loading="refreshing"
      >
        <el-icon><Refresh /></el-icon>
        刷新状态
      </el-button>
      <el-button 
        type="success" 
        size="small" 
        @click="enableAll"
        :disabled="allEnabled"
      >
        全部开启
      </el-button>
      <el-button 
        type="warning" 
        size="small" 
        @click="disableAll"
        :disabled="!anyEnabled"
      >
        全部关闭
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { VideoCamera, HotWater, Odometer, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const props = defineProps({
  sensorStatus: {
    type: Object,
    default: () => ({
      camera_ch1: { enabled: true, connected: false },
      camera_ch2: { enabled: true, connected: false },
      thermal: { enabled: true, connected: false },
      vibration: { enabled: true, connected: false, com_port: 'COM5' }
    })
  }
})

const emit = defineEmits(['toggle-sensor', 'change-com-port', 'refresh'])

// 本地状态
const localStatus = ref({
  camera_ch1: { enabled: true },
  camera_ch2: { enabled: true },
  thermal: { enabled: true },
  vibration: { enabled: true }
})

const selectedComPort = ref('COM5')
const availableComPorts = ref([])
const refreshing = ref(false)

// 计算属性
const allConnected = computed(() => {
  const s = props.sensorStatus
  return s.camera_ch1?.connected && s.camera_ch2?.connected && 
         s.thermal?.connected && s.vibration?.connected
})

const allEnabled = computed(() => {
  const s = localStatus.value
  return s.camera_ch1.enabled && s.camera_ch2.enabled && 
         s.thermal.enabled && s.vibration.enabled
})

const anyEnabled = computed(() => {
  const s = localStatus.value
  return s.camera_ch1.enabled || s.camera_ch2.enabled || 
         s.thermal.enabled || s.vibration.enabled
})

// 监听props变化
watch(() => props.sensorStatus, (newVal) => {
  if (newVal) {
    localStatus.value.camera_ch1.enabled = newVal.camera_ch1?.enabled !== false
    localStatus.value.camera_ch2.enabled = newVal.camera_ch2?.enabled !== false
    localStatus.value.thermal.enabled = newVal.thermal?.enabled !== false
    localStatus.value.vibration.enabled = newVal.vibration?.enabled !== false
    if (newVal.vibration?.com_port) {
      selectedComPort.value = newVal.vibration.com_port
    }
  }
}, { immediate: true, deep: true })

// 获取状态样式
const getStatusClass = (sensor) => {
  if (!sensor?.enabled) return 'status-disabled'
  if (sensor?.connected) return 'status-connected'
  return 'status-disconnected'
}

// 获取状态文本
const getStatusText = (sensor) => {
  if (!sensor?.enabled) return '已禁用'
  if (sensor?.connected) return '已连接'
  return '未连接'
}

// 切换传感器
const toggleSensor = (sensor, enabled) => {
  emit('toggle-sensor', sensor, enabled)
}

// 获取可用COM口
const fetchComPorts = async () => {
  try {
    const response = await axios.get('/api/slm/com_ports')
    if (response.data.success) {
      availableComPorts.value = response.data.ports
    }
  } catch (error) {
    console.error('获取COM口失败:', error)
    // 使用默认COM口
    availableComPorts.value = [
      { device: 'COM1', description: 'Default COM1' },
      { device: 'COM2', description: 'Default COM2' },
      { device: 'COM3', description: 'Default COM3' },
      { device: 'COM4', description: 'Default COM4' },
      { device: 'COM5', description: 'Default COM5' }
    ]
  }
}

// 切换COM口
const changeComPort = async (port) => {
  try {
    await axios.post(`/api/slm/vibration/com_port?port=${port}`)
    emit('change-com-port', port)
    ElMessage.success(`COM口已切换到 ${port}`)
  } catch (error) {
    ElMessage.error('切换COM口失败')
  }
}

// 刷新状态
const refreshStatus = async () => {
  refreshing.value = true
  await fetchComPorts()
  emit('refresh')
  setTimeout(() => {
    refreshing.value = false
  }, 500)
}

// 全部开启
const enableAll = () => {
  localStatus.value.camera_ch1.enabled = true
  localStatus.value.camera_ch2.enabled = true
  localStatus.value.thermal.enabled = true
  localStatus.value.vibration.enabled = true
  emit('toggle-sensor', 'camera_ch1', true)
  emit('toggle-sensor', 'camera_ch2', true)
  emit('toggle-sensor', 'thermal', true)
  emit('toggle-sensor', 'vibration', true)
}

// 全部关闭
const disableAll = () => {
  localStatus.value.camera_ch1.enabled = false
  localStatus.value.camera_ch2.enabled = false
  localStatus.value.thermal.enabled = false
  localStatus.value.vibration.enabled = false
  emit('toggle-sensor', 'camera_ch1', false)
  emit('toggle-sensor', 'camera_ch2', false)
  emit('toggle-sensor', 'thermal', false)
  emit('toggle-sensor', 'vibration', false)
}

onMounted(() => {
  fetchComPorts()
})
</script>

<style scoped>
.sensor-status-card {
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

.sensor-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.sensor-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(100, 116, 139, 0.2);
  transition: all 0.3s ease;
}

.sensor-item.disabled {
  opacity: 0.6;
}

.sensor-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sensor-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  transition: all 0.3s ease;
}

.sensor-icon.status-connected {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.sensor-icon.status-disconnected {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.sensor-icon.status-disabled {
  background: rgba(148, 163, 184, 0.2);
  color: #94a3b8;
}

.sensor-info {
  display: flex;
  flex-direction: column;
}

.sensor-name {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
}

.sensor-status {
  font-size: 12px;
  color: #94a3b8;
}

.sensor-hint {
  font-size: 10px;
  color: #64748b;
  font-style: italic;
}

.vibration-controls {
  display: flex;
  align-items: center;
}

.quick-actions {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(100, 116, 139, 0.2);
}

@media (max-width: 768px) {
  .sensor-grid {
    grid-template-columns: 1fr;
  }
}
</style>
