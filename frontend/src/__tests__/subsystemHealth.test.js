import {describe,it,expect} from 'vitest'
import {subsystemHealth} from '../views/slm/forming/subsystemHealth'
import {traceDiagnosis} from '../views/slm/forming/traceDiagnosis'
describe('子系统健康图',()=>{
 it('七类部件映射四个系统，复合故障同时标红',()=>{
  const trace={faultTypes:['scraper','feeder','laser','filter','gas','fan','chiller']}
  const systems=subsystemHealth(traceDiagnosis(trace),trace)
  expect(systems.map(s=>s.details.length)).toEqual([2,1,3,1])
  expect(systems.every(s=>s.state==='fault')).toBe(true)
 })
 it('未接入不是健康，只有显式健康结果标绿',()=>{
  const systems=subsystemHealth({faults:[]},{subsystemHealth:{optics:{state:'normal'}}})
  expect(systems.map(s=>s.state)).toEqual(['unknown','normal','unknown','unknown'])
 })
 it('工艺偏移不误标设备，回退后清除旧故障',()=>{
  expect(subsystemHealth(traceDiagnosis({conclusion:'由工艺因素诱发'}),null).every(s=>s.state==='unknown')).toBe(true)
  const trace={faultTypes:['feeder']}
  expect(subsystemHealth(traceDiagnosis(trace),trace)[0].state).toBe('fault')
  expect(subsystemHealth(traceDiagnosis(null),null)[0].details).toEqual([])
 })
})
