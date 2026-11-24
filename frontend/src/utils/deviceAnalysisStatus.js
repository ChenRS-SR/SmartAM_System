import { probabilityState } from './probabilityStyle'
import { traceDiagnosis } from '../views/slm/forming/traceDiagnosis'

// 总览与设备内部页共用结论，不再用采集在线状态或另一侧概率替代诊断结果。
export function deviceAnalysisStatus(frame) {
  const recognition = frame?.recognition
  const diagnosis = traceDiagnosis(frame?.trace)
  const equipmentAbnormal = ['fault', 'unclassified', 'process', 'reference'].includes(diagnosis.state)
  const printLabel = recognition?.label || '等待结果'
  return {
    printing: { text: printLabel, state: recognition?.available === false ? 'offline' : printLabel === '异常' ? (Number.isFinite(recognition.prob?.def) ? probabilityState(recognition.prob.def) : 'fault') : printLabel === '正常' ? 'healthy' : 'offline' },
    equipment: { text: diagnosis.state === 'normal' ? '正常' : equipmentAbnormal ? '异常' : '—', state: diagnosis.state === 'normal' ? 'healthy' : equipmentAbnormal ? 'fault' : 'offline' },
  }
}
