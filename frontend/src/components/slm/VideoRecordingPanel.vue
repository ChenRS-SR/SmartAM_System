<template>
  <el-card class="video-recording-panel" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">
          <el-icon><VideoCamera /></el-icon>
          视频采集与智能诊断
        </span>
        <div class="header-tags">
          <el-tag 
            :type="recordingStatus.is_recording ? 'success' : 'info'" 
            size="small"
            effect="dark"
          >
            {{ recordingStatus.is_recording ? '录制中' : '未录制' }}
          </el-tag>
          <el-tag 
            v-if="diagnosisStatus.status === 'running'"
            type="warning" 
            size="small"
            effect="dark"
          >
            诊断中 {{ Math.round(diagnosisProgress) }}%
          </el-tag>
        </div>
      </div>
    </template>

    <!-- 诊断模式切换 -->
    <div class="mode-switch">
      <el-radio-group v-model="diagnosisMode" size="small">
        <el-radio-button label="realtime">
          <el-icon><VideoPlay /></el-icon>
          实时诊断
        </el-radio-button>
        <el-radio-button label="simulation">
          <el-icon><FolderOpened /></el-icon>
          模拟诊断
        </el-radio-button>
      </el-radio-group>
      <el-tooltip content="实时诊断：诊断刚录制的视频&#10;模拟诊断：从目录加载预存视频进行诊断">
        <el-icon class="mode-help"><QuestionFilled /></el-icon>
      </el-tooltip>
    </div>

    <!-- 录制控制（仅在实时模式下显示） -->
    <div v-if="diagnosisMode === 'realtime'" class="recording-section">
      <el-divider content-position="left">
        <el-icon><Setting /></el-icon>
        录制设置
      </el-divider>
      
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="info-alert"
      >
        <template #title>实时视频将自动保存到默认目录，诊断时自动抽取50帧进行分析</template>
      </el-alert>

      <el-form :model="recordingConfig" label-width="120px" size="small">
        <el-form-item label="视频录制">
          <el-switch 
            v-model="recordingConfig.enabled" 
            @change="onEnableChange"
            :disabled="!isRunning"
          />
          <span class="form-hint">{{ isRunning ? '' : '（需先启动采集）' }}</span>
        </el-form-item>
        
        <el-form-item label="录制间隔">
          <el-slider 
            v-model="recordingConfig.interval" 
            :min="10" 
            :max="60" 
            :step="5"
            show-stops
            :marks="{10: '10s', 30: '30s', 60: '60s'}"
            @change="onIntervalChange"
            :disabled="!recordingConfig.enabled"
          />
          <span class="slider-value">{{ recordingConfig.interval }} 秒</span>
        </el-form-item>
        
        <el-form-item label="视频长度">
          <el-radio-group v-model="recordingConfig.duration" size="small" :disabled="!recordingConfig.enabled">
            <el-radio-button :label="3">3秒</el-radio-button>
            <el-radio-button :label="5">5秒</el-radio-button>
            <el-radio-button :label="10">10秒</el-radio-button>
          </el-radio-group>
          <span class="form-hint">（每{{ recordingConfig.duration }}秒视频抽取50帧诊断）</span>
        </el-form-item>
        
        <el-form-item label="保存目录">
          <div class="directory-input">
            <el-input 
              v-model="recordingConfig.saveDir" 
              readonly
              size="small"
            >
              <template #append>
                <el-button @click="selectDirectory" size="small">
                  <el-icon><Folder /></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>
        </el-form-item>
      </el-form>

      <!-- 最新录制视频快速诊断 -->
      <div v-if="latestVideos.length > 0" class="latest-videos">
        <el-divider content-position="left">最新录制（可快速诊断）</el-divider>
        <div class="video-list">
          <div 
            v-for="video in latestVideos" 
            :key="video.filepath"
            class="video-item"
            :class="{ 'selected': isVideoSelected(video) }"
            @click="toggleVideoSelection(video)"
          >
            <el-icon><VideoPlay /></el-icon>
            <span class="video-name">{{ video.channel }} - {{ video.timestamp }}</span>
            <el-tag size="small" type="info">{{ video.frame_count }}帧</el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 模拟模式：文件选择 -->
    <div v-else class="simulation-section">
      <el-divider content-position="left">
        <el-icon><FolderOpened /></el-icon>
        测试样本选择
      </el-divider>
      
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        class="info-alert"
      >
        <template #title>从保存目录中选择预存视频进行诊断测试</template>
      </el-alert>

      <!-- 目录选择 -->
      <div class="directory-browser">
        <el-input 
          v-model="simulationConfig.directory" 
          placeholder="选择视频目录"
          readonly
          size="small"
        >
          <template #append>
            <el-button @click="browseDirectory" size="small">
              <el-icon><Folder /></el-icon>
              浏览
            </el-button>
          </template>
        </el-input>
      </div>

      <!-- 视频文件列表 -->
      <div v-if="availableVideos.length > 0" class="video-browser">
        <div class="channel-tabs">
          <div 
            v-for="ch in ['CH1', 'CH2', 'CH3']" 
            :key="ch"
            class="channel-group"
          >
            <div class="channel-title">{{ ch }}</div>
            <el-select 
              v-model="selectedVideos[ch]" 
              placeholder="选择视频"
              size="small"
              clearable
              class="video-select"
            >
              <el-option 
                v-for="video in getVideosByChannel(ch)" 
                :key="video.filepath" 
                :label="video.filename" 
                :value="video.filepath"
              >
                <span>{{ video.filename }}</span>
                <span class="video-time">{{ video.timestamp }}</span>
              </el-option>
            </el-select>
          </div>
        </div>
      </div>
      <el-empty v-else description="目录中没有视频文件" />
    </div>

    <!-- 诊断控制 -->
    <div class="diagnosis-control">
      <el-divider content-position="left">
        <el-icon><FirstAidKit /></el-icon>
        诊断控制
      </el-divider>
      
      <div class="control-buttons">
        <el-button 
          type="primary" 
          size="default"
          @click="startDiagnosis"
          :loading="isDiagnosing"
          :disabled="!canStartDiagnosis"
        >
          <el-icon><VideoPlay /></el-icon>
          {{ diagnosisMode === 'realtime' ? '诊断最新视频' : '诊断选中视频' }}
        </el-button>
        
        <el-button 
          type="danger" 
          size="default"
          @click="stopDiagnosis"
          :disabled="!isDiagnosing"
        >
          <el-icon><CircleClose /></el-icon>
          停止诊断
        </el-button>

        <el-button
          type="info"
          size="default"
          @click="setupDiagnosisEngine"
          :loading="isSettingUp"
        >
          <el-icon><Setting /></el-icon>
          设置引擎
        </el-button>
      </div>

      <!-- 诊断进度 -->
      <div v-if="isDiagnosing" class="progress-section">
        <el-progress 
          :percentage="Math.round(diagnosisProgress)" 
          :status="diagnosisProgress >= 100 ? 'success' : ''"
          :stroke-width="10"
        />
        <div class="progress-detail">
          <span>正在处理: {{ diagnosisDetail.current_frame }} 帧</span>
          <span>异常帧: {{ diagnosisDetail.fault_count }}</span>
          <span>模式: {{ diagnosisMode === 'realtime' ? '实时' : '模拟' }}</span>
        </div>
      </div>

      <!-- 诊断结果 -->
      <div v-if="diagnosisResult" class="result-section">
        <el-alert 
          :type="getResultAlertType(diagnosisResult.status_code)"
          :closable="false"
          show-icon
        >
          <template #title>
            <div class="result-title">
              <span>诊断结果: {{ diagnosisResult.status_label }}</span>
              <el-tag size="small" type="info">置信度: {{ (diagnosisResult.confidence * 100).toFixed(1) }}%</el-tag>
            </div>
          </template>
          <template #default>
            <div class="result-detail">
              <p>状态码: {{ diagnosisResult.status_code }}</p>
              <p>处理帧数: {{ diagnosisResult.frame_count }}</p>
              <p v-if="diagnosisResult.details?.mode">推理模式: {{ diagnosisResult.details.mode === 'onnx' ? 'ONNX模型' : '模拟' }}</p>
            </div>
          </template>
        </el-alert>
        
        <div class="result-action">
          <el-button type="primary" size="small" @click="applyToHealthStatus">
            更新到设备健康状态
          </el-button>
        </div>
      </div>
    </div>

    <!-- 录制历史 -->
    <div v-if="recordingHistory.length > 0" class="history-section">
      <el-divider content-position="left">
        <el-icon><Timer /></el-icon>
        录制历史
      </el-divider>
      
      <el-table :data="recordingHistory" size="small" max-height="200">
        <el-table-column prop="channel" label="通道" width="70">
          <template #default="{ row }">
            <el-tag size="small" :type="getChannelTagType(row.channel)">
              {{ row.channel }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
        <el-table-column prop="timestamp" label="时间" width="130" />
        <el-table-column prop="frame_count" label="帧数" width="60" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button 
              type="primary" 
              size="small" 
              link
              @click="quickDiagnose(row)"
            >
              诊断
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { 
  VideoCamera, VideoPlay, FolderOpened, Folder, 
  Setting, FirstAidKit, CircleClose, Timer, QuestionFilled 
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const props = defineProps({
  isRunning: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['diagnosis-complete'])

// 诊断模式
const diagnosisMode = ref('realtime')  // 'realtime' 或 'simulation'

// 录制配置
const recordingConfig = reactive({
  enabled: false,
  interval: 30,
  duration: 5,
  saveDir: './recordings'
})

// 模拟模式配置
const simulationConfig = reactive({
  directory: './recordings'
})

// 状态
const recordingStatus = reactive({
  is_recording: false,
  save_directory: '',
  interval_seconds: 30,
  clip_duration: 5,
  fps: 10,
  history_count: 0
})

const recordingHistory = ref([])
const availableVideos = ref([])
const selectedVideos = reactive({
  CH1: '',
  CH2: '',
  CH3: ''
})

// 诊断状态
const isDiagnosing = ref(false)
const isSettingUp = ref(false)
const diagnosisProgress = ref(0)
const diagnosisDetail = reactive({
  current_frame: 0,
  fault_count: 0
})
const diagnosisResult = ref(null)
const diagnosisStatus = reactive({
  status: 'idle'
})

// 计算属性
const latestVideos = computed(() => {
  // 获取每个通道最新的视频
  const latest = {}
  recordingHistory.value.forEach(video => {
    if (!latest[video.channel] || video.timestamp > latest[video.channel].timestamp) {
      latest[video.channel] = video
    }
  })
  return Object.values(latest)
})

const canStartDiagnosis = computed(() => {
  if (diagnosisMode.value === 'realtime') {
    return latestVideos.value.length > 0
  } else {
    return selectedVideos.CH1 || selectedVideos.CH2 || selectedVideos.CH3
  }
})

// 获取视频列表
const fetchRecordingStatus = async () => {
  try {
    const response = await axios.get('/api/slm/video/status')
    if (response.data.success) {
      Object.assign(recordingStatus, response.data)
      recordingConfig.enabled = response.data.enabled
      recordingConfig.interval = response.data.interval_seconds
      recordingConfig.duration = response.data.clip_duration
      if (response.data.save_directory) {
        recordingConfig.saveDir = response.data.save_directory
        simulationConfig.directory = response.data.save_directory
      }
    }
  } catch (error) {
    console.error('获取录制状态失败:', error)
  }
}

const fetchRecordingHistory = async () => {
  try {
    const response = await axios.get('/api/slm/video/history?limit=50')
    if (response.data.success) {
      recordingHistory.value = response.data.history
    }
  } catch (error) {
    console.error('获取录制历史失败:', error)
  }
}

const fetchAvailableVideos = async () => {
  // 从历史记录中构建可用视频列表
  availableVideos.value = recordingHistory.value
}

const getVideosByChannel = (channel) => {
  return availableVideos.value.filter(v => v.channel === channel)
}

// 录制控制
const onEnableChange = async (val) => {
  try {
    await axios.post('/api/slm/video/enable', null, { params: { enabled: val } })
    ElMessage.success(val ? '视频录制已启用' : '视频录制已禁用')
  } catch (error) {
    ElMessage.error('设置失败: ' + error.message)
    recordingConfig.enabled = !val
  }
}

const onIntervalChange = async (val) => {
  try {
    await axios.post('/api/slm/video/interval', null, { params: { interval_seconds: val } })
  } catch (error) {
    console.error('设置间隔失败:', error)
  }
}

const selectDirectory = async () => {
  const newDir = prompt('请输入保存目录路径:', recordingConfig.saveDir)
  if (newDir && newDir !== recordingConfig.saveDir) {
    try {
      const response = await axios.post('/api/slm/video/directory', null, {
        params: { save_dir: newDir }
      })
      if (response.data.success) {
        recordingConfig.saveDir = response.data.save_directory
        simulationConfig.directory = response.data.save_directory
        ElMessage.success('保存目录已更新')
      }
    } catch (error) {
      ElMessage.error('设置目录失败: ' + error.message)
    }
  }
}

// 目录浏览（模拟模式）
const browseDirectory = async () => {
  const newDir = prompt('请输入视频目录路径:', simulationConfig.directory)
  if (newDir) {
    simulationConfig.directory = newDir
    // 重新加载视频列表
    await fetchRecordingHistory()
    await fetchAvailableVideos()
  }
}

// 视频选择
const isVideoSelected = (video) => {
  return Object.values(selectedVideos).includes(video.filepath)
}

const toggleVideoSelection = (video) => {
  if (selectedVideos[video.channel] === video.filepath) {
    selectedVideos[video.channel] = ''
  } else {
    selectedVideos[video.channel] = video.filepath
  }
}

const quickDiagnose = (video) => {
  selectedVideos[video.channel] = video.filepath
  diagnosisMode.value = 'simulation'
  startDiagnosis()
}

// 诊断引擎设置
const setupDiagnosisEngine = async () => {
  isSettingUp.value = true
  try {
    const response = await axios.post('/api/slm/diagnosis/setup', null, {
      params: { 
        model_path: null,  // 使用模拟模式
        frame_count: 50 
      }
    })
    if (response.data.success) {
      ElMessage.success(response.data.has_model ? 'ONNX模型加载成功' : '诊断引擎已启动（模拟模式）')
    }
  } catch (error) {
    ElMessage.error('设置诊断引擎失败: ' + error.message)
  } finally {
    isSettingUp.value = false
  }
}

// 开始诊断
const startDiagnosis = async () => {
  isDiagnosing.value = true
  diagnosisProgress.value = 0
  diagnosisDetail.current_frame = 0
  diagnosisDetail.fault_count = 0
  diagnosisResult.value = null
  
  try {
    // 准备视频文件参数
    const params = { mode: diagnosisMode.value }
    
    if (diagnosisMode.value === 'realtime') {
      // 使用最新录制的视频
      latestVideos.value.forEach(video => {
        params[`${video.channel.toLowerCase()}_video`] = video.filepath
      })
    } else {
      // 使用选中的视频
      if (selectedVideos.CH1) params.ch1_video = selectedVideos.CH1
      if (selectedVideos.CH2) params.ch2_video = selectedVideos.CH2
      if (selectedVideos.CH3) params.ch3_video = selectedVideos.CH3
    }
    
    const response = await axios.post('/api/slm/diagnosis/start', null, { params })
    
    if (response.data.success) {
      ElMessage.success('诊断已启动')
      // 轮询诊断状态
      pollDiagnosisStatus()
    } else {
      ElMessage.error(response.data.message || '启动失败')
      isDiagnosing.value = false
    }
  } catch (error) {
    ElMessage.error('启动诊断失败: ' + error.message)
    isDiagnosing.value = false
  }
}

// 轮询诊断状态
const pollDiagnosisStatus = async () => {
  const pollInterval = setInterval(async () => {
    try {
      const response = await axios.get('/api/slm/diagnosis/status')
      if (response.data.success) {
        diagnosisStatus.status = response.data.status
        diagnosisProgress.value = response.data.progress || 0
        diagnosisDetail.current_frame = response.data.current_frame || 0
        diagnosisDetail.fault_count = response.data.fault_count || 0
        
        // 诊断完成
        if (response.data.status === 'completed' || response.data.status === 'error') {
          clearInterval(pollInterval)
          isDiagnosing.value = false
          
          // 获取诊断结果
          const healthResponse = await axios.get('/api/slm/diagnosis/health')
          if (healthResponse.data.success) {
            diagnosisResult.value = {
              status_code: healthResponse.data.health.status_code,
              status_label: getStatusLabel(healthResponse.data.health.status_code),
              confidence: 0.85,  // 示例值
              frame_count: diagnosisDetail.current_frame,
              details: { mode: response.data.has_model ? 'onnx' : 'simulation' }
            }
            
            // 自动应用到健康状态
            applyToHealthStatus()
          }
        }
      }
    } catch (error) {
      console.error('获取诊断状态失败:', error)
    }
    
    // 超时停止
    if (!isDiagnosing.value) {
      clearInterval(pollInterval)
    }
  }, 500)
}

// 停止诊断
const stopDiagnosis = async () => {
  isDiagnosing.value = false
  ElMessage.info('诊断已停止')
}

// 应用到健康状态
const applyToHealthStatus = () => {
  if (diagnosisResult.value) {
    emit('diagnosis-complete', diagnosisResult.value)
    ElMessage.success('诊断结果已应用到设备健康状态')
  }
}

// 辅助函数
const getChannelTagType = (channel) => {
  const map = { 'CH1': 'primary', 'CH2': 'success', 'CH3': 'warning' }
  return map[channel] || 'info'
}

const getStatusLabel = (code) => {
  const map = {
    '-1': '未开机',
    '0': '健康',
    '1': '刮刀磨损',
    '2': '激光功率异常',
    '3': '保护气体异常',
    '4': '复合故障'
  }
  return map[String(code)] || '未知'
}

const getResultAlertType = (code) => {
  if (code === 0) return 'success'
  if (code === -1) return 'info'
  return 'error'
}

// 定时刷新
let refreshTimer = null

onMounted(() => {
  fetchRecordingStatus()
  fetchRecordingHistory()
  fetchAvailableVideos()
  
  refreshTimer = setInterval(() => {
    fetchRecordingStatus()
    fetchRecordingHistory()
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.video-recording-panel {
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

/* 模式切换 */
.mode-switch {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 0 10px;
}

.mode-help {
  color: #64748b;
  cursor: help;
}

/* 信息提示 */
.info-alert {
  margin-bottom: 16px;
}

/* 录制设置 */
.recording-section {
  padding: 0 10px;
}

.form-hint {
  margin-left: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.slider-value {
  margin-left: 10px;
  color: #e2e8f0;
  font-weight: 500;
}

.directory-input {
  display: flex;
  gap: 8px;
}

/* 最新视频列表 */
.latest-videos {
  margin-top: 16px;
}

.video-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.video-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 6px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.3s;
}

.video-item:hover {
  background: rgba(51, 65, 85, 0.5);
}

.video-item.selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.video-name {
  flex: 1;
  font-size: 13px;
  color: #e2e8f0;
}

/* 模拟模式 */
.simulation-section {
  padding: 0 10px;
}

.directory-browser {
  margin-bottom: 16px;
}

.video-browser {
  margin-top: 16px;
}

.channel-tabs {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.channel-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.channel-title {
  width: 50px;
  font-size: 13px;
  font-weight: 500;
  color: #94a3b8;
}

.video-select {
  flex: 1;
}

.video-time {
  float: right;
  color: #64748b;
  font-size: 11px;
}

/* 诊断控制 */
.diagnosis-control {
  margin-top: 20px;
  padding: 0 10px;
}

.control-buttons {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.progress-section {
  padding: 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
}

.progress-detail {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 12px;
  color: #94a3b8;
}

/* 诊断结果 */
.result-section {
  margin-top: 16px;
}

.result-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-detail {
  margin-top: 8px;
  font-size: 13px;
  color: #94a3b8;
}

.result-detail p {
  margin: 4px 0;
}

.result-action {
  margin-top: 12px;
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
