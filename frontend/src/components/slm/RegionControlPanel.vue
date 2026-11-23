<template>
  <div class="region-control">
    <section class="region-panel" aria-label="当前切片区域总览">
      <header><h2>当前切片区域</h2><span>第 {{ frame.layer }} 层</span></header>
      <div class="region-overview">
        <img class="slice-illustration" :src="slice.annotatedImage" :alt="`第${frame.layer}层切片区域引线标注图，共${slice.regions.length}个区域`" />
        <div class="region-list">
          <button v-for="(region, i) in slice.regions" :key="region.id" :class="{selected: selectedId === region.id}" @click="selectedId = region.id" :aria-pressed="selectedId === region.id">
            <strong><i :style="{background:region.color}"></i>{{ region.name }}</strong>
            <span>{{ plans[i]?.status || '读取参数配置…' }}</span>
            <small v-if="plans[i]">功率 {{ plans[i].parameters.fill_power }} W · 速度 {{ plans[i].parameters.fill_speed }} mm/s · 层间等待 {{ plans[i].parameters.layer_wait_time }} s</small>
          </button>
        </div>
      </div>
    </section>
    <section class="region-panel" aria-label="层间调控策略1">
      <header><h2>层间调控策略1</h2><RegionBadge :name="selectedRegion.name" :color="selectedRegion.color" /></header>
      <p v-if="error" class="config-error" role="alert">{{ error }}</p>
      <div v-else-if="activePlan" class="region-parameters">
        <section aria-label="当前工艺参数"><h3>当前工艺参数</h3>
          <label v-for="key in paramKeys" :key="key">{{ paramDefs[key].label }} / {{ paramDefs[key].unit }}<input :value="activePlan.baseline[key]" readonly :aria-label="`当前${paramDefs[key].label}`" /></label>
        </section>
        <section class="adaptive-form" aria-label="自适应调整"><div class="adaptive-heading"><h3>自适应调整</h3><input v-model="automatic" type="checkbox" role="switch" aria-label="区域自适应调整" /></div>
          <label v-for="key in paramKeys" :key="key" :class="{changed:activePlan.parameters[key] !== activePlan.baseline[key]}">{{ paramDefs[key].label }} / {{ paramDefs[key].unit }}<input :value="activePlan.parameters[key]" readonly :aria-label="`自适应${paramDefs[key].label}`" /></label>
        </section>
        <p class="plan-status" aria-live="polite">{{ selectedRegion.name }} · {{ activePlan.status }} · 第 {{ frame.layer }} 层</p>
      </div>
      <p v-else class="note">正在读取工艺基准…</p>
    </section>
    <LayerStrategyPlaceholders :region-name="selectedRegion.name" :region-color="selectedRegion.color" :enabled="!!activePlan && !submitting" @strategy="submitStrategy" />
  </div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { controlParameterKeys as paramKeys, controlParameterDefs as paramDefs } from './controlParameters'
import { REPLAY_CASES } from '../../stores/replay'
import { task4Api } from '../../utils/task4Api'
import { ElMessage } from 'element-plus'
import LayerStrategyPlaceholders from './LayerStrategyPlaceholders.vue'
import RegionBadge from './RegionBadge.vue'
const props = defineProps({ frame: { type: Object, required: true }, slice: { type: Object, required: true } })
const selectedId = ref(props.slice.regions[0].id)
const automatic = ref(true)
const config = ref(null)
const error = ref('')
// 跨层保留所选颜色区域；区域消失时选当前层首个真实区域，不保留旧层参数。
watch(() => props.slice, slice => {
  if (!slice.regions.some(r => r.id === selectedId.value)) selectedId.value = slice.regions[0].id
})
const selectedRegion = computed(() => props.slice.regions.find(r => r.id === selectedId.value))
const plans = ref([])
const submitting = ref(false)
let previewController, actionController
const deviceId = computed(() => REPLAY_CASES.find(c => c.id === props.frame.caseId)?.deviceId || props.frame.caseId)
function selection() {
  const baseline = config.value.defaults
  const request = { deviceId: deviceId.value, automatic: automatic.value,
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
watch([() => props.frame.caseId, () => props.frame.layer, () => props.frame.recognition?.layer,
  () => props.frame.processing?.real, automatic, config], async () => {
  previewController?.abort()
  if (!config.value) return
  const controller = new AbortController()
  previewController = controller
  plans.value = []
  try {
    const data = await task4Api('quality-control', selection(), controller.signal)
    if (controller.signal.aborted) return
    plans.value = data.regions.map(r => ({...r, baseline:fields(r.currentParameters), parameters:fields(r.controlParameters)}))
    error.value = ''
  } catch (e) { if (e.name !== 'AbortError') error.value = e.message }
}, { immediate:true })
async function submitStrategy(strategy) {
  if (submitting.value) return
  submitting.value = true
  const request = {...selection(), strategy, regionIds:[selectedId.value], operation:'save',
    requestId:`ui-${Date.now()}-${Math.random().toString(36).slice(2)}`}
  const regionName = selectedRegion.value.name
  const controller = new AbortController()
  actionController = controller
  try {
    const plan = await task4Api('quality-control', request, controller.signal)
    await task4Api('quality-control', {deviceId:request.deviceId, planId:plan.planId, operation:'simulate'}, controller.signal)
    ElMessage.success(`${regionName}策略已模拟`)
  } catch (e) { if (e.name !== 'AbortError') ElMessage.error(e.message) }
  finally { submitting.value = false }
}
onUnmounted(() => { previewController?.abort(); actionController?.abort() })
const activePlan = computed(() => plans.value.find(p => p.regionId === selectedId.value))
onMounted(async () => {
  try {
    const response = await fetch('/api/slm/control/config')
    if (!response.ok) throw new Error(`参数配置读取失败（${response.status}）`)
    config.value = await response.json()
  } catch (e) { error.value = e.message }
})
</script>
<style scoped>
.region-control { min-width: 0; }
.region-panel { border: 1px solid var(--am-card-border); border-radius: 4px; background: var(--am-card-bg); margin-bottom: 16px; overflow: hidden; }
header { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; padding: 14px 18px; background: var(--am-card-bg-2); border-bottom: 1px solid var(--am-card-border); }
h2,h3 { margin: 0; font-size: 16px; color: var(--am-text); }
header span, header label { font-size: 13px; color: var(--am-text-2); }
header label { margin-left: auto; display: flex; gap: 8px; align-items: center; }
.region-overview { display: flex; flex-direction: column; gap: 16px; padding: 18px; min-width: 0; }
.slice-illustration { display: block; width: 100%; height: auto; object-fit: contain; object-position: center; margin: 0 auto; box-sizing: border-box; border: 1px solid var(--am-card-border); background: white; }
.region-list { display: grid; grid-template-columns: repeat(auto-fit,minmax(min(100%,200px),1fr)); gap: 12px; min-width: 0; }
.region-list button { display: flex; flex-direction: column; align-items: flex-start; gap: 9px; width: 100%; padding: 16px; margin-bottom: 0; text-align: left; border: 1px solid var(--am-card-border); border-radius: 3px; background: var(--am-card-bg); color: var(--am-text); cursor: pointer; }
.region-list button.selected { border-color: var(--am-accent); background: var(--am-card-bg-2); }
.region-list i { width: 12px; height: 12px; display: inline-block; margin-right: 8px; border: 1px solid var(--am-card-border); }
.region-list small,.region-list span { font-size: 13px; }
.region-parameters { padding: 18px; display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 16px 24px; }
.region-parameters section { border: 1px solid var(--am-card-border); padding: 18px; min-width: 0; }
.adaptive-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.adaptive-form { border-top: 3px solid var(--am-accent) !important; background: var(--am-card-bg-2); }
.adaptive-heading input { accent-color: var(--am-accent); }
.region-parameters label { display: flex; flex-direction: column; gap: 8px; margin-top: 14px; font-size: 13px; color: var(--am-text-2); }
.region-parameters input:not([type="checkbox"]) { width: 100%; box-sizing: border-box; border: 1px solid var(--am-card-border); background: var(--am-card-bg-2); padding: 9px; color: var(--am-text); font: inherit; }
.region-parameters .changed input { color: var(--am-accent); font-weight: 700; border-color: var(--am-accent); }
.note { font-size: 12px; line-height: 1.8; color: var(--am-text-2); margin: 8px 0; }
.region-parameters > p { grid-column: 1 / -1; margin: 0; }
.plan-status { color: var(--am-accent); font-size: 14px; }
.config-error { color: var(--am-danger); padding: 16px; }
@media(max-width:600px) { .region-parameters { grid-template-columns: minmax(0,1fr); } }
</style>
