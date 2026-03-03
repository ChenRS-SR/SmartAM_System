<template>
  <div ref="containerRef" class="lazy-image" :style="containerStyle">
    <img
      v-if="loaded"
      :src="src"
      :alt="alt"
      class="lazy-image-img"
      @load="handleLoad"
      @error="handleError"
    />
    <div v-else-if="error" class="lazy-image-error">
      <el-icon size="32"><Picture /></el-icon>
      <span>加载失败</span>
    </div>
    <div v-else class="lazy-image-placeholder">
      <el-icon class="loading-icon" size="24"><Loading /></el-icon>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  src: { type: String, required: true },
  alt: { type: String, default: '' },
  width: { type: [String, Number], default: '100%' },
  height: { type: [String, Number], default: 'auto' },
  objectFit: { type: String, default: 'cover' },
  threshold: { type: Number, default: 0.1 } // 可见阈值
})

const containerRef = ref(null)
const loaded = ref(false)
const error = ref(false)
const isIntersecting = ref(false)

const containerStyle = computed(() => ({
  width: typeof props.width === 'number' ? `${props.width}px` : props.width,
  height: typeof props.height === 'number' ? `${props.height}px` : props.height
}))

let observer = null

const handleLoad = () => {
  // 图片加载完成
}

const handleError = () => {
  error.value = true
}

const startLoad = () => {
  if (!props.src) {
    error.value = true
    return
  }
  
  const img = new Image()
  img.onload = () => {
    loaded.value = true
  }
  img.onerror = () => {
    error.value = true
  }
  img.src = props.src
}

onMounted(() => {
  if (!containerRef.value) return
  
  // 使用 Intersection Observer 实现懒加载
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !isIntersecting.value) {
          isIntersecting.value = true
          startLoad()
          // 加载后取消观察
          observer.unobserve(entry.target)
        }
      })
    },
    {
      threshold: props.threshold,
      rootMargin: '50px' // 提前 50px 开始加载
    }
  )
  
  observer.observe(containerRef.value)
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
})
</script>

<style scoped>
.lazy-image {
  position: relative;
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.lazy-image-img {
  width: 100%;
  height: 100%;
  object-fit: v-bind(objectFit);
  animation: fadeIn 0.3s ease;
}

.lazy-image-placeholder,
.lazy-image-error {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #666;
  gap: 8px;
}

.lazy-image-error {
  color: #ff4d4f;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
