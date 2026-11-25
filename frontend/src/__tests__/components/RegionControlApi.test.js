import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import RegionControlPanel from '../../components/slm/RegionControlPanel.vue'
import LayerStrategyPlaceholders from '../../components/slm/LayerStrategyPlaceholders.vue'
import { ElMessage } from 'element-plus'
import { task4Api } from '../../utils/task4Api'
vi.mock('../../utils/task4Api', () => ({ task4Api: vi.fn() }))
vi.mock('element-plus', () => ({ElMessage:{success:vi.fn(),error:vi.fn(),info:vi.fn()}}))
afterEach(() => {vi.restoreAllMocks();vi.unstubAllGlobals();task4Api.mockReset()})
const slice={annotatedImage:'/slice.svg',regions:[{id:'region-1',name:'区域1',color:'#fff'}]}
const output=power=>({regions:[{regionId:'region-1',strategy:'adjust',automatic:true,status:'保持基准',currentParameters:{laserPower:200,fillSpeed:1000,layerWaitTime:2},controlParameters:{laserPower:power,fillSpeed:1000,layerWaitTime:2}}]})
const setup=async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({defaults:{fill_power:200,fill_speed:1000,layer_wait_time:2}})}))
 const w=mount(RegionControlPanel,{props:{slice,frame:{caseId:'b44-20250321-09-20',layer:8,offset:1000,recognition:{layer:8}}},global:{stubs:{ElButton:true}}})
 await flushPromises();return w
}
describe('区域调控通过开放接口统一生成方案',()=>{
 it('传递当前设备、层、游标及基准；到达旧请求不能覆盖新层',async()=>{
  let finishOld
  task4Api.mockImplementationOnce(()=>new Promise(resolve=>{finishOld=resolve})).mockResolvedValue(output(180))
  const w=await setup()
  expect(task4Api.mock.calls[0][1]).toMatchObject({deviceId:'slm-b44',layerNo:8,offset:1000,currentParameters:{laserPower:200,fillSpeed:1000,layerWaitTime:2}})
  await w.setProps({frame:{caseId:'b44-20250321-09-20',layer:9,offset:1100,recognition:{layer:9}}});await flushPromises()
  finishOld(output(220));await flushPromises()
  expect(w.get('[aria-label="自适应激光功率"]').element.value).toBe('180')
  w.unmount()
 })
 it('同层采样刷新和等价切片对象不重复请求调控方案',async()=>{
  task4Api.mockResolvedValue(output(180))
  const w=await setup()
  const calls=task4Api.mock.calls.length
  for(let i=0;i<5;i++){
   await w.setProps({slice:structuredClone(slice),frame:{caseId:'b44-20250321-09-20',layer:8,offset:1001+i,recognition:{layer:8}}})
   await flushPromises()
  }
  expect(task4Api.mock.calls.length).toBe(calls)
  expect(w.get('[aria-label="自适应激光功率"]').element.value).toBe('180')
  w.unmount()
 })
 it('按钮先保存再模拟，传递选定区域且不调用 execute',async()=>{
  task4Api.mockResolvedValue(output(180))
  const w=await setup()
  task4Api.mockResolvedValueOnce({planId:'P1'}).mockResolvedValueOnce({state:'simulated',executed:false})
  w.findComponent(LayerStrategyPlaceholders).vm.$emit('strategy','remelt');await flushPromises()
  expect(task4Api.mock.calls[1][1]).toMatchObject({operation:'save',regionIds:['region-1'],strategy:'remelt'})
  expect(task4Api.mock.calls[2][1]).toEqual({deviceId:'slm-b44',operation:'simulate',planId:'P1'})
  w.unmount()
 })
 it('整层重熔替代全部区域策略，并且只提示一次应用中',async()=>{
  const state={'region-1':'adjust','region-2':'adjust'}
  let saved
  task4Api.mockImplementation(async (_,body)=>{
   if(body.operation==='save'){saved=body;return {planId:'P2'}}
   if(body.operation==='simulate'){for(const id of saved.regionIds) state[id]=saved.strategy;return {state:'simulated'}}
   return {regions:Object.entries(state).map(([regionId,strategy])=>({...output(180).regions[0],regionId,strategy,automatic:strategy==='adjust',status:strategy==='adjust'?'自动调整':'策略2 · 重熔'}))}
  })
  const w=await setup()
  await w.setProps({slice:{...slice,regions:[...slice.regions,{id:'region-2',name:'区域2',color:'#ddd'}]}})
  const before=ElMessage.info.mock.calls.length
  w.findComponent(LayerStrategyPlaceholders).vm.$emit('strategy','remelt');await flushPromises()
  expect(w.get('[aria-label="区域自适应调整"]').element.checked).toBe(false)
  expect(w.find('.strategy-replacement').text()).toContain('重熔')
  expect(w.findAll('.region-strategy').map(x=>x.text())).toEqual(['策略2 · 重熔','策略2 · 重熔'])
  expect(ElMessage.info.mock.calls.length-before).toBe(1)
  expect(ElMessage.info.mock.lastCall[0].message).toContain('应用中')
  expect(ElMessage.success).not.toHaveBeenCalled()
  await w.findAll('.region-list button')[1].trigger('click')
  expect(w.get('[aria-label="区域自适应调整"]').element.checked).toBe(false)
  await w.findAll('.region-list button')[0].trigger('click')
  await w.get('[aria-label="区域自适应调整"]').setValue(true);await flushPromises()
  expect(w.find('.strategy-replacement').exists()).toBe(false)
  expect(state['region-1']).toBe('adjust')
  w.unmount()
 })

 it.each(['remelt','recoat','stop'])('整层策略 %s 提交所有区域且提示整层应用中',async strategy=>{
  task4Api.mockResolvedValue(output(180))
  const w=await setup()
  await w.setProps({slice:{...slice,regions:[...slice.regions,{id:'region-2',name:'区域2',color:'#ddd'}]}})
  task4Api.mockResolvedValueOnce({planId:'whole-layer'}).mockResolvedValueOnce({state:'simulated',executed:false})
  w.findComponent(LayerStrategyPlaceholders).vm.$emit('strategy',strategy);await flushPromises()
  const save=task4Api.mock.calls.find(([,body])=>body.operation==='save')[1]
  expect(save.regionIds).toEqual(['region-1','region-2'])
  expect(ElMessage.info.mock.lastCall[0].message).toContain('整层')
  const panels=w.findComponent(LayerStrategyPlaceholders).findAll('.strategy-panel')
  expect(panels[2].classes()).toContain('strategy-wide')
  expect(panels[0].classes()).not.toContain('strategy-wide')
  expect(panels[1].classes()).not.toContain('strategy-wide')
  expect(panels[0].find('.scope-label').text()).toBe('整层')
  expect(panels[1].find('.scope-label').text()).toBe('整层')
  expect(panels[2].find('.scope-label').text()).toBe('整层')
  w.unmount()
 })

})
