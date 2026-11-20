<template>
  <span class="region-badge" :style="{'--region-color': color}"><i aria-hidden="true"></i>{{ name }}</span>
</template>
<script setup>
defineProps({ name: {type:String,required:true}, color:{type:String,default:'#4150b4'} })
</script>
<style scoped>
.region-badge { display: inline-flex; align-items: center; gap: 8px; padding: 5px 11px; border: 1px solid var(--region-color); border-left-width: 4px; border-radius: 3px; color: var(--am-text); background: color-mix(in srgb,var(--region-color) 12%,var(--am-card-bg)); font-size: 14px; font-weight: 700; line-height: 1.3; white-space: nowrap; }
i { display: inline-block; width: 12px; height: 12px; background: var(--region-color); border: 1px solid color-mix(in srgb,var(--region-color) 65%,#324156); }
</style>
