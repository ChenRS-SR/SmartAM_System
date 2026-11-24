const definitions = [
  {key:'powder',name:'粉末输送与铺粉系统', faults:['scraper','feeder']},
  {key:'optics',name:'光学系统',faults:['laser']},
  {key:'gas',name:'气体循环系统',faults:['filter','gas','fan']},
  {key:'other',name:'其它系统',faults:['chiller']},
]
// 部件归属统一定义；未接入的子系统不能因其他系统已有故障而自动标为健康。
export function subsystemHealth(diagnosis, trace) {
  return definitions.map(system => {
    const faults = diagnosis.faults.filter(f => system.faults.includes(f.key))
    const measured = trace?.subsystemHealth?.[system.key]
    const normal = measured?.state === 'normal' || measured?.state === 'healthy'
    const state = faults.length || measured?.state === 'fault' ? 'fault' : normal ? 'normal' : 'unknown'
    return {...system, state, label:state === 'fault' ? '异常' : state === 'normal' ? '正常' : '未接入',
      details:faults.length ? faults.map(f=>f.name) : measured?.state === 'fault' ? [measured.faultType || '异常类别未登记'] : []}
  })
}
