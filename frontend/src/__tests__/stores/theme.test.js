import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useThemeStore } from '../../stores/theme.js'

describe('Theme Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Clear localStorage
    localStorage.clear()
  })

  it('should default to dark theme', () => {
    const store = useThemeStore()
    expect(store.themeMode).toBe('dark')
    expect(store.isDark).toBe(true)
  })

  it('should toggle theme', () => {
    const store = useThemeStore()
    
    store.toggleTheme()
    
    expect(store.themeMode).toBe('light')
    expect(store.isDark).toBe(false)
    expect(store.isLight).toBe(true)
    
    store.toggleTheme()
    
    expect(store.themeMode).toBe('dark')
    expect(store.isDark).toBe(true)
  })

  it('should set specific theme', () => {
    const store = useThemeStore()
    
    store.setTheme('light')
    expect(store.themeMode).toBe('light')
    
    store.setTheme('auto')
    expect(store.themeMode).toBe('auto')
  })

  it('should persist theme to localStorage', () => {
    const store = useThemeStore()
    
    store.setTheme('light')
    
    expect(localStorage.getItem('theme-mode')).toBe('light')
  })

  it('should load theme from localStorage', () => {
    localStorage.setItem('theme-mode', 'light')
    
    const store = useThemeStore()
    
    expect(store.themeMode).toBe('light')
  })

  it('should provide correct theme config for dark mode', () => {
    const store = useThemeStore()
    
    expect(store.themeConfig['--bg-primary']).toBe('#0f172a')
    expect(store.themeConfig['--text-primary']).toBe('#e2e8f0')
  })

  it('should provide correct theme config for light mode', () => {
    const store = useThemeStore()
    
    store.setTheme('light')
    
    expect(store.themeConfig['--bg-primary']).toBe('#f8fafc')
    expect(store.themeConfig['--text-primary']).toBe('#1e293b')
  })
})
