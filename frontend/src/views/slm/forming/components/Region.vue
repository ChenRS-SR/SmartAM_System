<template>
  <div class="region" :class="['k-' + kind]" :style="style">
    <div v-if="title" class="region-title">{{ title }}</div>
    <div class="region-body"><slot /></div>
  </div>
</template>

<script setup>
// kind：input 数据输入、param 参数配置、op 处理操作、vis 结果可视化（只用于区分区域，界面上不显示区域名称）
defineProps({ kind: { type: String, required: true }, title: String, style: [String, Object] })
</script>

<style scoped>
.region { position: relative; background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px;
  padding: 10px 14px; display: flex; flex-direction: column; min-height: 0; }
.region-title { font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 6px; }
.region-body { flex: 1; min-height: 0; }
.k-input { --kc: var(--k-input); }
.k-param { --kc: var(--k-param); }
.k-op { --kc: var(--k-op); }
.k-vis { --kc: var(--k-vis); }
</style>

