import { controlParameterKeys, controlParameters } from './controlParameters'

// 新案例封存元数据后自动纳入构建，区域数与设备数均不写死。
const packages = import.meta.glob('../../assets/control-regions/*.json', { eager: true, import: 'default' })
const cases = Object.fromEntries(Object.values(packages).map(item => [item.caseId, item]))
export function regionSlice(frame) {
  const data = cases[frame?.caseId]
  if (!data) return null
  // 用户确认典型截面可跨层持续展示；不复制数百份相同图片和区域元数据。
  return data.representative ? { ...data.representative, layer: frame.layer } : data.layers[String(frame.layer)] || null
}

// 经用户确认的自动展示策略：基准来自平台配置，不将层级概率冒充区域预测或实机反馈。
export function regionControlPlan(region, frame, defaults, ranges, automatic = true) {
  const parameters = controlParameters(defaults)
  const plan = { regionId: region.id, regionName: region.name, layer: frame?.layer ?? null, parameters,
    baseline: controlParameters(defaults), source: 'configured-region-control-demo', status: '保持基准', signalLayer: null }
  // 当前参数未填全或越界时不生成调整值；等待时间允许为零。
  for (const key of controlParameterKeys) {
    const value = parameters[key], range = ranges[key]
    if (!Number.isFinite(value) || !range || value < range.min || value > range.max) {
      return { ...plan, status: '请填写范围内的工艺参数', error: true }
    }
  }
  if (!automatic) return { ...plan, status: '自动调整已暂停' }
  const signal = frame?.controlSignal
  if (signal?.stop) return { ...plan, status: '停机检查，保持当前参数' }
  const recognition = frame?.recognition
  if (!signal && (!recognition || recognition.layer !== frame.layer)) return { ...plan, status: '等待本层识别' }
  const { proc, dev } = recognition?.prob || {}
  if (!signal && ![proc, dev].every(Number.isFinite)) return { ...plan, status: '缺少工艺/设备侧输出' }
  plan.signalLayer = signal ? frame.layer : recognition.layer
  if (!signal && Math.max(proc, dev) < .5) return plan
  // 设备故障档案按明确的场景方向演示；已有模型案例继续使用本层双侧识别。
  const processSide = signal ? signal.side === 'proc' : proc >= dev
  const strength = signal ? 1 : Math.min(1, Math.max(0, ((processSide ? proc : dev) - .5) / .5))
  const ratio = .05 + .05 * strength
  const increase = signal?.direction === 'increase'
  const key = processSide ? 'fill_power' : 'layer_wait_time'
  parameters[key] = processSide
    ? Math.round(defaults[key] * (1 + (increase ? ratio : -ratio)))
    : Number((defaults[key] + 1 + strength).toFixed(1))
  if (parameters[key] < ranges[key].min || parameters[key] > ranges[key].max) {
    return { ...plan, parameters: controlParameters(defaults), status: '调控值超出配置范围', error: true }
  }
  return { ...plan, status: processSide ? (increase ? '预计提高输入能量' : '预计降低输入能量') : '延长层间等待', adjustment: key }
}
