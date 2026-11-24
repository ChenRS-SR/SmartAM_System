import {describe,it,expect} from 'vitest'
import {createParameterDemo} from '../views/slm/workspace/demoParameters'
import {compareFeaturedDevices} from '../utils/devicePriority'
describe('置顶设备与缺失参数演示',()=>{
 it('四台完整案例优先，档案 B17 不混入',()=>{
  const ids=['slm-b17','slm-b44','huake-slm-02','slm-b17-replay','slm-b15','slm-b10']
  expect(ids.map(id=>({id})).sort(compareFeaturedDevices).slice(0,4).map(d=>d.id)).toEqual(['slm-b10','slm-b15','slm-b17-replay','slm-b44'])
 })
 it('缺失值持续变化，真实值与零值保持不变，诊断不被改写',()=>{
  const frame={parameters:[{id:'scraper_torque',value:0},{id:'gas_pressure',value:'4.7'}],access:{env:{}},trace:{conclusion:'故障记录'}}
  const demo=createParameterDemo(frame,'slm-test');demo.update()
  const first=frame.parameters.find(p=>p.id==='chamber_temperature').value
  demo.update();expect(frame.parameters.find(p=>p.id==='chamber_temperature').value).not.toBe(first)
  expect(frame.parameters.find(p=>p.id==='scraper_torque').value).toBe(0)
  expect(frame.parameters.find(p=>p.id==='gas_pressure').value).toBe('4.7')
  expect(frame.access.env['气源压力']).toBe(4.7)
  expect(frame.trace).toEqual({conclusion:'故障记录'})
  expect(frame.access.env['成形室温度']).toBe(frame.parameters.find(p=>p.id==='chamber_temperature').value)
 })
})
