// 一条曲线对应一种诱发因素；沿用各侧“分区贡献较大值”判据，不把分区当成诱发因素。
export function factorCurveRows(data) {
  return data.curve.layers.map(row => ({
    layer: row.layer,
    proc: Number.isFinite(row.proc_part) && Number.isFinite(row.proc_powder)
      ? Math.max(row.proc_part, row.proc_powder) : null,
    dev: data.mode === 'dual'
      ? Math.max(row.dev_part, row.dev_powder)
      : Math.max(row.part, row.powder)
  }))
}
