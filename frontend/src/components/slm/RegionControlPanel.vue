<template>
  <div class="region-control">
    <section class="region-panel" aria-label="当前切片区域总览">
      <header><h2>当前切片区域</h2><span>第 {{ frame.layer }} 层 · {{ slice.sourceFile }}</span></header>
      <div class="region-overview">
        <img class="slice-illustration" :src="slice.annotatedImage" :alt="`第${frame.layer}层切片区域引线标注图，共${slice.regions.length}个区域`" />
        <div class="region-list">
          <p class="note">{{ frame.recognition?.layer === frame.layer ? `本层识别：${frame.recognition.label}` : '等待本层识别' }} · 自动调控示意</p>
          <button v-for="(region, i) in slice.regions" :key="region.id" :class="{selected: selectedId === region.id}" @click="selectedId = region.id" :aria-pressed="selectedId === region.id">
            <strong><i :style="{background:region.color}"></i>{{ region.name }}</strong>
            <span>{{ plans[i]?.status || '读取参数配置…' }}</span>
            <small v-if="plans[i]">功率 {{ plans[i].parameters.fill_power }} W · 速度 {{ plans[i].parameters.fill_speed }} mm/s · 送粉 {{ plans[i].parameters.powder_feed_rate }} g/min</small>
          </button>
          <p class="note">区域与当前层切片颜色对应；当前层识别统一触发，各区域分别生成参数组。</p>
        </div>
      </div>
    </section>
    <section class="region-panel" aria-label="层间调控策略1">
      <header><h2>层间调控策略1</h2><span>{{ selectedRegion.name }}</span><label><input v-model="automatic" type="checkbox" role="switch" aria-label="区域自适应调整" />自适应调整</label></header>
      <p v-if="error" class="config-error" role="alert">{{ error }}</p>
      <div v-else-if="activePlan" class="region-parameters">
        <section aria-label="当前工艺参数"><h3>当前工艺参数</h3>
          <label v-for="(range, key) in config.safe_ranges" :key="key">{{ range.description }} / {{ range.unit }}<input :value="activePlan.baseline[key]" readonly :aria-label="`当前${range.description}`" /></label>
        </section>
        <section aria-label="调控参数"><h3>调控参数</h3>
          <label v-for="(range, key) in config.safe_ranges" :key="key" :class="{changed:activePlan.parameters[key] !== activePlan.baseline[key]}">{{ range.description }} / {{ range.unit }}<input :value="activePlan.parameters[key]" readonly :aria-label="`调控${range.description}`" /></label>
        </section>
        <p class="plan-status" aria-live="polite">{{ selectedRegion.name }} · {{ activePlan.status }} · 第 {{ frame.layer }} 层</p>
        <p class="note">示意策略：工艺侧触发时降低功率，设备侧触发时增加送粉。参数按当前层自动更新，不下发设备。</p>
      </div>
      <p v-else class="note">正在读取工艺基准…</p>
    </section>
    <LayerStrategyPlaceholders :region-name="selectedRegion.name" />
  </div>
</template>
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { regionControlPlan } from './regionControl'
import LayerStrategyPlaceholders from './LayerStrategyPlaceholders.vue'
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
const plans = computed(() => config.value ? props.slice.regions.map(r => regionControlPlan(r, props.frame, config.value.defaults, config.value.safe_ranges, automatic.value)) : [])
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
.region-overview { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(260px, 1fr); gap: 20px; padding: 18px; }
.slice-illustration { width: 100%; max-height: 400px; object-fit: contain; border: 1px solid var(--am-card-border); background: white; }
.region-list { min-width: 0; }
.region-list button { display: flex; flex-direction: column; align-items: flex-start; gap: 9px; width: 100%; padding: 16px; margin-bottom: 12px; text-align: left; border: 1px solid var(--am-card-border); border-radius: 3px; background: var(--am-card-bg); color: var(--am-text); cursor: pointer; }
.region-list button.selected { border-color: var(--am-accent); background: var(--am-card-bg-2); }
.region-list i { width: 12px; height: 12px; display: inline-block; margin-right: 8px; border: 1px solid var(--am-card-border); }
.region-list small,.region-list span { font-size: 13px; }
.region-parameters { padding: 18px; display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 16px 24px; }
.region-parameters section { border: 1px solid var(--am-card-border); padding: 18px; min-width: 0; }
.region-parameters label { display: flex; flex-direction: column; gap: 8px; margin-top: 14px; font-size: 13px; color: var(--am-text-2); }
.region-parameters input { width: 100%; box-sizing: border-box; border: 1px solid var(--am-card-border); background: var(--am-card-bg-2); padding: 9px; color: var(--am-text); font: inherit; }
.region-parameters .changed input { color: var(--am-accent); font-weight: 700; border-color: var(--am-accent); }
.note { font-size: 12px; line-height: 1.8; color: var(--am-text-2); margin: 8px 0; }
.region-parameters > p { grid-column: 1 / -1; margin: 0; }
.plan-status { color: var(--am-accent); font-size: 14px; }
.config-error { color: var(--am-danger); padding: 16px; }
@media(max-width:900px) { .region-overview { grid-template-columns: minmax(0,1fr); } }
@media(max-width:600px) { .region-parameters { grid-template-columns: minmax(0,1fr); } }
</style>
