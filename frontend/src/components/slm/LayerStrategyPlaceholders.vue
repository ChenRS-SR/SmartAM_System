<template>
  <!-- 后续策略先保留独立框和按钮，不下发设备指令。 -->
  <section v-for="strategy in strategies" :key="strategy.number" class="strategy-panel" :aria-label="`层间调控策略${strategy.number}`">
    <div class="strategy-header"><strong>层间调控策略{{ strategy.number }}</strong><span v-if="regionName">{{ regionName }}</span></div>
    <div class="strategy-body"><el-button type="primary" @click="ElMessage.info(`${regionName ? regionName + ' · ' : ''}${strategy.name}策略待配置`)">{{ strategy.name }}</el-button></div>
  </section>
</template>
<script setup>
import { ElMessage } from 'element-plus'
defineProps({ regionName: { type: String, default: '' } })
const strategies = [{ number: 2, name: '重熔' }, { number: 3, name: '重铺粉' }, { number: 4, name: '统计调整' }]
</script>
<style scoped>
.strategy-panel { margin-top: 16px; background: var(--am-card-bg); border: 1px solid var(--am-card-border); border-radius: 4px; overflow: hidden; }
.strategy-header { padding: 12px 16px; background: var(--am-card-bg-2); border-bottom: 1px solid var(--am-card-border-2); display: flex; justify-content: space-between; font-size: 14px; color: var(--am-text); }
.strategy-header span { color: var(--am-text-2); }
.strategy-body { min-height: 150px; padding: 20px; display: flex; align-items: flex-end; justify-content: flex-end; }
</style>
