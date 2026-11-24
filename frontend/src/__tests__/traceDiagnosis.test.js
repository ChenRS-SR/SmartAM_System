import { describe, expect, it } from 'vitest'
import { traceDiagnosis } from '../views/slm/forming/traceDiagnosis'
import { faultTypes } from '../views/slm/forming/faultTypes'

describe('故障类别与部件图对应',()=>{
 it.each(faultTypes)('$name 使用独立配图键',type=>{
  const result=traceDiagnosis({faultTypes:[type.key]})
  expect(result.faults.map(f=>f.key)).toEqual([type.key])
  expect(result.conclusion).toBe(type.name)
 })
 it('B17 档案对应落粉轴扭矩，不把其他设备的数据带入',()=>{
  const result=traceDiagnosis({device:{id:'slm-b17'},recordDiagnosis:{state:'fault'}})
  expect(result.conclusion).toBe('落粉轴扭矩故障')
  expect(traceDiagnosis({device:{id:'slm-b44'},conclusion:'由设备因素诱发'}).faults).toEqual([])
 })
 it('多种故障分别展示，不折叠成笼统复合故障',()=>{
  const result=traceDiagnosis({device:{id:'slm-b28'},recordDiagnosis:{state:'fault'}})
  expect(result.faults.map(f=>f.key)).toEqual(['scraper','laser','chiller'])
 })
 it('工艺问题使用灰色整机图，不等同于激光器故障',()=>{
  const result=traceDiagnosis({device:{id:'huake-slm-02'},recordDiagnosis:{state:'fault'}})
  expect(result.image).toBe('power_off.png');expect(result.faults).toEqual([])
 })
 it('拖回无结果位置不保留未来层故障，不用新层识别猜旧层类型',()=>{
  expect(traceDiagnosis(null).conclusion).toBe('—')
  expect(traceDiagnosis({conclusion:'贡献超限，待复核'}, {layer:99,label:'异常'}).faults).toEqual([])
  expect(traceDiagnosis({conclusion:'未见异常'}).state).toBe('normal')
 })
})

it('仅贡献超参考水平不生成额外故障类别，正常概率结果显示正常', () => {
 const trace={device:{id:'slm-b44'},task:{id:'B44-20250321-09-20'},conclusion:'贡献超限，待复核',factors:{proc:{prob:.1},dev:{prob:.2}}}
 expect(traceDiagnosis(trace)).toMatchObject({state:'normal',conclusion:'正常',faults:[]})
 trace.factors.dev.prob=.8
 expect(traceDiagnosis(trace).conclusion).toBe('刮刀扭矩故障')
 trace.factors.dev.prob=.1;trace.factors.proc.prob=.8
 expect(traceDiagnosis(trace).state).toBe('process')
})
