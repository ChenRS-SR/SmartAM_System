<template>
  <el-card class="sensor-status-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">传感器连接状态</span>
        <div class="header-actions">
          <el-button type="primary" size="small" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </template>
    
    <div class="sensor-grid">
      <!-- CH1主摄像头 -->
      <div class="sensor-item" :class="{ 'disabled': !sensorStatus.camera_ch1?.enabled }">
        <div class="sensor-icon" :class="getStatusClass(sensorStatus.camera_ch1)">
          <el-icon><VideoCamera /></el-icon>
        </div>
        <div class="sensor-info">
          <div class="sensor-name">CH1 主摄像头</div>
          <div class="sensor-status" :class="getStatusClass(sensorStatus.camera_ch1)">
            {{ getStatusText(sensorStatus.camera_ch1) }}
          </div>
        </div>
        <el-switch
          v-model="sensorStatus.camera_ch1.enabled"
          @change="(val) => handleToggle('camera_ch1', val)"
          size="small"
        />
      </div>
      
      <!-- CH2副摄像头 -->
      <div class="sensor-item" :class="{ 'disabled': !sensorStatus.camera_ch2?.enabled }">
        <div class="sensor-icon" :class="getStatusClass(sensorStatus.camera_ch2)">
          <el-icon><VideoCamera /></el-icon>
        </div>
        <div class="sensor-info">
          <div class="sensor-name">CH2 副摄像头</div>
          <div class="sensor-status" :class="getStatusClass(sensorStatus.camera_ch2)">
            {{ getStatusText(sensorStatus.camera_ch2) }}
          </div>
        </div>
        <el-switch
          v-model="sensorStatus.camera_ch2.enabled"
          @change="(val) => handleToggle('camera_ch2', val)"
          size="small"
        />
      </div>
      
      <!-- 红外热像仪 (Fotric/IR8062) -->
      <div class="sensor-item" :class="{ 'disabled': !sensorStatus.thermal?.enabled }">
        <div class="sensor-icon" :class="getStatusClass(sensorStatus.thermal)">
          <el-icon><MostlyCloudy /></el-icon>
        </div>
        <div class="sensor-info">
          <div class="sensor-name">
            红外热像仪
            <el-tag size="small" type="info" class="thermal-type">
              {{ sensorStatus.thermal?.type === 'ir8062' ? 'IR8062' : 'Fotric' }}
            </el-tag>
          </div>
          <div class="sensor-status" :class="getStatusClass(sensorStatus.thermal)">
            {{ getStatusText(sensorStatus.thermal) }}
          </div>
        </div>
        <el-switch
          v-model="sensorStatus.thermal.enabled"
          @change="(val) => handleToggle('thermal', val)"
          size="small"
        />
      </div>
      
      <!-- 振动传感器 -->
      <div class="sensor-item" :class="{ 'disabled': !sensorStatus.vibration?.enabled }">
        <div class="sensor-icon" :class="getStatusClass(sensorStatus.vibration)">
          <el-icon><Odometer /></el-icon>
        </div>
        <div class="sensor-info">
          <div class="sensor-name">振动传感器</div>
          <div class="sensor-status" :class="getStatusClass(sensorStatus.vibration)">
            {{ getStatusText(sensorStatus.vibration) }}
          </div>
          <div class="sensor-detail" v-if="sensorStatus.vibration?.com_port">
            {{ sensorStatus.vibration.com_port }}
          </div>
        </div>
        <div class="sensor-actions">
          <el-select 
            v-model="selectedComPort" 
            size="small" 
            style="width: 100px"
            @change="handleComPortChange"
            placeholder="COM口"
          >
            <el-option
              v-for="port in availableComPorts"
              :key="port.device"
              :label="port.device"
              :value="port.device"
            />
          </el-select>
          <el-switch
            v-model="sensorStatus.vibration.enabled"
            @change="(val) => handleToggle('vibration', val)"
            size="small"
          />
        </div>
      </div>
      
      <!-- 舵机控制 (SLS特有) -->
      <div class="sensor-item" :class="{ 'disabled': !sensorStatus.servo?.enabled }">
        <div class="sensor-icon" :class="getStatusClass(sensorStatus.servo)">
          <el-icon><Switch /></el-icon>
        </div>
        <div class="sensor-info">
          <div class="sensor-name">舵机控制</div>
          <div class="sensor-status" :class="getStatusClass(sensorStatus.servo)">
            {{ getStatusText(sensorStatus.servo) }}
          </div>
          <div class="sensor-detail" v-if="sensorStatus.servo?.com_port">
            {{ sensorStatus.servo.com_port }}
          </div>
        </div>
        <div class="sensor-actions">
          <el-select 
            v-model="selectedServoComPort" 
            size="small" 
            style="width: 100px"
            @change="handleServoComPortChange"
            placeholder="COM口"
          >
            <el-option
              v-for="port in availableComPorts"
              :key="port.device"
              :label="port.device"
              :value="port.device"
            />
          </el-select>
          <el-switch
            v-model="sensorStatus.servo.enabled"
            @change="(val) => handleToggle('servo', val)"
            size="small"
          />
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Refresh, VideoCamera, MostlyCloudy, Odometer, Switch } from '@element-plus/icons-vue'

const props = defineProps({
  sensorStatus: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['toggle-sensor', 'change-com-port', 'change-servo-com-port', 'refresh'])

const availableComPorts = ref([])
const selectedComPort = ref(props.sensorStatus.vibration?.com_port || 'COM5')
const selectedServoComPort = ref(props.sensorStatus.servo?.com_port || 'COM16')

// 监听props变化更新选择
watch(() => props.sensorStatus.vibration?.com_port, (newVal) => {
  if (newVal) selectedComPort.value = newVal
})

watch(() => props.sensorStatus.servo?.com_port, (newVal) => {
  if (newVal) selectedServoComPort.value = newVal
})

const getStatusClass = (status) => {
  if (!status?.enabled) return 'disabled'
  if (status?.connected) return 'connected'
  return 'disconnected'
}

const getStatusText = (status) => {
  if (!status?.enabled) return '已禁用'
  if (status?.connected) return '已连接'
  return '未连接'
}

const handleToggle = (sensor, enabled) => {
  emit('toggle-sensor', sensor, enabled)
}

const handleComPortChange = (port) => {
  emit('change-com-port', port)
}

const handleServoComPortChange = (port) => {
  emit('change-servo-com-port', port)
}

const handleRefresh = () => {
  emit('refresh')
}
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
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.sensor-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(100, 116, 139, 0.2);
  transition: all 0.3s ease;
}

.sensor-item.disabled {
  opacity: 0.6;
}

.sensor-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: rgba(100, 116, 139, 0.2);
  color: #64748b;
  transition: all 0.3s ease;
}

.sensor-icon.connected {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.sensor-icon.disconnected {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.sensor-icon.disabled {
  background: rgba(100, 116, 139, 0.1);
  color: #475569;
}

.sensor-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sensor-name {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.thermal-type {
  font-size: 10px;
}

.sensor-status {
  font-size: 12px;
  color: #64748b;
}

.sensor-status.connected {
  color: #22c55e;
}

.sensor-status.disconnected {
  color: #ef4444;
}

.sensor-status.disabled {
  color: #475569;
}

.sensor-detail {
  font-size: 11px;
  color: #64748b;
  font-family: 'Courier New', monospace;
}

.sensor-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

@media (max-width: 768px) {
  .sensor-grid {
    grid-template-columns: 1fr;
  }
  
  .sensor-item {
    flex-wrap: wrap;
  }
  
  .sensor-actions {
    flex-direction: row;
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
