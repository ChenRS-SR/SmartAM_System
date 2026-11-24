import records from '../../../assets/fault-labels.json'
// 仅以明确的故障词匹配类别；功率偏移、收粉桶满等不能偷换成激光器或滤芯故障。
export const faultTypes = [
  {key:'scraper',name:'刮刀扭矩故障',pattern:/刮刀扭矩故障/},
  {key:'feeder',name:'落粉轴扭矩故障',pattern:/落粉轴扭矩故障/},
  {key:'laser',name:'激光器故障',pattern:/激光器(?:#\d+)?故障/},
  {key:'filter',name:'滤芯压力过大',pattern:/滤芯(?:压力过大|压差过大|阻力过大)/},
  {key:'gas',name:'气源压力故障',pattern:/气源压力故障/},
  {key:'fan',name:'风机转速过高',pattern:/风机转速过高/},
  {key:'chiller',name:'水冷机故障',pattern:/水冷机故障/},
]
export function recordedFaults(trace) {
  const record = records[trace?.device?.id]
  // 已标注的层级类别优先；设备档案仅用于档案页面，不能冒充逐层模型判断。
  const names = trace?.faultTypes
  if (Array.isArray(names)) return faultTypes.filter(t => names.includes(t.key) || names.includes(t.name))
  if (!trace?.recordDiagnosis || !record) return []
  const text = [record.status, ...record.diagnosis.evidence.map(e => e.text)].join('；')
  return faultTypes.filter(type => type.pattern.test(text))
}
export function processRecord(trace) {
  return trace?.recordDiagnosis && records[trace.device?.id]?.control.side === 'proc'
}
