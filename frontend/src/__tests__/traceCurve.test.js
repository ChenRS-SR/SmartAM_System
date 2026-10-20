import { describe, expect, it } from 'vitest'
import { factorCurveRows } from '../views/slm/forming/traceCurve'

describe('诱发因素贡献曲线', () => {
  it('双侧结果分别取各自分区较大值，不混用两个分区', () => {
    expect(factorCurveRows({ mode: 'dual', curve: { layers: [
      { layer: 1, proc_part: 4, proc_powder: 2, dev_part: 1, dev_powder: 8 }
    ] } })).toEqual([{ layer: 1, proc: 4, dev: 8 }])
  })
  it('单侧数据不能把零件区贡献或示意工艺值当作工艺曲线', () => {
    expect(factorCurveRows({ mode: 'single', factors: { proc: { illustrative: true, prob: .03 } }, curve: { layers: [
      { layer: 1, part: 4, powder: 8 }
    ] } })).toEqual([{ layer: 1, proc: null, dev: 8 }])
  })
  it('真实小值、零和负贡献均保留，不按异常阈值隐藏', () => {
    const layers = [-1.46511, .000001, 0].map((value, i) => ({
      layer: i + 1, proc_part: value, proc_powder: value - 1, dev_part: 27.24871, dev_powder: 5.17267
    }))
    expect(factorCurveRows({ mode: 'dual', curve: { layers } }).map(r => r.proc))
      .toEqual([-1.46511, .000001, 0])
  })
})
