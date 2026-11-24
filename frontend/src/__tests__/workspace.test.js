import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { reactive } from 'vue'
import { createRecordSession } from '../views/slm/workspace/recordSession'
import { pendingAnalysis } from '../views/slm/workspace/analysisPresentation'
import Recognition from '../views/slm/forming/views/Recognition.vue'
import Trace from '../views/slm/forming/views/Trace.vue'
import RegionControlPanel from '../components/slm/RegionControlPanel.vue'
import { factorCurveRows } from '../views/slm/forming/traceCurve'
import { monitoringAccess, monitoringImages } from '../views/slm/workspace/accessPresentation'
import { slmTabs, slmTab } from '../utils/slmNavigation'
import { mediaUrl } from '../views/slm/forming/api'

const frame = () => ({ layer: 8, time: '12:00:00', access: {
 device:{id:'slm-test',name:'测试设备'},task:{id:'task',name:'当前任务'},
 images:{before:{url:null}},torque:{t:[],scraper:[],platform:[],events:[]}
}})
const payload = id => ({schemaVersion:1,manifest:{deviceId:id},device:{id,name:id},snapshot:{caseId:id,
 access:{device:{id}},recognition:{device:{id}},trace:{device:{id}}}})
afterEach(()=>{vi.unstubAllGlobals();vi.restoreAllMocks()})

describe('统一工作区状态',()=>{
 it('全部设备使用固定通道槽位，不修改原始快照',()=>{
  const empty={images:{},channels:[]}
  const full={images:{before:{url:'/before.png'},video_0:{videoUrl:'/coax.mp4'}},channels:[{name:'同轴图像',imageKey:'video_0'}]}
  const a=monitoringAccess(empty),b=monitoringAccess(full)
  expect(a.channels.map(c=>c.name)).toEqual(b.channels.map(c=>c.name))
  expect(Object.keys(a.images)).toHaveLength(monitoringImages.length)
  expect(b.images.coax.videoUrl).toBe('/coax.mp4')
  expect(b.channels.map(c=>c.name)).toContain('可见光图像')
  expect(b.channels.map(c=>c.name)).not.toContain('侧轴图像')
  const sideOnly=monitoringAccess({images:{side:{videoUrl:'/side.mp4'}},channels:[{name:'侧轴图像',imageKey:'side'}]})
  expect(sideOnly.images.coax.available).toBe(false)
  expect(a.images.before.url).toBe(null)
  expect(empty.images).toEqual({})
  expect(slmTabs.map(t=>t.key)).toEqual(['status','recognition','trace','control'])
  expect(slmTab('access').key).toBe('status')
 })
 it('缺失模型输出保留识别和诊断卡片，未知量不显示为正常概率',async()=>{
  const session=reactive({snapshot:frame(),playing:false,manifest:{deviceId:'slm-test'}})
  for(const View of [Recognition,Trace]) {
   const w=mount(View,{global:{plugins:[createPinia()],provide:{formingReplay:session,formingEmbedded:true},stubs:{EChart:true,RouterLink:true}}})
   expect(w.find('.c-img').exists()).toBe(true)
   expect(w.find('.c-res').exists()).toBe(true)
   expect(w.find(View === Trace ? '.c-curve' : '.c-rec').exists()).toBe(true)
   expect(w.text()).not.toContain('100.0%')
   expect(w.text()).not.toContain('NaN')
   expect(w.text()).not.toContain('未见异常')
   w.unmount()
  }
 })
 it('没有区域时四种策略全部保留且不可提交',async()=>{
  const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({defaults:{}})})
  vi.stubGlobal('fetch',fetch)
  const w=mount(RegionControlPanel,{props:{frame:{caseId:'slm-b5',layer:8}},global:{stubs:{ElButton:{template:'<button :disabled="$attrs.disabled"><slot /></button>'}}}})
  await flushPromises()
  expect(w.find('[aria-label="层间调控策略1"]').exists()).toBe(true)
  expect(w.findAll('.strategy-panel')).toHaveLength(3)
  expect(w.findAll('.strategy-panel button').every(b=>b.element.disabled)).toBe(true)
  expect(w.get('[aria-label="区域自适应调整"]').element.disabled).toBe(true)
  expect(fetch.mock.calls.every(([url])=>url==='/api/slm/control/config')).toBe(true)
  w.unmount()
 })
 it('参数演示重载只有一个计时器，离开后停止刷新',async()=>{
  vi.useFakeTimers()
  const session=createRecordSession('slm-b17')
  vi.stubGlobal('fetch',vi.fn().mockImplementation(async()=>({ok:true,json:async()=>payload('slm-b17')})))
  try {
   await session.open();expect(vi.getTimerCount()).toBe(1)
   const first=session.snapshot.parameters.find(p=>p.id==='chamber_temperature').value
   await vi.advanceTimersByTimeAsync(1000)
   expect(session.snapshot.parameters.find(p=>p.id==='chamber_temperature').value).not.toBe(first)
   await session.open();expect(vi.getTimerCount()).toBe(1)
   session.dispose();expect(vi.getTimerCount()).toBe(0)
  } finally {session.dispose();vi.useRealTimers()}
 })
 it('旧请求不能覆盖重试，离开工作区不会再写入',async()=>{
  const completions=[]
  vi.stubGlobal('fetch',vi.fn(()=>new Promise(resolve=>completions.push(resolve))))
  const session=createRecordSession('slm-b17')
  const first=session.open(), second=session.open()
  completions[1]({ok:true,json:async()=>payload('slm-b17')});await second
  completions[0]({ok:true,json:async()=>payload('slm-other')});await first
  expect(session.snapshot.caseId).toBe('slm-b17')
  const third=session.open();session.dispose()
  completions[2]({ok:true,json:async()=>payload('slm-b17')});await third
  expect(session.snapshot).toBe(null)
 })
 it('接口错误和设备错配明确报错，重试可以恢复',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce({ok:false,status:503})
   .mockResolvedValueOnce({ok:true,json:async()=>payload('wrong')})
   .mockResolvedValueOnce({ok:true,json:async()=>payload('slm-b17')}))
  const session=createRecordSession('slm-b17')
  await session.open();expect(session.error).toContain('503');expect(session.snapshot).toBe(null)
  await session.open();expect(session.error).toContain('不匹配')
  await session.open();expect(session.error).toBe('');expect(session.snapshot.caseId).toBe('slm-b17');session.dispose()
 })
 it('贡献空值不变为零，公共静态资源路径不被改写',()=>{
  const d=pendingAnalysis(frame(),'trace')
  d.curve.layers=[{layer:8,dev_part:null,dev_powder:null}]
  expect(factorCurveRows(d)).toEqual([{layer:8,proc:null,dev:null}])
  expect(mediaUrl('/control-regions/B44.svg')).toBe('/control-regions/B44.svg')
 })
})
