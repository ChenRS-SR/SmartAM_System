<template>
  <div class="settings-page">
    <h2 class="page-title">系统设置</h2>
    
    <div class="settings-grid" :class="{ 'mobile-layout': isMobile }">
      <!-- OctoPrint 配置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <el-icon><Connection /></el-icon>
            <span>OctoPrint 配置</span>
          </div>
        </template>
        
        <el-form :model="config.octoprint" label-position="top">
          <el-form-item label="主机地址">
            <el-input v-model="config.octoprint.host" placeholder="localhost:5000" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input 
              v-model="config.octoprint.api_key" 
              type="password" 
              placeholder="OctoPrint API Key"
              show-password
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveConfig('octoprint')">
              <el-icon><Check /></el-icon>
              保存配置
            </el-button>
            <el-button @click="testConnection">
              <el-icon><Link /></el-icon>
              测试连接
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- 相机配置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <el-icon><Camera /></el-icon>
            <span>相机配置</span>
          </div>
        </template>
        
        <el-form :model="config.camera" label-position="top">
          <el-form-item label="IDS 相机">
            <el-switch v-model="config.camera.ids_enabled" />
          </el-form-item>
          <el-form-item label="IDS 设备 ID">
            <el-input-number v-model="config.camera.ids_device_id" :min="0" :max="10" />
          </el-form-item>
          <el-form-item label="旁轴相机 URL">
            <el-input v-model="config.camera.side_url" placeholder="http://..." />
          </el-form-item>
          <el-form-item label="分辨率">
            <el-select v-model="config.camera.resolution">
              <el-option label="1920x1080" value="1920x1080" />
              <el-option label="1280x720" value="1280x720" />
              <el-option label="640x480" value="640x480" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveConfig('camera')">
              <el-icon><Check /></el-icon>
              保存配置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- Fotric 热成像 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <el-icon><FirstAidKit /></el-icon>
            <span>Fotric 热成像</span>
          </div>
        </template>
        
        <el-form :model="config.thermal" label-position="top">
          <el-form-item label="启用 Fotric">
            <el-switch v-model="config.thermal.enabled" />
          </el-form-item>
          <el-form-item label="COM 端口">
            <el-input v-model="config.thermal.port" placeholder="COM3" />
          </el-form-item>
          <el-form-item label="波特率">
            <el-select v-model="config.thermal.baudrate">
              <el-option :label="9600" :value="9600" />
              <el-option :label="115200" :value="115200" />
              <el-option :label="921600" :value="921600" />
            </el-select>
          </el-form-item>
          <el-form-item label="发射率">
            <el-slider v-model="config.thermal.emissivity" :min="0.1" :max="1" :step="0.05" show-stops />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveConfig('thermal')">
              <el-icon><Check /></el-icon>
              保存配置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- PacNet 模型配置 -->
      <el-card class="settings-card">
        <template #header>
          <div class="card-header">
            <el-icon><Cpu /></el-icon>
            <span>PacNet 模型配置</span>
          </div>
        </template>
        
        <el-form :model="config.model" label-position="top">
          <el-form-item label="模型文件路径">
            <el-input v-model="config.model.path" placeholder="weights/model_full.pt" />
          </el-form-item>
          <el-form-item label="Scaler 路径">
            <el-input v-model="config.model.scaler_path" placeholder="weights/scaler.pkl" />
          </el-form-item>
          <el-form-item label="使用 GPU">
            <el-switch v-model="config.model.use_gpu" />
          </el-form-item>
          <el-form-item label="推理频率 (Hz)">
            <el-slider v-model="config.model.frequency" :min="1" :max="10" :step="1" show-stops />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveConfig('model')">
              <el-icon><Check /></el-icon>
              保存配置
            </el-button>
            <el-button @click="reloadModel">
              <el-icon><Refresh /></el-icon>
              重新加载
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
      
      <!-- 设备管理 -->
      <el-card class="settings-card" style="grid-column: span 2;">
        <template #header>
          <div class="card-header">
            <el-icon><Connection /></el-icon>
            <span>设备管理</span>
          </div>
        </template>
        
        <div class="device-management">
          <div class="device-status-section">
            <el-row :gutter="20">
              <el-col :span="4" v-for="(status, name) in deviceStatus" :key="name">
                <div class="device-status-item">
                  <el-tag :type="status ? 'success' : 'danger'" size="large" effect="dark">
                    {{ getDeviceName(name) }}
                  </el-tag>
                  <div class="status-text" :class="status ? 'connected' : 'disconnected'">
                    {{ status ? '已连接' : '未连接' }}
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
          
          <el-divider />
          
          <div class="device-actions">
            <el-button 
              type="primary" 
              size="large" 
              @click="connectAllDevices"
              :loading="connectLoading"
              :disabled="allDevicesConnected"
            >
              <el-icon><Link /></el-icon>
              一键连接所有设备
            </el-button>
            <el-button 
              type="danger" 
              size="large" 
              @click="disconnectAllDevices"
              :loading="disconnectLoading"
              :disabled="!anyDeviceConnected"
            >
              <el-icon><CircleClose /></el-icon>
              一键断开所有设备
            </el-button>
            <el-button 
              type="info" 
              size="large" 
              @click="refreshDeviceStatus"
              :loading="refreshLoading"
            >
              <el-icon><Refresh /></el-icon>
              刷新状态
            </el-button>
          </div>
          
          <el-divider />
          
          <div class="acquisition-actions">
            <el-button 
              type="success" 
              size="large" 
              @click="startAcquisition"
              :loading="startAcqLoading"
              :disabled="!anyDeviceConnected || acquisitionRunning"
            >
              <el-icon><VideoPlay /></el-icon>
              启动数据采集
            </el-button>
            <el-button 
              type="warning" 
              size="large" 
              @click="stopAcquisition"
              :loading="stopAcqLoading"
              :disabled="!acquisitionRunning"
            >
              <el-icon><VideoPause /></el-icon>
              停止数据采集
            </el-button>
          </div>
        </div>
      </el-card>
      
      <!-- API 连接测试 -->
      <el-card class="settings-card" style="grid-column: span 2;">
        <APITestPanel />
      </el-card>
      
      <!-- 系统信息 -->
      <el-card class="settings-card" style="grid-column: span 2;">
        <template #header>
          <div class="card-header">
            <el-icon><InfoFilled /></el-icon>
            <span>系统信息</span>
          </div>
        </template>
        
        <el-descriptions :column="3" border>
          <el-descriptions-item label="后端版本">1.0.0</el-descriptions-item>
          <el-descriptions-item label="前端版本">1.0.0</el-descriptions-item>
          <el-descriptions-item label="PacNet 版本">v2.1</el-descriptions-item>
          <el-descriptions-item label="WebSocket 状态">
            <el-tag :type="store.connected ? 'success' : 'danger'">
              {{ store.connected ? '数据流正常' : '连接断开' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="摄像头状态">
            <el-tag :type="store.latestData.camera.ids_available ? 'success' : 'danger'">
              {{ store.latestData.camera.ids_available ? '正常' : '异常' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="打印机状态">
            {{ store.latestData.printer.state }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { systemApi, printerApi, deviceApi } from '../utils/api'
import { useDataStore } from '../stores/data'
import { useNotification } from '../composables/useNotification'
import { useResponsive } from '../composables/useResponsive'
import APITestPanel from '../components/APITestPanel.vue'

const store = useDataStore()
const { success, error } = useNotification()
const { isMobile } = useResponsive()

const saving = ref(false)

// 设备管理相关
const deviceStatus = ref({
  ids: false,
  side_camera: false,
  fotric: false,
  vibration: false,
  m114: false
})
const acquisitionRunning = ref(false)
const connectLoading = ref(false)
const disconnectLoading = ref(false)
const refreshLoading = ref(false)
const startAcqLoading = ref(false)
const stopAcqLoading = ref(false)

const allDevicesConnected = computed(() => {
  return Object.values(deviceStatus.value).every(v => v)
})

const anyDeviceConnected = computed(() => {
  return Object.values(deviceStatus.value).some(v => v)
})

const getDeviceName = (name) => {
  const names = {
    ids: 'IDS相机',
    side_camera: '旁轴相机',
    fotric: 'Fotric热成像',
    vibration: '振动传感器',
    m114: 'M114坐标'
  }
  return names[name] || name
}

const config = ref({
  octoprint: { host: 'localhost:5000', api_key: '' },
  camera: { 
    ids_enabled: true, 
    ids_device_id: 0, 
    side_url: '',
    resolution: '1920x1080'
  },
  thermal: { 
    enabled: true, 
    port: 'COM3', 
    baudrate: 921600,
    emissivity: 0.95
  },
  model: { 
    path: 'weights/model_full.pt', 
    scaler_path: 'weights/scaler.pkl',
    use_gpu: true,
    frequency: 5
  }
})

const loadConfig = async () => {
  try {
    const res = await systemApi.getConfig()
    Object.assign(config.value, res.data)
  } catch (e) {
    error('加载配置失败，使用默认配置')
  }
}

const saveConfig = async (section) => {
  try {
    await systemApi.saveConfig(section, config.value[section])
    success('配置已保存')
  } catch (e) {
    error('保存失败')
  }
}

const testConnection = async () => {
  try {
    await printerApi.testConnection()
    success('连接成功')
  } catch (e) {
    error('连接失败')
  }
}

const reloadModel = async () => {
  try {
    await systemApi.reloadModel()
    success('模型已重新加载')
  } catch (e) {
    error('加载失败')
  }
}

// 设备管理方法
const refreshDeviceStatus = async () => {
  refreshLoading.value = true
  try {
    const res = await deviceApi.getStatus()
    if (res.data.available) {
      deviceStatus.value = res.data.devices
      success('设备状态已刷新')
    } else {
      error(res.data.message || '设备状态获取失败')
    }
  } catch (e) {
    error('刷新设备状态失败')
  } finally {
    refreshLoading.value = false
  }
}

const connectAllDevices = async () => {
  connectLoading.value = true
  try {
    const res = await deviceApi.connectAll()
    success(res.data.message)
    await refreshDeviceStatus()
  } catch (e) {
    error('连接设备失败')
  } finally {
    connectLoading.value = false
  }
}

const disconnectAllDevices = async () => {
  disconnectLoading.value = true
  try {
    const res = await deviceApi.disconnectAll()
    success(res.data.message)
    await refreshDeviceStatus()
  } catch (e) {
    error('断开设备失败')
  } finally {
    disconnectLoading.value = false
  }
}

const startAcquisition = async () => {
  startAcqLoading.value = true
  try {
    const res = await deviceApi.startAcquisition()
    success(res.data.message)
    acquisitionRunning.value = true
  } catch (e) {
    error('启动采集失败')
  } finally {
    startAcqLoading.value = false
  }
}

const stopAcquisition = async () => {
  stopAcqLoading.value = true
  try {
    const res = await deviceApi.stopAcquisition()
    success(res.data.message)
    acquisitionRunning.value = false
  } catch (e) {
    error('停止采集失败')
  } finally {
    stopAcqLoading.value = false
  }
}

onMounted(() => {
  loadConfig()
  refreshDeviceStatus()
})
</script>

<style scoped>
.settings-page {
  padding: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 20px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.settings-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  color: #00d4ff;
}

:deep(.el-form-item__label) {
  color: #a0aec0;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 212, 255, 0.2);
}

:deep(.el-descriptions__label) {
  background: rgba(0, 212, 255, 0.1);
  color: #a0aec0;
}

:deep(.el-descriptions__content) {
  background: rgba(0, 0, 0, 0.2);
  color: #e2e8f0;
}

@media (max-width: 1200px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
  
  .settings-grid .settings-card:last-child {
    grid-column: span 1;
  }
}

@media (max-width: 768px) {
  .settings-grid.mobile-layout .settings-card {
    padding: 12px;
  }
}

/* 设备管理样式 */
.device-management {
  padding: 10px 0;
}

.device-status-section {
  margin-bottom: 20px;
}

.device-status-item {
  text-align: center;
  padding: 15px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(0, 212, 255, 0.1);
}

.status-text {
  margin-top: 8px;
  font-size: 12px;
  font-weight: 500;
}

.status-text.connected {
  color: #67c23a;
}

.status-text.disconnected {
  color: #f56c6c;
}

.device-actions,
.acquisition-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  flex-wrap: wrap;
}

.device-actions .el-button,
.acquisition-actions .el-button {
  min-width: 180px;
}

@media (max-width: 768px) {
  .device-actions,
  .acquisition-actions {
    flex-direction: column;
  }
  
  .device-actions .el-button,
  .acquisition-actions .el-button {
    width: 100%;
  }
}
</style>
