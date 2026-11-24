import { caseDiagnosisFor } from './caseDiagnosis'
const definitions = [
  {key:'powder',name:'粉末输送与铺粉系统', faults:['scraper','feeder']},
  {key:'optics',name:'光学系统',faults:['laser']},
  {key:'gas',name:'气体循环系统',faults:['filter','gas','fan']},
  {key:'other',name:'其它系统',faults:['chiller']},
]
// 部件归属统一定义；未接入的子系统不能因其他系统已有故障而自动标为健康。
export function subsystemHealth(diagnosis, trace, frame) {
  // 仅为四个已登记完整案例关联当前接入快照；已接入不等同于已诊断健康。
  // B17 原始接入包沿用 blt-s430 编号，仅在其明确案例内识别该旧编号。
  const sameDevice = frame?.access?.device?.id === trace?.device?.id || (trace?.device?.id === 'slm-b17-replay' && frame?.caseId === 'blt-s430-20240828' && frame?.access?.device?.id === 'blt-s430')
  const connectedCase = !!caseDiagnosisFor(trace) && trace?.available !== false && sameDevice
  const hasParameter = names => frame?.parameters?.some(p => names.includes(p.name) && Number.isFinite(p.value))
  const connections = connectedCase ? {
    powder: hasParameter(['刮刀扭矩', '加工平台扭矩', '储粉桶物位']),
    optics: !!frame.access.images?.before?.url && !!frame.access.images?.after?.url,
    gas: hasParameter(['气源压力', '氩气压力', '循环气体流量', '风机转速']),
    other: hasParameter(['成形室温度', '加热板温度']),
  } : {}
  return definitions.map(system => {
    const faults = diagnosis.faults.filter(f => system.faults.includes(f.key))
    const measured = trace?.subsystemHealth?.[system.key]
    const normal = diagnosis.demoHealth === 'normal' || measured?.state === 'normal' || measured?.state === 'healthy'
    const state = faults.length || measured?.state === 'fault' ? 'fault' : normal ? 'normal' : connections[system.key] ? 'connected' : 'unknown'
    return {...system, state, label:state === 'fault' ? '异常' : state === 'normal' ? '正常' : state === 'connected' ? '已接入' : '未接入',
      details:faults.length ? faults.map(f=>f.name) : measured?.state === 'fault' ? [measured.faultType || '异常类别未登记'] : []}
  })
}
