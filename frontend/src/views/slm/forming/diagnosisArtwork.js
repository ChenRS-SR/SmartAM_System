import { faultTypes } from './faultTypes'

const knownFaults = new Set(faultTypes.map(fault => fault.key))
// 未明确部件时只展示设备问题总览，避免图示误报具体故障。
export function diagnosisArtwork({ state, faults = [], healthy = false, equipmentIssue = false }) {
  let name = 'neutral'
  if (state === 'process') name = 'process'
  else if (faults.length === 1 && knownFaults.has(faults[0].key)) name = faults[0].key
  else if (faults.length || equipmentIssue || state === 'unclassified' || state === 'fault') name = 'equipment'
  else if (healthy) name = 'healthy'
  return `/state_picture/diagnosis-v2/${name}.png`
}
