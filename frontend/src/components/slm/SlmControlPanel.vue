<template>
  <div class="slm-control">
    <section class="control-panel">
      <header><h2>层间调控策略1</h2></header>
      <p v-if="error" role="alert">{{ error }}</p>
      <div v-else-if="config" class="parameter-comparison">
        <section aria-label="当前工艺参数"><h3>当前工艺参数</h3>
          <label v-for="key in paramKeys" :key="key">{{ paramDefs[key].label }} / {{ paramDefs[key].unit }}
            <el-input-number v-model="inputValues[key]" :min="config.safe_ranges[key].min" :max="config.safe_ranges[key].max" :step="paramDefs[key].step" :precision="paramDefs[key].precision" :controls="false" :aria-label="`当前${paramDefs[key].label}`" />
          </label>
        </section>
        <section class="adaptive-form" aria-label="自适应调整">
          <div class="adaptive-heading"><h3>自适应调整</h3><el-switch :model-value="automatic" @change="setAutomatic" aria-label="自适应调整开关" /></div>
          <template v-if="strategy === 'adjust'">
          <label v-for="key in paramKeys" :key="key">{{ paramDefs[key].label }} / {{ paramDefs[key].unit }}
            <el-input :model-value="plan.parameters[key]?.toFixed(paramDefs[key].precision)" readonly :aria-label="`自适应${paramDefs[key].label}`" />
          </label>
          </template>
          <p v-else class="strategy-notice">当前采用层间调控策略{{ controlStrategies[strategy].number }} · {{ controlStrategies[strategy].name }}</p>
        </section>
      </div>
    </section>
    <LayerStrategyPlaceholders :enabled="!!config" :active-strategy="strategy" @strategy="selectStrategy" />
  </div>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { controlParameterKeys as paramKeys, controlParameterDefs as paramDefs } from './controlParameters'
import { ElMessage } from 'element-plus'
import { controlStrategies } from './controlStrategies'
import { regionControlPlan } from './regionControl'
import LayerStrategyPlaceholders from './LayerStrategyPlaceholders.vue'
const props = defineProps({ historical: Boolean, replayContext: Object })
const automatic = ref(true), config = ref(null), error = ref('')
const inputValues = reactive({})
const strategy = ref('adjust')
// 尚无区域档案的设备保留本页策略示意，选择其他策略同样停用策略1。
function selectStrategy(value) {
  strategy.value = value
  automatic.value = false
  ElMessage.info({message:`${controlStrategies[value].scope === 'layer' ? '整层 · ' : ''}${controlStrategies[value].name}应用中`, duration:2000})
}
function setAutomatic(value) {
  strategy.value = 'adjust'
  automatic.value = value
  ElMessage.info({message:'自适应调整应用中', duration:2000})
}
// 展示端只生成参数方案；实机协议保留在后端，不在这里启动监听或下发指令。
const plan = computed(() => config.value ? regionControlPlan({id:'current',name:'当前区域'},props.replayContext,inputValues,config.value.safe_ranges,automatic.value) : null)
onMounted(async () => {
  try {
    const response = await fetch('/api/slm/control/config')
    if (!response.ok) throw new Error('工艺参数读取失败')
    config.value = await response.json()
    for (const key of paramKeys) inputValues[key] = config.value.defaults[key]
  } catch (e) { error.value = e.message }
})
</script>
<style scoped>
.slm-control { min-width: 0; }
.control-panel { background: var(--am-card-bg); border: 1px solid var(--am-card-border); border-radius: 4px; }
header { padding: 14px 18px; background: var(--am-card-bg-2); border-bottom: 1px solid var(--am-card-border); }
h2,h3 { margin: 0; font-size: 16px; color: var(--am-text); }
.parameter-comparison { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); padding: 18px; gap: 24px; }
.parameter-comparison section { border: 1px solid var(--am-card-border); padding: 18px; min-width: 0; }
.adaptive-heading { display: flex; align-items: center; justify-content: space-between; }
.adaptive-form { border-top: 3px solid var(--am-accent) !important; background: var(--am-card-bg-2); }
label { display: flex; flex-direction: column; gap: 8px; margin-top: 14px; font-size: 13px; color: var(--am-text-2); }
:deep(.el-input-number) { width: 100%; }
@media(max-width:600px) { .parameter-comparison { grid-template-columns: minmax(0,1fr); } }
</style>
