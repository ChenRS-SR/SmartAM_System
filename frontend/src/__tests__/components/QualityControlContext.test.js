import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { qualityContext, recordQualityResult } from '../../views/slm/forming/qualityContext'
import { state } from '../../views/slm/forming/state'
import { api } from '../../views/slm/forming/api'

const result = (overrides = {}) => ({
  device: { id: 'forming-01', name: '成形设备一' },
  task: { id: 'task-01', name: '任务一' },
  layer: 12, label: '异常', prob: { def: 0.86 },
  conclusion: '由工艺因素诱发', actions: ['工艺参数'],
  ...overrides
})

beforeEach(() => {
  Object.keys(qualityContext).forEach(key => delete qualityContext[key])
  state.devices = [{ id: 'forming-01', aliases: ['machine-01'] }]
  state.layer = { 'forming-01': 12 }
})
afterEach(() => vi.unstubAllGlobals())

describe('成形分析会话结果隔离', () => {
  it('使用接口实际返回的同层识别和溯源结果，按设备保存', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, text: async () => JSON.stringify(result())
    }))
    await api.recognize({ device_id: 'forming-01', layer: 12 })
    await api.trace({ device_id: 'forming-01', layer: 12 })
    expect(qualityContext['forming-01'].recognition.probability).toBe(.86)
    expect(qualityContext['forming-01'].trace.conclusion).toBe('由工艺因素诱发')
    expect(qualityContext['machine-02']).toBeUndefined()
  })

  it('更换层号或任务时不拼接旧结果，重新识别时清除旧溯源', () => {
    recordQualityResult('recognition', result())
    recordQualityResult('trace', result())
    recordQualityResult('recognition', result({ label: '正常' }))
    expect(qualityContext['forming-01'].trace).toBeNull()
    recordQualityResult('trace', result({ layer: 13 }))
    expect(qualityContext['forming-01'].recognition).toBeNull()
    recordQualityResult('recognition', result({ layer: 13, task: { id: 'task-02', name: '任务二' } }))
    expect(qualityContext['forming-01'].trace).toBeNull()
  })

  it('接口失败时不伪造分析摘要', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 503, text: async () => JSON.stringify({ detail: '分析服务不可用' })
    }))
    await expect(api.trace({ device_id: 'forming-01', layer: 12 })).rejects.toThrow('分析服务不可用')
    expect(Object.keys(qualityContext)).toHaveLength(0)
  })
})
