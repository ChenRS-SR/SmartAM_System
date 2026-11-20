import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { useThemeStore } from '../../stores/theme.js'

let media, change
beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
  media = { matches: false, addEventListener: vi.fn((type, listener) => { change = listener }), removeEventListener: vi.fn() }
  vi.stubGlobal('matchMedia', () => media)
})
afterEach(() => vi.unstubAllGlobals())

describe('统一主题', () => {
  it('默认浅色，手动切换同步样式和持久化', () => {
    const store = useThemeStore()
    expect(store.isLight).toBe(true)
    store.toggleTheme()
    expect(store.isDark).toBe(true)
    expect(localStorage.getItem('theme-mode')).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    store.toggleTheme()
    expect(store.isLight).toBe(true)
  })
  it('读取保存的主题，兼容变量沿用公共配色', () => {
    localStorage.setItem('theme-mode', 'dark')
    const store = useThemeStore()
    expect(store.isDark).toBe(true)
    expect(store.themeConfig['--bg-primary']).toBe('var(--am-page-bg)')
    expect(store.themeConfig['--text-primary']).toBe('var(--am-text)')
  })
  it('自动模式响应系统变化，手动模式不受系统事件干扰', async () => {
    const store = useThemeStore()
    store.setTheme('auto')
    change({ matches: true })
    await nextTick()
    expect(store.isDark).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    change({ matches: false })
    await nextTick()
    expect(store.isLight).toBe(true)
    store.setTheme('dark')
    change({ matches: false })
    await nextTick()
    expect(store.isDark).toBe(true)
  })
  it('释放 store 时解绑系统监听', () => {
    useThemeStore().$dispose()
    expect(media.removeEventListener).toHaveBeenCalledWith('change', change)
  })
})
