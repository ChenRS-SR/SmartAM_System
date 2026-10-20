<template>
  <section class="energy-correction" aria-label="输入能量偏移回调">
    <h3>自适应调整 · 输入能量偏移回调</h3>
    <div class="energy-fields">
      <label>成形层厚 / mm<el-input-number v-model="thickness" aria-label="成形层厚" :min="0.001" :step="0.001" :precision="3" :controls="false" placeholder="填写成形层厚" /></label>
      <label>目标能量密度 / J·mm⁻³<el-input-number v-model="target" aria-label="目标能量密度" :min="0.001" :precision="3" :controls="false" placeholder="填写工艺目标" /></label>
      <label>允许偏差 / %<el-input-number v-model="tolerance" aria-label="允许偏差" :min="0" :max="20" :step="0.5" :controls="false" /></label>
      <label>回调参数<select v-model="actuator" aria-label="回调参数"><option value="fill_power">激光功率</option><option value="fill_speed">扫描速度</option></select></label>
    </div>
    <div class="energy-readings">
      <div><span>当前工艺基准能量密度</span><strong>{{ result.current == null ? '—' : result.current.toFixed(3) }} <small>J/mm³</small></strong></div>
      <div><span>相对目标偏移</span><strong>{{ result.deviation == null ? '—' : `${result.deviation > 0 ? '+' : ''}${result.deviation.toFixed(2)}%` }}</strong></div>
      <div><span>回调方向</span><strong>{{ direction }}</strong></div>
    </div>
    <p v-if="result.error" class="energy-note">{{ result.error }}</p>
    <p v-else-if="result.status !== 'normal'" class="energy-adjustment">
      调控{{ actuator === 'fill_power' ? '激光功率' : '扫描速度' }}：{{ params[actuator] }} → {{ result.value }} {{ actuator === 'fill_power' ? 'W' : 'mm/s' }}；
      预计能量密度 {{ result.predicted.toFixed(3) }} J/mm³
    </p>
    <p v-else class="energy-adjustment">当前参数处于目标允许偏差内，保持不变。</p>
    <p class="energy-note">按 P / (v × h × t) 计算能量偏移，以当前参数为基准进行回调。调控后参数随目标自动更新，保存或发送由下方操作完成。</p>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { energyCorrection } from './energyCorrection'
const props = defineProps({ params: { type: Object, required: true }, ranges: { type: Object, required: true } })
const emit = defineEmits(['plan'])
const thickness = ref(null)
const target = ref(null)
const tolerance = ref(2)
const actuator = ref('fill_power')
const result = computed(() => energyCorrection(props.params, thickness.value, target.value, tolerance.value, actuator.value, props.ranges))
const direction = computed(() => {
  if (!result.value.status) return '待设置目标'
  if (result.value.status === 'normal') return '目标范围内'
  const high = result.value.status === 'high'
  return `${high ? '能量偏高' : '能量偏低'} · ${actuator.value === 'fill_power' ? (high ? '降低功率' : '提高功率') : (high ? '提高速度' : '降低速度')}`
})
watch(result, value => emit('plan', value), { immediate: true })
</script>

<style scoped>
.energy-correction { border: 1px solid var(--am-card-border); background: var(--am-card-bg-2); padding: 16px; margin: 6px 0; border-radius: 3px; }
h3 { font-size: 15px; margin: 0 0 16px; color: var(--am-text); }
.energy-fields { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 14px; }
label { display: flex; flex-direction: column; gap: 8px; color: var(--am-text-2); font-size: 12px; min-width: 0; }
.el-input-number, select { width: 100%; min-width: 0; }
select { padding: 8px; border: 1px solid var(--am-card-border); background: var(--am-card-bg); color: var(--am-text); border-radius: 3px; }
.energy-readings { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 16px; margin: 20px 0 12px; }
.energy-readings div { display: flex; flex-direction: column; gap: 8px; }
.energy-readings span, small, .energy-note { font-size: 12px; color: var(--am-text-2); font-weight: 400; }
strong { color: var(--am-text); font-size: 17px; }
.energy-adjustment { font-size: 13px; color: var(--am-accent); }
p { line-height: 1.7; }
@media(max-width:1000px) { .energy-fields { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media(max-width:600px) { .energy-fields,.energy-readings { grid-template-columns:1fr; } }
</style>
