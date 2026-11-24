<template>
  <el-card class="maintenance-panel" shadow="never">
    <template #header><div class="maintenance-heading"><span>视情维护可视化</span><el-tag :type="overall.type">{{ overall.label }}</el-tag></div></template>
    <div v-if="records.length" class="assessment-toolbar">
      <label for="maintenance-task">评估任务</label>
      <select id="maintenance-task" v-model="selectedTask"><option v-for="row in records" :key="row.task" :value="row.task">{{ row.task }}</option></select>
      <span>{{ records.length }} 条任务记录</span>
    </div>
    <div class="systems-grid">
      <button v-for="system in systems" :key="system.key" class="system-card" :aria-label="`${system.name}维护详情`" @click="openDetail(system)">
        <div class="system-title"><strong>{{ system.name }}</strong><span>{{ system.model || '—' }}</span></div>
        <template v-if="system.model === 'PHM'">
          <div class="risk-track">
            <i v-for="field in ['wl', 'wr', 'wu'].filter(key => Number.isFinite(system[key]))" :key="field" :class="field" :style="{ left: riskPosition(system, system[field]) + '%' }" :title="`${field.toUpperCase()} ${fmt(system[field])}`"></i>
            <b v-if="Number.isFinite(system.w)" class="risk-point" :style="{ left: riskPosition(system, system.w) + '%' }" :title="`W ${fmt(system.w)}`"></b>
          </div>
          <div class="metric-grid"><span>风险 W <b>{{ fmt(system.w) }}</b></span><span>经济 WL <b>{{ fmt(system.wl) }}</b></span><span>可靠性 WR <b>{{ fmt(system.wr) }}</b></span><span>维修 WU <b>{{ fmt(system.wu) }}</b></span></div>
        </template>
        <div class="reliability-row"><span>可靠性 R</span><strong>{{ percent(system.reliability) }}</strong></div>
        <div class="reliability-track"><div :style="{width: `${(system.reliability || 0) * 100}%`, background: reliabilityColor(system)}"></div></div>
        <div class="age-row"><span>下限 {{ percent(system.rmin) }}</span><span>役龄 {{ fmt(system.age) }} {{ system.unit }}</span></div>
        <el-tag :type="maintenanceStatus(system).type">{{ maintenanceStatus(system).label }}</el-tag>
      </button>
    </div>
    <div class="maintenance-advice"><strong>维护建议</strong><p v-for="system in attention" :key="system.key">{{ system.name }}：{{ maintenanceStatus(system).label }}，建议安排维护检查。</p><p v-if="!attention.length">{{ records.length ? '继续监测各子系统状态。' : '暂无已接入的维护评估。' }}</p></div>
    <p v-if="statisticsError" role="alert">{{ statisticsError }}</p>
    <div class="statistics-section"><div><span>累计发生故障任务</span><strong>{{ statistics.totalFaults }}</strong></div><div><span>维护记录次数</span><strong>{{ statistics.preventiveRepairs }}</strong></div><div><span>故障任务率</span><strong>{{ statistics.rateText }}%</strong></div></div>
    <MaintenanceDetailDialog v-model="detailVisible" :system-key="detailKey" :system-name="detail?.name || ''" :device-name="deviceName" :organization-label="organizationLabel" :measurements="detail" />
  </el-card>
</template>
<script setup>
import { computed, ref, watch } from 'vue'
import MaintenanceDetailDialog from './MaintenanceDetailDialog.vue'
import { useMaintenanceStatistics } from '../../composables/useMaintenanceStatistics'
import { maintenanceSystems, maintenanceRecords, initialMaintenanceTask, maintenanceStatus, maintenanceMeasurements, riskPosition } from '../../utils/maintenanceAssessment'
const props = defineProps({ deviceId: {type: String, default: ''}, deviceName: {type: String, default: ''}, organizationLabel: {type: String, default: ''} })
const records = computed(() => maintenanceRecords(props.deviceId))
const selectedTask = ref('')
const detailVisible = ref(false)
const detailKey = ref('powder')
watch(() => props.deviceId, id => { selectedTask.value = initialMaintenanceTask(id); detailVisible.value = false }, {immediate: true})
const systems = computed(() => records.value.find(row => row.task === selectedTask.value)?.systems || maintenanceSystems.map(([key, name]) => ({key, name})))
const attention = computed(() => systems.value.filter(system => maintenanceStatus(system).rank > 0))
const overall = computed(() => {
  if (!records.value.length) return {type: 'info', label: '评估数据未接入'}
  const status = systems.value.map(maintenanceStatus).sort((a,b) => b.rank - a.rank)[0]
  if (status.rank > 0) return {type: status.type, label: '存在维护需求'}
  if (systems.value.some(system => maintenanceStatus(system).rank < 0)) return {type: 'info', label: '部分评估数据缺失'}
  return {type: 'success', label: '持续监测'}
})
const detail = computed(() => maintenanceMeasurements(records.value, selectedTask.value, detailKey.value))
function openDetail(system) { detailKey.value = system.key; detailVisible.value = true }
const fmt = value => Number.isFinite(value) ? value.toFixed(3) : '—'
const percent = value => Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : '—'
const reliabilityColor = system => !Number.isFinite(system.reliability) ? '#87919d' : system.reliability < system.rmin ? '#dc4545' : '#31966c'
const { statistics, error: statisticsError } = useMaintenanceStatistics(() => props.deviceId ? [props.deviceId] : null)
</script>
<style scoped>
.maintenance-panel {color:var(--am-text);background:var(--am-card-bg);border:1px solid var(--am-card-border)}
.maintenance-heading,.assessment-toolbar,.system-title,.reliability-row,.age-row {display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.maintenance-heading {font-size:18px;font-weight:600}
.assessment-toolbar {justify-content:flex-start;margin-bottom:18px;font-size:14px}
.assessment-toolbar select {min-height:38px;max-width:100%;padding:6px 12px;color:var(--am-text);background:var(--am-card-bg-2);border:1px solid var(--am-card-border);border-radius:4px}
.assessment-toolbar>span,.system-title>span,.age-row {color:var(--am-text-2);font-size:12px}
.systems-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:16px}
.system-card {display:flex;flex-direction:column;gap:12px;min-width:0;padding:16px;text-align:left;background:var(--am-card-bg-2);border:1px solid var(--am-card-border);border-radius:4px;color:var(--am-text);font:inherit;cursor:pointer}
.system-card:hover,.system-card:focus-visible {border-color:var(--am-accent)}
.system-title {font-size:15px}.system-card>.el-tag {align-self:flex-start;margin-top:auto}
.risk-track {position:relative;height:20px;margin:6px 0;background:linear-gradient(transparent 8px,var(--am-card-border) 8px,var(--am-card-border) 12px,transparent 12px)}
.risk-track i {position:absolute;height:20px;border-left:2px dashed;transform:translateX(-50%)}
.wl {color:#4686b8}.wr {color:#18a2a4}.wu {color:#dc4545}
.risk-point {position:absolute;top:5px;width:10px;height:10px;background:var(--am-text);border:1px solid var(--am-card-bg);transform:translateX(-50%)}
.metric-grid {display:grid;grid-template-columns:1fr 1fr;gap:8px 12px;font-size:12px}.metric-grid span {display:flex;justify-content:space-between;gap:6px;flex-wrap:wrap}
.reliability-row {margin-top:auto;font-size:13px}.reliability-row strong {font-size:20px}
.reliability-track {height:5px;background:var(--am-card-border)}.reliability-track>div {height:100%}
.maintenance-advice {margin-top:20px;padding:16px;border:1px solid var(--am-card-border);border-radius:4px;font-size:14px}.maintenance-advice p {margin:8px 0 0;line-height:1.6}
.statistics-section {display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:16px}.statistics-section>div {display:flex;flex-direction:column;gap:8px;padding:16px;border:1px solid var(--am-card-border);border-radius:4px}.statistics-section span {font-size:12px;color:var(--am-text-2)}.statistics-section strong {font-size:22px}
.system-card,.statistics-section {font-variant-numeric:tabular-nums}
@media(max-width:600px){.systems-grid,.statistics-section {grid-template-columns:1fr}.assessment-toolbar select {width:100%}}
</style>
