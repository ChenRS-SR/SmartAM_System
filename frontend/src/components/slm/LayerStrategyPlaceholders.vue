<template>
  <!-- 有区域上下文时由父组件保存并模拟方案，未接入设备执行器。 -->
  <div class="strategy-grid">
    <section v-for="strategy in strategies" :key="strategy.number" class="strategy-panel" :class="{ 'strategy-stop': strategy.number === 4 }" :aria-label="`层间调控策略${strategy.number}`">
      <div class="strategy-title"><strong>层间调控策略{{ strategy.number }}</strong><RegionBadge v-if="regionName" :name="regionName" :color="regionColor" /></div>
      <el-button class="strategy-button" :disabled="!enabled" @click="emit('strategy', strategy.key)">{{ strategy.name }}</el-button>
    </section>
  </div>
</template>
<script setup>
import RegionBadge from './RegionBadge.vue'
const emit = defineEmits(['strategy'])
defineProps({ enabled:{type:Boolean,default:false}, regionName: { type: String, default: '' }, regionColor: {type:String,default:'#4150b4'} })
const strategies = [{ number: 2, key:'remelt', name: '重熔' }, { number: 3, key:'recoat', name: '重铺粉' }, { number: 4, key:'stop', name: '停机调整' }]
</script>
<style scoped>
.strategy-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
.strategy-panel { display: flex; flex-direction: column; align-items: stretch; gap: 10px; padding: 14px 16px; background: var(--am-card-bg); border: 1px solid var(--am-card-border); border-radius: 4px; min-width: 0; }
.strategy-title { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; font-size: 14px; color: var(--am-text); }
.strategy-stop { grid-column: 1 / -1; }
.strategy-button { width: 100%; height: 38px; margin: 0; color: var(--am-text); background: var(--am-card-bg-2); border-color: var(--am-card-border); }
.strategy-button:hover,.strategy-button:focus-visible { color: var(--am-text); background: var(--am-card-bg); border-color: var(--am-text-2); }
@media(max-width:600px) { .strategy-grid { grid-template-columns: minmax(0,1fr); } }
</style>
