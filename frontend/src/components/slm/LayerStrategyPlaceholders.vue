<template>
  <!-- 有区域上下文时由父组件保存并模拟方案，未接入设备执行器。 -->
  <div class="strategy-grid">
    <section v-for="strategy in strategies" :key="strategy.number" class="strategy-panel" :class="{ 'strategy-wide': strategy.number === 2, active:activeStrategy === strategy.key }" :aria-label="`层间调控策略${strategy.number}`">
      <div class="strategy-title"><strong>层间调控策略{{ strategy.number }}</strong><span v-if="activeStrategy === strategy.key" class="active-label">当前策略</span><span v-if="strategy.scope === 'layer'" class="scope-label">整层</span><RegionBadge v-else-if="regionName" :name="regionName" :color="regionColor" /></div>
      <el-button class="strategy-button" :disabled="!enabled" :aria-pressed="activeStrategy === strategy.key" @click="emit('strategy', strategy.key)">{{ pendingStrategy === strategy.key ? '指令发送中…' : strategy.name }}</el-button>
    </section>
  </div>
</template>
<script setup>
import { controlStrategies } from './controlStrategies'
import RegionBadge from './RegionBadge.vue'
const emit = defineEmits(['strategy'])
defineProps({ activeStrategy:{type:String,default:'adjust'}, pendingStrategy:{type:String,default:''}, enabled:{type:Boolean,default:false}, regionName: { type: String, default: '' }, regionColor: {type:String,default:'#4150b4'} })
const strategies = Object.entries(controlStrategies).filter(([key]) => key !== 'adjust').map(([key, value]) => ({key, ...value}))
</script>
<style scoped>
.strategy-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
.strategy-panel { display: flex; flex-direction: column; align-items: stretch; gap: 10px; padding: 14px 16px; background: var(--am-card-bg); border: 1px solid var(--am-card-border); border-radius: 4px; min-width: 0; }
.strategy-title { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; font-size: 14px; color: var(--am-text); }
.strategy-panel.active { border-color:var(--am-text-2); box-shadow:inset 0 0 0 1px var(--am-text-2); }
.active-label { font-size:12px; color:var(--am-text-2); }
.scope-label { font-size:12px; padding:2px 8px; border:1px solid var(--am-card-border); border-radius:3px; }
.strategy-wide { grid-column: 1 / -1; }
.strategy-button { width: 100%; height: 38px; margin: 0; color: var(--am-text); background: var(--am-card-bg-2); border-color: var(--am-card-border); }
.strategy-button:hover,.strategy-button:focus-visible { color: var(--am-text); background: var(--am-card-bg); border-color: var(--am-text-2); }
@media(max-width:600px) { .strategy-grid { grid-template-columns: minmax(0,1fr); } }
</style>
