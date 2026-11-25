import { describe, expect, it } from 'vitest'
import { regionSlice, regionControlPlan } from '../components/slm/regionControl'

const defaults = { fill_power: 200, fill_speed: 1000, layer_wait_time: 2 }
const ranges = { fill_power: { min: 50, max: 500 }, fill_speed: { min: 100, max: 5000 }, layer_wait_time: { min: 0, max: 600 } }
const frame = (layer = 3, proc = .1, dev = .95) => ({ caseId: 'b44-20250321-09-20', layer, recognition: { layer, prob: { proc, dev } } })

describe('真实切片区域与自动调控示意', () => {
  it('B44当前层精确对应原切片，不跨层或跨设备借图', () => {
    const slice = regionSlice(frame())
    expect(slice.image).toContain('/bp_3.png')
    expect(slice.regions.map(r => [r.name, r.color])).toEqual([['区域1', '#ffb0da'], ['区域2', '#4150b4']])
    expect(regionSlice({ ...frame(), layer: 999 })).toBeNull()
    expect(regionSlice({ ...frame(), caseId: 'blt-s430-20240828' }).regions.length).toBe(2)
  })
  it('异常层为各区域单独生成层间等待参数，不修改基准', () => {
    const f = frame()
    const plans = regionSlice(f).regions.map(r => regionControlPlan(r, f, defaults, ranges))
    expect(plans[0].parameters.layer_wait_time).toBe(3.9)
    expect(plans[0].parameters.fill_power).toBe(200)
    plans[0].parameters.fill_power = 180
    expect(plans[1].parameters.fill_power).toBe(200)
    expect(defaults.fill_power).toBe(200)
    expect(plans[0].source).toBe('configured-region-control-demo')
  })
  it('工艺侧示例降低功率，正常层直接显示基准值', () => {
    const r = regionSlice(frame()).regions[0]
    expect(regionControlPlan(r, frame(3, .99, .1), defaults, ranges).parameters.fill_power).toBe(180)
    expect(regionControlPlan(r, frame(3, .1, .1), defaults, ranges).parameters).toEqual(defaults)
  })
  it('回退或切层后不使用其他层的识别，暂停自动调整保留基准', () => {
    const f = frame(); f.recognition.layer = 2
    const r = regionSlice(f).regions[0]
    expect(regionControlPlan(r, f, defaults, ranges).status).toBe('等待本层识别')
    expect(regionControlPlan(r, frame(), defaults, ranges, false).parameters).toEqual(defaults)
  })
  it('各案例首尾层有对应截面，区域数符合设备光源配置', () => {
    const specs = [['blt-s430-20240828', 700, 2700], ['b10-20250509-07-47', 1600, 6600], ['b15-20250107-20-02', 100, 200], ['m130-20251120', 6, 954]]
    for (const [caseId, first, last] of specs) {
      const a = regionSlice({caseId, layer:first}), b = regionSlice({caseId, layer:last})
      expect(a.regions.length).toBeGreaterThan(0)
      expect(a.regions.length).toBe(caseId === 'blt-s430-20240828' ? 2 : 1)
      expect(a.annotatedImage).toBe(b.annotatedImage)
      expect(a.image).toContain(caseId)
    }
    expect(regionSlice({caseId:'b10-20250509-07-47',layer:1600}).regions.length).toBe(1)
  })
  it('故障场景按过功率/欠功率调整，停机场景保持基准', () => {
    const region = {id:'region-1', name:'区域1'}
    const f = direction => ({layer:1,controlSignal:{side:'proc',direction}})
    expect(regionControlPlan(region, f('increase'), defaults, ranges).parameters.fill_power).toBe(220)
    expect(regionControlPlan(region, f('decrease'), defaults, ranges).parameters.fill_power).toBe(180)
    expect(regionControlPlan(region, {layer:1, controlSignal:{stop:true}}, defaults, ranges).parameters).toEqual(defaults)
  })
  it('超出配置范围时阻止生成越界值', () => {
    const r = regionSlice(frame()).regions[0]
    const p = regionControlPlan(r, frame(), defaults, { ...ranges, layer_wait_time: { min: 0, max: 3 } })
    expect(p.error).toBe(true)
    expect(p.parameters).toEqual(defaults)
  })
})
