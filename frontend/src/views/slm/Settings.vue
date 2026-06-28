<template>
  <div class="slm-settings">
    <h2 class="page-title">SLM 设置</h2>

    <!-- 华科实验台连接设置 -->
    <el-card class="settings-card" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon size="20"><VideoCamera /></el-icon>
          <span>华科实验台连接设置</span>
          <el-tag :type="benchSettings.use_mock ? 'warning' : 'success'" size="small" effect="dark">
            {{ benchSettings.use_mock ? '模拟数据' : '真实硬件' }}
          </el-tag>
        </div>
      </template>

      <div class="settings-content">
        <el-alert
          title="实验台采集连接参数"
          description="这里集中维护华科实验台 USB 摄像头、红外热像仪和调试模式设置；设备状态监测页启动采集时读取此处保存的配置。"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />

        <el-form :model="benchSettings" label-width="140px" size="default">
          <el-divider content-position="left">摄像头设置 (USB)</el-divider>
          <el-form-item label="CH1主摄像头">
            <div class="camera-select-row">
              <el-select v-model="benchSettings.camera_ch1_index" style="width: 240px" :loading="camerasLoading">
                <el-option
                  v-for="cam in availableCameras"
                  :key="`ch1-${cam.index}`"
                  :label="formatCameraLabel(cam)"
                  :value="cam.index"
                />
                <el-option v-if="availableCameras.length === 0 && !camerasLoading" label="未检测到摄像头" :value="-1" disabled />
                <el-option v-if="camerasLoading" label="正在检测..." :value="-1" disabled />
              </el-select>
              <el-button type="primary" @click="fetchCameras" :loading="camerasLoading">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="CH2副摄像头">
            <el-select v-model="benchSettings.camera_ch2_index" style="width: 240px" :loading="camerasLoading">
              <el-option
                v-for="cam in availableCameras"
                :key="`ch2-${cam.index}`"
                :label="formatCameraLabel(cam)"
                :value="cam.index"
              />
              <el-option v-if="availableCameras.length === 0 && !camerasLoading" label="未检测到摄像头" :value="-1" disabled />
              <el-option v-if="camerasLoading" label="正在检测..." :value="-1" disabled />
            </el-select>
          </el-form-item>

          <el-divider content-position="left">红外热像仪</el-divider>
          <el-form-item>
            <el-alert
              type="info"
              :closable="false"
              show-icon
            >
              <template #title>
                红外热像仪通过 PIX Connect SDK 连接，不需要 COM 口
              </template>
              <template #default>
                请确认 PIX Connect 软件已安装并启动、热像仪设备已连接，并在 PIX Connect 中启用 IPC 通信。
              </template>
            </el-alert>
          </el-form-item>

          <el-divider content-position="left">调试模式</el-divider>
          <el-form-item label="使用模拟数据">
            <el-switch v-model="benchSettings.use_mock" />
            <span class="form-hint inline-hint">
              开启后无需连接真实硬件，用于界面测试
            </span>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="saveBenchSettings">
              <el-icon><Check /></el-icon>
              保存连接设置
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    
    <!-- 设备目录模拟视频扫描 -->
    <el-card class="settings-card" shadow="never" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <el-icon size="20"><VideoCamera /></el-icon>
          <span>设备模拟视频扫描</span>
          <el-tag type="info" size="small">由设备文件数据库决定</el-tag>
        </div>
      </template>
      
      <div class="settings-content">
        <el-alert
          title="模拟视频按设备目录自动扫描"
          description="在单台设备数据库目录下放入 mock_video/CH1、mock_video/CH2、mock_video/CH3 文件夹；每个通道文件夹内放一个支持格式的视频即可自动接入。"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />

        <el-table :data="mockCaseRows" border size="small">
          <el-table-column prop="name" label="设备" min-width="180" />
          <el-table-column prop="caseLabel" label="扫描结果" min-width="160" />
          <el-table-column prop="folder" label="目录结构" min-width="260" />
          <el-table-column prop="status" label="状态" width="120" />
        </el-table>
      </div>
    </el-card>
    
    <!-- 畸变矫正信息 -->
    <el-card class="settings-card" shadow="never" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <el-icon size="20"><Crop /></el-icon>
          <span>畸变矫正信息</span>
          <el-button 
            type="primary" 
            size="small" 
            @click="reloadCalibration"
            :loading="reloadingCalibration"
          >
            重新加载
          </el-button>
        </div>
      </template>
      
      <div class="correction-info">
        <!-- 标定文件路径 -->
        <el-form label-width="150px" size="small" style="margin-bottom: 15px;">
          <el-form-item label="标定文件路径">
            <el-input 
              v-model="calibrationFilePath" 
              placeholder="默认: 项目根目录/calibration_points.json"
            >
              <template #append>
                <el-button @click="setCalibrationPath">
                  设置路径
                </el-button>
              </template>
            </el-input>
            <div class="form-hint">
              默认自动查找项目根目录下的 calibration_points.json 文件
            </div>
          </el-form-item>
        </el-form>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="标定文件">
            {{ correctionInfo.calibration_file ? '已加载' : '未加载' }}
          </el-descriptions-item>
          <el-descriptions-item label="已标定通道">
            <el-tag 
              v-for="ch in calibratedChannels" 
              :key="ch"
              type="success"
              size="small"
              style="margin-right: 5px;"
            >
              {{ ch }}
            </el-tag>
            <span v-if="calibratedChannels.length === 0">无</span>
          </el-descriptions-item>
        </el-descriptions>
        
        <div v-if="calibratedChannels.length > 0" class="channel-details">
          <h4>通道详情</h4>
          <el-table :data="channelDetails" border size="small">
            <el-table-column prop="channel" label="通道" width="80" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.calibrated ? 'success' : 'info'" size="small">
                  {{ row.calibrated ? '已标定' : '未标定' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="source_points" label="源标定点" />
            <el-table-column prop="output_size" label="输出尺寸" width="120" />
          </el-table>
        </div>
        
        <el-alert
          v-else
          title="未找到标定数据"
          description="请确保 calibration_points.json 文件存在于项目根目录，并包含有效的4点标定数据。"
          type="warning"
          :closable="false"
          show-icon
          style="margin-top: 15px;"
        />
      </div>
    </el-card>
    
    <!-- ROI区域配置 -->
    <el-card class="settings-card" shadow="never" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <el-icon size="20"><Crop /></el-icon>
          <span>ROI区域配置</span>
          <el-tag v-if="roiConfigured" type="success" size="small" effect="dark">已配置</el-tag>
        </div>
      </template>
      
      <ROIConfigPanel 
        @config-loaded="onROIConfigLoaded"
        @config-cleared="onROIConfigCleared"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, Check, Refresh, Crop } from '@element-plus/icons-vue'
import ROIConfigPanel from '../../components/slm/ROIConfigPanel.vue'
import { readSlmBenchSettings, writeSlmBenchSettings } from '../../utils/slmBenchSettings'
import { useSlmDeviceStore } from '../../stores/slmDevices'
import { getDeviceMockCase } from '../../utils/slmMockCases'

// API 基础地址
const API_BASE = '/api/slm'
const slmDeviceStore = useSlmDeviceStore()

// 华科实验台连接设置，供设备状态监测页启动采集时读取。
const benchSettings = reactive(readSlmBenchSettings())
const availableCameras = ref([])
const camerasLoading = ref(false)

// 畸变矫正信息
const correctionInfo = reactive({
  calibration_file: '',
  channels: {}
})

// 标定文件路径
const calibrationFilePath = ref('')

// 加载状态
const reloadingCalibration = ref(false)

// ROI配置状态
const roiConfigured = ref(false)

// 计算属性
const calibratedChannels = computed(() => {
  return Object.keys(correctionInfo.channels).filter(ch => 
    correctionInfo.channels[ch]?.calibrated
  )
})

const channelDetails = computed(() => {
  return Object.entries(correctionInfo.channels).map(([channel, info]) => ({
    channel,
    calibrated: info.calibrated,
    source_points: info.source_points?.map(p => `[${p[0]}, ${p[1]}]`).join(', ') || '-',
    output_size: info.output_size ? `${info.output_size[0]} x ${info.output_size[1]}` : '-'
  }))
})

const mockCaseRows = computed(() => slmDeviceStore.devices.map((device) => {
  const mockCase = getDeviceMockCase(device)
  return {
    id: device.id,
    name: device.name,
    hasCase: Boolean(mockCase),
    caseLabel: mockCase?.label || '暂不支持接入',
    folder: mockCase ? `${device.dataDirectory}/mock_video/CH1..CH3` : '--',
    status: mockCase?.supported ? '已接入' : '未接入'
  }
}))

function formatCameraLabel(camera) {
  const resolution = camera.resolution?.length === 2
    ? `${camera.resolution[0]}x${camera.resolution[1]}`
    : '未知分辨率'
  return `摄像头 ${camera.index} (${resolution})`
}

async function fetchCameras() {
  camerasLoading.value = true
  try {
    const response = await fetch(`${API_BASE}/cameras`)
    const result = await response.json()

    if (result.success) {
      availableCameras.value = result.cameras || []

      // 只在当前保存的索引不存在时，按检测顺序填入可用摄像头。
      const availableIndices = availableCameras.value.map(camera => camera.index)
      const ch1Valid = availableIndices.includes(benchSettings.camera_ch1_index)
      const ch2Valid = availableIndices.includes(benchSettings.camera_ch2_index)

      if (availableCameras.value.length >= 2) {
        if (!ch1Valid) benchSettings.camera_ch1_index = availableCameras.value[0].index
        if (!ch2Valid) benchSettings.camera_ch2_index = availableCameras.value[1].index
      } else if (availableCameras.value.length === 1) {
        if (!ch1Valid) benchSettings.camera_ch1_index = availableCameras.value[0].index
      }
    } else {
      ElMessage.warning(result.message || '摄像头检测失败')
    }
  } catch (error) {
    console.error('获取摄像头失败:', error)
    ElMessage.error('摄像头检测失败: ' + error.message)
  } finally {
    camerasLoading.value = false
  }
}

function saveBenchSettings() {
  writeSlmBenchSettings(benchSettings)
  ElMessage.success('华科实验台连接设置已保存')
}

// ROI配置回调
function onROIConfigLoaded(config) {
  roiConfigured.value = true
  ElMessage.success('ROI配置已加载')
}

function onROIConfigCleared() {
  roiConfigured.value = false
}

// 加载畸变矫正信息
async function loadCorrectionInfo() {
  try {
    const response = await fetch(`${API_BASE}/capture/correction_info`)
    const result = await response.json()
    
    if (result.success) {
      Object.assign(correctionInfo, result)
    }
  } catch (error) {
    console.error('获取矫正信息失败:', error)
  }
}

// 设置标定文件路径
async function setCalibrationPath() {
  if (!calibrationFilePath.value) {
    ElMessage.warning('请输入标定文件路径')
    return
  }
  
  try {
    const response = await fetch(`${API_BASE}/capture/correction/set_path`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        path: calibrationFilePath.value
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      ElMessage.success('标定文件路径已设置')
      await loadCorrectionInfo()
    } else {
      ElMessage.error(result.message || '设置失败')
    }
  } catch (error) {
    console.error('设置路径失败:', error)
    ElMessage.error('设置路径失败: ' + error.message)
  }
}

// 重新加载标定数据
async function reloadCalibration() {
  reloadingCalibration.value = true
  
  try {
    const response = await fetch(`${API_BASE}/capture/correction/reload`, {
      method: 'POST'
    })
    
    const result = await response.json()
    
    if (result.success) {
      ElMessage.success('标定数据已重新加载')
      await loadCorrectionInfo()
    } else {
      ElMessage.error(result.message || '重新加载失败')
    }
  } catch (error) {
    console.error('重新加载失败:', error)
    ElMessage.error('重新加载失败: ' + error.message)
  } finally {
    reloadingCalibration.value = false
  }
}

// 初始化
onMounted(() => {
  fetchCameras()
  loadCorrectionInfo()
  slmDeviceStore.loadDevicesFromBackend().catch((error) => {
    ElMessage.error(error.message || '加载设备模拟用例绑定失败')
  })
})
</script>

<style scoped>
.slm-settings {
  padding: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0 0 20px 0;
}

.settings-card {
  border: none;
  background: rgba(15, 23, 42, 0.6);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  color: #e2e8f0;
}

.settings-content {
  padding: 10px 0;
}

.form-hint {
  font-size: 12px;
  color: #64748b;
  margin-top: 5px;
}

.inline-hint {
  margin-left: 10px;
  margin-top: 0;
}

.camera-select-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.correction-info {
  padding: 10px 0;
}

.channel-details {
  margin-top: 20px;
}

.channel-details h4 {
  color: #e2e8f0;
  margin-bottom: 15px;
}

:deep(.el-descriptions__label) {
  background: rgba(30, 41, 59, 0.8) !important;
  color: #94a3b8 !important;
}

:deep(.el-descriptions__content) {
  background: rgba(15, 23, 42, 0.4) !important;
  color: #e2e8f0 !important;
}

</style>
