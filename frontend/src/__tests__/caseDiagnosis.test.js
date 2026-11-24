import {describe,it,expect} from 'vitest'
import {caseDiagnosis} from '../views/slm/forming/caseDiagnosis'
import {traceDiagnosis} from '../views/slm/forming/traceDiagnosis'
import {subsystemHealth} from '../views/slm/forming/subsystemHealth'
const trace=(id,prob=.8)=>({device:{id},task:{id:caseDiagnosis[id].taskId},conclusion:'已识别异常，归因待确认',factors:{dev:{prob},proc:{prob:.01}}})
describe('授权案例演示映射',()=>{
 it('B10 始终作为健康展示，不改写原始结果',()=>{
  const t=trace('slm-b10'),copy=JSON.stringify(t),d=traceDiagnosis(t)
  expect(d.faults).toEqual([]);expect(d.state).toBe('normal')
  expect(subsystemHealth(d,t).every(s=>s.state==='normal')).toBe(true)
  expect(JSON.stringify(t)).toBe(copy)
 })
 it.each([['slm-b15','gas'],['slm-b17-replay','feeder'],['slm-b44','scraper']])('%s 仅在设备侧异常时映射 %s',(id,key)=>{
  expect(traceDiagnosis(trace(id)).faults[0].key).toBe(key)
  expect(traceDiagnosis(trace(id,.1)).faults).toEqual([])
  const t=trace(id);t.available=false;expect(traceDiagnosis(t).faults).toEqual([])
  t.available=true;t.task.id='new-task';expect(traceDiagnosis(t).faults).toEqual([])
 })
 it('明确标签优先，纯工艺问题不套用设备部件',()=>{
  const t=trace('slm-b44');t.faultTypes=['laser'];expect(traceDiagnosis(t).faults[0].key).toBe('laser')
  const p=trace('slm-b15',.1);p.conclusion='由工艺因素诱发';expect(traceDiagnosis(p).state).toBe('process')
 })
})
