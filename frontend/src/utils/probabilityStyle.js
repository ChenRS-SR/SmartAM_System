// 异常概率统一分级；融合权重不是异常概率，不使用警示配色。
export function probabilityState(value) {
  if (!Number.isFinite(value)) return 'offline'
  return value >= .7 ? 'fault' : value >= .5 ? 'warning' : 'healthy'
}
export function probabilityColor(value) {
  return {offline:'var(--am-text-3)', healthy:'var(--am-ok)', warning:'var(--am-prob-warning)', fault:'var(--am-danger)'}[probabilityState(value)]
}
