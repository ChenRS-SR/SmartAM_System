import { describe, expect, it } from 'vitest'
import { energyCorrection, energyDensity } from '../components/slm/energyCorrection'

const params = { fill_power: 200, fill_speed: 1000, scan_spacing: .1, powder_feed_rate: 5 }
const ranges = { fill_power: { min: 50, max: 500 }, fill_speed: { min: 100, max: 5000 } }
const plan = (target, actuator = 'fill_power', thickness = .04, tolerance = 2) =>
  energyCorrection(params, thickness, target, tolerance, actuator, ranges)

describe('输入能量偏移回调', () => {
  it('用成形层厚计算能量，不受送粉速率影响', () => {
    expect(energyDensity(params, .04)).toBe(50)
    expect(energyDensity({ ...params, powder_feed_rate: 12 }, .04)).toBe(50)
    expect(energyDensity(params, .08)).toBe(25)
  })
  it('能量偏高时降功率或提速度，回到同一目标', () => {
    expect(plan(40)).toMatchObject({ status: 'high', value: 160, predicted: 40 })
    expect(plan(40, 'fill_speed')).toMatchObject({ status: 'high', value: 1250, predicted: 40 })
  })
  it('能量偏低时提功率或降速度，回到同一目标', () => {
    expect(plan(80)).toMatchObject({ status: 'low', value: 320, predicted: 80 })
    expect(plan(80, 'fill_speed')).toMatchObject({ status: 'low', value: 625, predicted: 80 })
    expect(params.fill_power).toBe(200)
  })
  it('目标偏差内不改变参数', () => {
    expect(plan(50.5)).toMatchObject({ status: 'normal', value: 200, predicted: 50 })
  })
  it('未设置目标、缺少层厚及非法数值不能生成调控参数', () => {
    for (const target of [null, undefined, 0, -1, NaN, Infinity]) expect(plan(target).error).toBeTruthy()
    expect(plan(80, 'fill_power', null).error).toBeTruthy()
    expect(plan(80, 'fill_power', .04, -1).error).toBeTruthy()
    expect(energyCorrection({ ...params, powder_feed_rate: null }, .04, 80, 2, 'fill_power', ranges).error).toBeTruthy()
  })
  it('超限或参数分辨率无法达到目标时报告，不静默截断', () => {
    expect(plan(200).error).toContain('超出配置范围')
    expect(plan(50.123, 'fill_power', .04, 0).error).toContain('参数精度')
  })
})
