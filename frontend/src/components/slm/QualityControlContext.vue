<template>
  <section class="analysis-context" aria-label="调控分析依据">
    <div class="context-heading">
      <h3>调控分析依据</h3>
      <el-button size="small" @click="$emit('open-trace')">查看异常溯源</el-button>
    </div>
    <template v-if="context">
      <div class="analysis-meta">
        <span>分析设备：{{ context.device.name }}</span>
        <span>成形任务：{{ context.task.name }}</span>
        <span>分析层：{{ context.layer }}</span>
      </div>
      <dl class="analysis-results">
        <div><dt>异常识别</dt><dd>{{ context.recognition ? `${context.recognition.label}（异常概率 ${(context.recognition.probability * 100).toFixed(1)}%）` : '本层尚无识别记录' }}</dd></div>
        <div><dt>异常溯源</dt><dd>{{ context.trace?.conclusion || '本层尚无溯源记录' }}</dd></div>
        <div><dt>处置对象</dt><dd>{{ context.trace ? (context.trace.actions.join('、') || '无需处置') : '待溯源确认' }}</dd></div>
      </dl>
      <p class="context-note">以上为本次会话的分析记录。请核对下方试验台的任务、层号和零件后调整参数；分析结果不会自动下发。</p>
    </template>
    <p v-else class="context-note">当前设备、当前分析层尚无本次会话的分析记录。可先完成异常识别与异常溯源，再核对调控对象。</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { state } from '../../views/slm/forming/state'
import { qualityContext } from '../../views/slm/forming/qualityContext'

const props = defineProps({ device: { type: String, required: true } })
defineEmits(['open-trace'])
// 宿主设备编号通过已有别名映射到成形设备，避免跨设备或跨层串用分析结果。
const context = computed(() => {
  const matched = state.devices.find(d => d.id === props.device || (d.aliases || []).includes(props.device))
  if (!matched) return null
  const result = qualityContext[matched.id]
  return result && state.layer[matched.id] === result.layer ? result : null
})
</script>

<style scoped>
.analysis-context { border: 1px solid var(--am-card-border); border-radius: 3px; background: var(--am-card-bg); padding: 16px; }
.context-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
h3 { margin: 0; font-size: 14px; font-weight: 600; }
.analysis-meta { display: flex; flex-wrap: wrap; gap: 12px 24px; margin-top: 14px; font-size: 12px; color: var(--am-text-2); }
.analysis-results { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; padding: 14px 0; margin: 14px 0 0; border-top: 1px solid var(--am-card-border-2); }
dt { font-size: 12px; color: var(--am-text-2); }
dd { margin: 8px 0 0; font-size: 14px; }
.context-note { color: var(--am-text-2); font-size: 12px; line-height: 1.8; margin-bottom: 0; }
@media (max-width: 768px) { .analysis-results { grid-template-columns: 1fr; } }
</style>
