import { ref, computed, onMounted, onUnmounted } from 'vue'

/**
 * 虚拟滚动 Composable
 * @param {Object} options
 * @param {Ref<Array>} options.items - 数据列表
 * @param {Number} options.itemHeight - 每项高度
 * @param {Number} options.buffer - 缓冲区大小
 * @param {Ref<HTMLElement>} options.containerRef - 容器元素
 */
export function useVirtualScroll(options) {
  const { items, itemHeight = 50, buffer = 5, containerRef } = options
  
  const scrollTop = ref(0)
  const containerHeight = ref(0)
  
  // 总高度
  const totalHeight = computed(() => 
    (items.value?.length || 0) * itemHeight
  )
  
  // 可见区域的起始索引
  const startIndex = computed(() => {
    const index = Math.floor(scrollTop.value / itemHeight)
    return Math.max(0, index - buffer)
  })
  
  // 可见区域的结束索引
  const endIndex = computed(() => {
    const visibleCount = Math.ceil(containerHeight.value / itemHeight)
    const index = startIndex.value + visibleCount + buffer * 2
    return Math.min(items.value?.length || 0, index)
  })
  
  // 可见数据
  const visibleItems = computed(() => {
    if (!items.value) return []
    return items.value.slice(startIndex.value, endIndex.value).map((item, i) => ({
      data: item,
      index: startIndex.value + i,
      key: `${startIndex.value + i}-${item.id || JSON.stringify(item)}`
    }))
  })
  
  // 偏移量
  const offset = computed(() => startIndex.value * itemHeight)
  
  // 滚动处理
  const onScroll = (e) => {
    scrollTop.value = e.target.scrollTop
  }
  
  // 更新容器高度
  const updateHeight = () => {
    if (containerRef?.value) {
      containerHeight.value = containerRef.value.clientHeight
    }
  }
  
  // 滚动到指定项
  const scrollTo = (index) => {
    if (containerRef?.value) {
      containerRef.value.scrollTop = index * itemHeight
    }
  }
  
  // 滚动到顶部
  const scrollToTop = () => scrollTo(0)
  
  // 滚动到底部
  const scrollToBottom = () => scrollTo((items.value?.length || 0) - 1)
  
  onMounted(() => {
    updateHeight()
    window.addEventListener('resize', updateHeight)
  })
  
  onUnmounted(() => {
    window.removeEventListener('resize', updateHeight)
  })
  
  return {
    totalHeight,
    visibleItems,
    offset,
    startIndex,
    endIndex,
    onScroll,
    scrollTo,
    scrollToTop,
    scrollToBottom
  }
}

/**
 * 无限滚动 Composable
 * @param {Object} options
 * @param {Function} options.loadMore - 加载更多数据的函数
 * @param {Number} options.threshold - 触发加载的阈值（px）
 */
export function useInfiniteScroll(options) {
  const { loadMore, threshold = 100 } = options
  
  const loading = ref(false)
  const finished = ref(false)
  const error = ref(false)
  
  const onScroll = async (e) => {
    if (loading.value || finished.value || error.value) return
    
    const { scrollTop, scrollHeight, clientHeight } = e.target
    
    if (scrollHeight - scrollTop - clientHeight < threshold) {
      loading.value = true
      try {
        const hasMore = await loadMore()
        if (!hasMore) {
          finished.value = true
        }
      } catch (e) {
        error.value = true
      } finally {
        loading.value = false
      }
    }
  }
  
  const reset = () => {
    loading.value = false
    finished.value = false
    error.value = false
  }
  
  return {
    loading,
    finished,
    error,
    onScroll,
    reset
  }
}

/**
 * 防抖滚动 Composable
 * @param {Number} wait - 防抖等待时间
 */
export function useDebouncedScroll(wait = 16) {
  const scrollTop = ref(0)
  const scrollDirection = ref('none') // 'up' | 'down' | 'none'
  
  let lastScrollTop = 0
  let timer = null
  
  const onScroll = (e) => {
    if (timer) clearTimeout(timer)
    
    timer = setTimeout(() => {
      const currentScrollTop = e.target.scrollTop
      scrollDirection.value = currentScrollTop > lastScrollTop ? 'down' : 'up'
      lastScrollTop = currentScrollTop
      scrollTop.value = currentScrollTop
    }, wait)
  }
  
  return {
    scrollTop,
    scrollDirection,
    onScroll
  }
}
