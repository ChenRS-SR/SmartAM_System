import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 图片懒加载 Composable
 * @param {Object} options
 * @param {Ref<HTMLElement>} options.targetRef - 目标元素
 * @param {String} options.src - 图片地址
 * @param {Number} options.threshold - 可见阈值
 * @param {String} options.rootMargin - 根边距
 */
export function useLazyLoad(options) {
  const { targetRef, src, threshold = 0.1, rootMargin = '50px' } = options
  
  const loaded = ref(false)
  const error = ref(false)
  const isIntersecting = ref(false)
  
  let observer = null
  
  const loadImage = () => {
    if (!src) {
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
    img.src = src
  }
  
  onMounted(() => {
    if (!targetRef.value) return
    
    // 如果浏览器不支持 IntersectionObserver，直接加载
    if (!('IntersectionObserver' in window)) {
      loadImage()
      return
    }
    
    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !isIntersecting.value) {
            isIntersecting.value = true
            loadImage()
            observer?.unobserve(entry.target)
          }
        })
      },
      {
        threshold,
        rootMargin
      }
    )
    
    observer.observe(targetRef.value)
  })
  
  onUnmounted(() => {
    if (observer) {
      observer.disconnect()
    }
  })
  
  return {
    loaded,
    error,
    isIntersecting
  }
}

/**
 * 批量懒加载 Composable
 * @param {Object} options
 * @param {Ref<Array>} options.items - 数据列表
 * @param {Function} options.onLoad - 加载回调
 * @param {Number} options.batchSize - 批量大小
 */
export function useBatchLoad(options) {
  const { items, onLoad, batchSize = 10 } = options
  
  const loadedItems = ref([])
  const loading = ref(false)
  const hasMore = ref(true)
  
  let currentIndex = 0
  
  const loadBatch = async () => {
    if (loading.value || !hasMore.value) return
    
    loading.value = true
    
    const batch = items.value.slice(currentIndex, currentIndex + batchSize)
    
    if (batch.length === 0) {
      hasMore.value = false
      loading.value = false
      return
    }
    
    // 模拟异步加载
    await new Promise(resolve => setTimeout(resolve, 100))
    
    loadedItems.value.push(...batch)
    currentIndex += batch.length
    
    if (currentIndex >= items.value.length) {
      hasMore.value = false
    }
    
    loading.value = false
    
    if (onLoad) {
      onLoad(batch)
    }
  }
  
  const reset = () => {
    loadedItems.value = []
    currentIndex = 0
    hasMore.value = true
    loading.value = false
  }
  
  return {
    loadedItems,
    loading,
    hasMore,
    loadBatch,
    reset
  }
}

/**
 * 分页加载 Composable
 * @param {Object} options
 * @param {Function} options.fetch - 获取数据的函数
 * @param {Number} options.pageSize - 每页大小
 */
export function usePagination(options) {
  const { fetch, pageSize = 20 } = options
  
  const items = ref([])
  const loading = ref(false)
  const error = ref(null)
  const currentPage = ref(1)
  const total = ref(0)
  const hasMore = computed(() => items.value.length < total.value)
  
  const loadPage = async (page = 1) => {
    loading.value = true
    error.value = null
    
    try {
      const result = await fetch({
        page,
        pageSize,
        offset: (page - 1) * pageSize
      })
      
      if (page === 1) {
        items.value = result.items
      } else {
        items.value.push(...result.items)
      }
      
      total.value = result.total
      currentPage.value = page
    } catch (e) {
      error.value = e
    } finally {
      loading.value = false
    }
  }
  
  const loadMore = () => {
    if (!hasMore.value || loading.value) return
    return loadPage(currentPage.value + 1)
  }
  
  const refresh = () => loadPage(1)
  
  return {
    items,
    loading,
    error,
    currentPage,
    total,
    hasMore,
    loadPage,
    loadMore,
    refresh
  }
}
