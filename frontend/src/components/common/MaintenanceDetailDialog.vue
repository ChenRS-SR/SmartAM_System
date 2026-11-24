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
          {{ measurements ? '评估参数' : '未接入' }}
        </el-tag>
      </div>
      <div class="detail-info-grid">
        <div class="detail-info-card">
          <div class="detail-info-label">当前风险指标 W</div>
          <div class="detail-info-value" style="color: #c026d3;">
            {{ fmt(chartData.currentW) }}
          </div>
        </div>
        <div class="detail-info-card">
          <div class="detail-info-label">经济阈值 WL</div>
          <div class="detail-info-value" style="color: #3b82f6;">
            {{ fmt(chartData.currentWL) }}
          </div>
        </div>
        <div class="detail-info-card">
          <div class="detail-info-label">可靠性阈值 WR</div>
          <div class="detail-info-value" style="color: #06b6d4;">
            {{ fmt(chartData.currentWR) }}
          </div>
        </div>
        <div class="detail-info-card">
          <div class="detail-info-label">维修阈值上限 WU</div>
          <div class="detail-info-value" style="color: #ef4444;">
            {{ fmt(chartData.currentWU) }}
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { amVar } from '@/utils/themeColor'
import { onBeforeUnmount, computed, nextTick, ref, watch } from 'vue'
import { ArrowLeft, ArrowRight, TrendCharts, Cpu } from '@element-plus/icons-vue'

const props = defineProps({
  measurements: {type:Object, default:null},
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
let chartRevision = 0
let resizeObserver = null

const dialogTitle = computed(() => `${props.systemName} - 监测融合指标与阈值关系`)

// 未绑定该设备的运维模型时显示空图，不生成随机风险曲线。
const chartData = computed(() => props.measurements || {
  duration: [], wValues: [], wlValues: [], wrValues: [], wuValues: [],
  currentW: null, currentWL: null, currentWR: null, currentWU: null
})
const fmt = value => Number.isFinite(value) ? value.toFixed(2) : '—'

const statusTag = computed(() => {
  const { currentW, currentWL, currentWU } = chartData.value
  if (![currentW, currentWL, currentWU].every(Number.isFinite)) return {type: 'info', label: '评估数据未接入'}
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
        color: amVar('--am-text'),
        fontSize: 16,
        fontWeight: 600
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: amVar('--am-card-bg'),
      borderColor: amVar('--am-card-border'),
      textStyle: { color: amVar('--am-text') },
      axisPointer: {
        type: 'cross',
        lineStyle: { color: amVar('--am-card-border') }
      }
    },
    legend: {
      data: ['监测点风险指标 W', '经济阈值 WL', '可靠性阈值 WR', '维修阈值上限 WU'],
      top: 44,
      type: 'scroll',
      textStyle: { color: amVar('--am-text-2') }
    },
    grid: {
      left: 12,
      right: 18,
      top: 90,
      bottom: 50,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      name: 'duration',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: { color: amVar('--am-text-2') },
      data: data.duration,
      axisLine: { lineStyle: { color: amVar('--am-card-border') } },
      axisLabel: { color: amVar('--am-text-2') },
      splitLine: { show: true, lineStyle: { color: amVar('--am-card-border-2') } }
    },
    yAxis: {
      type: 'value',
      name: '风险指标 W',
      nameTextStyle: { color: amVar('--am-text-2') },
      axisLine: { lineStyle: { color: amVar('--am-card-border') } },
      axisLabel: { color: amVar('--am-text-2') },
      splitLine: { lineStyle: { color: amVar('--am-card-border-2') } }
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
  disposeChart()
  const revision = chartRevision
  await nextTick()

  if (!echartsModule) {
    echartsModule = await import('echarts')
  }
  const echarts = echartsModule.default || echartsModule

  // 异步加载期间关闭或离开页面时，禁止在已销毁的容器上创建图表。
  if (revision !== chartRevision || !visible.value || !chartContainer.value) return
  chartInstance = echarts.init(chartContainer.value, null, { renderer: 'canvas' })
  chartInstance.setOption(buildChartOption())
  resizeObserver = new ResizeObserver(() => chartInstance?.resize())
  resizeObserver.observe(chartContainer.value)
}

const disposeChart = () => {
  chartRevision += 1
  resizeObserver?.disconnect()
  resizeObserver = null
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

watch(() => props.modelValue, value => { if (!value) disposeChart() })
onBeforeUnmount(disposeChart)

watch(() => [props.systemKey, props.systemName, props.deviceName, props.measurements], () => {
  if (visible.value && chartInstance) {
    chartInstance.setOption(buildChartOption(), true)
  }
})

defineExpose({
  initChart,
  disposeChart
})
</script>

<style>
.maintenance-detail-dialog {
  --el-dialog-bg-color: var(--am-card-bg) !important;
  --el-dialog-box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6) !important;
  background: var(--am-card-bg) !important;
  border: 1px solid color-mix(in srgb, var(--am-accent) 35%, transparent);
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
}

.maintenance-detail-dialog .el-dialog__header {
  --el-dialog-title-font-size: 16px;
  margin-right: 0;
  padding: 16px 20px;
  background: var(--am-card-bg) !important;
  border-bottom: 1px solid var(--am-card-border);
}

.maintenance-detail-dialog .el-dialog__title {
  color: var(--am-text) !important;
}

.maintenance-detail-dialog .el-dialog__footer {
  background: var(--am-card-bg) !important;
  border-top: 1px solid var(--am-card-border);
}

.maintenance-detail-dialog .el-dialog__body {
  padding: 20px;
  background: var(--am-card-bg) !important;
  color: var(--am-text);
}

.maintenance-detail-dialog .el-dialog__headerbtn .el-dialog__close {
  color: var(--am-text-2);
}

.maintenance-detail-dialog .el-dialog__headerbtn:hover .el-dialog__close {
  color: var(--am-text);
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
  color: var(--am-text);
}

.detail-title .system-name {
  color: var(--am-accent);
  margin-right: 6px;
}

.detail-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--am-text-2);
}

.detail-breadcrumb .el-icon {
  font-size: 12px;
  color: var(--am-text-3);
}

.detail-panel {
  background: var(--am-card-bg);
  border: 1px solid var(--am-card-border);
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
  border-bottom: 1px solid color-mix(in srgb, var(--am-accent) 10%, transparent);
}

.detail-panel-header h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--am-text);
}

.detail-panel-header h3 .el-icon {
  color: var(--am-accent);
}

.detail-chart-container {
  width: 100%;
  height: 420px;
  border-radius: 8px;
  background: var(--am-card-bg-2);
  border: 1px solid var(--am-card-border-2);
  overflow: hidden;
}

.detail-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 20px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--am-card-border-2);
}

.detail-legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--am-text-2);
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
  background: var(--am-card-bg-2);
  border-radius: 10px;
  border: 1px solid var(--am-card-border-2);
  text-align: center;
}

.detail-info-label {
  font-size: 12px;
  color: var(--am-text-2);
  margin-bottom: 8px;
}

.detail-info-value {
  font-size: 22px;
  font-weight: 700;
  font-family: 'Courier New', monospace;
}

.backend-tag {
  background: color-mix(in srgb, var(--am-accent) 18%, transparent) !important;
  color: var(--am-accent) !important;
  border: 1px solid color-mix(in srgb, var(--am-accent) 30%, transparent) !important;
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
