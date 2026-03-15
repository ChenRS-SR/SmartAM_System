<template>
  <div class="roi-config-panel">
    <div class="panel-header">
      <span class="panel-title">📍 ROI区域配置</span>
      <el-tag v-if="hasConfig" type="success" size="small" effect="dark">已配置</el-tag>
      <el-tag v-else type="info" size="small" effect="dark">未配置</el-tag>
    </div>
    
    <!-- 配置文件选择 -->
    <div class="config-section">
      <div class="section-label">配置文件</div>
      <div class="file-input-row">
        <el-input 
          v-model="configFilePath" 
          placeholder="选择ROI配置文件 (JSON)"
          readonly
          size="small"
        >
          <template #append>
            <el-button @click="selectConfigFile">
              <el-icon><Folder /></el-icon>
            </el-button>
          </template>
        </el-input>
        <el-button 
          type="primary" 
          size="small" 
          @click="loadConfig"
          :loading="isLoading"
          :disabled="!configFilePath"
        >
          加载
        </el-button>
      </div>
      <div class="file-hint">
        支持JSON格式，定义ROI区域位置和要计算的特征
      </div>
    </div>
    
    <!-- ROI区域列表 -->
    <div v-if="rois.length > 0" class="roi-list-section">
      <div class="section-label">已定义区域 ({{ rois.length }})</div>
      <div class="roi-list">
        <div 
          v-for="roi in rois" 
          :key="roi.id"
          class="roi-item"
          :class="{ 'active': selectedROI === roi.id }"
          @click="selectROI(roi.id)"
        >
          <div class="roi-info">
            <span class="roi-name">{{ roi.name }}</span>
            <span class="roi-type">{{ getROITypeLabel(roi.type) }}</span>
          </div>
          <div class="roi-coords">{{ formatCoords(roi.coords) }}</div>
        </div>
      </div>
    </div>
    
    <!-- 特征设置 -->
    <div v-if="rois.length > 0" class="feature-section">
      <div class="section-label">计算特征</div>
      <el-checkbox-group v-model="selectedFeatures" size="small">
        <el-checkbox label="mean">灰度均值</el-checkbox>
        <el-checkbox label="std">标准差</el-checkbox>
        <el-checkbox label="max">最大值</el-checkbox>
        <el-checkbox label="min">最小值</el-checkbox>
        <el-checkbox label="median">中位数</el-checkbox>
        <el-checkbox label="area">面积</el-checkbox>
      </el-checkbox-group>
    </div>
    
    <!-- 显示设置 -->
    <div v-if="rois.length > 0" class="display-section">
      <div class="section-label">显示设置</div>
      <el-switch
        v-model="showROIOnVideo"
        active-text="在视频上显示ROI区域"
        size="small"
        @change="onShowROIChange"
      />
      <div class="display-hint">
        开启后将在CH1-CH3视频画面上显示ROI区域红框
      </div>
    </div>
    
    <!-- 操作按钮 -->
    <div class="action-buttons">
      <el-button 
        type="success" 
        size="small" 
        @click="saveConfig"
        :loading="isSaving"
        :disabled="rois.length === 0"
      >
        <el-icon><Check /></el-icon>
        保存配置
      </el-button>
      <el-button 
        type="danger" 
        size="small" 
        @click="clearConfig"
        :disabled="!hasConfig"
      >
        <el-icon><Delete /></el-icon>
        清除
      </el-button>
    </div>
    
    <!-- 配置文件示例 -->
    <el-collapse class="example-collapse">
      <el-collapse-item title="配置文件示例">
        <pre class="config-example">{
  "rois": {
    "pool_center": {
      "name": "熔池中心",
      "type": "rectangle",
      "coords": [320, 240, 100, 100],
      "description": "熔池中心区域"
    },
    "pool_edge": {
      "name": "熔池边缘",
      "type": "rectangle", 
      "coords": [300, 220, 140, 140],
      "description": "熔池边缘区域"
    }
  },
  "features": ["mean", "std", "max"],
  "update_mode": "layer"
}</pre>
      </el-collapse-item>
    </el-collapse>
    
    <!-- 隐藏的文件输入 -->
    <input 
      ref="fileInput"
      type="file"
      accept=".json"
      style="display: none"
      @change="onFileSelected"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Folder, Check, Delete } from '@element-plus/icons-vue'
import axios from 'axios'
import { useROIStore } from '../../stores/roiStore'

const emit = defineEmits(['config-loaded', 'config-cleared'])

// Store
const roiStore = useROIStore()

// 状态
const configFilePath = ref('')
const rois = ref([])
const selectedROI = ref(null)
const selectedFeatures = ref(['mean', 'std'])
const isLoading = ref(false)
const isSaving = ref(false)
const fileInput = ref(null)
const showROIOnVideo = ref(false)

// 计算属性
const hasConfig = computed(() => rois.value.length > 0)

// ROI类型标签
const roiTypeLabels = {
  rectangle: '矩形',
  circle: '圆形',
  polygon: '多边形'
}

function getROITypeLabel(type) {
  return roiTypeLabels[type] || type
}

// 格式化坐标显示
function formatCoords(coords) {
  if (!coords || !Array.isArray(coords)) return ''
  if (coords.length === 4) {
    return `(${coords[0]}, ${coords[1]}, ${coords[2]}, ${coords[3]})`
  }
  if (coords.length === 3) {
    return `(${coords[0]}, ${coords[1]}, r=${coords[2]})`
  }
  return `${coords.length} points`
}

// 选择配置文件
function selectConfigFile() {
  fileInput.value?.click()
}

// 文件选择回调
function onFileSelected(event) {
  const file = event.target.files[0]
  if (file) {
    configFilePath.value = file.path || file.name
    // 自动加载
    loadConfigFromFile(file)
  }
  // 清空input以便再次选择同一文件
  event.target.value = ''
}

// 从文件加载配置
async function loadConfigFromFile(file) {
  isLoading.value = true
  
  try {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const config = JSON.parse(e.target.result)
        console.log('[ROIConfigPanel] 从文件加载配置:', config)
        parseConfig(config)
        ElMessage.success('配置文件加载成功')
        emit('config-loaded', config)
      } catch (error) {
        ElMessage.error('配置文件格式错误: ' + error.message)
      }
    }
    reader.readAsText(file)
  } catch (error) {
    ElMessage.error('读取文件失败: ' + error.message)
  } finally {
    isLoading.value = false
  }
}

// 加载配置（从路径）
async function loadConfig() {
  if (!configFilePath.value) return
  
  isLoading.value = true
  try {
    console.log('[ROIConfigPanel] 开始加载配置:', configFilePath.value)
    // 通过后端API加载配置文件
    const response = await axios.post('/api/slm/roi/load', {
      config_path: configFilePath.value
    })
    
    console.log('[ROIConfigPanel] 加载响应:', response.data)
    
    if (response.data.success) {
      parseConfig(response.data.config)
      ElMessage.success('配置加载成功')
      emit('config-loaded', response.data.config)
    } else {
      ElMessage.error(response.data.message || '加载失败')
    }
  } catch (error) {
    console.error('[ROIConfigPanel] 加载失败:', error)
    // 如果后端API不可用，尝试直接读取
    ElMessage.warning('后端API不可用，尝试本地读取')
  } finally {
    isLoading.value = false
  }
}

// 解析配置
function parseConfig(config) {
  console.log('[ROIConfigPanel] 解析配置:', config)
  
  // 处理可能的嵌套结构
  const actualConfig = config.config || config
  
  if (actualConfig.rois && Object.keys(actualConfig.rois).length > 0) {
    rois.value = Object.entries(actualConfig.rois).map(([id, roi]) => ({
      id,
      ...roi
    }))
    console.log('[ROIConfigPanel] 加载ROI:', rois.value)
  } else {
    console.log('[ROIConfigPanel] 配置中没有ROIs')
    rois.value = []
  }
  
  if (actualConfig.features) {
    selectedFeatures.value = actualConfig.features
  }
  
  // 默认选中第一个ROI
  if (rois.value.length > 0) {
    selectedROI.value = rois.value[0].id
  }
  
  // 同步到store
  roiStore.setROIConfig({
    rois: actualConfig.rois || {},
    features: actualConfig.features || ['mean', 'std'],
    update_mode: actualConfig.update_mode || 'layer'
  })
}

// 选择ROI
function selectROI(roiId) {
  selectedROI.value = roiId
}

// 保存配置
async function saveConfig() {
  if (rois.value.length === 0) return
  
  isSaving.value = true
  
  try {
    const config = {
      rois: {},
      features: selectedFeatures.value,
      update_mode: 'layer'
    }
    
    rois.value.forEach(roi => {
      config.rois[roi.id] = {
        name: roi.name,
        type: roi.type,
        coords: roi.coords,
        description: roi.description || ''
      }
    })
    
    const response = await axios.post('/api/slm/roi/save', {
      config: config,
      config_path: configFilePath.value || 'roi_config.json'
    })
    
    if (response.data.success) {
      ElMessage.success('配置保存成功')
    } else {
      ElMessage.error(response.data.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.message || error.message))
  } finally {
    isSaving.value = false
  }
}

// 清除配置
function clearConfig() {
  rois.value = []
  selectedROI.value = null
  configFilePath.value = ''
  selectedFeatures.value = ['mean', 'std']
  showROIOnVideo.value = false
  roiStore.clearConfig()
  roiStore.setShowROIOnVideo(false)
  emit('config-cleared')
  ElMessage.success('配置已清除')
}

// 显示ROI开关变化
function onShowROIChange(val) {
  roiStore.setShowROIOnVideo(val)
  ElMessage.success(val ? '已开启ROI区域显示' : '已关闭ROI区域显示')
}

// 组件挂载时尝试加载已有配置
onMounted(async () => {
  // 从store加载显示设置
  roiStore.loadFromStorage()
  showROIOnVideo.value = roiStore.showROIOnVideo
  
  // 如果store中有配置，直接使用
  if (roiStore.hasConfig) {
    parseConfig(roiStore.roiConfig)
  }
  
  try {
    const response = await axios.get('/api/slm/roi/config')
    if (response.data.success && response.data.config) {
      parseConfig(response.data.config)
      if (response.data.config_path) {
        configFilePath.value = response.data.config_path
      }
    }
  } catch (error) {
    // 静默失败，可能后端API不存在
    console.log('ROI配置API不可用')
  }
})
</script>

<style scoped>
.roi-config-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 8px;
  padding: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(100, 116, 139, 0.2);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.section-label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.config-section {
  margin-bottom: 16px;
}

.file-input-row {
  display: flex;
  gap: 8px;
}

.file-input-row .el-input {
  flex: 1;
}

.file-hint {
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
}

.roi-list-section {
  margin-bottom: 16px;
}

.roi-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.roi-item {
  padding: 10px 12px;
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(100, 116, 139, 0.2);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.roi-item:hover {
  background: rgba(30, 41, 59, 0.8);
}

.roi-item.active {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
}

.roi-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.roi-name {
  font-size: 13px;
  font-weight: 500;
  color: #e2e8f0;
}

.roi-type {
  font-size: 11px;
  color: #94a3b8;
  background: rgba(100, 116, 139, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
}

.roi-coords {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}

.feature-section {
  margin-bottom: 16px;
}

.feature-section :deep(.el-checkbox) {
  margin-right: 16px;
  color: #e2e8f0;
}

.feature-section :deep(.el-checkbox__label) {
  font-size: 12px;
}

.display-section {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 6px;
  border: 1px solid rgba(100, 116, 139, 0.2);
}

.display-hint {
  font-size: 11px;
  color: #64748b;
  margin-top: 8px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.example-collapse {
  --el-collapse-border-color: rgba(100, 116, 139, 0.2);
  --el-collapse-header-bg-color: transparent;
  --el-collapse-header-text-color: #94a3b8;
  --el-collapse-content-bg-color: transparent;
}

.example-collapse :deep(.el-collapse-item__header) {
  font-size: 12px;
  padding-left: 0;
}

.example-collapse :deep(.el-collapse-item__content) {
  padding: 8px 0;
}

.config-example {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 4px;
  padding: 12px;
  font-size: 11px;
  color: #94a3b8;
  overflow-x: auto;
  margin: 0;
}
</style>
