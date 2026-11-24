import { describe, expect, it } from 'vitest'
import { diagnosisArtwork } from '../views/slm/forming/diagnosisArtwork'
import { faultTypes } from '../views/slm/forming/faultTypes'

describe('立体诊断图与类别对应', () => {
  it.each(faultTypes)('$name 使用独立部件图', fault => {
    expect(diagnosisArtwork({state:'fault',faults:[fault]})).toContain(`/${fault.key}.png`)
  })
  it('多故障和未分类设备问题不指定单一部件', () => {
    expect(diagnosisArtwork({faults:faultTypes.slice(0,2)})).toContain('/equipment.png')
    expect(diagnosisArtwork({state:'unclassified'})).toContain('/equipment.png')
  })
  it('工艺、健康与未接入状态分别展示', () => {
    expect(diagnosisArtwork({state:'process'})).toContain('/process.png')
    expect(diagnosisArtwork({healthy:true})).toContain('/healthy.png')
    expect(diagnosisArtwork({state:'pending'})).toContain('/neutral.png')
  })
  it('正常结论统一使用健康图，与子系统是否全部正常无关', () => {
    expect(diagnosisArtwork({state:'normal',healthy:false})).toContain('/healthy.png')
    expect(diagnosisArtwork({state:'normal',healthy:true})).toContain('/healthy.png')
    expect(diagnosisArtwork({state:'normal',equipmentIssue:true})).toContain('/equipment.png')
  })
})
