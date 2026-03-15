<template>
  <div class="vibration-waveform">
    <div class="waveform-header">
      <div class="header-left">
        <span class="section-title">振动波形监测</span>
        <div class="status-badges">
          <el-tag v-if="!enabled" type="info" size="small">已禁用</el-tag>
          <el-tag v-else-if="!connected" type="danger" size="small">未连接</el-tag>
          <el-tag v-else type="success" size="small">采集中</el-tag>
          <el-tag v-if="latestVibration?.magnitude > 0.05" type="warning" size="small" effect="dark">
            振动告警
          </el-tag>
        </div>
      </div>
      <div class="header-right">
        <span class="sample-info">样本: {{ waveformData.sample_count || 0 }}点</span>
        <el-radio-group v-model="timeRange" size="small">
          <el-radio-button label="1s">1秒</el-radio-button>
          <el-radio-button label="5s">5秒</el-radio-button>
          <el-radio-button label="10s">10秒</el-radio-button>
        </el-radio-group>
      </div>
    </div>
    
    <!-- 实时数值显示 -->
    <div class="vibration-values">
      <div class="value-card x-axis">
        <div class="value-icon">
          <span class="axis-label">X</span>
        </div>
        <div class="value-content">
          <span class="value-number">{{ formatValue(latestVibration?.vx) }}</span>
          <span class="value-unit">mm/s</span>
        </div>
        <div class="value-stats">
          <span>RMS: {{ formatValue(vibrationStats.vx?.rms) }}</span>
        </div>
      </div>
      
      <div class="value-card y-axis">
        <div class="value-icon">
          <span class="axis-label">Y</span>
        </div>
        <div class="value-content">
          <span class="value-number">{{ formatValue(latestVibration?.vy) }}</span>
          <span class="value-unit">mm/s</span>
        </div>
        <div class="value-stats">
          <span>RMS: {{ formatValue(vibrationStats.vy?.rms) }}</span>
        </div>
      </div>
      
      <div class="value-card z-axis">
        <div class="value-icon">
          <span class="axis-label">Z</span>
        </div>
        <div class="value-content">
          <span class="value-number">{{ formatValue(latestVibration?.vz) }}</span>
          <span class="value-unit">mm/s</span>
        </div>
        <div class="value-stats">
          <span>RMS: {{ formatValue(vibrationStats.vz?.rms) }}</span>
        </div>
      </div>
      
      <div class="value-card magnitude">
        <div class="value-icon">
          <el-icon><Odometer /></el-icon>
        </div>
        <div class="value-content">
          <span class="value-number">{{ formatValue(latestVibration?.magnitude) }}</span>
          <span class="value-unit">合成</span>
        </div>
        <div class="value-stats">
          <span>峰值: {{ formatValue(vibrationStats.magnitude?.max) }}</span>
        </div>
      </div>
      
      <div class="value-card temperature">
        <div class="value-icon">
          <el-icon><HotWater /></el-icon>
        </div>
        <div class="value-content">
          <span class="value-number">{{ formatValue(latestVibration?.temperature) }}</span>
          <span class="value-unit">°C</span>
        </div>
        <div class="value-stats">
          <span>传感器温度</span>
        </div>
      </div>
    </div>
    
    <!-- 波形图表 -->
    <div class="chart-container" ref="chartContainer">
      <canvas ref="waveformCanvas" class="waveform-canvas"></canvas>
      <div v-if="!enabled" class="chart-overlay">
        <el-icon :size="32"><Warning /></el-icon>
        <span>振动传感器已禁用</span>
      </div>
      <div v-else-if="!connected" class="chart-overlay">
        <el-icon :size="32"><Warning /></el-icon>
        <span>振动传感器未连接</span>
      </div>
    </div>
    
    <!-- 频谱图 -->
    <div class="spectrum-section">
      <div class="spectrum-header">
        <span class="spectrum-title">频谱分析</span>
        <el-radio-group v-model="spectrumAxis" size="small">
          <el-radio-button label="x">X轴</el-radio-button>
          <el-radio-button label="y">Y轴</el-radio-button>
          <el-radio-button label="z">Z轴</el-radio-button>
        </el-radio-group>
      </div>
      <div class="spectrum-chart" ref="spectrumContainer">
        <canvas ref="spectrumCanvas" class="spectrum-canvas"></canvas>
      </div>
    </div>
    
    <!-- 统计信息 -->
    <div class="statistics-section">
      <el-collapse>
        <el-collapse-item title="详细统计数据" name="statistics">
          <div class="stats-grid">
            <div v-for="(axis, axisName) in vibrationStats" :key="axisName" class="stats-column">
              <h4>{{ axisName.toUpperCase() }} 轴统计</h4>
              <div class="stats-row">
                <span class="stats-label">均值:</span>
                <span class="stats-value">{{ formatValue(axis?.mean) }}</span>
              </div>
              <div class="stats-row">
                <span class="stats-label">标准差:</span>
                <span class="stats-value">{{ formatValue(axis?.std) }}</span>
              </div>
              <div class="stats-row">
                <span class="stats-label">最大值:</span>
                <span class="stats-value">{{ formatValue(axis?.max) }}</span>
              </div>
              <div class="stats-row">
                <span class="stats-label">最小值:</span>
                <span class="stats-value">{{ formatValue(axis?.min) }}</span>
              </div>
              <div class="stats-row">
                <span class="stats-label">RMS:</span>
                <span class="stats-value">{{ formatValue(axis?.rms) }}</span>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Odometer, Warning } from '@element-plus/icons-vue'

const props = defineProps({
  waveformData: {
    type: Object,
    default: () => ({ x: [], y: [], z: [], sample_count: 0 })
  },
  latestVibration: {
    type: Object,
    default: () => ({})
  },
  enabled: {
    type: Boolean,
    default: true
  },
  connected: {
    type: Boolean,
    default: false
  }
})

const timeRange = ref('5s')
const spectrumAxis = ref('x')
const chartContainer = ref(null)
const waveformCanvas = ref(null)
const spectrumContainer = ref(null)
const spectrumCanvas = ref(null)

let waveformCtx = null
let spectrumCtx = null
let animationId = null

// 振动统计（基于历史数据计算）
const vibrationStats = computed(() => {
  const data = props.waveformData
  const stats = {}
  
  const axes = ['x', 'y', 'z', 'magnitude']
  axes.forEach(axis => {
    const values = data[axis] || []
    if (values.length === 0) {
      stats[axis] = { mean: 0, std: 0, max: 0, min: 0, rms: 0 }
      return
    }
    
    const sum = values.reduce((a, b) => a + b, 0)
    const mean = sum / values.length
    const squareSum = values.reduce((a, b) => a + b * b, 0)
    const rms = Math.sqrt(squareSum / values.length)
    const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length
    const std = Math.sqrt(variance)
    const max = Math.max(...values)
    const min = Math.min(...values)
    
    stats[axis] = { mean, std, max, min, rms }
  })
  
  return stats
})

// 格式化数值
const formatValue = (val) => {
  if (val === undefined || val === null) return '0.00'
  return val.toFixed(3)
}

// 绘制波形
const drawWaveform = () => {
  if (!waveformCtx || !waveformCanvas.value) return
  
  const canvas = waveformCanvas.value
  const ctx = waveformCtx
  const width = canvas.width
  const height = canvas.height
  
  // 清空画布
  ctx.fillStyle = '#0f172a'
  ctx.fillRect(0, 0, width, height)
  
  // 绘制网格
  ctx.strokeStyle = '#1e293b'
  ctx.lineWidth = 1
  for (let i = 0; i < width; i += 50) {
    ctx.beginPath()
    ctx.moveTo(i, 0)
    ctx.lineTo(i, height)
    ctx.stroke()
  }
  for (let i = 0; i < height; i += 30) {
    ctx.beginPath()
    ctx.moveTo(0, i)
    ctx.lineTo(width, i)
    ctx.stroke()
  }
  
  if (!props.enabled || !props.connected) return
  
  // 获取数据
  const data = props.waveformData
  const axes = ['x', 'y', 'z']
  const colors = ['#ef4444', '#22c55e', '#3b82f6']
  const yOffsets = [height * 0.17, height * 0.5, height * 0.83]
  
  axes.forEach((axis, index) => {
    const values = data[axis] || []
    if (values.length < 2) return
    
    // 根据时间范围截断数据
    let displayValues = values
    const range = parseInt(timeRange.value)
    const maxPoints = range * 20  // 假设20Hz采样率
    if (values.length > maxPoints) {
      displayValues = values.slice(-maxPoints)
    }
    
    // 计算缩放
    const maxVal = Math.max(...displayValues.map(Math.abs), 0.1)
    const scale = (height * 0.25) / maxVal
    
    // 绘制波形
    ctx.strokeStyle = colors[index]
    ctx.lineWidth = 2
    ctx.beginPath()
    
    displayValues.forEach((val, i) => {
      const x = (i / (maxPoints - 1)) * width
      const y = yOffsets[index] - val * scale
      
      if (i === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    
    ctx.stroke()
    
    // 绘制轴标签
    ctx.fillStyle = colors[index]
    ctx.font = 'bold 12px Arial'
    ctx.fillText(`${axis.toUpperCase()} 轴`, 10, yOffsets[index] - height * 0.15)
    
    // 绘制中心线
    ctx.strokeStyle = 'rgba(255,255,255,0.1)'
    ctx.lineWidth = 1
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.moveTo(0, yOffsets[index])
    ctx.lineTo(width, yOffsets[index])
    ctx.stroke()
    ctx.setLineDash([])
  })
}

// 绘制频谱
const drawSpectrum = () => {
  if (!spectrumCtx || !spectrumCanvas.value) return
  
  const canvas = spectrumCanvas.value
  const ctx = spectrumCtx
  const width = canvas.width
  const height = canvas.height
  
  // 清空画布
  ctx.fillStyle = '#0f172a'
  ctx.fillRect(0, 0, width, height)
  
  // 绘制网格
  ctx.strokeStyle = '#1e293b'
  ctx.lineWidth = 1
  for (let i = 0; i < width; i += 50) {
    ctx.beginPath()
    ctx.moveTo(i, 0)
    ctx.lineTo(i, height)
    ctx.stroke()
  }
  for (let i = 0; i < height; i += 30) {
    ctx.beginPath()
    ctx.moveTo(0, i)
    ctx.lineTo(width, i)
    ctx.stroke()
  }
  
  if (!props.enabled || !props.connected) return
  
  // 获取数据
  const data = props.waveformData[spectrumAxis.value] || []
  if (data.length < 8) return
  
  // 简单的FFT模拟（使用实际FFT会更准确）
  const fftSize = Math.min(256, data.length)
  const fftData = data.slice(-fftSize)
  
  // 计算频谱（简化版）
  const spectrum = []
  const freqBins = 64
  
  for (let i = 0; i < freqBins; i++) {
    let sum = 0
    const start = Math.floor((i / freqBins) * fftSize)
    const end = Math.floor(((i + 1) / freqBins) * fftSize)
    
    for (let j = start; j < end && j < fftSize; j++) {
      sum += Math.abs(fftData[j] || 0)
    }
    
    spectrum.push(sum / (end - start))
  }
  
  // 绘制频谱柱状图
  const barWidth = (width / freqBins) * 0.8
  const gap = (width / freqBins) * 0.2
  const maxVal = Math.max(...spectrum, 0.01)
  
  spectrum.forEach((val, i) => {
    const barHeight = (val / maxVal) * height * 0.9
    const x = i * (barWidth + gap) + gap / 2
    const y = height - barHeight
    
    // 渐变色
    const gradient = ctx.createLinearGradient(0, height, 0, 0)
    gradient.addColorStop(0, '#22c55e')
    gradient.addColorStop(0.5, '#eab308')
    gradient.addColorStop(1, '#ef4444')
    
    ctx.fillStyle = gradient
    ctx.fillRect(x, y, barWidth, barHeight)
  })
  
  // 绘制频率标签
  ctx.fillStyle = '#94a3b8'
  ctx.font = '10px Arial'
  ctx.fillText('0 Hz', 5, height - 5)
  ctx.fillText('Nyquist', width - 50, height - 5)
}

// 动画循环
const animate = () => {
  drawWaveform()
  drawSpectrum()
  animationId = requestAnimationFrame(animate)
}

// 监听数据变化
watch(() => props.waveformData, () => {
  // 数据更新时自动重绘
}, { deep: true })

watch(() => timeRange.value, () => {
  // 时间范围变化时重绘
})

watch(() => spectrumAxis.value, () => {
  // 频谱轴变化时重绘
})

onMounted(() => {
  // 初始化Canvas
  if (waveformCanvas.value) {
    waveformCanvas.value.width = chartContainer.value.clientWidth
    waveformCanvas.value.height = 250
    waveformCtx = waveformCanvas.value.getContext('2d')
  }
  
  if (spectrumCanvas.value) {
    spectrumCanvas.value.width = spectrumContainer.value.clientWidth
    spectrumCanvas.value.height = 150
    spectrumCtx = spectrumCanvas.value.getContext('2d')
  }
  
  // 启动动画
  animate()
  
  // 监听窗口大小变化
  const handleResize = () => {
    if (waveformCanvas.value && chartContainer.value) {
      waveformCanvas.value.width = chartContainer.value.clientWidth
    }
    if (spectrumCanvas.value && spectrumContainer.value) {
      spectrumCanvas.value.width = spectrumContainer.value.clientWidth
    }
  }
  
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
  }
})
</script>

<style scoped>
.vibration-waveform {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.waveform-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
}

.status-badges {
  display: flex;
  gap: 6px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sample-info {
  font-size: 12px;
  color: #94a3b8;
}

/* 数值卡片 */
.vibration-values {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.value-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(100, 116, 139, 0.2);
}

.value-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  color: #fff;
}

.x-axis .value-icon {
  background: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.y-axis .value-icon {
  background: rgba(34, 197, 94, 0.3);
  color: #22c55e;
}

.z-axis .value-icon {
  background: rgba(59, 130, 246, 0.3);
  color: #3b82f6;
}

.magnitude .value-icon {
  background: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

.temperature .value-icon {
  background: rgba(168, 85, 247, 0.3);
  color: #a855f7;
}

.value-content {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.value-number {
  font-size: 20px;
  font-weight: 700;
  color: #e2e8f0;
}

.value-unit {
  font-size: 12px;
  color: #94a3b8;
}

.value-stats {
  font-size: 11px;
  color: #64748b;
}

/* 图表容器 */
.chart-container {
  position: relative;
  height: 250px;
  background: #0f172a;
  border-radius: 8px;
  overflow: hidden;
}

.waveform-canvas {
  width: 100%;
  height: 100%;
}

.chart-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(15, 23, 42, 0.9);
  color: #64748b;
}

/* 频谱部分 */
.spectrum-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.spectrum-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.spectrum-title {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
}

.spectrum-chart {
  height: 150px;
  background: #0f172a;
  border-radius: 8px;
  overflow: hidden;
}

.spectrum-canvas {
  width: 100%;
  height: 100%;
}

/* 统计信息 */
.statistics-section {
  background: rgba(30, 41, 59, 0.3);
  border-radius: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 12px;
}

.stats-column h4 {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(100, 116, 139, 0.2);
}

.stats-row {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: 12px;
}

.stats-label {
  color: #94a3b8;
}

.stats-value {
  color: #e2e8f0;
  font-weight: 500;
  font-family: monospace;
}

@media (max-width: 1200px) {
  .vibration-values {
    grid-template-columns: repeat(3, 1fr);
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .vibration-values {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .waveform-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
