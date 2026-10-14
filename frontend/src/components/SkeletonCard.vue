<template>
  <div class="skeleton-card" :style="{ height: height }">
    <div v-if="showHeader" class="skeleton-header">
      <div class="skeleton-title"></div>
      <div class="skeleton-action"></div>
    </div>
    <div class="skeleton-body">
      <div 
        v-for="i in rows" 
        :key="i" 
        class="skeleton-row"
        :style="{ width: getRowWidth(i) }"
      >
        <div class="skeleton-text"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  rows: { type: Number, default: 3 },
  height: { type: String, default: 'auto' },
  showHeader: { type: Boolean, default: true }
})

const getRowWidth = (i) => {
  const widths = ['100%', '85%', '70%', '90%', '60%']
  return widths[(i - 1) % widths.length]
}
</script>

<style scoped>
.skeleton-card {
  background: var(--am-card-bg);
  border: 1px solid color-mix(in srgb, var(--am-accent) 10%, transparent);
  border-radius: 12px;
  padding: 16px;
  overflow: hidden;
}

.skeleton-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid color-mix(in srgb, var(--am-accent) 10%, transparent);
}

.skeleton-title {
  width: 120px;
  height: 16px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 25%,
    color-mix(in srgb, var(--am-accent) 22%, transparent) 50%,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 75%
  );
  background-size: 200% 100%;
  border-radius: 4px;
  animation: shimmer 1.5s infinite;
}

.skeleton-action {
  width: 60px;
  height: 24px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 25%,
    color-mix(in srgb, var(--am-accent) 22%, transparent) 50%,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 75%
  );
  background-size: 200% 100%;
  border-radius: 4px;
  animation: shimmer 1.5s infinite;
}

.skeleton-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-row {
  height: 12px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--am-accent) 8%, transparent) 25%,
    color-mix(in srgb, var(--am-accent) 18%, transparent) 50%,
    color-mix(in srgb, var(--am-accent) 8%, transparent) 75%
  );
  background-size: 200% 100%;
  border-radius: 4px;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
