import { describe, expect, it } from 'vitest'
import { traceDiagnosis } from '../views/slm/forming/traceDiagnosis'

describe('设备诊断图与证据一致', () => {
  it('识别异常但尚无溯源时，不显示健康或已确认部件故障', () => {
    const result = traceDiagnosis(null, { label: '异常' })
    expect(result.state).toBe('pending')
    expect(result.powder).toBe('待诊断')
    expect(result.title).toContain('已识别缺陷')
  })
  it('贡献超限待复核时不强行归为设备故障', () => {
    expect(traceDiagnosis({ conclusion: '贡献超限，待复核' }).state).toBe('pending')
  })
  it('确认设备侧归因后恢复旧版铺粉故障图，结论不直接断言磨损', () => {
    const result = traceDiagnosis({ conclusion: '由设备因素诱发' })
    expect(result.image).toBe('fault_powder.png')
    expect(result.conclusion).toContain('具体部件待检查')
  })
  it('工艺侧归因不会误点亮设备故障图', () => {
    const result = traceDiagnosis({ conclusion: '由工艺因素诱发' })
    expect(result.image).not.toContain('fault_')
    expect(result.process).toBe('相关异常')
  })
})
