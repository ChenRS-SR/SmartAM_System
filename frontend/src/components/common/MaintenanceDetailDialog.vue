<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="90%"
    top="5vh"
    :close-on-click-modal="true"
    destroy-on-close
    class="maintenance-detail-dialog"
    @opened="initChart"
    @closed="disposeChart"
  >
    <template #header>
      <div class="detail-header">
        <el-button size="small" @click="visible = false">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <div>
          <h2 class="detail-title">
            <span class="system-name">{{ systemName }}</span>监测融合指标与阈值关系
          </h2>
          <div class="detail-breadcrumb">
            <span>{{ organizationLabel }}</span>
            <el-icon><ArrowRight /></el-icon>
            <span>{{ deviceName }}</span>
            <el-icon><ArrowRight /></el-icon>
            <span>{{ systemName }}</span>
          </div>
        </div>
      </div>
    </template>

    <div class="detail-panel">
      <div class="detail-panel-header">
        <h3>
          <el-icon><TrendCharts /></el-icon>
          风险指标 W 与阈值关系
        </h3>
        <el-tag :type="statusTag.type" size="small" effect="dark">
          {{ statusTag.label }}
        </el-tag>
      </div>
      <div ref="chartContainer" class="detail-chart-container"></div>
      <div class="detail-legend">
        <div class="detail-legend-item">
          <div class="detail-legend-symbol" style="background: #c026d3;"></div>
          <span>监测点风险指标 W</span>
        </div>
        <div class="detail-legend-item">
          <div class="detail-legend-line" style="border-top-color: #3b82f6;"></div>
          <span>经济阈值 WL</span>
        </div>
        <div class="detail-legend-item">
          <div class="detail-legend-line" style="border-top-color: #06b6d4;"></div>
          <span>可靠性阈值 WR</span>
        </div>
        <div class="detail-legend-item">
          <div class="detail-legend-line" style="border-top-color: #ef4444;"></div>
          <span>维修阈值上限 WU</span>
        </div>
      </div>
    </div>

    <div class="detail-panel">
      <div class="detail-panel-header">
        <h3>
          <el-icon><Cpu /></el-icon>
          当前监测与决策参数
        </h3>
        <el-tag type="info" size="small" effect="plain" class="backend-tag">
          后端计算预留接口
        </el-tag>
      </div>
      <div class="detail-info-grid">
        <div class="detail-info-card">
          <div class="detail-info-label">当前风险指标 W</div>
          <div class="detail-info-value" style="color: #c026d3;">
            {{ chartData.currentW.toFixed(2) }}
          </div>
        </div>
        <div class="detail-info-card">
          <div class="detail-info-label">经济阈值 WL</div>
          <div class="detail-info-value" style="color: #3b82f6;">
            {{ chartData.currentWL.toFixed(2) }}
          </div>
        </div>
        <div class="detail-info-card">
          <div class="detail-info-label">可靠性阈值 WR</div>
          <div class="detail-info-value" style="color: #06b6d4;">
            {{ chartData.currentWR.toFixed(2) }}
          </div>
        </div>
        <div class="detail-info-card">
          <div class="detail-info-label">维修阈值上限 WU</div>
          <div class="detail-info-value" style="color: #ef4444;">
            {{ chartData.currentWU.toFixed(2) }}
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowLeft, ArrowRight, TrendCharts, Cpu } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  systemKey: {
    type: String,
    default: 'filter'
  },
  systemName: {
    type: String,
    default: '高效滤芯'
  },
  deviceName: {
    type: String,
    default: 'SLM 设备'
  },
  organizationLabel: {
    type: String,
    default: '全部单位'
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const chartContainer = ref(null)
let chartInstance = null
let echartsModule = null

const dialogTitle = computed(() => `${props.systemName} - 监测融合指标与阈值关系`)

/**
 * 生成系统级阈值关系模拟数据
 * 与 F:\课题4\课题4界面设计\index.html 中的 generateSystemThresholdData 保持一致
 */
const generateSystemThresholdData = (systemKey) => {
  const points = 25
  const duration = []
  const wValues = []
  const wlValues = []
  const wrValues = []
  const wuValues = []

  const factor = {
    filter: 1.0,
    argon: 1.15,
    powder: 0.9,
    feeder: 0.85,
    laser: 0.7,
    fan: 1.05
  }[systemKey] || 1.0

  for (let i = 0; i < points; i++) {
    const x = i * 3.5
    duration.push(+x.toFixed(1))

    wValues.push(+(Math.sin(i * 0.35) * 0.12 - 0.42 + (Math.random() - 0.5) * 0.08).toFixed(2))
    wlValues.push(+(0.10 - 0.036 * i * factor).toFixed(2))
    wrValues.push(+(2.8 * Math.exp(-0.075 * i * factor) - 0.25).toFixed(2))
    wuValues.push(+(0.40 - 0.025 * i * factor).toFixed(2))
  }

  return {
    duration,
    wValues,
    wlValues,
    wrValues,
    wuValues,
    currentW: wValues[wValues.length - 1],
    currentWL: wlValues[wlValues.length - 1],
    currentWR: wrValues[wrValues.length - 1],
    currentWU: wuValues[wuValues.length - 1]
  }
}

const chartData = computed(() => generateSystemThresholdData(props.systemKey))

const statusTag = computed(() => {
  const { currentW, currentWL, currentWU } = chartData.value
  if (currentW >= currentWU) {
    return { type: 'danger', label: '超维修阈值' }
  }
  if (currentW >= currentWL) {
    return { type: 'warning', label: '预警' }
  }
  return { type: 'success', label: '正常' }
})

const buildChartOption = () => {
  const data = chartData.value
  return {
    backgroundColor: 'transparent',
    title: {
      text: `${props.deviceName} - ${props.systemName} 风险指标趋势`,
      left: 'center',
      top: 12,
      textStyle: {
        color: '#e2e8f0',
        fontSize: 16,
        fontWeight: 600
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      borderColor: 'rgba(0, 212, 255, 0.3)',
      textStyle: { color: '#e2e8f0' },
      axisPointer: {
        type: 'cross',
        lineStyle: { color: 'rgba(0, 212, 255, 0.3)' }
      }
    },
    legend: {
      data: ['监测点风险指标 W', '经济阈值 WL', '可靠性阈值 WR', '维修阈值上限 WU'],
      top: 44,
      textStyle: { color: '#94a3b8' }
    },
    grid: {
      left: 60,
      right: 40,
      top: 90,
      bottom: 50,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      name: 'duration',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: { color: '#94a3b8' },
      data: data.duration,
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.3)' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { show: true, lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }
    },
    yAxis: {
      type: 'value',
      name: '风险指标 W',
      nameTextStyle: { color: '#94a3b8' },
      axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.3)' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }
    },
    series: [
      {
        name: '监测点风险指标 W',
        type: 'line',
        data: data.wValues,
        symbol: 'rect',
        symbolSize: 10,
        lineStyle: { color: '#c026d3', width: 2, type: 'dashed' },
        itemStyle: { color: '#c026d3' }
      },
      {
        name: '经济阈值 WL',
        type: 'line',
        data: data.wlValues,
        symbol: 'none',
        lineStyle: { color: '#3b82f6', width: 2, type: 'dashed' }
      },
      {
        name: '可靠性阈值 WR',
        type: 'line',
        data: data.wrValues,
        symbol: 'none',
        lineStyle: { color: '#06b6d4', width: 2, type: 'dashed' }
      },
      {
        name: '维修阈值上限 WU',
        type: 'line',
        data: data.wuValues,
        symbol: 'none',
        lineStyle: { color: '#ef4444', width: 2, type: 'dashed' }
      }
    ]
  }
}

const initChart = async () => {
  if (!chartContainer.value) return
  await nextTick()

  if (!echartsModule) {
    echartsModule = await import('echarts')
  }
  const echarts = echartsModule.default || echartsModule

  disposeChart()
  chartInstance = echarts.init(chartContainer.value, 'dark', { renderer: 'canvas' })
  chartInstance.setOption(buildChartOption())
}

const disposeChart = () => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

watch(() => props.modelValue, (value) => {
  if (value) {
    window.addEventListener('resize', handleResize)
  } else {
    window.removeEventListener('resize', handleResize)
  }
})

watch(() => [props.systemKey, props.systemName, props.deviceName], () => {
  if (visible.value && chartInstance) {
    chartInstance.setOption(buildChartOption(), true)
  }
})

defineExpose({
  initChart,
  disposeChart
})
</script>

<style scoped>
.maintenance-detail-dialog :deep(.el-dialog) {
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.maintenance-detail-dialog :deep(.el-dialog__header) {
  margin-right: 0;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(100, 116, 139, 0.2);
}

.maintenance-detail-dialog :deep(.el-dialog__body) {
  padding: 20px;
  color: #e2e8f0;
}

.maintenance-detail-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: #94a3b8;
}

.maintenance-detail-dialog :deep(.el-dialog__headerbtn:hover .el-dialog__close) {
  color: #e2e8f0;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.detail-title {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: #e2e8f0;
}

.detail-title .system-name {
  color: #00d4ff;
  margin-right: 6px;
}

.detail-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #94a3b8;
}

.detail-breadcrumb .el-icon {
  font-size: 12px;
  color: #64748b;
}

.detail-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 10px;
  padding: 18px;
  margin-bottom: 16px;
}

.detail-panel:last-child {
  margin-bottom: 0;
}

.detail-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.detail-panel-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.detail-panel-header h3 .el-icon {
  color: #00d4ff;
}

.detail-chart-container {
  width: 100%;
  height: 420px;
  border-radius: 8px;
  background: rgba(30, 41, 59, 0.3);
  border: 1px solid rgba(100, 116, 139, 0.2);
  overflow: hidden;
}

.detail-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 20px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(100, 116, 139, 0.2);
}

.detail-legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #94a3b8;
}

.detail-legend-line {
  width: 24px;
  height: 0;
  border-top: 3px dashed;
  border-radius: 2px;
}

.detail-legend-symbol {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.detail-info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.detail-info-card {
  padding: 16px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 10px;
  border: 1px solid rgba(100, 116, 139, 0.2);
  text-align: center;
}

.detail-info-label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.detail-info-value {
  font-size: 22px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

.backend-tag {
  background: rgba(0, 212, 255, 0.15) !important;
  color: #00d4ff !important;
  border: 1px solid rgba(0, 212, 255, 0.3) !important;
}

@media (max-width: 900px) {
  .detail-info-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .detail-title {
    font-size: 16px;
  }

  .detail-chart-container {
    height: 320px;
  }

  .detail-info-grid {
    grid-template-columns: 1fr;
  }

  .detail-legend {
    gap: 12px;
  }
}
</style>
