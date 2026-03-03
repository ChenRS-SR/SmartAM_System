import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', () => {
  // 主题模式: 'dark' | 'light' | 'auto'
  const themeMode = ref(localStorage.getItem('theme-mode') || 'dark')
  
  // 实际主题（auto 时根据系统偏好决定）
  const actualTheme = computed(() => {
    if (themeMode.value === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
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
  
  // 监听系统主题变化
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', () => {
    if (themeMode.value === 'auto') {
      applyTheme()
    }
  })
  
  // 监听主题变化自动应用
  watch(actualTheme, applyTheme, { immediate: true })
  
  // 主题配置
  const themeConfig = computed(() => {
    if (isDark.value) {
      return {
        '--bg-primary': '#0f172a',
        '--bg-secondary': '#1e293b',
        '--bg-card': 'rgba(15, 23, 42, 0.6)',
        '--bg-hover': 'rgba(0, 212, 255, 0.1)',
        '--text-primary': '#e2e8f0',
        '--text-secondary': '#a0aec0',
        '--text-muted': '#64748b',
        '--border-color': 'rgba(0, 212, 255, 0.2)',
        '--shadow-color': 'rgba(0, 0, 0, 0.5)'
      }
    } else {
      return {
        '--bg-primary': '#f8fafc',
        '--bg-secondary': '#f1f5f9',
        '--bg-card': 'rgba(255, 255, 255, 0.9)',
        '--bg-hover': 'rgba(0, 212, 255, 0.05)',
        '--text-primary': '#1e293b',
        '--text-secondary': '#475569',
        '--text-muted': '#94a3b8',
        '--border-color': 'rgba(0, 212, 255, 0.3)',
        '--shadow-color': 'rgba(0, 0, 0, 0.1)'
      }
    }
  })
  
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
