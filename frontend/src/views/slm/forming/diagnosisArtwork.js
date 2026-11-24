import { faultTypes } from './faultTypes'

const knownFaults = new Set(faultTypes.map(fault => fault.key))
// 未明确部件时只展示设备问题总览，避免图示误报具体故障。
export function diagnosisArtwork({ state, faults = [], healthy = false, equipmentIssue = false }) {
  let name = 'neutral'
  if (state === 'process') name = 'process'
  else if (faults.length === 1 && knownFaults.has(faults[0].key)) name = faults[0].key
  else if (faults.length || equipmentIssue || state === 'unclassified' || state === 'fault') name = 'equipment'
  // 正常诊断统一使用正常设备图，不因子系统接入状态不同而退回灰色底图。
  else if (state === 'normal' || healthy) name = 'healthy'
  return `/state_picture/diagnosis-v2/${name}.png`
}
