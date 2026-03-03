<template>
  <div class="chart-container">
    <div class="chart-header">
      <span class="chart-title">{{ title }}</span>
      <div class="chart-actions">
        <el-button size="small" type="primary" text @click="fetchTemperature" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新温度
        </el-button>
        <el-button size="small" type="info" text @click="clearData">
          <el-icon><Delete /></el-icon>
          清空
        </el-button>
      </div>
    </div>
    <div class="current-temps">
      <el-tag type="danger" effect="dark" size="small">
        喷嘴: {{ currentNozzleTemp.toFixed(1) }}°C / {{ currentNozzleTarget.toFixed(0) }}°C
      </el-tag>
      <el-tag type="success" effect="dark" size="small">
        热床: {{ currentBedTemp.toFixed(1) }}°C / {{ currentBedTarget.toFixed(0) }}°C
      </el-tag>
    </div>
    <div ref="chartRef" class="chart-body"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'
import { useDataStore } from '../stores/data'
import { useResponsive } from '../composables/useResponsive'
import { darkTheme } from '../utils/echarts-theme'
import { printerApi } from '../utils/api'
import { ElMessage } from 'element-plus'

const props = defineProps({
  title: { type: String, default: '温度曲线' },
  showMeltPool: { type: Boolean, default: true }
})

const store = useDataStore()
const { chartHeight } = useResponsive()
const chartRef = ref(null)
let chart = null

// 当前温度
const currentNozzleTemp = ref(0)
const currentNozzleTarget = ref(0)
const currentBedTemp = ref(0)
const currentBedTarget = ref(0)
const loading = ref(false)

const chartData = computed(() => {
  // 过滤掉熔池温度中的 0 值（替换为 null，在图表中不显示）
  const meltPoolData = store.historyData.meltPoolTemps.map(temp => 
    temp > 0 ? temp : null
  )
  
  return {
    timestamps: store.historyData.timestamps,
    nozzle: store.historyData.nozzleTemps,
    bed: store.historyData.bedTemps,
    nozzleTarget: store.historyData.nozzleTargetTemps,
    bedTarget: store.historyData.bedTargetTemps,
    meltPool: meltPoolData
  }
})

// 获取实时温度（仅更新当前显示，不添加历史点）
const fetchTemperature = async () => {
  loading.value = true
  try {
    const res = await printerApi.getTemperature()
    if (res.data.success) {
      currentNozzleTemp.value = res.data.nozzle.actual
      currentNozzleTarget.value = res.data.nozzle.target
      currentBedTemp.value = res.data.bed.actual
      currentBedTarget.value = res.data.bed.target
      
      // 不手动添加历史数据点，让 WebSocket 数据驱动图表更新
      // 这样避免重复数据和 0 值填充问题
      
      ElMessage.success('温度已更新')
    } else {
      ElMessage.warning(res.data.error || '获取温度失败')
    }
  } catch (e) {
    ElMessage.error('获取温度失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const initChart = () => {
  if (!chartRef.value) return
  
  chart = echarts.init(chartRef.value, null, { renderer: 'canvas' })
  
  const option = {
    backgroundColor: darkTheme.backgroundColor,
    color: darkTheme.color,
    textStyle: darkTheme.textStyle,
    grid: {
      top: 50,
      left: 60,
      right: 40,
      bottom: 40
    },
    tooltip: {
      trigger: 'axis',
      ...darkTheme.tooltip
    },
    legend: {
      data: [
        '喷嘴实际', '喷嘴目标',
        '热床实际', '热床目标',
        '熔池温度'
      ],
      ...darkTheme.legend,
      top: 5,
      itemWidth: 25,
      itemHeight: 10,
      textStyle: { fontSize: 11 }
    },
    xAxis: {
      type: 'category',
      data: [],
      boundaryGap: false,
      ...darkTheme.categoryAxis,
      axisLabel: {
        interval: 'auto',
        rotate: 0,
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: '温度 (°C)',
      nameTextStyle: { color: '#a0aec0', fontSize: 11 },
      min: 0,
      max: 300,
      interval: 50,
      ...darkTheme.valueAxis
    },
    series: [
      {
        name: '喷嘴实际',
        type: 'line',
        data: [],
        smooth: false,
        symbol: 'none',
        connectNulls: false,
        lineStyle: { color: '#ff4757', width: 2 },
      },
      {
        name: '喷嘴目标',
        type: 'line',
        data: [],
        smooth: false,
        symbol: 'none',
        connectNulls: false,
        lineStyle: { color: '#ff4757', width: 1.5, type: 'dashed', opacity: 0.7 },
      },
      {
        name: '热床实际',
        type: 'line',
        data: [],
        smooth: false,
        symbol: 'none',
        connectNulls: false,
        lineStyle: { color: '#2ed573', width: 2 },
      },
      {
        name: '热床目标',
        type: 'line',
        data: [],
        smooth: false,
        symbol: 'none',
        connectNulls: false,
        lineStyle: { color: '#2ed573', width: 1.5, type: 'dashed', opacity: 0.7 },
      },
      {
        name: '熔池温度',
        type: 'line',
        data: [],
        smooth: false,
        symbol: 'none',
        connectNulls: true,
        lineStyle: { color: '#ffa502', width: 1.5, type: 'dotted' },
      }
    ]
  }
  
  chart.setOption(option)
  
  // 响应式
  const resizeObserver = new ResizeObserver(() => {
    chart?.resize()
  })
  resizeObserver.observe(chartRef.value)
}

const updateChart = () => {
  if (!chart) return
  
  // 获取最新温度值用于图例显示
  const lastIdx = chartData.value.nozzle.length - 1
  const nozzleActual = lastIdx >= 0 ? chartData.value.nozzle[lastIdx] : 0
  const nozzleTarget = lastIdx >= 0 ? chartData.value.nozzleTarget[lastIdx] : 0
  const bedActual = lastIdx >= 0 ? chartData.value.bed[lastIdx] : 0
  const bedTarget = lastIdx >= 0 ? chartData.value.bedTarget[lastIdx] : 0
  
  chart.setOption({
    xAxis: { data: chartData.value.timestamps },
    legend: {
      formatter: function(name) {
        // 在图例中显示当前值
        if (name === '喷嘴实际') return `喷嘴: ${nozzleActual.toFixed(1)}°C`
        if (name === '喷嘴目标') return `目标: ${nozzleTarget.toFixed(0)}°C`
        if (name === '热床实际') return `热床: ${bedActual.toFixed(1)}°C`
        if (name === '热床目标') return `目标: ${bedTarget.toFixed(0)}°C`
        return name
      }
    },
    series: [
      { data: chartData.value.nozzle },       // 喷嘴实际
      { data: chartData.value.nozzleTarget }, // 喷嘴目标
      { data: chartData.value.bed },          // 热床实际
      { data: chartData.value.bedTarget },    // 热床目标
      { data: props.showMeltPool ? chartData.value.meltPool : [] } // 熔池
    ]
  })
}

const clearData = () => {
  store.clearHistory()
}

watch(chartData, updateChart, { deep: true })

// 定时刷新温度
let refreshInterval = null

onMounted(() => {
  initChart()
  fetchTemperature() // 初始获取
  // 每 5 秒自动刷新
  refreshInterval = setInterval(fetchTemperature, 5000)
})

onUnmounted(() => {
  chart?.dispose()
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.chart-container {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  overflow: hidden;
}

.chart-header {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  background: rgba(0, 0, 0, 0.2);
}

.chart-title {
  font-size: 14px;
  font-weight: 500;
  color: #00d4ff;
}

.current-temps {
  padding: 8px 16px;
  display: flex;
  gap: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.chart-body {
  height: v-bind(chartHeight + 'px');
  min-height: 200px;
  padding: 10px;
}
</style>
