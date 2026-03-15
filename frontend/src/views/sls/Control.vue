<template>
  <div class="sls-control">
    <div class="page-header">
      <h1 class="page-title">SLS 系统控制</h1>
    </div>
    
    <el-row :gutter="20">
      <!-- 舵机控制 -->
      <el-col :xs="24" :lg="12">
        <el-card class="control-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon><Switch /></el-icon>
                舵机控制
              </span>
            </div>
          </template>
          
          <div class="control-content">
            <div class="servo-status">
              <div class="status-item">
                <span class="label">当前位置:</span>
                <span class="value">{{ servoPosition }}</span>
              </div>
              <div class="status-item">
                <span class="label">挡板状态:</span>
                <el-tag :type="servoIsOpen ? 'success' : 'danger'" size="small">
                  {{ servoIsOpen ? '开启 (可拍摄)' : '关闭 (保护)' }}
                </el-tag>
              </div>
            </div>
            
            <div class="control-buttons">
              <el-button type="danger" @click="closeServo">
                <el-icon><CircleClose /></el-icon>
                关闭挡板
              </el-button>
              <el-button type="success" @click="openServo">
                <el-icon><CircleCheck /></el-icon>
                开启挡板
              </el-button>
            </div>
            
            <el-divider />
            
            <div class="fine-control">
              <span class="label">精细控制:</span>
              <el-slider v-model="targetPosition" :min="1500" :max="2500" :step="10" />
              <el-button type="primary" @click="moveServo(targetPosition)">移动</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 系统参数 -->
      <el-col :xs="24" :lg="12">
        <el-card class="control-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>
                <el-icon><Setting /></el-icon>
                烧结参数
              </span>
            </div>
          </template>
          
          <div class="control-content">
            <el-form :model="processParams" label-width="100px">
              <el-form-item label="层厚">
                <el-input-number v-model="processParams.layerThickness" :min="0.01" :max="0.5" :step="0.01" />
                <span class="unit">mm</span>
              </el-form-item>
              <el-form-item label="扫描速度">
                <el-input-number v-model="processParams.scanSpeed" :min="100" :max="5000" :step="100" />
                <span class="unit">mm/s</span>
              </el-form-item>
              <el-form-item label="激光功率">
                <el-input-number v-model="processParams.laserPower" :min="10" :max="100" :step="1" />
                <span class="unit">W</span>
              </el-form-item>
              <el-form-item label="预热温度">
                <el-input-number v-model="processParams.preheatTemp" :min="0" :max="200" :step="5" />
                <span class="unit">°C</span>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="updateParams">更新参数</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 设备状态 -->
    <el-card class="status-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>设备状态</span>
          <el-button type="primary" size="small" @click="refreshStatus">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <div class="device-status">
        <div class="status-grid">
          <div class="status-item" v-for="(status, name) in deviceStatus" :key="name">
            <div class="status-icon" :class="status.connected ? 'connected' : 'disconnected'">
              <el-icon v-if="name === 'camera'"><VideoCamera /></el-icon>
              <el-icon v-else-if="name === 'thermal'"><MostlyCloudy /></el-icon>
              <el-icon v-else-if="name === 'vibration'"><Odometer /></el-icon>
              <el-icon v-else-if="name === 'servo'"><Switch /></el-icon>
            </div>
            <div class="status-info">
              <span class="name">{{ status.name }}</span>
              <el-tag :type="status.connected ? 'success' : 'danger'" size="small">
                {{ status.connected ? '已连接' : '未连接' }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { 
  Switch, Setting, CircleClose, CircleCheck, 
  Refresh, VideoCamera, MostlyCloudy, Odometer 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const servoPosition = ref(1500)
const servoIsOpen = ref(false)
const targetPosition = ref(2000)

const processParams = reactive({
  layerThickness: 0.1,
  scanSpeed: 800,
  laserPower: 50,
  preheatTemp: 80
})

const deviceStatus = reactive({
  camera: { name: '摄像头', connected: false },
  thermal: { name: '红外热像', connected: false },
  vibration: { name: '振动传感器', connected: false },
  servo: { name: '舵机控制', connected: false }
})

const openServo = async () => {
  try {
    await axios.post('/api/sls/servo/move', { position: 2500 })
    servoPosition.value = 2500
    servoIsOpen.value = true
    ElMessage.success('挡板已开启')
  } catch (error) {
    ElMessage.error('舵机控制失败')
  }
}

const closeServo = async () => {
  try {
    await axios.post('/api/sls/servo/move', { position: 1500 })
    servoPosition.value = 1500
    servoIsOpen.value = false
    ElMessage.success('挡板已关闭')
  } catch (error) {
    ElMessage.error('舵机控制失败')
  }
}

const moveServo = async (position) => {
  try {
    await axios.post('/api/sls/servo/move', { position })
    servoPosition.value = position
    servoIsOpen.value = position > 2000
    ElMessage.success(`舵机移动到 ${position}`)
  } catch (error) {
    ElMessage.error('舵机控制失败')
  }
}

const updateParams = () => {
  ElMessage.success('参数已更新')
}

const refreshStatus = () => {
  ElMessage.success('状态已刷新')
}
</script>

<style scoped>
.sls-control {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.control-card,
.status-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.control-content {
  padding: 10px 0;
}

.servo-status {
  display: flex;
  gap: 30px;
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.label {
  color: #94a3b8;
}

.value {
  font-weight: 600;
  color: #e2e8f0;
  font-family: 'Courier New', monospace;
}

.control-buttons {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.fine-control {
  display: flex;
  align-items: center;
  gap: 16px;
}

.fine-control .el-slider {
  flex: 1;
}

.unit {
  margin-left: 10px;
  color: #64748b;
}

.device-status {
  padding: 10px 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.status-grid .status-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
}

.status-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.status-icon.connected {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.status-icon.disconnected {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-info .name {
  font-size: 14px;
  color: #e2e8f0;
}

@media (max-width: 768px) {
  .servo-status {
    flex-direction: column;
    gap: 10px;
  }
  
  .control-buttons {
    flex-direction: column;
  }
  
  .fine-control {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
