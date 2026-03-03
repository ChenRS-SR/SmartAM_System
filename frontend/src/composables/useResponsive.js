import { ref, computed, onMounted, onUnmounted } from 'vue'

// 断点定义 (px)
const breakpoints = {
  xs: 480,   // 手机
  sm: 768,   // 平板
  md: 992,   // 小桌面
  lg: 1200,  // 桌面
  xl: 1600   // 大桌面
}

export function useResponsive() {
  const windowWidth = ref(window.innerWidth)
  const windowHeight = ref(window.innerHeight)

  // 计算当前断点
  const currentBreakpoint = computed(() => {
    const w = windowWidth.value
    if (w < breakpoints.xs) return 'xs'
    if (w < breakpoints.sm) return 'sm'
    if (w < breakpoints.md) return 'md'
    if (w < breakpoints.lg) return 'lg'
    return 'xl'
  })

  // 设备类型判断
  const isMobile = computed(() => windowWidth.value < breakpoints.sm)
  const isTablet = computed(() => windowWidth.value >= breakpoints.sm && windowWidth.value < breakpoints.md)
  const isDesktop = computed(() => windowWidth.value >= breakpoints.md)
  const isLargeScreen = computed(() => windowWidth.value >= breakpoints.lg)

  // 响应式网格列数
  const gridCols = computed(() => {
    if (isMobile.value) return 1
    if (isTablet.value) return 2
    if (windowWidth.value < breakpoints.lg) return 3
    return 4
  })

  // 响应式字体大小
  const fontSize = computed(() => {
    if (isMobile.value) return '14px'
    if (isTablet.value) return '15px'
    return '16px'
  })

  // 响应式间距
  const spacing = computed(() => {
    if (isMobile.value) return 12
    if (isTablet.value) return 16
    return 24
  })

  // 图表高度
  const chartHeight = computed(() => {
    if (isMobile.value) return 200
    if (isTablet.value) return 250
    return 300
  })

  // 侧边栏是否收起（移动端默认收起）
  const sidebarCollapsed = computed(() => {
    return isMobile.value || windowWidth.value < breakpoints.md
  })

  // 更新窗口尺寸
  const updateSize = () => {
    windowWidth.value = window.innerWidth
    windowHeight.value = window.innerHeight
  }

  onMounted(() => {
    window.addEventListener('resize', updateSize)
    updateSize()
  })

  onUnmounted(() => {
    window.removeEventListener('resize', updateSize)
  })

  return {
    // 基础尺寸
    windowWidth,
    windowHeight,
    
    // 断点
    breakpoint: currentBreakpoint,
    breakpoints,
    
    // 设备类型
    isMobile,
    isTablet,
    isDesktop,
    isLargeScreen,
    
    // 响应式配置
    gridCols,
    fontSize,
    spacing,
    chartHeight,
    sidebarCollapsed
  }
}

export default useResponsive
