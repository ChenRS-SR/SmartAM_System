// 跟随 SmartAM 的深色/浅色主题（html.dark），给图表提供对应配色；独立运行时始终为浅色。
import { computed, ref } from 'vue'

export const isDark = ref(false)
if (typeof document !== 'undefined') {
  const html = document.documentElement
  const update = () => { isDark.value = html.classList.contains('dark') }
  update()
  new MutationObserver(update).observe(html, { attributes: true, attributeFilter: ['class'] })
}

const LIGHT = {
  text: '#1f2933', axis: '#52606d', split: '#eef0f3', ink: '#222222', mark: '#555555',
  proc: '#b2312e', dev: '#3b6ba5', scraper: '#3b6ba5', platform: '#7b8794',
  upperProc: '#7a1f1d', upperDev: '#1d3a63', upper: '#2f7d4f', recoatArea: 'rgba(59,107,165,0.08)',
}
const DARK = {
  text: '#e3eaf3', axis: '#9fb0c6', split: '#22364f', ink: '#e3eaf3', mark: '#9fb0c6',
  proc: '#e0605c', dev: '#6f9bd1', scraper: '#6f9bd1', platform: '#9aa8b8',
  upperProc: '#f08a87', upperDev: '#9cc0ec', upper: '#4cb782', recoatArea: 'rgba(111,155,209,0.12)',
}
export const pal = computed(() => (isDark.value ? DARK : LIGHT))
