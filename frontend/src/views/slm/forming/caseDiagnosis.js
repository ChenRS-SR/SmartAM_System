// 用户授权的案例演示标定；限定设备与任务，不能扩散到同设备后续采集任务。
export const caseDiagnosis = {
  'slm-b10': {taskId:'B10-20250509-07-47',health:'normal'},
  'slm-b15': {taskId:'B15-20250107-20-02',fault:'gas'},
  'slm-b17-replay': {taskId:'T20240828',fault:'feeder'},
  'slm-b44': {taskId:'B44-20250321-09-20',fault:'scraper'},
}
export function caseDiagnosisFor(trace) {
  const rule=caseDiagnosis[trace?.device?.id]
  return rule && trace.task?.id===rule.taskId ? rule : null
}
export function demoFault(trace) {
  const rule=caseDiagnosisFor(trace)
  if (!rule?.fault || trace.available===false || trace.recordDiagnosis || Array.isArray(trace.faultTypes)) return null
  // 使用溯源结果自身的设备侧概率，跳转时不拼入其他层的识别结果。
  const dev=trace.factors?.dev?.prob
  return ['由设备因素诱发','由二者共同诱发'].includes(trace.conclusion) || (Number.isFinite(dev) && dev>=.5) ? rule.fault : null
}
