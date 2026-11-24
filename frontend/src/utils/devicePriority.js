// 置顶的是完整案例 B17，不能与只有故障档案的 slm-b17 混淆。
export const featuredDevices = ['slm-b10', 'slm-b15', 'slm-b17-replay', 'slm-b44']
export function compareFeaturedDevices(a, b) {
  const rank = id => { const i = featuredDevices.indexOf(id); return i < 0 ? featuredDevices.length : i }
  return rank(a.id) - rank(b.id)
}
