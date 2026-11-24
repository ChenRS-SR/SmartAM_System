import { traceDiagnosis } from '../views/slm/forming/traceDiagnosis'

// 总览与设备内部页共用结论，不再用采集在线状态或另一侧概率替代诊断结果。
export function deviceAnalysisStatus(frame) {
  const recognition = frame?.recognition
  const diagnosis = traceDiagnosis(frame?.trace)
  const printLabel = recognition?.label || '等待结果'
  return {
    printing: { text: printLabel, state: recognition?.available === false ? 'offline' : printLabel === '异常' ? 'fault' : printLabel === '正常' ? 'healthy' : 'offline' },
    equipment: { text: diagnosis.conclusion, state: diagnosis.state === 'normal' ? 'healthy' : ['fault', 'unclassified'].includes(diagnosis.state) ? 'fault' : diagnosis.state === 'process' ? 'warning' : 'offline' },
  }
}
