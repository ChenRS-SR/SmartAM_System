<template>
  <div v-if="visible" class="app-loading" :class="{ fullscreen: fullscreen }">
    <div class="loading-content">
      <div class="spinner">
        <div class="ring"></div>
        <div class="ring"></div>
        <div class="ring"></div>
      </div>
      <p v-if="text" class="loading-text">{{ text }}</p>
      <p v-if="subText" class="loading-subtext">{{ subText }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: true },
  fullscreen: { type: Boolean, default: false },
  text: { type: String, default: '加载中...' },
  subText: { type: String, default: '' }
})
</script>

<style scoped>
.app-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(4px);
}

.app-loading.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
}

.app-loading:not(.fullscreen) {
  position: absolute;
  inset: 0;
  z-index: 100;
  border-radius: inherit;
}

.loading-content {
  text-align: center;
}

.spinner {
  position: relative;
  width: 60px;
  height: 60px;
  margin: 0 auto 16px;
}

.ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #00d4ff;
  animation: spin 1.5s linear infinite;
}

.ring:nth-child(1) {
  animation-duration: 1.5s;
}

.ring:nth-child(2) {
  inset: 8px;
  border-top-color: #00ff88;
  animation-duration: 1.2s;
  animation-direction: reverse;
}

.ring:nth-child(3) {
  inset: 16px;
  border-top-color: #ffc107;
  animation-duration: 0.9s;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 14px;
  color: #e2e8f0;
  margin: 0;
}

.loading-subtext {
  font-size: 12px;
  color: #64748b;
  margin: 8px 0 0;
}
</style>
