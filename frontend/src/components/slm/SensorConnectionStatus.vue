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
      <div
        v-for="sensor in sensorItems"
        :key="sensor.key"
        class="sensor-item"
        :class="{ disabled: !sensorStatus[sensor.key]?.enabled }"
      >
        <div class="sensor-header">
          <div class="sensor-icon" :class="getStatusClass(sensorStatus[sensor.key])">
            <el-icon>
              <component :is="sensor.icon" />
            </el-icon>
          </div>
          <div class="sensor-info">
            <span class="sensor-name">{{ sensor.name }}</span>
            <span class="sensor-status">{{ getStatusText(sensorStatus[sensor.key]) }}</span>
            <span v-if="sensor.hint" class="sensor-hint">{{ sensor.hint }}</span>
          </div>
        </div>
        <el-switch
          v-model="localStatus[sensor.key].enabled"
          active-text="开启"
          inactive-text="关闭"
          size="small"
          @change="(val) => toggleSensor(sensor.key, val)"
        />
      </div>
    </div>

    <div class="quick-actions">
      <el-button
        type="primary"
        size="small"
        :loading="refreshing"
        @click="refreshStatus"
      >
        <el-icon><Refresh /></el-icon>
        刷新状态
      </el-button>
      <el-button
        type="success"
        size="small"
        :disabled="allEnabled"
        @click="enableAll"
      >
        全部开启
      </el-button>
      <el-button
        type="warning"
        size="small"
        :disabled="!anyEnabled"
        @click="disableAll"
      >
        全部关闭
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { HotWater, Refresh, VideoCamera } from '@element-plus/icons-vue'

const sensorItems = [
  { key: 'camera_ch1', name: '主摄像头 CH1', icon: VideoCamera },
  { key: 'camera_ch2', name: '副摄像头 CH2', icon: VideoCamera },
  { key: 'thermal', name: '红外热像仪 (CH3)', icon: HotWater, hint: 'PIX Connect SDK' }
]

const props = defineProps({
  sensorStatus: {
    type: Object,
    default: () => ({
      camera_ch1: { enabled: true, connected: false },
      camera_ch2: { enabled: true, connected: false },
      thermal: { enabled: true, connected: false }
    })
  }
})

const emit = defineEmits(['toggle-sensor', 'refresh'])

const refreshing = ref(false)
const localStatus = ref({
  camera_ch1: { enabled: true },
  camera_ch2: { enabled: true },
  thermal: { enabled: true }
})

const sensorKeys = sensorItems.map((sensor) => sensor.key)

const allConnected = computed(() => sensorKeys.every((key) => props.sensorStatus[key]?.connected))
const allEnabled = computed(() => sensorKeys.every((key) => localStatus.value[key].enabled))
const anyEnabled = computed(() => sensorKeys.some((key) => localStatus.value[key].enabled))

watch(() => props.sensorStatus, (nextStatus) => {
  sensorKeys.forEach((key) => {
    localStatus.value[key].enabled = nextStatus[key]?.enabled !== false
  })
}, { immediate: true, deep: true })

const getStatusClass = (sensor) => {
  if (!sensor?.enabled) return 'status-disabled'
  if (sensor?.connected) return 'status-connected'
  return 'status-disconnected'
}

const getStatusText = (sensor) => {
  if (!sensor?.enabled) return '已禁用'
  if (sensor?.connected) return '已连接'
  return '未连接'
}

const toggleSensor = (sensor, enabled) => {
  emit('toggle-sensor', sensor, enabled)
}

const refreshStatus = () => {
  refreshing.value = true
  emit('refresh')
  setTimeout(() => {
    refreshing.value = false
  }, 500)
}

const enableAll = () => {
  sensorKeys.forEach((key) => {
    localStatus.value[key].enabled = true
    emit('toggle-sensor', key, true)
  })
}

const disableAll = () => {
  sensorKeys.forEach((key) => {
    localStatus.value[key].enabled = false
    emit('toggle-sensor', key, false)
  })
}
</script>

<style scoped>
.sensor-status-card {
  background: var(--am-card-bg);
  border: 1px solid var(--am-card-border);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--am-text);
}

.sensor-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.sensor-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: var(--am-card-bg-2);
  border-radius: 8px;
  border: 1px solid var(--am-card-border-2);
  transition: opacity 0.2s ease, border-color 0.2s ease;
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
  transition: background 0.2s ease, color 0.2s ease;
}

.sensor-icon.status-connected {
  background: color-mix(in srgb, var(--am-ok) 20%, transparent);
  color: var(--am-ok);
}

.sensor-icon.status-disconnected {
  background: color-mix(in srgb, var(--am-danger) 18%, transparent);
  color: var(--am-danger);
}

.sensor-icon.status-disabled {
  background: var(--am-card-bg-2);
  color: var(--am-text-3);
}

.sensor-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.sensor-name {
  color: var(--am-text);
  font-size: 14px;
  font-weight: 600;
}

.sensor-status {
  color: var(--am-text-2);
  font-size: 12px;
}

.sensor-hint {
  color: var(--am-text-3);
  font-size: 11px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid var(--am-card-border-2);
}

@media (max-width: 960px) {
  .sensor-grid {
    grid-template-columns: 1fr;
  }
}
</style>
