<template>
  <div class="region-control">
    <section class="region-panel" aria-label="当前切片区域总览">
      <header><h2>当前切片区域</h2><span>第 {{ frame.layer ?? '—' }} 层</span><button v-if="isReplay" class="export-button" :disabled="exporting || !config" @click="exportCurrent">{{ exporting ? '正在导出…' : '导出当前接口数据' }}</button></header>
      <div class="region-overview">
        <img v-if="slice?.annotatedImage" class="slice-illustration" :src="slice.annotatedImage" :alt="`第${frame.layer}层切片区域引线标注图，共${slice.regions.length}个区域`" />
        <p v-else class="unavailable" role="status">当前任务未登记切片区域，区域调控不可用。</p>
        <div class="region-list">
          <button v-for="region in (slice?.regions || [])" :key="region.id" :class="{selected: selectedId === region.id}" @click="selectedId = region.id" :aria-pressed="selectedId === region.id">
            <strong><i :style="{background:region.color}"></i>{{ region.name }}</strong>
            <span class="region-strategy" v-if="planFor(region.id)">策略{{ controlStrategies[planFor(region.id).strategy].number }} · {{ controlStrategies[planFor(region.id).strategy].name }}</span>
            <span>{{ planFor(region.id)?.status || '读取参数配置…' }}</span>
            <small v-if="planFor(region.id)?.strategy === 'adjust'">功率 {{ planFor(region.id).parameters.fill_power }} W · 速度 {{ planFor(region.id).parameters.fill_speed }} mm/s · 层间等待 {{ planFor(region.id).parameters.layer_wait_time }} s</small>
          </button>
        </div>
      </div>
    </section>
    <section class="region-panel" aria-label="层间调控策略1">
      <header><h2>层间调控策略1</h2><RegionBadge v-if="selectedRegion" :name="selectedRegion?.name" :color="selectedRegion?.color" /></header>
      <p v-if="error" class="config-error" role="alert">{{ error }} <button :disabled="submitting || refreshing" @click="config ? refreshPlans() : loadConfig()">重试</button></p>
      <div v-else-if="activePlan" class="region-parameters">
        <section aria-label="当前工艺参数"><h3>当前工艺参数</h3>
          <label v-for="key in paramKeys" :key="key">{{ paramDefs[key].label }} / {{ paramDefs[key].unit }}<input :value="activePlan.baseline[key]" readonly :aria-label="`当前${paramDefs[key].label}`" /></label>
        </section>
        <section class="adaptive-form" :class="{replaced:activePlan.strategy !== 'adjust'}" aria-label="自适应调整"><div class="adaptive-heading"><h3>自适应调整</h3><input :checked="activePlan.automatic" :disabled="submitting || refreshing || blocked" @change="submitStrategy('adjust', $event.target.checked)" type="checkbox" role="switch" aria-label="区域自适应调整" /></div>
          <template v-if="activePlan.strategy === 'adjust'">
          <label v-for="key in paramKeys" :key="key" :class="{changed:activePlan.parameters[key] !== activePlan.baseline[key]}">{{ paramDefs[key].label }} / {{ paramDefs[key].unit }}<input :value="activePlan.parameters[key]" readonly :aria-label="`自适应${paramDefs[key].label}`" /></label>
          </template>
          <div v-else class="strategy-replacement"><strong>层间调控策略{{ controlStrategies[activePlan.strategy].number }} · {{ controlStrategies[activePlan.strategy].name }}</strong><span>当前区域已切换策略，自适应参数调整已停用</span></div>
        </section>
        <p class="plan-status" aria-live="polite">{{ selectedRegion?.name }} · {{ activePlan.status }} · 第 {{ frame.layer ?? '—' }} 层</p>
      </div>
      <div v-else class="region-parameters unavailable-parameters">
        <section><h3>当前工艺参数</h3><label v-for="key in paramKeys" :key="key">{{ paramDefs[key].label }} / {{ paramDefs[key].unit }}<input disabled value="—" /></label></section>
        <section><div class="adaptive-heading"><h3>自适应调整</h3><input type="checkbox" role="switch" aria-label="区域自适应调整" disabled /></div><label v-for="key in paramKeys" :key="key">{{ paramDefs[key].label }} / {{ paramDefs[key].unit }}<input disabled value="—" /></label></section>
        <p class="note" role="status">{{ blocked ? '设备数据读取失败，调控已禁用' : !slice ? '未登记切片区域' : '正在读取工艺基准…' }}</p>
      </div>
    </section>
    <LayerStrategyPlaceholders :enabled="!!activePlan && !submitting && !refreshing && !error && !blocked" :active-strategy="activePlan?.strategy" :pending-strategy="pendingRegion === '*' || pendingRegion === selectedId ? pendingStrategy : ''" @strategy="submitStrategy" />
  </div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { controlParameterKeys as paramKeys, controlParameterDefs as paramDefs } from './controlParameters'
import { REPLAY_CASES } from '../../stores/replay'
import { task4Api } from '../../utils/task4Api'
import { readCurrentTask4, downloadTask4 } from '../../utils/exportTask4'
import { controlStrategies } from './controlStrategies'
import { ElMessage } from 'element-plus'
import LayerStrategyPlaceholders from './LayerStrategyPlaceholders.vue'
import RegionBadge from './RegionBadge.vue'
const props = defineProps({ frame: { type: Object, required: true }, slice: { type: Object, default: null }, blocked: { type: Boolean, default: false } })
const selectedId = ref(props.slice?.regions[0]?.id || '')
const config = ref(null)
const error = ref('')
// 跨层保留所选颜色区域；区域消失时选当前层首个真实区域，不保留旧层参数。
watch(() => props.slice, slice => {
  if (!slice?.regions.some(r => r.id === selectedId.value)) selectedId.value = slice?.regions[0]?.id || ''
})
const selectedRegion = computed(() => props.slice?.regions.find(r => r.id === selectedId.value))
const plans = ref([])
const planFor = id => plans.value.find(plan => plan.regionId === id)
const submitting = ref(false)
const refreshing = ref(false)
const pendingRegion = ref(''), pendingStrategy = ref('')
let disposed = false
const exporting = ref(false)
const configController = new AbortController()
const isReplay = computed(() => REPLAY_CASES.some(c => c.id === props.frame.caseId))
async function exportCurrent() {
  exporting.value = true
  const frame = props.frame
  const request = selection()
  try {
    const data = await readCurrentTask4(request.deviceId, frame, {currentParameters:request.currentParameters})
    downloadTask4(data)
  } catch (e) { ElMessage.error(e.message) }
  finally { exporting.value = false }
}
let previewController, actionController
const deviceId = computed(() => REPLAY_CASES.find(c => c.id === props.frame.caseId)?.deviceId || props.frame.caseId)
function selection() {
  const baseline = config.value.defaults
  const request = { deviceId: deviceId.value,
    currentParameters: { laserPower: baseline.fill_power, fillSpeed: baseline.fill_speed, layerWaitTime: baseline.layer_wait_time } }
  // 档案设备没有逐层模型数据；真实案例传当前游标，避免读取尚未到达的层结果。
  if (REPLAY_CASES.some(c => c.deviceId === deviceId.value)) {
    request.layerNo = props.frame.layer
    request.offset = props.frame.offset
    request.processingMode = props.frame.processing?.real ? 'real' : 'archive'
  }
  return request
}
const fields = p => ({fill_power:p.laserPower, fill_speed:p.fillSpeed, layer_wait_time:p.layerWaitTime})
async function refreshPlans() {
  previewController?.abort()
  if (!config.value || disposed || submitting.value || !props.slice || props.blocked) { plans.value = []; return }
  const controller = new AbortController()
  previewController = controller
  refreshing.value = true
  plans.value = []
  try {
    const data = await task4Api('quality-control', selection(), controller.signal)
    if (controller.signal.aborted || disposed) return
    plans.value = data.regions.map(r => ({...r, baseline:fields(r.currentParameters), parameters:fields(r.controlParameters)}))
    error.value = ''
  } catch (e) { if (e.name !== 'AbortError' && !controller.signal.aborted && !disposed) error.value = e.message }
  finally { if (previewController === controller) refreshing.value = false }
}
watch([() => props.frame.caseId, () => props.frame.layer, () => props.frame.recognition?.layer,
  () => props.frame.processing?.real, () => props.slice?.regions.map(r => r.id).join('|'), () => props.blocked, config], refreshPlans, { immediate:true })
async function submitStrategy(strategy, automatic = true) {
  if (submitting.value || refreshing.value || !activePlan.value || !config.value || !props.slice || props.blocked) return
  submitting.value = true
  error.value = ''
  previewController?.abort()
  const wholeLayer = controlStrategies[strategy].scope === 'layer'
  const request = {...selection(), strategy, automatic, regionIds:wholeLayer ? props.slice.regions.map(r => r.id) : [selectedId.value], operation:'save',
    requestId:`ui-${Date.now()}-${Math.random().toString(36).slice(2)}`}
  pendingRegion.value = wholeLayer ? '*' : selectedId.value
  pendingStrategy.value = strategy
  // 当前只提示提交过程；成功/失败结论留给后续真实执行器回执。
  ElMessage.info({message:`${wholeLayer ? '整层' : selectedRegion.value.name} · ${controlStrategies[strategy].name}应用中`, duration:2000})
  const controller = new AbortController()
  actionController = controller
  try {
    const plan = await task4Api('quality-control', request, controller.signal)
    await task4Api('quality-control', {deviceId:request.deviceId, planId:plan.planId, operation:'simulate'}, controller.signal)
  } catch (e) { if (e.name !== 'AbortError') error.value = e.message }
  finally {
    submitting.value = false
    pendingRegion.value = ''; pendingStrategy.value = ''
  }
  // 从持久化状态重读全部区域，旧的预览请求不得把已切换策略覆盖回策略1。
  if (!error.value && !disposed) await refreshPlans()
}
onUnmounted(() => { disposed = true; configController.abort(); previewController?.abort(); actionController?.abort() })
const activePlan = computed(() => plans.value.find(p => p.regionId === selectedId.value))
async function loadConfig() {
  try {
    const response = await fetch('/api/slm/control/config', {signal: configController.signal})
    if (!response.ok) throw new Error(`参数配置读取失败（${response.status}）`)
    const next = await response.json()
    if (!disposed) config.value = next
  } catch (e) { if (!disposed && e.name !== 'AbortError') error.value = e.message }
}
onMounted(loadConfig)
</script>
<style scoped>
.export-button { margin-left:auto; padding:6px 10px; border:1px solid var(--am-card-border); background:var(--am-card-bg); color:var(--am-text); cursor:pointer; }
.region-control { min-width: 0; }
.region-panel { border: 1px solid var(--am-card-border); border-radius: 4px; background: var(--am-card-bg); margin-bottom: 16px; overflow: hidden; }
header { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; padding: 14px 18px; background: var(--am-card-bg-2); border-bottom: 1px solid var(--am-card-border); }
h2,h3 { margin: 0; font-size: 16px; color: var(--am-text); }
header span, header label { font-size: 13px; color: var(--am-text-2); }
header label { margin-left: auto; display: flex; gap: 8px; align-items: center; }
/* 左图右选区，限制总览高度，完整保留切片及引线。 */
.region-overview { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(280px, 1fr); align-items: center; gap: 16px; padding: 14px; min-width: 0; }
.slice-illustration { display: block; width: 100%; height: clamp(240px, 28vw, 340px); object-fit: contain; object-position: center; margin: 0 auto; box-sizing: border-box; background: transparent; }
.region-list { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); align-content: center; gap: 10px; min-width: 0; }
.region-list button { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; width: 100%; min-width: 0; padding: 12px; overflow-wrap: anywhere; margin-bottom: 0; text-align: left; border: 1px solid var(--am-card-border); border-radius: 3px; background: var(--am-card-bg); color: var(--am-text); cursor: pointer; }
.region-list button.selected { border-color: var(--am-accent); background: var(--am-card-bg-2); }
.region-list i { width: 12px; height: 12px; display: inline-block; margin-right: 8px; border: 1px solid var(--am-card-border); }
.region-list small,.region-list span { font-size: 13px; }
.region-parameters { padding: 18px; display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 16px 24px; }
.region-parameters section { border: 1px solid var(--am-card-border); padding: 18px; min-width: 0; }
.adaptive-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.adaptive-form { border-top: 3px solid var(--am-accent) !important; background: var(--am-card-bg-2); }
.region-strategy { font-weight:600; }
.adaptive-form.replaced { border-top-color:var(--am-card-border) !important; }
.strategy-replacement { min-height:150px; display:flex; flex-direction:column; justify-content:center; gap:12px; font-size:14px; }
.strategy-replacement span { color:var(--am-text-2); }
.adaptive-heading input { accent-color: var(--am-accent); }
.region-parameters label { display: flex; flex-direction: column; gap: 8px; margin-top: 14px; font-size: 13px; color: var(--am-text-2); }
.region-parameters input:not([type="checkbox"]) { width: 100%; box-sizing: border-box; border: 1px solid var(--am-card-border); background: var(--am-card-bg-2); padding: 9px; color: var(--am-text); font: inherit; }
.region-parameters .changed input { color: var(--am-accent); font-weight: 700; border-color: var(--am-accent); }
.unavailable { display: grid; place-items: center; min-height: 240px; color: var(--am-text-2); margin: 0; }
.note { font-size: 12px; line-height: 1.8; color: var(--am-text-2); margin: 8px 0; }
.region-parameters > p { grid-column: 1 / -1; margin: 0; }
.plan-status { color: var(--am-accent); font-size: 14px; }
.config-error { color: var(--am-danger); padding: 16px; }
@media(max-width:900px) {
  .region-overview { grid-template-columns: minmax(0,1fr); }
  .slice-illustration { height: auto; max-height: 320px; }
}
@media(max-width:420px) { .region-list { grid-template-columns: minmax(0,1fr); } }
@media(max-width:600px) { .region-parameters { grid-template-columns: minmax(0,1fr); } }
</style>
