// 新案例封存元数据后自动纳入构建，区域数与设备数均不写死。
const packages = import.meta.glob('../../assets/control-regions/*.json', { eager: true, import: 'default' })
const cases = Object.fromEntries(Object.values(packages).map(item => [item.caseId, item]))
export const regionSlice = frame => cases[frame?.caseId]?.layers[String(frame.layer)] || null

// 经用户确认的自动展示策略：基准来自平台配置，不将层级概率冒充区域预测或实机反馈。
export function regionControlPlan(region, frame, defaults, ranges, automatic = true) {
  const parameters = { ...defaults }
  const plan = { regionId: region.id, regionName: region.name, layer: frame.layer, parameters,
    baseline: { ...defaults }, source: 'configured-region-control-demo', status: '保持基准', signalLayer: null }
  const recognition = frame.recognition
  if (!automatic) return { ...plan, status: '自动调整已暂停' }
  if (!recognition || recognition.layer !== frame.layer) return { ...plan, status: '等待本层识别' }
  const { proc, dev } = recognition.prob
  if (![proc, dev].every(Number.isFinite)) return { ...plan, status: '缺少工艺/设备侧输出' }
  plan.signalLayer = recognition.layer
  if (Math.max(proc, dev) < .5) return plan
  // 仅作为预先约定的示意场景：工艺侧按能量偏高回调功率，设备侧按铺粉不足调整送粉。
  const processSide = proc >= dev
  const probability = processSide ? proc : dev
  const ratio = .05 + .05 * Math.min(1, Math.max(0, (probability - .5) / .5))
  const key = processSide ? 'fill_power' : 'powder_feed_rate'
  parameters[key] = Number((defaults[key] * (1 + (processSide ? -ratio : ratio))).toFixed(processSide ? 0 : 1))
  if (parameters[key] < ranges[key].min || parameters[key] > ranges[key].max) {
    return { ...plan, parameters: { ...defaults }, status: '调控值超出配置范围', error: true }
  }
  return { ...plan, status: processSide ? '预计降低输入能量' : '预计增加送粉', adjustment: key }
}
