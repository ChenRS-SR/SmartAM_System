import assessments from '../assets/maintenance-assessments.json'

export const maintenanceSystems = [
  ['powder', '刮刀'], ['fan', '风机'], ['filter', '滤芯'], ['feeder', '落粉轴'],
  ['argon', '气源系统'], ['laser', '激光器'], ['chiller', '水冷机']
]
const devices = { 'slm-b10': 'B10', 'slm-b15': 'B15', 'slm-b17-replay': 'B17', 'slm-b17': 'B17', 'slm-b44': 'B44' }
const taskDates = { 'slm-b10': '20250509-07-47', 'slm-b15': '20250107-20-02', 'slm-b17-replay': '20240828', 'slm-b44': '20250321-09-20' }
export function maintenanceRecords(deviceId, frame = null) {
  const recorded = assessments.devices[devices[deviceId]]
  if (recorded) return recorded
  if (!frame?.demonstration) return []
  // 无运维历史设备使用单次状态展示评估，不生成虚假的维修或故障历史。
  const phase = Date.parse(frame.time) / 1000
  const faults = frame.trace?.faultTypes || []
  const keys = {powder:'scraper', argon:'gas', feeder:'feeder', fan:'fan', filter:'filter', laser:'laser', chiller:'chiller'}
  const systems = assessments.devices.B10[0].systems.map((source, index) => {
    const fault = faults.includes(keys[source.key])
    const wave = .01 * Math.sin(phase * .2 + index)
    const reliability = fault ? source.rmin * .75 + wave : Math.min(.9999, Math.max(source.rmin + .005, .99 + wave * .2))
    return {...source, source:'generated-maintenance-demo', age:Math.max(1,source.age), reliability,
      ...(source.model === 'PHM' ? {w:fault ? Math.max(source.wr,source.wu) + .2 + wave : source.wl - .5 + wave} : {})}
  })
  return [{task:frame.recognition.task.id, systems}]
}
export function initialMaintenanceTask(deviceId) {
  const rows = maintenanceRecords(deviceId)
  const date = taskDates[deviceId]
  // B17 无同名评估任务，只选此前最近记录；界面保留真实任务编号。
  return (date ? rows.filter(row => row.task <= date).at(-1) : rows.at(-1))?.task || ''
}
export function maintenanceStatus(system) {
  if (!system || !Number.isFinite(system.reliability) || (system.model === 'PHM' && !['w', 'wl', 'wr', 'wu'].every(key => Number.isFinite(system[key])))) {
    return { type: 'info', label: '未接入', rank: -1 }
  }
  if (system.model === 'PHM' && system.w >= system.wu) return { type: 'danger', label: '达到维修上限', rank: 2 }
  if (system.reliability < system.rmin || (system.model === 'PHM' && system.w >= system.wr)) return { type: 'danger', label: '达到可靠性维护条件', rank: 2 }
  if (system.model === 'PHM' && system.w >= system.wl) return { type: 'warning', label: '进入经济维护区间', rank: 1 }
  return { type: 'success', label: '持续监测', rank: 0 }
}
export function maintenanceMeasurements(records, task, key) {
  const row = records.find(item => item.task === task)
  const current = row?.systems.find(item => item.key === key)
  if (!current) return null
  // 逐任务记录不插值为逐层数据；仅展示选定任务及此前的评估历史。
  const history = records.filter(item => item.task <= task)
  return { ...current, task, status: maintenanceStatus(current), duration: history.map(item => item.task),
    history: history.map(item => item.systems.find(system => system.key === key)) }
}
export function riskPosition(system, value) {
  const values = [system.w, system.wl, maintenanceLimit(system)].filter(Number.isFinite)
  if (!Number.isFinite(value) || !values.length) return 0
  const low = Math.min(...values), high = Math.max(...values)
  // W 可为负值，按实际值域定位，不能直接换算成百分比风险。
  return high === low ? 50 : 5 + 90 * (value - low) / (high - low)
}

// 两项上限按每个任务取较小值；任一缺失时不伪造合并阈值。
export function maintenanceLimit(system) {
  return Number.isFinite(system?.wr) && Number.isFinite(system?.wu) ? Math.min(system.wr, system.wu) : null
}

export function maintenanceChartSeries(measurements) {
  const definitions = measurements?.model === 'PLP'
    ? [['reliability', '可靠性 R', '#4686b8'], ['rmin', '可靠性下限 Rmin', '#dc4545']]
    : [['w', '风险指标 W', '#7189ba'], ['wl', '阈值下限 WL', '#4686b8'], ['limit', '阈值上限 min(WR, WU)', '#dc4545']]
  return definitions.map(([key, name, color], index) => ({
    name, type: 'line',
    data: (measurements?.history || []).map(row => key === 'limit' ? maintenanceLimit(row) : row[key] ?? null),
    connectNulls: false, symbol: index ? 'none' : 'circle', symbolSize: 7, showSymbol: index === 0, showAllSymbol: index === 0,
    // 指标采用带点实线；阈值为无点虚线。
    lineStyle: {color, width: 2, type: index ? 'dashed' : 'solid'}, itemStyle: {color}
  }))
}
