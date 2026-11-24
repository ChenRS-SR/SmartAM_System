import { expect, it } from 'vitest'
import { deviceAnalysisStatus } from '../utils/deviceAnalysisStatus'

it('打印异常与设备正常分别显示，不交叉代替结论', () => {
  const result=deviceAnalysisStatus({recognition:{label:'异常'},trace:{conclusion:'未见异常'}})
  expect(result.printing).toEqual({text:'异常',state:'fault'})
  expect(result.equipment).toEqual({text:'正常',state:'healthy'})
})
it('设备具体故障沿用诊断页分类', () => {
  const result=deviceAnalysisStatus({recognition:{label:'正常'},trace:{faultTypes:['scraper']}})
  expect(result.equipment).toEqual({text:'异常',state:'fault'})
  expect(result.printing.text).toBe('正常')
})
it('无结果不默认正常，工艺问题保留原结论', () => {
  expect(deviceAnalysisStatus(null).equipment).toEqual({text:'—',state:'offline'})
  expect(deviceAnalysisStatus(null).printing.text).toBe('等待结果')
  expect(deviceAnalysisStatus({trace:{conclusion:'由工艺因素诱发'}}).equipment.text).toBe('异常')
})
