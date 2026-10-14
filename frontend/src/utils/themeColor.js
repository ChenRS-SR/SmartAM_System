// 读取当前主题（styles/am-theme.css）的颜色变量，供 ECharts 等不能直接使用 CSS 变量的地方取色。
export function amVar(name, fallback = '') {
  if (typeof document === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}
