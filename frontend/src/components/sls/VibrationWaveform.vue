<template>
  <el-card class="vibration-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">
          <el-icon><Odometer /></el-icon>
          振动波形监测
        </span>
        <div class="header-stats" v-if="latestVibration">
          <el-tag size="small" type="info">X: {{ latestVibration.x?.toFixed(3) || '0.000' }}</el-tag>
          <el-tag size="small" type="info">Y: {{ latestVibration.y?.toFixed(3) || '0.000' }}</el-tag>
          <el-tag size="small" type="info">Z: {{ latestVibration.z?.toFixed(3) || '0.000' }}</el-tag>
          <el-tag size="small" :type="amplitudeTagType">幅度: {{ amplitude.toFixed(3) }}</el-tag>
        </div>
      </div>
    </template>
    
    <div class="vibration-content">
      <div ref="chartRef" class="waveform-chart"></div>
      
      <div class="vibration-stats">
        <div class="stat-item">
          <span class="stat-label">采样数:</span>
          <span class="stat-value">{{ waveformData?.sample_count || 0 }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">状态:</span>
          <el-tag :type="enabled ? (connected ? 'success' : 'danger') : 'info'" size="small">
            {{ enabled ? (connected ? '监测中' : '未连接') : '已禁用' }}
          </el-tag>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Odometer } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

const props = defineProps({
  waveformData: {
    type: Object,
    default: () => ({ x: [], y: [], z: [], sample_count: 0 })
  },
  latestVibration: {
    type: Object,
    default: null
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

const chartRef = ref(null)
let chart = null

const amplitude = computed(() => {
  if (!props.latestVibration) return 0
  return Math.sqrt(
    Math.pow(props.latestVibration.x || 0, 2) +
    Math.pow(props.latestVibration.y || 0, 2) +
    Math.pow(props.latestVibration.z || 0, 2)
  )
})

const amplitudeTagType = computed(() => {
  const amp = amplitude.value
  if (amp < 0.1) return 'success'
  if (amp < 0.5) return 'warning'
  return 'danger'
})

const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value)
  
  const option = {
    backgroundColor: 'transparent',
    grid: {
      top: 20,
      right: 20,
      bottom: 30,
      left: 50
    },
    xAxis: {
      type: 'category',
      data: [],
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#64748b' }
    },
    yAxis: {
      type: 'value',
      name: '振动速度(m/s)',
      nameTextStyle: { color: '#94a3b8' },
      axisLine: { lineStyle: { color: '#475569' } },
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: '#1e293b' } }
    },
    series: [
      {
        name: 'X轴',
        type: 'line',
        data: [],
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#ef4444', width: 2 }
      },
      {
        name: 'Y轴',
        type: 'line',
        data: [],
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#22c55e', width: 2 }
      },
      {
        name: 'Z轴',
        type: 'line',
        data: [],
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#3b82f6', width: 2 }
      }
    ],
    legend: {
      data: ['X轴', 'Y轴', 'Z轴'],
      textStyle: { color: '#94a3b8' },
      top: 0
    }
  }
  
  chart.setOption(option)
}

const updateChart = () => {
  if (!chart) return
  
  const x = props.waveformData?.x || []
  const y = props.waveformData?.y || []
  const z = props.waveformData?.z || []
  
  // 生成时间标签
  const labels = x.map((_, i) => i)
  
  chart.setOption({
    xAxis: { data: labels },
    series: [
      { data: x },
      { data: y },
      { data: z }
    ]
  })
}

watch(() => props.waveformData, updateChart, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chart?.resize())
})

onUnmounted(() => {
  chart?.dispose()
  window.removeEventListener('resize', () => chart?.resize())
})
</script>

<style scoped>
.vibration-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.vibration-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.waveform-chart {
  width: 100%;
  height: 250px;
}

.vibration-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-label {
  font-size: 13px;
  color: #94a3b8;
}

.stat-value {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  font-family: 'Courier New', monospace;
}

@media (max-width: 768px) {
  .header-stats {
    width: 100%;
  }
  
  .waveform-chart {
    height: 200px;
  }
}
</style>
