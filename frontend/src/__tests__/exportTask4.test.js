import { afterEach, describe, expect, it, vi } from 'vitest'
import { readCurrentTask4 } from '../utils/exportTask4'
import { task4Api } from '../utils/task4Api'
vi.mock('../utils/task4Api', () => ({task4Api:vi.fn()}))
afterEach(()=>task4Api.mockReset())
describe('当前画面导出',()=>{
 it('四接口共用点击瞬间的设备、游标和当前工艺参数',async()=>{
  task4Api.mockResolvedValue({ok:true})
  const frame={layer:9,offset:1950.25,processing:{real:false}}
  const pending=readCurrentTask4('slm-b44',frame,{currentParameters:{laserPower:240,fillSpeed:1200,layerWaitTime:3},automatic:false})
  frame.offset=2000;frame.layer=10
  const result=await pending
  expect(result.selection).toEqual({deviceId:'slm-b44',layerNo:9,offset:1950.25,processingMode:'archive'})
  const requests=Object.fromEntries(task4Api.mock.calls.map(([name,body])=>[name,body]))
  expect(requests['defect-recognition']).toMatchObject({offset:1950.25,resultScope:'display'})
  expect(requests['equipment-diagnosis']).toMatchObject({deviceIds:['slm-b44'],offset:1950.25,resultScope:'display'})
  expect(requests['quality-control']).toMatchObject({offset:1950.25,automatic:false,currentParameters:{laserPower:240,fillSpeed:1200,layerWaitTime:3}})
  expect(requests['maintenance-statistics']).toEqual({deviceIds:['slm-b44']})
 })
 it('没有快照时拒绝导出，不能偷偷查询默认起点',async()=>{
  await expect(readCurrentTask4('slm-b44',null)).rejects.toThrow('尚无可导出')
  expect(task4Api).not.toHaveBeenCalled()
 })
})
