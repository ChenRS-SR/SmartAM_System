import { ref, computed, watch, onScopeDispose } from 'vue'
import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', () => {
  // 主题模式: 'dark' | 'light' | 'auto'
  const themeMode = ref(localStorage.getItem('theme-mode') || 'light')
  
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  const systemDark = ref(mediaQuery.matches)

  // 实际主题（auto 时根据系统偏好决定）
  const actualTheme = computed(() => {
    if (themeMode.value === 'auto') {
      return systemDark.value ? 'dark' : 'light'
    }
    return themeMode.value
  })
  
  const isDark = computed(() => actualTheme.value === 'dark')
  const isLight = computed(() => actualTheme.value === 'light')
  
  // 设置主题
  const setTheme = (mode) => {
    themeMode.value = mode
    localStorage.setItem('theme-mode', mode)
    applyTheme()
  }
  
  // 切换主题
  const toggleTheme = () => {
    const newMode = isDark.value ? 'light' : 'dark'
    setTheme(newMode)
  }
  
  // 应用主题到 DOM
  const applyTheme = () => {
    const html = document.documentElement
    if (isDark.value) {
      html.classList.add('dark')
      html.classList.remove('light')
    } else {
      html.classList.add('light')
      html.classList.remove('dark')
    }
  }
  
  // 将系统事件转成响应式状态；否则 computed 会缓存旧值，自动主题不会切换。
  const updateSystemTheme = event => { systemDark.value = event.matches }
  mediaQuery.addEventListener('change', updateSystemTheme)
  onScopeDispose(() => mediaQuery.removeEventListener('change', updateSystemTheme))

  // 监听主题变化自动应用
  watch(actualTheme, applyTheme, { immediate: true })
  
  // 主题配置：两种主题的具体颜色见 styles/am-theme.css，这里只把原有变量指向主题变量
  const themeConfig = computed(() => ({
    '--bg-primary': 'var(--am-page-bg)',
    '--bg-secondary': 'var(--am-card-bg-2)',
    '--bg-card': 'var(--am-card-bg)',
    '--bg-hover': 'var(--am-accent-soft)',
    '--text-primary': 'var(--am-text)',
    '--text-secondary': 'var(--am-text-2)',
    '--text-muted': 'var(--am-text-3)',
    '--border-color': 'var(--am-card-border)',
    '--shadow-color': isDark.value ? 'rgba(0, 0, 0, 0.5)' : 'rgba(0, 0, 0, 0.1)'
  }))

  // 应用 CSS 变量
  watch(themeConfig, (config) => {
    const root = document.documentElement
    Object.entries(config).forEach(([key, value]) => {
      root.style.setProperty(key, value)
    })
  }, { immediate: true, deep: true })
  
  return {
    themeMode,
    actualTheme,
    isDark,
    isLight,
    setTheme,
    toggleTheme,
    applyTheme,
    themeConfig
  }
})
