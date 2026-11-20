// 图像只表达已确认的归因方向，设备侧贡献不能直接断言刮刀磨损或其他部件损坏。
export function traceDiagnosis(trace, recognition) {
  if (!trace) return {
    image: 'power_off.png', state: 'pending', title: recognition?.label === '异常' ? '已识别缺陷，等待故障诊断' : '等待故障诊断',
    conclusion: '诊断证据尚未齐备', powder: '待诊断', process: '待诊断',
  }
  const dev = ['由设备因素诱发', '由二者共同诱发'].includes(trace.conclusion)
  const proc = ['由工艺因素诱发', '由二者共同诱发'].includes(trace.conclusion)
  const normal = trace.conclusion === '未见异常'
  return {
    image: dev ? 'fault_powder.png' : normal ? 'health.png' : 'power_off.png',
    state: dev || proc ? 'fault' : normal ? 'normal' : 'pending',
    title: trace.conclusion,
    conclusion: dev && proc ? '工艺输入与铺粉机构共同相关' : dev ? '铺粉机构相关异常，具体部件待检查' : proc ? '工艺输入偏移，需核对当前参数' : normal ? '当前层未见异常证据' : '识别与贡献证据需进一步复核',
    powder: dev ? '相关异常' : '未确认故障', process: proc ? '相关异常' : '未确认偏移',
  }
}
