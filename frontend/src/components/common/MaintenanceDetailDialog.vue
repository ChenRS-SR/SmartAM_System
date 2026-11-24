<template>
  <el-dialog v-model="visible" :title="`${deviceName} · ${systemName}维护详情`" width="90%" top="5vh" destroy-on-close class="maintenance-detail-dialog" @opened="initChart" @closed="disposeChart">
    <div class="detail-panel">
      <div class="detail-panel-header"><h3>{{ isPLP ? '可靠性与下限' : '风险指标 W 与阈值关系' }}</h3><el-tag :type="statusTag.type">{{ statusTag.label }}</el-tag></div>
      <p class="detail-context">{{ organizationLabel }} / {{ deviceName }} / {{ measurements?.task || '暂无评估任务' }}</p>
      <div ref="chartContainer" class="detail-chart-container"></div>
    </div>
    <div class="detail-panel">
      <div class="detail-panel-header"><h3>当前维护评估参数</h3></div>
      <div class="detail-info-grid"><div v-for="item in metrics" :key="item.label" class="detail-info-card"><div class="detail-info-label">{{ item.label }}</div><div class="detail-info-value">{{ item.value }}</div></div></div>
    </div>
  </el-dialog>
</template>
<script setup>
import { amVar } from '@/utils/themeColor'
import { onBeforeUnmount, computed, nextTick, ref, watch } from 'vue'
const props = defineProps({
  measurements: {type: Object, default: null}, modelValue: Boolean,
  systemKey: {type: String, default: ''}, systemName: {type: String, default: ''},
  deviceName: {type: String, default: ''}, organizationLabel: {type: String, default: ''}
})
const emit = defineEmits(['update:modelValue'])
const visible = computed({get: () => props.modelValue, set: value => emit('update:modelValue', value)})
const chartContainer = ref(null)
let chartInstance = null
let echartsModule = null
let chartRevision = 0
let resizeObserver = null
const isPLP = computed(() => props.measurements?.model === 'PLP')
const statusTag = computed(() => props.measurements?.status || {type: 'info', label: '评估数据未接入'})
const fmt = value => Number.isFinite(value) ? value.toFixed(3) : '—'
const percent = value => Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : '—'
const metrics = computed(() => {
  const data = props.measurements
  if (!data) return []
  const risk = isPLP.value ? [] : [['风险指标 W', data.w], ['经济阈值 WL', data.wl], ['可靠性阈值 WR', data.wr], ['维修阈值上限 WU', data.wu]].map(([label, value]) => ({label, value: fmt(value)}))
  return [...risk, {label: '可靠性 R', value: percent(data.reliability)}, {label: '可靠性下限 Rmin', value: percent(data.rmin)}, {label: `役龄（${data.unit}）`, value: fmt(data.age)}]
})
const buildChartOption = () => {
  const data = props.measurements
  const definitions = isPLP.value
    ? [['reliability', '可靠性 R', '#4686b8'], ['rmin', '可靠性下限 Rmin', '#dc4545']]
    : [['w', '风险指标 W', '#7189ba'], ['wl', '经济阈值 WL', '#4686b8'], ['wr', '可靠性阈值 WR', '#18a2a4'], ['wu', '维修阈值上限 WU', '#dc4545']]
  return {
    backgroundColor: 'transparent',
    tooltip: {trigger: 'axis', confine: true, backgroundColor: amVar('--am-card-bg'), textStyle: {color: amVar('--am-text')}, valueFormatter: value => value == null ? '—' : Number(value).toFixed(4)},
    legend: {top: 12, left: 'center', type: 'scroll', itemWidth: 36, itemHeight: 16, itemGap: 22, textStyle: {color: amVar('--am-text-2'), fontSize: 15}},
    grid: {left: 14, right: 20, top: 64, bottom: 72, containLabel: true},
    xAxis: {type: 'category', data: data?.duration || [], axisLabel: {color: amVar('--am-text-2'), formatter: value => `${value.slice(0,4)}-${value.slice(4,6)}-${value.slice(6,8)}`}},
    yAxis: {type: 'value', name: isPLP.value ? '可靠性 R' : '风险指标 W', ...(isPLP.value ? {min:0, max:1} : {}), nameTextStyle: {color: amVar('--am-text-2')}, axisLabel: {color: amVar('--am-text-2')}, splitLine: {lineStyle: {color: amVar('--am-card-border')}}},
    dataZoom: [{type: 'inside'}, {type: 'slider', bottom: 8, height: 22, textStyle: {color: amVar('--am-text-2')}}],
    // 曲线始终绘制每个任务的数据点，与图例的圆点线段保持一致。
    series: definitions.map(([key, name, color], index) => ({name, type: 'line', data: (data?.history || []).map(row => row[key] ?? null), connectNulls: false, symbol: 'circle', symbolSize: 7, showSymbol: true, showAllSymbol: true, lineStyle: {color, width: 2, type: index ? 'dashed' : 'solid'}, itemStyle: {color}}))
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
  --el-dialog-bg-color: var(--am-card-bg);
  background: var(--am-card-bg); color: var(--am-text);
  border: 1px solid var(--am-card-border); border-radius: 4px;
}
.maintenance-detail-dialog .el-dialog__title,.maintenance-detail-dialog .el-dialog__body {color:var(--am-text)}
.detail-panel {padding:18px;margin-bottom:16px;border:1px solid var(--am-card-border);border-radius:4px}
.detail-panel:last-child {margin-bottom:0}
.detail-panel-header {display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.detail-panel-header h3 {margin:0;font-size:16px;font-weight:600}
.detail-context {color:var(--am-text-2);overflow-wrap:anywhere}
.detail-chart-container {width:100%;height:420px;background:var(--am-card-bg-2);border:1px solid var(--am-card-border-2);border-radius:4px;overflow:hidden}
.detail-info-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:16px}
.detail-info-card {padding:16px;background:var(--am-card-bg-2);border:1px solid var(--am-card-border-2);border-radius:4px;text-align:center}
.detail-info-label {font-size:13px;color:var(--am-text-2);margin-bottom:8px}
.detail-info-value {font-size:22px;font-weight:600;font-variant-numeric:tabular-nums}
@media(max-width:640px){.detail-panel{padding:12px}.detail-chart-container{height:320px}.detail-info-grid{grid-template-columns:1fr}}
</style>
