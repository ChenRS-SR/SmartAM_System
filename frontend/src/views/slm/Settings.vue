<template>
  <div class="slm-settings">
    <h2 class="page-title">SLM 设置</h2>
    
    <!-- 模拟模式设置 -->
    <el-card class="settings-card" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon size="20"><VideoCamera /></el-icon>
          <span>视频模拟设置</span>
          <el-tag v-if="videoFileMode.enabled" type="success" size="small" effect="dark">已启用</el-tag>
          <el-tag v-else type="info" size="small">未启用</el-tag>
        </div>
      </template>
      
      <div class="settings-content">
        <el-alert
          title="视频文件模拟模式"
          description="使用本地视频文件替代真实摄像头。系统会自动扫描 simulation_record 文件夹中的视频文件。"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />
        
        <!-- 自动扫描按钮 -->
        <el-form label-width="120px" size="default">
          <el-form-item>
            <el-button type="primary" @click="scanVideoFiles" :loading="scanning">
              <el-icon><Search /></el-icon>
              自动扫描视频文件
            </el-button>
            <span class="form-hint" style="margin-left: 10px;">
              扫描 simulation_record 文件夹
            </span>
          </el-form-item>
        </el-form>
        
        <!-- 扫描结果显示 -->
        <div v-if="scannedVideos.CH1 || scannedVideos.CH2 || scannedVideos.CH3" class="scan-result">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item v-if="scannedVideos.CH1" label="CH1 视频">
              <el-tag type="success" size="small">找到</el-tag>
              {{ scannedVideos.CH1.filename }}
            </el-descriptions-item>
            <el-descriptions-item v-else label="CH1 视频">
              <el-tag type="warning" size="small">未找到</el-tag>
            </el-descriptions-item>
            
            <el-descriptions-item v-if="scannedVideos.CH2" label="CH2 视频">
              <el-tag type="success" size="small">找到</el-tag>
              {{ scannedVideos.CH2.filename }}
            </el-descriptions-item>
            <el-descriptions-item v-else label="CH2 视频">
              <el-tag type="warning" size="small">未找到</el-tag>
            </el-descriptions-item>
            
            <el-descriptions-item v-if="scannedVideos.CH3" label="CH3 视频">
              <el-tag type="success" size="small">找到</el-tag>
              {{ scannedVideos.CH3.filename }}
            </el-descriptions-item>
            <el-descriptions-item v-else label="CH3 视频">
              <el-tag type="warning" size="small">未找到</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        
        <!-- 畸变矫正 -->
        <el-form :model="videoFileConfig" label-width="120px" size="default" style="margin-top: 20px;">
          <el-form-item label="畸变矫正">
            <el-switch
              v-model="videoFileConfig.enableCorrection"
              active-text="启用"
              inactive-text="禁用"
            />
            <div class="form-hint">
              使用 calibration_points.json 中的标定数据进行透视变换矫正
            </div>
          </el-form-item>
          
          <!-- FPS 控制滑块 -->
          <el-form-item label="播放帧率">
            <div class="fps-slider-container">
              <el-slider
                v-model="videoFileConfig.fps"
                :min="1"
                :max="60"
                :step="1"
                show-stops
                :marks="{1: '1', 10: '10', 20: '20', 30: '30', 60: '60'}"
                style="width: 300px;"
              />
              <span class="fps-value">{{ videoFileConfig.fps }} FPS</span>
            </div>
            <div class="form-hint">
              控制视频播放速度 (1-60 FPS)，默认 30 FPS
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button 
              type="primary" 
              @click="applyVideoFileMode"
              :loading="applying"
              :disabled="!hasValidVideoFiles"
            >
              <el-icon><Check /></el-icon>
              应用设置
            </el-button>
            <el-button 
              @click="disableVideoFileMode"
              :loading="disabling"
              :disabled="!videoFileMode.enabled"
            >
              禁用模拟
            </el-button>
            <el-button @click="refreshConfig">
              <el-icon><Refresh /></el-icon>
              刷新状态
            </el-button>
          </el-form-item>
        </el-form>
        
        <!-- 当前配置状态 -->
        <div v-if="videoFileMode.enabled" class="current-config">
          <el-divider />
          <h4>当前配置</h4>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="CH1">{{ videoFileMode.video_files.CH1 || '未设置' }}</el-descriptions-item>
            <el-descriptions-item label="CH2">{{ videoFileMode.video_files.CH2 || '未设置' }}</el-descriptions-item>
            <el-descriptions-item label="CH3">{{ videoFileMode.video_files.CH3 || '未设置' }}</el-descriptions-item>
            <el-descriptions-item label="畸变矫正">{{ videoFileMode.correction_enabled ? '启用' : '禁用' }}</el-descriptions-item>
            <el-descriptions-item label="播放帧率">{{ videoFileMode.fps || 30 }} FPS</el-descriptions-item>
          </el-descriptions>
        </div>
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, Search, Check, Refresh, Crop } from '@element-plus/icons-vue'

// API 基础地址
const API_BASE = '/api/slm'

// 视频文件配置
const videoFileConfig = reactive({
  enableCorrection: true,
  fps: 30
})

// 扫描到的视频文件
const scannedVideos = reactive({
  CH1: null,
  CH2: null,
  CH3: null
})

// 当前视频文件模式状态
const videoFileMode = reactive({
  enabled: false,
  video_files: {},
  correction_enabled: true,
  fps: 30
})

// 畸变矫正信息
const correctionInfo = reactive({
  calibration_file: '',
  channels: {}
})

// 标定文件路径
const calibrationFilePath = ref('')

// 加载状态
const applying = ref(false)
const disabling = ref(false)
const scanning = ref(false)
const reloadingCalibration = ref(false)

// 计算属性
const hasValidVideoFiles = computed(() => {
  return scannedVideos.CH1 || scannedVideos.CH2 || scannedVideos.CH3
})

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

// 扫描视频文件
async function scanVideoFiles() {
  scanning.value = true
  
  try {
    const response = await fetch(`${API_BASE}/video_file_mode/scan`)
    const result = await response.json()
    
    if (result.success) {
      // 更新扫描结果
      scannedVideos.CH1 = result.videos.CH1 || null
      scannedVideos.CH2 = result.videos.CH2 || null
      scannedVideos.CH3 = result.videos.CH3 || null
      
      const foundCount = [scannedVideos.CH1, scannedVideos.CH2, scannedVideos.CH3].filter(v => v).length
      ElMessage.success(`扫描完成，找到 ${foundCount} 个视频文件`)
    } else {
      ElMessage.error(result.message || '扫描失败')
    }
  } catch (error) {
    console.error('扫描视频文件失败:', error)
    ElMessage.error('扫描视频文件失败: ' + error.message)
  } finally {
    scanning.value = false
  }
}

// 应用视频文件模式
async function applyVideoFileMode() {
  if (!hasValidVideoFiles.value) {
    ElMessage.warning('请先扫描视频文件')
    return
  }
  
  applying.value = true
  
  try {
    // 构建视频文件字典
    const videoFiles = {}
    if (scannedVideos.CH1) videoFiles.CH1 = scannedVideos.CH1.path
    if (scannedVideos.CH2) videoFiles.CH2 = scannedVideos.CH2.path
    if (scannedVideos.CH3) videoFiles.CH3 = scannedVideos.CH3.path
    
    const response = await fetch(`${API_BASE}/video_file_mode/setup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        video_files: videoFiles,
        enable_correction: videoFileConfig.enableCorrection
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      ElMessage.success('视频文件模拟模式已启用')
      // 设置 FPS
      await setVideoFileFps()
      await refreshConfig()
    } else {
      ElMessage.error(result.message || '设置失败')
    }
  } catch (error) {
    console.error('应用设置失败:', error)
    ElMessage.error('应用设置失败: ' + error.message)
  } finally {
    applying.value = false
  }
}

// 禁用视频文件模式
async function disableVideoFileMode() {
  disabling.value = true
  
  try {
    const response = await fetch(`${API_BASE}/video_file_mode/disable`, {
      method: 'POST'
    })
    
    const result = await response.json()
    
    if (result.success) {
      ElMessage.success('视频文件模拟模式已禁用')
      videoFileMode.enabled = false
      videoFileMode.video_files = {}
    } else {
      ElMessage.error(result.message || '禁用失败')
    }
  } catch (error) {
    console.error('禁用失败:', error)
    ElMessage.error('禁用失败: ' + error.message)
  } finally {
    disabling.value = false
  }
}

// 设置视频文件 FPS
async function setVideoFileFps() {
  try {
    const response = await fetch(`${API_BASE}/video_file_mode/fps?fps=${videoFileConfig.fps}`, {
      method: 'POST'
    })
    
    const result = await response.json()
    
    if (result.success) {
      ElMessage.success(`播放帧率已设置为 ${videoFileConfig.fps} FPS`)
    } else {
      console.log('FPS 设置提示:', result.message)
    }
  } catch (error) {
    console.error('设置 FPS 失败:', error)
  }
}

// 刷新配置
async function refreshConfig() {
  try {
    // 获取视频文件模式配置
    const modeResponse = await fetch(`${API_BASE}/video_file_mode/config`)
    const modeResult = await modeResponse.json()
    
    if (modeResult.success) {
      videoFileMode.enabled = modeResult.enabled
      videoFileMode.video_files = modeResult.video_files || {}
      videoFileMode.correction_enabled = modeResult.correction_enabled
      videoFileMode.fps = modeResult.fps || 30
      // 同步到配置表单
      videoFileConfig.fps = modeResult.fps || 30
    }
    
    // 获取畸变矫正信息
    await loadCorrectionInfo()
  } catch (error) {
    console.error('刷新配置失败:', error)
    ElMessage.error('刷新配置失败: ' + error.message)
  }
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
  refreshConfig()
  // 自动扫描一次
  scanVideoFiles()
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

.scan-result {
  margin: 20px 0;
  padding: 15px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
}

.form-hint {
  font-size: 12px;
  color: #64748b;
  margin-top: 5px;
}

.current-config {
  margin-top: 20px;
}

.current-config h4 {
  color: #e2e8f0;
  margin-bottom: 15px;
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

.fps-slider-container {
  display: flex;
  align-items: center;
  gap: 15px;
}

.fps-value {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
  min-width: 60px;
}

:deep(.el-slider__runway) {
  background-color: rgba(100, 116, 139, 0.3);
}

:deep(.el-slider__bar) {
  background-color: #409eff;
}

:deep(.el-slider__button) {
  border-color: #409eff;
}

:deep(.el-slider__stop) {
  background-color: rgba(100, 116, 139, 0.5);
}

:deep(.el-slider__marks-text) {
  color: #94a3b8;
}
</style>
