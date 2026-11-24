<template>
  <figure class="equipment-diagnosis" :class="diagnosis.state" aria-label="设备故障诊断图">
    <div class="diagram-heading"><strong>{{ diagnosis.title }}</strong><span>{{ diagnosis.source || (trace?.available === false ? '—' : trace ? `诊断层：${trace.layer}` : '—') }}</span></div>
    <div class="diagnosis-visual">
      <SubsystemDiagram :systems="systems" :faults="diagnosis.faults" :diagnosis-state="diagnosis.state" :process-issue="diagnosis.state === 'process'" />
      <details v-if="diagnosis.faults.length" class="fault-details"><summary>异常部件详情</summary><div class="fault-gallery"><figure v-for="fault in diagnosis.faults" :key="fault.key"><img :src="`/state_picture/diagnosis-v2/${fault.key}.png`" :alt="fault.name" /><figcaption>{{ fault.name }}</figcaption></figure></div></details>
      <!-- 结论与诊断图共用一个画布，底部预留标注空间，不遮挡设备结构。 -->
      <div class="diagram-conclusion" role="status">
        <span>诊断结论</span>
        <strong>{{ diagnosis.conclusion }}</strong>
      </div>
    </div>

  </figure>
</template>
<script setup>
import { computed } from 'vue'
import SubsystemDiagram from './SubsystemDiagram.vue'
import { subsystemHealth } from '../subsystemHealth'
import { traceDiagnosis } from '../traceDiagnosis'
const props = defineProps({ trace: Object, recognition: Object })
const diagnosis = computed(() => traceDiagnosis(props.trace, props.recognition))
const systems = computed(() => subsystemHealth(diagnosis.value, props.trace))
</script>
<style scoped>
.fault-gallery { display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:12px; }
.fault-gallery figure { margin:0; }
.fault-gallery figcaption { justify-content:center; font-weight:600; }
.fault-details summary { cursor:pointer; padding:8px 0; color:var(--text-2); font-size:13px; }
.equipment-diagnosis { margin: 0; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
.diagram-heading { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; font-size: 15px; }
.diagram-heading span { color: var(--text-2); font-size: 13px; }
.diagnosis-visual { position: relative; display: grid; grid-template-rows: minmax(0, 1fr) auto; background: var(--img-bg); border: 1px solid var(--border-2); border-radius: 4px; padding: 12px; gap: 10px; }
img { display: block; width: 100%; height: clamp(220px, 22vw, 300px); object-fit: contain; }
.diagram-conclusion { display: flex; flex-direction: column; gap: 5px; text-align: center; padding: 10px 12px; border: 1px solid var(--border); border-left: 4px solid var(--text-3); border-radius: 3px; background: var(--card-bg); }
.diagram-conclusion span { font-size: 12px; color: var(--text-2); }
.diagram-conclusion strong { font-size: 18px; line-height: 1.5; color: var(--text); overflow-wrap: anywhere; }
.fault .diagram-conclusion { border-left-color: var(--warn); }
.normal .diagram-conclusion { border-left-color: var(--ok); }
.pending img { filter: grayscale(1); opacity: .75; }
figcaption { display: flex; flex-wrap: wrap; gap: 8px 18px; font-size: 13px; color: var(--text-2); }
figcaption b { color: var(--text); font-weight: 500; }
</style>
