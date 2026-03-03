<template>
  <div class="video-stream-container">
    <div class="video-header">
      <span class="video-title">{{ title }}</span>
      <el-tag v-if="status" :type="statusType" size="small" effect="dark">
        {{ statusText }}
      </el-tag>
    </div>
    <div class="video-wrapper">
      <img 
        :src="src" 
        class="video-image"
        @error="handleError"
        @load="handleLoad"
      />
      <div v-if="!loaded" class="video-loading">
        <el-icon class="loading-icon" size="32"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  src: { type: String, required: true },
  title: { type: String, default: '视频流' },
  status: { type: String, default: '' }
})

const loaded = ref(false)
const error = ref(false)

const statusType = computed(() => {
  if (props.status === 'connected') return 'success'
  if (props.status === 'connecting') return 'warning'
  return 'danger'
})

const statusText = computed(() => {
  if (props.status === 'connected') return '正常'
  if (props.status === 'connecting') return '连接中'
  return '未连接'
})

const handleLoad = () => {
  loaded.value = true
  error.value = false
}

const handleError = () => {
  loaded.value = false
  error.value = true
}
</script>

<style scoped>
.video-stream-container {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  overflow: hidden;
}

.video-header {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  background: rgba(0, 0, 0, 0.2);
}

.video-title {
  font-size: 14px;
  font-weight: 500;
  color: #00d4ff;
}

.video-wrapper {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
}

.video-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #a0aec0;
  gap: 12px;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
