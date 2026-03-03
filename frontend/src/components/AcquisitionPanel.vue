<template>
  <div class="acquisition-panel">
    <el-card class="panel-card">
      <template #header>
        <div class="card-header">
          <span>{{ $t('acquisition.title') }}</span>
          <el-tag :type="statusType">{{ statusText }}</el-tag>
        </div>
      </template>
      
      <!-- 状态显示 -->
      <div class="status-info" v-if="status">
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="status-item">
              <span class="label">{{ $t('acquisition.frameCount') }}:</span>
              <span class="value">{{ status.frame_count || 0 }}</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="status-item">
              <span class="label">{{ $t('acquisition.duration') }}:</span>
              <span class="value">{{ formatDuration(status.duration || 0) }}</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="status-item">
              <span class="label">{{ $t('acquisition.fps') }}:</span>
              <span class="value">{{ status.fps || config.capture_fps }}</span>
            </div>
          </el-col>
        </el-row>
        
        <div class="save-path" v-if="status.save_directory">
          <span class="label">{{ $t('acquisition.savePath') }}:</span>
          <el-tooltip :content="status.save_directory" placement="top">
            <span class="value path">{{ status.save_directory }}</span>
          </el-tooltip>
        </div>
      </div>
      
      <!-- 配置区域 -->
      <div class="config-section" v-if="!isRunning">
        <el-divider>{{ $t('acquisition.settings') }}</el-divider>
        
        <!-- 保存路径 -->
        <el-form-item :label="$t('acquisition.saveDirectory')">
          <el-input
            v-model="config.save_directory"
            :placeholder="$t('acquisition.saveDirectoryPlaceholder')"
          >
            <template #append>
              <el-button @click="selectDirectory">
                <el-icon><Folder /></el-icon>
              </el-button>
            </template>
          </el-input>
        </el-form-item>
        
        <!-- 采集帧率 -->
        <el-form-item :label="$t('acquisition.frameRate')">
          <el-slider
            v-model="config.capture_fps"
            :min="1"
            :max="30"
            :step="1"
            show-stops
            show-input
          />
          <div class="fps-hint">
            {{ $t('acquisition.frameRateHint', { interval: (1000/config.capture_fps).toFixed(0) }) }}
          </div>
        </el-form-item>
        
        <!-- 设备选择 -->
        <el-form-item :label="$t('acquisition.devices')">
          <el-checkbox-group v-model="selectedDevices">
            <el-checkbox label="ids">IDS {{ $t('acquisition.camera') }}</el-checkbox>
            <el-checkbox label="side">{{ $t('acquisition.sideCamera') }}</el-checkbox>
            <el-checkbox label="fotric">Fotric {{ $t('acquisition.thermalCamera') }}</el-checkbox>
            <el-checkbox label="vibration">{{ $t('acquisition.vibrationSensor') }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <!-- OctoPrint 配置 -->
        <el-form-item :label="$t('acquisition.octoprintUrl')">
          <el-input
            v-model="config.octoprint_url"
            :placeholder="$t('acquisition.octoprintUrlPlaceholder')"
          />
        </el-form-item>
        
        <el-form-item :label="$t('acquisition.octoprintApiKey')">
          <el-input
            v-model="config.octoprint_api_key"
            type="password"
            show-password
            :placeholder="$t('acquisition.octoprintApiKeyPlaceholder')"
          />
        </el-form-item>
        
        <!-- 采集模式选择 -->
        <el-divider>{{ $t('acquisition.acquisitionMode') }}</el-divider>
        
        <el-form-item :label="$t('acquisition.paramMode')">
          <el-radio-group v-model="config.param_mode" :disabled="isRunning">
            <el-radio value="fixed">{{ $t('acquisition.modeFixed') }}</el-radio>
            <el-radio value="random">{{ $t('acquisition.modeRandom') }}</el-radio>
            <el-radio value="tower">{{ $t('acquisition.modeTower') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <!-- 随机模式配置 -->
        <div v-if="config.param_mode === 'random'" class="mode-config">
          <el-form-item :label="$t('acquisition.randomInterval')">
            <el-input-number
              v-model="config.random_interval_sec"
              :min="30"
              :max="600"
              :step="10"
              style="width: 150px"
            />
            <span class="unit">{{ $t('acquisition.seconds') }}</span>
          </el-form-item>
          <div class="param-hint">{{ $t('acquisition.randomIntervalHint') }}</div>
        </div>
        
        <!-- 标准塔模式配置 -->
        <div v-if="config.param_mode === 'tower'" class="mode-config">
          <el-form-item :label="$t('acquisition.currentTower')">
            <el-select v-model="config.current_tower" style="width: 200px">
              <el-option 
                v-for="tower in towerOptions" 
                :key="tower.id" 
                :label="tower.label" 
                :value="tower.id"
              />
            </el-select>
          </el-form-item>
          <div class="tower-info" v-if="selectedTowerInfo">
            <div class="tower-desc">{{ selectedTowerInfo.description }}</div>
            <div class="tower-params">
              T={{ selectedTowerInfo.hotend_temp }}°C, 
              Z={{ selectedTowerInfo.z_offset }}mm
            </div>
          </div>
        </div>
        
        <!-- 时空同步缓冲配置 -->
        <el-divider>{{ $t('acquisition.syncBuffer') }}</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item :label="$t('acquisition.stabilityZDiff')">
              <el-input-number
                v-model="config.stability_z_diff_mm"
                :min="0.1"
                :max="2.0"
                :step="0.1"
                style="width: 120px"
              />
              <span class="unit">mm</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('acquisition.silentHeight')">
              <el-input-number
                v-model="config.silent_height_mm"
                :min="0.5"
                :max="3.0"
                :step="0.1"
                style="width: 120px"
              />
              <span class="unit">mm</span>
            </el-form-item>
          </el-col>
        </el-row>
        
        <div class="param-hint">{{ $t('acquisition.syncBufferHint') }}</div>
        
        <!-- 打印参数 (用于计算class) -->
        <el-divider>{{ $t('acquisition.printParams') }}</el-divider>
        
        <!-- 初始Z补偿配置 -->
        <el-form-item :label="$t('acquisition.initialZOffset')">
          <el-input-number
            v-model="config.initial_z_offset"
            :min="-5"
            :max="5"
            :step="0.01"
            style="width: 100%"
            :disabled="isRunning || config.param_mode === 'tower'"
          />
          <div class="param-hint">{{ $t('acquisition.initialZOffsetHint') }}</div>
        </el-form-item>
        
        <!-- 当前参数显示和编辑 -->
        <div class="current-params-section" v-if="isRunning || isPaused">
          <div class="section-title">{{ $t('acquisition.currentParams') }}</div>
          <el-row :gutter="20">
            <el-col :span="12">
              <div class="param-display">
                <span class="param-label">{{ $t('acquisition.flowRate') }}:</span>
                <span class="param-value" :class="getParamClass('flow_rate')">{{ currentParams.flow_rate }}%</span>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="param-display">
                <span class="param-label">{{ $t('acquisition.feedRate') }}:</span>
                <span class="param-value" :class="getParamClass('feed_rate')">{{ currentParams.feed_rate }}%</span>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="20" style="margin-top: 10px;">
            <el-col :span="12">
              <div class="param-display">
                <span class="param-label">{{ $t('acquisition.zOffset') }}:</span>
                <span class="param-value" :class="getParamClass('z_offset')">{{ currentParams.z_offset }}mm</span>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="param-display">
                <span class="param-label">{{ $t('acquisition.targetHotend') }}:</span>
                <span class="param-value" :class="getParamClass('hotend')">{{ currentParams.target_hotend }}°C</span>
              </div>
            </el-col>
          </el-row>
          
          <!-- 标准塔当前区间信息 -->
          <div v-if="config.param_mode === 'tower' && currentSegmentInfo" class="segment-info">
            <el-divider content-position="left">{{ $t('acquisition.currentSegment') }}</el-divider>
            <div class="segment-detail">
              <div>{{ currentSegmentInfo.height_range }}: {{ currentSegmentInfo.description }}</div>
              <div>F={{ currentSegmentInfo.feed_rate }}%, E={{ currentSegmentInfo.flow_rate }}%</div>
            </div>
          </div>
        </div>
        
        <!-- 参数调节 (固定模式) -->
        <template v-if="config.param_mode === 'fixed'">
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="$t('acquisition.flowRate')">
                <el-input-number
                  v-model="config.flow_rate"
                  :min="20"
                  :max="200"
                  :step="1"
                  style="width: 100%"
                  @change="onParamChange"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="$t('acquisition.feedRate')">
                <el-input-number
                  v-model="config.feed_rate"
                  :min="20"
                  :max="200"
                  :step="1"
                  style="width: 100%"
                  @change="onParamChange"
                />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item :label="$t('acquisition.zOffset')">
                <el-input-number
                  v-model="config.z_offset"
                  :min="-0.5"
                  :max="0.5"
                  :step="0.01"
                  style="width: 100%"
                  @change="onParamChange"
                />
              </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('acquisition.targetHotend')">
              <el-input-number
                v-model="config.target_hotend"
                :min="150"
                :max="260"
                :step="1"
                style="width: 100%"
                @change="onParamChange"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 回正参数按钮 -->
        <el-form-item>
          <el-button 
            type="primary" 
            @click="resetParams"
            :disabled="!isRunning && !isPaused"
          >
            <el-icon><Refresh /></el-icon>
            {{ $t('acquisition.resetParams') }}
          </el-button>
        </el-form-item>
        </template>
      </div>
      
      <!-- 控制按钮 -->
      <div class="control-buttons">
        <el-button
          v-if="!isRunning && !isPaused"
          type="primary"
          size="large"
          :loading="isLoading"
          @click="startAcquisition"
          :disabled="!canStart"
        >
          <el-icon><VideoPlay /></el-icon>
          {{ $t('acquisition.start') }}
        </el-button>
        
        <template v-else-if="isRunning">
          <el-button
            type="warning"
            size="large"
            @click="pauseAcquisition"
            :loading="isLoading"
          >
            <el-icon><VideoPause /></el-icon>
            {{ $t('acquisition.pause') }}
          </el-button>
          
          <el-button
            type="danger"
            size="large"
            @click="stopAcquisition"
            :loading="isLoading"
          >
            <el-icon><CircleClose /></el-icon>
            {{ $t('acquisition.stop') }}
          </el-button>
        </template>
        
        <template v-else-if="isPaused">
          <el-button
            type="success"
            size="large"
            @click="resumeAcquisition"
            :loading="isLoading"
          >
            <el-icon><VideoPlay /></el-icon>
            {{ $t('acquisition.resume') }}
          </el-button>
          
          <el-button
            type="danger"
            size="large"
            @click="stopAcquisition"
            :loading="isLoading"
          >
            <el-icon><CircleClose /></el-icon>
            {{ $t('acquisition.stop') }}
          </el-button>
        </template>
      </div>
      
      <!-- 提示信息 -->
      <el-alert
        v-if="message"
        :title="message"
        :type="messageType"
        :closable="false"
        show-icon
        class="message-alert"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, VideoPause, CircleClose, Folder, Refresh } from '@element-plus/icons-vue'
import axios from 'axios'

const { t } = useI18n()

// 状态
const status = ref({})
const isLoading = ref(false)
const message = ref('')
const messageType = ref('info')
const statusTimer = ref(null)

// 配置
const config = ref({
  save_directory: './data',
  capture_fps: 2,  // 默认2Hz (标准数据集要求)
  octoprint_url: 'http://127.0.0.1:5000',
  octoprint_api_key: '',
  // 打印参数 (用于生成CSV中的class列)
  flow_rate: 100,        // 默认流量百分比
  feed_rate: 100,        // 默认进给百分比
  z_offset: 0.0,         // 默认Z偏移(相对于初始补偿的调节值)
  target_hotend: 200,    // 默认目标热端温度
  // 初始Z补偿(打印机调平后的基准值，只发送一次)
  initial_z_offset: -2.55,
  // 参数模式: fixed/random/tower
  param_mode: 'fixed',
  // 随机模式配置
  random_interval_sec: 120,
  // 标准塔模式配置
  current_tower: 1,
  // 时空同步缓冲配置
  stability_z_diff_mm: 0.6,  // 参数变化后Z轴变化多少mm开始采集
  silent_height_mm: 1.0      // 参数变化后静默区高度
})

// 当前参数(采集运行中显示)
const currentParams = ref({
  flow_rate: 100,
  feed_rate: 100,
  z_offset: 0.0,
  target_hotend: 200
})

// 当前区间信息(标准塔模式)
const currentSegmentInfo = ref(null)

const selectedDevices = ref(['ids', 'side', 'fotric'])

// 9组标准塔选项
const towerOptions = [
  { id: 1, label: 'Tower 1: 185°C / -0.15mm (LL)' },
  { id: 2, label: 'Tower 2: 185°C / 0.00mm (LN)' },
  { id: 3, label: 'Tower 3: 185°C / +0.25mm (LH)' },
  { id: 4, label: 'Tower 4: 215°C / -0.15mm (NL)' },
  { id: 5, label: 'Tower 5: 215°C / 0.00mm (NN) - 黄金样本' },
  { id: 6, label: 'Tower 6: 215°C / +0.25mm (NH)' },
  { id: 7, label: 'Tower 7: 245°C / -0.15mm (HL)' },
  { id: 8, label: 'Tower 8: 245°C / 0.00mm (HN)' },
  { id: 9, label: 'Tower 9: 245°C / +0.25mm (HH)' }
]

// 塔详细信息
const towerDetails = {
  1: { hotend_temp: 185, z_offset: -0.15, description: '低温+压头，高风险易堵头' },
  2: { hotend_temp: 185, z_offset: 0.00, description: '低温，层间结合差' },
  3: { hotend_temp: 185, z_offset: 0.25, description: '低温+远离，易脱落' },
  4: { hotend_temp: 215, z_offset: -0.15, description: '正常温+压头，表面波浪纹' },
  5: { hotend_temp: 215, z_offset: 0.00, description: '黄金样本（标准态）' },
  6: { hotend_temp: 215, z_offset: 0.25, description: '正常温+远离，层间缝隙' },
  7: { hotend_temp: 245, z_offset: -0.15, description: '高温+压头，严重溢料' },
  8: { hotend_temp: 245, z_offset: 0.00, description: '高温，拉丝多' },
  9: { hotend_temp: 245, z_offset: 0.25, description: '高温+远离，结构松散' }
}

// 选中塔的详细信息
const selectedTowerInfo = computed(() => {
  return towerDetails[config.value.current_tower]
})

// 计算属性
const isRunning = computed(() => status.value?.state === 'running')
const isPaused = computed(() => status.value?.state === 'paused')
const isIdle = computed(() => status.value?.state === 'idle')

const statusType = computed(() => {
  switch (status.value?.state) {
    case 'running': return 'success'
    case 'paused': return 'warning'
    case 'stopping': return 'danger'
    default: return 'info'
  }
})

const statusText = computed(() => {
  switch (status.value?.state) {
    case 'running': return t('acquisition.status.running')
    case 'paused': return t('acquisition.status.paused')
    case 'stopping': return t('acquisition.status.stopping')
    default: return t('acquisition.status.idle')
  }
})

const canStart = computed(() => {
  return config.value.save_directory && selectedDevices.value.length > 0
})

// 方法
const formatDuration = (seconds) => {
  const hrs = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const selectDirectory = async () => {
  // 由于浏览器安全限制，无法直接选择本地目录
  // 这里提供一个输入框让用户手动输入或使用默认路径
  ElMessageBox.prompt(
    t('acquisition.enterSavePath'),
    t('acquisition.selectDirectory'),
    {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      inputValue: config.value.save_directory
    }
  ).then(({ value }) => {
    config.value.save_directory = value
  }).catch(() => {})
}

const showMessage = (msg, type = 'info') => {
  message.value = msg
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 5000)
}

// 获取参数分类样式
const getParamClass = (param) => {
  const value = currentParams.value[param]
  // 阈值配置(与后端保持一致)
  const thresholds = {
    flow_rate: [90, 110],      // <90为低, 90-110为正常, >110为高
    feed_rate: [80, 120],      // <80为低, 80-120为正常, >120为高
    z_offset: [-0.05, 0.15],   // <-0.05为低, -0.05~0.15为正常, >0.15为高
    hotend: [200, 230]         // <200为低, 200-230为正常, >230为高
  }
  const [low, high] = thresholds[param] || [0, 100]
  if (value <= low) return 'param-low'
  if (value > high) return 'param-high'
  return 'param-normal'
}

// 参数变化时发送到后端
const onParamChange = async () => {
  if (!isRunning.value && !isPaused.value) return
  
  try {
    // 更新当前参数显示
    currentParams.value = {
      flow_rate: config.value.flow_rate,
      feed_rate: config.value.feed_rate,
      z_offset: config.value.z_offset,
      target_hotend: config.value.target_hotend
    }
    
    // 发送到后端
    await axios.post('/api/acquisition/params', {
      flow_rate: config.value.flow_rate,
      feed_rate: config.value.feed_rate,
      z_offset: config.value.z_offset,
      target_hotend: config.value.target_hotend
    })
  } catch (error) {
    console.error('更新参数失败:', error)
  }
}

// 回正参数(恢复到默认值)
const resetParams = async () => {
  try {
    // 设置默认值
    config.value.flow_rate = 100
    config.value.feed_rate = 100
    config.value.z_offset = 0.0
    config.value.target_hotend = 200
    
    // 更新当前参数显示
    currentParams.value = {
      flow_rate: 100,
      feed_rate: 100,
      z_offset: 0.0,
      target_hotend: 200
    }
    
    // 发送到后端
    await axios.post('/api/acquisition/params', {
      flow_rate: 100,
      feed_rate: 100,
      z_offset: 0.0,
      target_hotend: 200
    })
    
    showMessage(t('acquisition.msg.paramsReset'), 'success')
    ElMessage.success(t('acquisition.msg.paramsReset'))
  } catch (error) {
    console.error('回正参数失败:', error)
    showMessage(t('acquisition.msg.resetFailed'), 'error')
  }
}

const startAcquisition = async () => {
  try {
    isLoading.value = true
    
    // 标准塔模式：提示是否采集标准数据集
    if (config.value.param_mode === 'tower') {
      const towerInfo = towerDetails[config.value.current_tower]
      const confirmMsg = t('acquisition.standardDatasetConfirm', {
        towerId: config.value.current_tower,
        temp: towerInfo.hotend_temp,
        zoff: towerInfo.z_offset
      })
      
      const confirmed = await ElMessageBox.confirm(
        confirmMsg,
        t('acquisition.standardDatasetTitle'),
        {
          confirmButtonText: t('acquisition.startStandardDataset'),
          cancelButtonText: t('common.cancel'),
          type: 'info',
          closeOnClickModal: false
        }
      ).catch(() => false)
      
      if (!confirmed) {
        isLoading.value = false
        return
      }
    }
    
    // 先发送配置
    await axios.post('/api/acquisition/config', {
      save_directory: config.value.save_directory,
      capture_fps: config.value.capture_fps,
      enable_ids: selectedDevices.value.includes('ids'),
      enable_side_camera: selectedDevices.value.includes('side'),
      enable_fotric: selectedDevices.value.includes('fotric'),
      enable_vibration: selectedDevices.value.includes('vibration'),
      octoprint_url: config.value.octoprint_url,
      octoprint_api_key: config.value.octoprint_api_key,
      // 打印参数
      flow_rate: config.value.flow_rate,
      feed_rate: config.value.feed_rate,
      z_offset: config.value.z_offset,
      target_hotend: config.value.target_hotend,
      // 初始Z补偿(只发送一次，用于计算实际M290值)
      initial_z_offset: config.value.initial_z_offset,
      // 参数模式配置
      param_mode: config.value.param_mode,
      random_interval_sec: config.value.random_interval_sec,
      current_tower: config.value.current_tower,
      // 时空同步缓冲配置
      stability_z_diff_mm: config.value.stability_z_diff_mm,
      silent_height_mm: config.value.silent_height_mm
    })
    
    // 更新当前参数显示
    currentParams.value = {
      flow_rate: config.value.flow_rate,
      feed_rate: config.value.feed_rate,
      z_offset: config.value.z_offset,
      target_hotend: config.value.target_hotend
    }
    
    // 开始采集
    const response = await axios.post('/api/acquisition/start')
    
    if (response.data.success) {
      status.value = response.data.data
      showMessage(t('acquisition.msg.started'), 'success')
      ElMessage.success(t('acquisition.msg.started'))
    } else {
      showMessage(response.data.message, 'error')
      ElMessage.error(response.data.message)
    }
  } catch (error) {
    console.error('开始采集失败:', error)
    showMessage(t('acquisition.msg.startFailed'), 'error')
    ElMessage.error(t('acquisition.msg.startFailed'))
  } finally {
    isLoading.value = false
  }
}

const pauseAcquisition = async () => {
  try {
    isLoading.value = true
    const response = await axios.post('/api/acquisition/pause')
    
    if (response.data.success) {
      status.value = response.data.data
      showMessage(t('acquisition.msg.paused'), 'success')
      ElMessage.success(t('acquisition.msg.paused'))
    } else {
      showMessage(response.data.message, 'warning')
    }
  } catch (error) {
    console.error('暂停采集失败:', error)
    showMessage(t('acquisition.msg.pauseFailed'), 'error')
  } finally {
    isLoading.value = false
  }
}

const resumeAcquisition = async () => {
  try {
    isLoading.value = true
    const response = await axios.post('/api/acquisition/resume')
    
    if (response.data.success) {
      status.value = response.data.data
      showMessage(t('acquisition.msg.resumed'), 'success')
      ElMessage.success(t('acquisition.msg.resumed'))
    } else {
      showMessage(response.data.message, 'warning')
    }
  } catch (error) {
    console.error('恢复采集失败:', error)
    showMessage(t('acquisition.msg.resumeFailed'), 'error')
  } finally {
    isLoading.value = false
  }
}

const stopAcquisition = async () => {
  try {
    const confirmed = await ElMessageBox.confirm(
      t('acquisition.confirmStop'),
      t('common.warning'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    ).catch(() => false)
    
    if (!confirmed) return
    
    isLoading.value = true
    const response = await axios.post('/api/acquisition/stop')
    
    if (response.data.success) {
      status.value = response.data.data
      showMessage(t('acquisition.msg.stopped'), 'success')
      ElMessage.success(t('acquisition.msg.stopped'))
    } else {
      showMessage(response.data.message, 'warning')
    }
  } catch (error) {
    console.error('停止采集失败:', error)
    showMessage(t('acquisition.msg.stopFailed'), 'error')
  } finally {
    isLoading.value = false
  }
}

const fetchStatus = async () => {
  try {
    const response = await axios.get('/api/acquisition/status')
    if (response.data.success) {
      status.value = response.data.data
      
      // 更新当前参数显示
      if (response.data.data.current_params) {
        currentParams.value = response.data.data.current_params
      }
      
      // 更新当前区间信息(标准塔模式)
      if (response.data.data.current_segment) {
        currentSegmentInfo.value = response.data.data.current_segment
      }
    }
  } catch (error) {
    console.error('获取状态失败:', error)
  }
}

// 生命周期
onMounted(() => {
  fetchStatus()
  // 定时刷新状态
  statusTimer.value = setInterval(fetchStatus, 1000)
})

onUnmounted(() => {
  if (statusTimer.value) {
    clearInterval(statusTimer.value)
  }
})
</script>

<style scoped>
.acquisition-panel {
  margin: 20px 0;
}

.panel-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.status-info {
  margin-bottom: 20px;
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.status-item .label {
  font-size: 12px;
  color: var(--text-secondary);
}

.status-item .value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.save-path {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 10px;
}

.save-path .label {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.save-path .value.path {
  font-size: 12px;
  color: var(--text-primary);
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
}

.config-section {
  margin: 20px 0;
}

.fps-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 5px;
}

.control-buttons {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.control-buttons .el-button {
  min-width: 120px;
}

.message-alert {
  margin-top: 15px;
}

:deep(.el-form-item__label) {
  color: var(--text-primary);
}

/* 参数显示区域 */
.current-params-section {
  margin: 15px 0;
  padding: 15px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border-left: 4px solid var(--el-color-primary);
}

.section-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 10px;
  color: var(--text-primary);
}

.param-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.param-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.param-value {
  font-size: 14px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.param-value.param-low {
  background: #fdf6ec;
  color: #e6a23c;
}

.param-value.param-normal {
  background: #f0f9ff;
  color: #67c23a;
}

.param-value.param-high {
  background: #fef0f0;
  color: #f56c6c;
}

.param-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 5px;
}

:deep(.el-checkbox__label) {
  color: var(--text-primary);
}
</style>
