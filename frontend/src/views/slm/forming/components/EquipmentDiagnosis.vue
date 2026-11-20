<template>
  <figure class="equipment-diagnosis" :class="diagnosis.state" aria-label="设备故障诊断图">
    <div class="diagram-heading"><strong>{{ diagnosis.title }}</strong><span>{{ trace ? `诊断层：${trace.layer}` : '等待诊断证据' }}</span></div>
    <img :src="`/state_picture/${diagnosis.image}`" :alt="diagnosis.title" />
    <figcaption>
      <span>铺粉与供粉机构：<b>{{ diagnosis.powder }}</b></span>
      <span>工艺输入：<b>{{ diagnosis.process }}</b></span>
      <span>光路、气氛等其他系统：<b>暂无独立诊断证据</b></span>
    </figcaption>
  </figure>
</template>
<script setup>
import { computed } from 'vue'
import { traceDiagnosis } from '../traceDiagnosis'
const props = defineProps({ trace: Object, recognition: Object })
const diagnosis = computed(() => traceDiagnosis(props.trace, props.recognition))
</script>
<style scoped>
.equipment-diagnosis { margin: 0; min-width: 0; display: flex; flex-direction: column; gap: 12px; }
.diagram-heading { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; font-size: 15px; }
.diagram-heading span { color: var(--text-2); font-size: 13px; }
img { width: 100%; height: clamp(240px, 24vw, 330px); object-fit: contain; background: var(--img-bg); border: 1px solid var(--border-2); border-radius: 4px; }
.pending img { filter: grayscale(1); opacity: .75; }
figcaption { display: flex; flex-wrap: wrap; gap: 8px 18px; font-size: 13px; color: var(--text-2); }
figcaption b { color: var(--text); font-weight: 500; }
</style>
