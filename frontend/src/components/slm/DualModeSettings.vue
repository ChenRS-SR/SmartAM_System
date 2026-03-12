<template>
  <div class="dual-mode-settings dark-theme">
    <el-form label-width="100px" size="small">
      <!-- 场景选择 -->
      <el-form-item label="场景">
        <el-select v-model="selectedFolder" placeholder="选择场景" @change="onFolderChange">
          <el-option label="正常打印 (Normal)" value="normal" />
          <el-option label="欠功率 (Underpower)" value="scene_underpower" />
          <el-option label="过功率 (Overpower)" value="scene_overpower" />
        </el-select>
      </el-form-item>

      <!-- 播放模式选择 -->
      <el-form-item label="播放模式">
        <el-radio-group v-model="playMode" @change="onModeChange">
          <el-radio-button label="preprocessed">
            <el-icon><VideoPlay /></el-icon>
            预处理模式
          </el-radio-button>
          <el-radio-button label="realtime">
            <el-icon><Cpu /></el-icon>
            实时处理
          </el-radio-button>
        </el-radio-group>
      </el-form-item>

      <!-- 预处理模式说明 -->
      <el-alert
        v-if="playMode === 'preprocessed'"
        type="success"
        :closable="false"
        class="mode-info"
        effect="dark"
      >
        <template #title>
          <strong>预处理模式（推荐）</strong>
        </template>
        <div class="info-content">
          <p>提前完成畸变矫正和视角调整</p>
          <p>流畅播放，零实时计算</p>
          <p>适合正式演示</p>
        </div>
      </el-alert>

      <!-- 实时模式说明 -->
      <el-alert
        v-else
        type="warning"
        :closable="false"
        class="mode-info"
        effect="dark"
      >
        <template #title>
          <strong>实时处理模式</strong>
        </template>
        <div class="info-content">
          <p>实时畸变矫正和视角调整</p>
          <p>GPU负载较高，可能卡顿</p>
          <p>可调参数，适合调试和标定</p>
        </div>
      </el-alert>

      <!-- 帧率设置 -->
      <el-form-item label="播放帧率">
        <el-slider v-model="fps" :min="1" :max="30" :step="1" show-stops />
        <span class="fps-value">{{ fps }} FPS</span>
      </el-form-item>

      <!-- 预处理状态 -->
      <el-form-item v-if="playMode === 'preprocessed'" label="预处理状态">
        <div class="preprocess-status">
          <el-tag v-if="preprocessStatus.allProcessed" type="success" effect="dark">
            <el-icon><Check /></el-icon> 已完成
          </el-tag>
          <el-tag v-else-if="preprocessStatus.anyProcessed" type="warning" effect="dark">
            <el-icon><Warning /></el-icon> 部分完成
          </el-tag>
          <el-tag v-else type="info" effect="dark">
            <el-icon><InfoFilled /></el-icon> 未处理
          </el-tag>
          
          <el-button 
            v-if="!preprocessStatus.allProcessed"
            type="primary" 
            size="small"
            :loading="isPreprocessing"
            @click="runPreprocess"
          >
            <el-icon><Refresh /></el-icon>
            {{ isPreprocessing ? '处理中...' : '开始预处理' }}
          </el-button>
          
          <el-button
            v-else
            type="warning"
            size="small"
            :loading="isPreprocessing"
            @click="runPreprocess(true)"
          >
            <el-icon><RefreshRight /></el-icon>
            重新处理
          </el-button>
        </div>
      </el-form-item>

      <!-- 实时模式选项 -->
      <template v-if="playMode === 'realtime'">
        <el-form-item label="畸变矫正">
          <el-switch v-model="enableCorrection" active-text="启用" />
        </el-form-item>
        
        <el-form-item label="标定文件">
          <el-input v-model="calibrationPath" placeholder="标定文件路径">
            <template #append>
              <el-button @click="selectCalibrationFile">
                <el-icon><Folder /></el-icon>
              </el-button>
            </template>
          </el-input>
        </el-form-item>
      </template>

      <!-- 操作按钮 -->
      <el-form-item>
        <el-button type="primary" @click="applySettings" :loading="isApplying">
          <el-icon><Check /></el-icon>
          应用设置
        </el-button>
        <el-button @click="resetSettings">
          <el-icon><RefreshLeft /></el-icon>
          重置
        </el-button>
      </el-form-item>
    </el-form>

    <!-- 通道状态 -->
    <el-divider class="dark-divider">通道状态</el-divider>
    <div class="channel-status">
      <div v-for="(status, ch) in channelStatus" :key="ch" class="channel-item">
        <span class="channel-name">{{ ch }}</span>
        <el-tag v-if="status.processed" size="small" type="success" effect="dark">已预处理</el-tag>
        <el-tag v-else-if="status.original" size="small" type="info" effect="dark">原始视频</el-tag>
        <el-tag v-else size="small" type="danger" effect="dark">未找到</el-tag>
      </div>
    </div>

    <!-- 预处理进度对话框 -->
    <el-dialog
      v-model="showProgressDialog"
      title="视频预处理"
      width="500px"
      :close-on-click-modal="false"
      :show-close="!isPreprocessing"
      class="dark-dialog"
    >
      <div class="progress-content">
        <el-progress 
          :percentage="preprocessProgress" 
          :status="preprocessStatusText"
        />
        <p class="progress-message">{{ preprocessMessage }}</p>
        <el-input
          v-model="preprocessLog"
          type="textarea"
          :rows="8"
          readonly
          class="progress-log"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  VideoPlay, Cpu, Check, Warning, InfoFilled,
  Refresh, RefreshRight, RefreshLeft, Folder
} from '@element-plus/icons-vue'
import axios from 'axios'

const props = defineProps({
  initialFolder: { type: String, default: 'normal' },
  initialFps: { type: Number, default: 10 }
})

const emit = defineEmits(['settings-applied', 'mode-changed'])

// 状态
const selectedFolder = ref(props.initialFolder)
const playMode = ref('preprocessed')
const fps = ref(props.initialFps)
const enableCorrection = ref(false)
const calibrationPath = ref('')
const isPreprocessing = ref(false)
const isApplying = ref(false)
const showProgressDialog = ref(false)
const preprocessProgress = ref(0)
const preprocessStatusText = ref('')
const preprocessMessage = ref('')
const preprocessLog = ref('')

// 预处理状态
const preprocessStatus = ref({
  allProcessed: false,
  anyProcessed: false,
  channels: {}
})

// 通道状态
const channelStatus = ref({
  CH1: { processed: false, original: false },
  CH2: { processed: false, original: false },
  CH3: { processed: false, original: false }
})

// 方法
const fetchPreprocessStatus = async () => {
  try {
    const response = await axios.get(
      `/api/slm/video_file_mode/preprocess/status?folder=${selectedFolder.value}`
    )
    
    if (response.data.success) {
      preprocessStatus.value = {
        allProcessed: response.data.is_processed,
        anyProcessed: Object.values(response.data.channels).some(c => c.processed),
        channels: response.data.channels
      }
      
      for (const [ch, info] of Object.entries(response.data.channels)) {
        channelStatus.value[ch] = {
          processed: info.processed,
          original: info.original_exists
        }
      }
    }
  } catch (error) {
    console.error('获取预处理状态失败:', error)
  }
}

const runPreprocess = async (force = false) => {
  isPreprocessing.value = true
  showProgressDialog.value = true
  preprocessProgress.value = 0
  preprocessStatusText.value = ''
  preprocessMessage.value = '正在启动预处理...'
  preprocessLog.value = ''
  
  try {
    const response = await axios.post('/api/slm/video_file_mode/preprocess', {
      folder: selectedFolder.value,
      fps: fps.value,
      force: force
    })
    
    const result = response.data
    
    if (result.success) {
      preprocessProgress.value = 100
      preprocessStatusText.value = 'success'
      preprocessMessage.value = '预处理完成！'
      preprocessLog.value = result.output || '处理成功'
      ElMessage.success('视频预处理完成')
      await fetchPreprocessStatus()
    } else {
      preprocessProgress.value = 0
      preprocessStatusText.value = 'exception'
      preprocessMessage.value = '预处理失败'
      preprocessLog.value = result.message
      ElMessage.error(result.message)
    }
  } catch (error) {
    preprocessProgress.value = 0
    preprocessStatusText.value = 'exception'
    preprocessMessage.value = '预处理出错'
    preprocessLog.value = error.message
    ElMessage.error('预处理请求失败')
  } finally {
    isPreprocessing.value = false
  }
}

const applySettings = async () => {
  isApplying.value = true
  
  try {
    if (playMode.value === 'preprocessed' && !preprocessStatus.value.allProcessed) {
      ElMessage.warning('请先完成视频预处理')
      isApplying.value = false
      return
    }
    
    // 1. 扫描视频文件
    const scanResponse = await axios.get(`/api/slm/video_file_mode/scan?folder=${selectedFolder.value}`)
    if (!scanResponse.data.success || Object.keys(scanResponse.data.videos).length === 0) {
      ElMessage.error('未找到视频文件')
      isApplying.value = false
      return
    }
    
    // 2. 设置视频文件模式（只使用旧的API，与采集系统集成）
    const videoFiles = {}
    for (const [ch, info] of Object.entries(scanResponse.data.videos)) {
      videoFiles[ch] = info.path
    }
    
    const setupResponse = await axios.post('/api/slm/video_file_mode/setup', {
      video_files: videoFiles,
      enable_correction: false
    })
    
    if (!setupResponse.data.success) {
      ElMessage.error(setupResponse.data.message || '设置视频文件模式失败')
      isApplying.value = false
      return
    }
    
    // 3. 设置帧率
    await axios.post('/api/slm/video_file_mode/fps', null, {
      params: { fps: fps.value }
    })
    
    ElMessage.success('设置已应用，请在仪表盘点击"刷新状态"开始播放')
    emit('settings-applied', {
      mode: playMode.value,
      folder: selectedFolder.value,
      fps: fps.value,
      videoFiles: videoFiles
    })
  } catch (error) {
    console.error('应用设置失败:', error)
    ElMessage.error('应用设置失败: ' + (error.response?.data?.message || error.message))
  } finally {
    isApplying.value = false
  }
}

const resetSettings = () => {
  selectedFolder.value = props.initialFolder
  playMode.value = 'preprocessed'
  fps.value = props.initialFps
  enableCorrection.value = false
  calibrationPath.value = ''
}

const onFolderChange = () => {
  fetchPreprocessStatus()
  // 立即通知父组件场景变化
  emit('settings-applied', {
    mode: playMode.value,
    folder: selectedFolder.value,
    fps: fps.value
  })
}

const onModeChange = () => {
  emit('mode-changed', playMode.value)
}

const selectCalibrationFile = () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = (e) => {
    const file = e.target.files[0]
    if (file) {
      calibrationPath.value = file.path || file.name
    }
  }
  input.click()
}

onMounted(() => {
  fetchPreprocessStatus()
})
</script>

<style scoped>
.dark-theme {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --bg-tertiary: #0f3460;
  --text-primary: #eaeaea;
  --text-secondary: #a0a0a0;
}

.dual-mode-settings {
  padding: 10px;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.mode-info { margin: 10px 0; }

.info-content {
  font-size: 12px;
  line-height: 1.6;
}

.info-content p { margin: 4px 0; }

.fps-value {
  margin-left: 10px;
  color: var(--text-secondary);
}

.preprocess-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dark-divider :deep(.el-divider__text) {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.channel-status {
  display: flex;
  gap: 20px;
  justify-content: center;
}

.channel-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.channel-name {
  font-weight: bold;
  color: var(--text-primary);
}

.progress-content { padding: 20px; }

.progress-message {
  margin: 15px 0;
  color: var(--text-secondary);
  text-align: center;
}

.progress-log {
  font-family: monospace;
  font-size: 12px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.progress-log :deep(.el-textarea__inner) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

:deep(.dark-dialog) {
  background: var(--bg-secondary);
}

:deep(.dark-dialog .el-dialog__header) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

:deep(.dark-dialog .el-dialog__body) {
  background: var(--bg-secondary);
  color: var(--text-primary);
}
</style>
