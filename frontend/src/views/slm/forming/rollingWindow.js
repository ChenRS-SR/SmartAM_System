export const WINDOW_SIZE = 50
// 溯源按成形层滚动，独立于扭矩采样点窗口。
export const TRACE_WINDOW_SIZE = 40

// 只裁剪展示数据，不改变模型输入；统一游标决定点的到达，横轴贴合实际采样范围。
export function torqueWindow(torque) {
  const live = Number.isFinite(torque.cursor)
  const indices = torque.t.map((_, i) => i)
    .filter(i => !live || (torque.t[i] <= torque.cursor && torque.t[i] >= torque.cursor - WINDOW_SIZE))
    .slice(-WINDOW_SIZE)
  const t = indices.map(i => torque.t[i])
  // 50 个点不等于 50 秒；用首尾采样时间定界，避免曲线只占窗口右半侧。
  const max = t.length ? t[t.length - 1] : 1
  const min = t.length ? t[0] : 0
  return {
    t, scraper: indices.map(i => torque.scraper[i]), platform: indices.map(i => torque.platform[i]),
    min: min === max ? min - 1 : min, max,
  }
}

export function layerWindow(rows, currentLayer) {
  return rows.filter(r => r.layer > currentLayer - TRACE_WINDOW_SIZE && r.layer <= currentLayer).slice(-TRACE_WINDOW_SIZE)
}

export const replayTimeLabel = value => new Date(value * 1000).toLocaleTimeString('zh-CN', {
  timeZone: 'Asia/Shanghai', hour12: false,
})
