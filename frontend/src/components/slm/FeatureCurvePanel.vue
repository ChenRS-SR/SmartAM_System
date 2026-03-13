<template>
  <div class="feature-curve-panel">
    <div class="panel-header">
      <span class="panel-title">📈 区域特征曲线</span>
      <div class="header-controls">
        <!-- ROI选择 -->
        <el-select 
          v-model="selectedROI" 
          placeholder="选择ROI区域" 
          size="small"
          style="width: 150px; margin-right: 10px;"
        >
          <el-option 
            v-for="roi in availableROIs" 
            :key="roi.id" 
            :label="roi.name" 
            :value="roi.id"
          />
        </el-select>
        
        <!-- 特征选择 -->
        <el-select 
          v-model="selectedFeature" 
          placeholder="选择特征" 
          size="small"
          style="width: 120px; margin-right: 10px;"
        >
          <el-option label="灰度均值" value="mean" />
          <el-option label="标准差" value="std" />
          <el-option label="最大值" value="max" />
          <el-option label="最小值" value="min" />
          <el-option label="中位数" value="median" />
          <el-option label="面积" value="area" />
        </el-select>
        
        <!-- 更新模式 -->
        <el-radio-group v-model="updateMode" size="small" style="margin-right: 10px;">
          <el-radio-button label="layer">按层</el-radio-button>
          <el-radio-button label="frame">按帧</el-radio-button>
        </el-radio-group>
        
        <!-- 模拟数据开关 -->
        <el-switch 
          v-model="useMockData" 
          active-text="模拟数据"
          size="small"
        />
      </div>
    </div>
    
    <!-- 图表区域 -->
    <div class="chart-container">
      <div ref="chartRef" class="chart"></div>
      
      <!-- 无数据提示 -->
      <div v-if="!hasData" class="no-data">
        <el-icon :size="40" color="#64748b"><TrendCharts /></el-icon>
        <p>暂无特征数据</p>
        <p class="sub-text">请在设置中配置ROI区域</p>
      </div>
    </div>
    
    <!-- 统计信息 -->
    <div v-if="hasData" class="stats-row">
      <div class="stat-item">
        <span class="stat-label">当前值</span>
        <span class="stat-value" :style="{ color: currentValueColor }">{{ currentValue.toFixed(2) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">平均值</span>
        <span class="stat-value">{{ averageValue.toFixed(2) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">最大值</span>
        <span class="stat-value max">{{ maxValue.toFixed(2) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">最小值</span>
        <span class="stat-value min">{{ minValue.toFixed(2) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">数据点</span>
        <span class="stat-value">{{ dataPoints.length }}</span>
      </div>
    </div>
    
    <!-- 当前层标记 -->
    <div v-if="currentLayer > 0" class="layer-indicator">
      <el-tag type="info" size="small" effect="dark">
        当前层: {{ currentLayer }}
      </el-tag>
      <el-tag v-if="isLayerStart" type="success" size="small" effect="dark" style="margin-left: 8px;">
        层开始
      </el-tag>
      <el-tag v-if="isLayerEnd" type="warning" size="small" effect="dark" style="margin-left: 8px;">
        层结束
      </el-tag>
    </div>
    
    <!-- 调试信息 -->
    <div class="debug-info">
      <el-tag size="small" effect="plain">ROI: {{ selectedROI || '未选择' }}</el-tag>
      <el-tag size="small" effect="plain" style="margin-left: 8px;">特征: {{ selectedFeature }}</el-tag>
      <el-tag size="small" effect="plain" style="margin-left: 8px;">数据点: {{ dataPoints.length }}</el-tag>
      <el-tag size="small" effect="plain" style="margin-left: 8px;">模拟: {{ useMockData ? '开' : '关' }}</el-tag>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { TrendCharts } from '@element-plus/icons-vue'
import axios from 'axios'
import { useROIStore } from '../../stores/roiStore'

const props = defineProps({
  // 当前层信息
  currentLayer: {
    type: Number,
    default: 0
  },
  // 是否为层开始
  isLayerStart: {
    type: Boolean,
    default: false
  },
  // 是否为层结束
  isLayerEnd: {
    type: Boolean,
    default: false
  },
  // 是否正在运行
  isRunning: {
    type: Boolean,
    default: false
  }
})

// Store
const roiStore = useROIStore()

// 状态
const chartRef = ref(null)
let chart = null

const availableROIs = ref([])
const selectedROI = ref('')
const selectedFeature = ref('mean')
const updateMode = ref('layer')  // layer: 按层, frame: 按帧
const useMockData = ref(true)  // 默认使用模拟数据，方便测试

const dataPoints = ref([])  // { layer: number, value: number, timestamp: number }
const lastUpdateLayer = ref(0)

// 计算属性
const hasData = computed(() => dataPoints.value.length > 0)

const currentValue = computed(() => {
  if (dataPoints.value.length === 0) return 0
  return dataPoints.value[dataPoints.value.length - 1].value
})

const averageValue = computed(() => {
  if (dataPoints.value.length === 0) return 0
  const sum = dataPoints.value.reduce((acc, p) => acc + p.value, 0)
  return sum / dataPoints.value.length
})

const maxValue = computed(() => {
  if (dataPoints.value.length === 0) return 0
  return Math.max(...dataPoints.value.map(p => p.value))
})

const minValue = computed(() => {
  if (dataPoints.value.length === 0) return 0
  return Math.min(...dataPoints.value.map(p => p.value))
})

const currentValueColor = computed(() => {
  // 根据特征类型返回不同颜色
  const value = currentValue.value
  if (selectedFeature.value === 'mean') {
    // 灰度均值：低值红色，高值绿色
    if (value < 50) return '#ef4444'
    if (value > 200) return '#22c55e'
    return '#e2e8f0'
  }
  return '#e2e8f0'
})

// 初始化图表
function initChart() {
  console.log('[FeatureCurve] 初始化图表')
  
  if (!chartRef.value) {
    console.log('[FeatureCurve] 图表容器未找到')
    return
  }
  
  console.log('[FeatureCurve] 图表容器:', chartRef.value)
  chart = echarts.init(chartRef.value, 'dark')
  console.log('[FeatureCurve] 图表实例创建成功')
  
  const option = {
    backgroundColor: 'transparent',
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: 'rgba(100, 116, 139, 0.3)',
      textStyle: {
        color: '#e2e8f0'
      },
      formatter: function(params) {
        const data = params[0]
        return `层 ${data.name}<br/>${selectedFeature.value}: ${data.value.toFixed(2)}`
      }
    },
    xAxis: {
      type: 'category',
      data: [],
      axisLine: {
        lineStyle: {
          color: 'rgba(100, 116, 139, 0.3)'
        }
      },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        lineStyle: {
          color: 'rgba(100, 116, 139, 0.3)'
        }
      },
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(100, 116, 139, 0.1)'
        }
      }
    },
    series: [{
      name: '特征值',
      type: 'line',
      data: [],
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        width: 2,
        color: '#3b82f6'
      },
      itemStyle: {
        color: '#3b82f6'
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
          { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
        ])
      },
      markLine: {
        silent: true,
        lineStyle: {
          color: '#f59e0b',
          type: 'dashed'
        },
        data: []
      }
    }]
  }
  
  chart.setOption(option)
}

// 更新图表
function updateChart() {
  console.log(`[FeatureCurve] 更新图表: 数据点=${dataPoints.value.length}`)
  
  if (!chart) {
    console.log('[FeatureCurve] 图表未初始化，跳过更新')
    return
  }
  
  const xData = dataPoints.value.map(p => p.layer.toString())
  const yData = dataPoints.value.map(p => p.value)
  
  console.log(`[FeatureCurve] X轴数据: ${xData.join(', ')}`)
  console.log(`[FeatureCurve] Y轴数据: ${yData.map(v => v.toFixed(1)).join(', ')}`)
  
  chart.setOption({
    xAxis: {
      data: xData
    },
    series: [{
      data: yData,
      markLine: {
        data: [
          { type: 'average', name: '平均值' }
        ]
      }
    }]
  })
  
  console.log('[FeatureCurve] 图表更新完成')
}

// 添加数据点
function addDataPoint(layer, value) {
  console.log(`[FeatureCurve] 添加数据点: 层=${layer}, 值=${value.toFixed(2)}`)
  
  // 检查是否已存在该层的数据
  const existingIndex = dataPoints.value.findIndex(p => p.layer === layer)
  
  if (existingIndex >= 0) {
    // 更新现有数据点
    dataPoints.value[existingIndex].value = value
    dataPoints.value[existingIndex].timestamp = Date.now()
    console.log(`[FeatureCurve] 更新现有数据点[${existingIndex}]`)
  } else {
    // 添加新数据点
    dataPoints.value.push({
      layer,
      value,
      timestamp: Date.now()
    })
    console.log(`[FeatureCurve] 添加新数据点, 总数=${dataPoints.value.length}`)
    
    // 限制数据点数量（保留最近100个）
    if (dataPoints.value.length > 100) {
      dataPoints.value.shift()
    }
  }
  
  // 按层排序
  dataPoints.value.sort((a, b) => a.layer - b.layer)
  
  // 更新图表
  updateChart()
}

// 获取特征数据
async function fetchFeatureData() {
  console.log(`[FeatureCurve] fetchFeatureData被调用: ROI=${selectedROI.value}, 特征=${selectedFeature.value}, 层=${props.currentLayer}`)
  
  if (!selectedROI.value) {
    console.log('[FeatureCurve] 未选择ROI，跳过')
    return
  }
  if (!selectedFeature.value) {
    console.log('[FeatureCurve] 未选择特征，跳过')
    return
  }
  
  console.log(`[FeatureCurve] 获取特征数据: ROI=${selectedROI.value}, 特征=${selectedFeature.value}, 层=${props.currentLayer}, 模拟=${useMockData.value}`)
  
  // 如果使用模拟数据，直接生成
  if (useMockData.value) {
    generateMockData()
    return
  }
  
  try {
    const response = await axios.get('/api/slm/roi/features', {
      params: {
        roi_id: selectedROI.value,
        feature: selectedFeature.value,
        layer: props.currentLayer
      }
    })
    
    if (response.data.success && response.data.value !== undefined) {
      console.log(`[FeatureCurve] 获取到特征值: ${response.data.value}`)
      addDataPoint(props.currentLayer, response.data.value)
    } else {
      console.log('[FeatureCurve] 后端返回无数据:', response.data)
      // 如果没有数据，生成模拟数据用于测试
      generateMockData()
    }
  } catch (error) {
    console.log('[FeatureCurve] 获取特征数据失败:', error)
    // 如果后端API不存在，生成模拟数据用于测试
    generateMockData()
  }
}

// 生成模拟数据（用于测试）
function generateMockData() {
  if (!selectedROI.value || !selectedFeature.value || props.currentLayer <= 0) return
  
  // 基于层号生成一些模拟数据
  let mockValue = 0
  const layer = props.currentLayer
  
  if (selectedFeature.value === 'mean') {
    // 灰度均值：模拟从低到高再到低的变化
    mockValue = 100 + Math.sin(layer * 0.3) * 50 + Math.random() * 20
  } else if (selectedFeature.value === 'std') {
    // 标准差
    mockValue = 20 + Math.cos(layer * 0.2) * 10 + Math.random() * 5
  } else if (selectedFeature.value === 'max') {
    mockValue = 200 + Math.random() * 55
  } else if (selectedFeature.value === 'min') {
    mockValue = 10 + Math.random() * 20
  } else {
    mockValue = 50 + Math.random() * 100
  }
  
  console.log(`[FeatureCurve] 生成模拟数据: 层=${layer}, 值=${mockValue.toFixed(2)}`)
  addDataPoint(layer, mockValue)
}

// 加载可用ROI列表
async function loadROIs() {
  // 首先从store加载
  roiStore.loadFromStorage()
  
  if (roiStore.hasConfig) {
    console.log('[FeatureCurve] 从store加载ROI配置')
    availableROIs.value = roiStore.roiList
    
    if (availableROIs.value.length > 0 && !selectedROI.value) {
      selectedROI.value = availableROIs.value[0].id
      console.log('[FeatureCurve] 默认选中ROI:', selectedROI.value)
      
      if (props.currentLayer > 0) {
        fetchFeatureData()
      }
    }
    return
  }
  
  try {
    console.log('[FeatureCurve] 开始加载ROI列表')
    const response = await axios.get('/api/slm/roi/config')
    console.log('[FeatureCurve] ROI配置响应:', response.data)
    if (response.data.success && response.data.config) {
      const config = response.data.config
      if (config.rois && Object.keys(config.rois).length > 0) {
        availableROIs.value = Object.entries(config.rois).map(([id, roi]) => ({
          id,
          ...roi
        }))
        
        console.log('[FeatureCurve] 可用ROI列表:', availableROIs.value)
        
        // 同步到store
        roiStore.setROIConfig(config)
        
        // 默认选中第一个
        if (availableROIs.value.length > 0 && !selectedROI.value) {
          selectedROI.value = availableROIs.value[0].id
          console.log('[FeatureCurve] 默认选中ROI:', selectedROI.value)
          
          // 如果当前已有层信息，立即获取数据
          if (props.currentLayer > 0) {
            console.log('[FeatureCurve] ROI加载完成，立即获取当前层数据')
            fetchFeatureData()
          }
        }
      } else {
        console.log('[FeatureCurve] 配置中没有ROIs，使用默认ROI')
        useDefaultROIs()
      }
    } else {
      console.log('[FeatureCurve] 获取ROI配置失败:', response.data)
      useDefaultROIs()
    }
  } catch (error) {
    console.log('[FeatureCurve] 加载ROI配置失败，使用默认ROI:', error)
    useDefaultROIs()
  }
}

// 使用默认ROI（当后端不可用时）
function useDefaultROIs() {
  availableROIs.value = [
    { id: 'pool_center', name: '熔池中心', type: 'rectangle', coords: [320, 240, 100, 100] },
    { id: 'pool_edge', name: '熔池边缘', type: 'rectangle', coords: [280, 200, 180, 180] }
  ]
  
  if (!selectedROI.value) {
    selectedROI.value = availableROIs.value[0].id
    console.log('[FeatureCurve] 使用默认ROI:', selectedROI.value)
    
    if (props.currentLayer > 0) {
      fetchFeatureData()
    }
  }
}

// 监听层变化
watch(() => props.currentLayer, (newLayer, oldLayer) => {
  console.log(`[FeatureCurve] 层变化: ${oldLayer} -> ${newLayer}, isLayerStart=${props.isLayerStart}, isLayerEnd=${props.isLayerEnd}`)
  if (newLayer !== oldLayer && newLayer > 0) {
    // 层变化时获取数据
    if (updateMode.value === 'layer') {
      // 按层更新：在层开始或结束时更新
      if (props.isLayerStart || props.isLayerEnd) {
        fetchFeatureData()
      }
    } else {
      // 按帧更新：立即更新
      fetchFeatureData()
    }
  }
})

// 监听层开始/结束标记
watch(() => props.isLayerStart, (isStart) => {
  if (isStart && updateMode.value === 'layer' && props.currentLayer > 0) {
    fetchFeatureData()
  }
})

watch(() => props.isLayerEnd, (isEnd) => {
  if (isEnd && updateMode.value === 'layer' && props.currentLayer > 0) {
    fetchFeatureData()
  }
})

// 监听选择变化
watch([selectedROI, selectedFeature], () => {
  // 清空数据并重新加载
  dataPoints.value = []
  if (props.currentLayer > 0) {
    fetchFeatureData()
  }
})

// 窗口大小变化时重新调整图表
function handleResize() {
  chart?.resize()
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    initChart()
    loadROIs()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.feature-curve-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
  border-radius: 8px;
  overflow: hidden;
  padding: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.header-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.chart-container {
  position: relative;
  height: 250px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 6px;
  border: 1px solid rgba(100, 116, 139, 0.2);
}

.chart {
  width: 100%;
  height: 100%;
}

.no-data {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
}

.no-data p {
  margin: 8px 0 0;
  font-size: 14px;
}

.no-data .sub-text {
  font-size: 12px;
  color: #94a3b8;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(100, 116, 139, 0.2);
}

.stat-item {
  text-align: center;
  padding: 8px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 4px;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
}

.stat-value.max {
  color: #ef4444;
}

.stat-value.min {
  color: #22c55e;
}

.layer-indicator {
  margin-top: 12px;
  display: flex;
  align-items: center;
}

.debug-info {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(100, 116, 139, 0.2);
}

@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-controls {
    width: 100%;
  }
  
  .stats-row {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
