// VED 采用成形层厚，不使用铺粉量；只计算方案，不在此处发送设备指令。
export function energyDensity(params, thickness) {
  const values = [params.fill_power, params.fill_speed, params.scan_spacing, thickness]
  if (!values.every(v => typeof v === 'number' && Number.isFinite(v) && v > 0)) return null
  return params.fill_power / (params.fill_speed * params.scan_spacing * thickness)
}

export function energyCorrection(params, thickness, target, tolerance, actuator, ranges) {
  const current = energyDensity(params, thickness)
  // 调控后需发送整组参数，未参与 VED 的字段也必须有效。
  for (const [key, value] of Object.entries(params)) {
    if (!Number.isFinite(value) || value <= 0 ||
        (ranges[key] && (value < ranges[key].min || value > ranges[key].max))) {
      return { current, error: '请完整填写配置范围内的当前工艺参数' }
    }
  }
  if (current === null || !Number.isFinite(target) || target <= 0 ||
      !Number.isFinite(tolerance) || tolerance < 0 || tolerance > 20) {
    return { current, error: '请填写有效的工艺参数、成形层厚、目标能量密度及允许偏差' }
  }
  const deviation = (current / target - 1) * 100
  const status = Math.abs(deviation) <= tolerance ? 'normal' : deviation > 0 ? 'high' : 'low'
  const range = ranges[actuator]
  if (!['fill_power', 'fill_speed'].includes(actuator) || !range) return { current, error: '调控参数范围尚未加载' }
  // 每次仅改变功率或速度，保持扫描间距和层厚不变，避免多参数同时补偿。
  const value = status === 'normal' ? params[actuator] : Math.round(actuator === 'fill_power'
    ? target * params.fill_speed * params.scan_spacing * thickness
    : params.fill_power / (target * params.scan_spacing * thickness))
  const result = { current, target, tolerance, thickness, deviation, status, actuator, value }
  if (value < range.min || value > range.max) {
    return { ...result, error: `调控值 ${value} 超出配置范围 ${range.min}–${range.max}，请调整目标或切换回调参数` }
  }
  const parameters = { ...params, [actuator]: value }
  const predicted = energyDensity(parameters, thickness)
  if (Math.abs((predicted / target - 1) * 100) > tolerance + 1e-9) {
    return { ...result, error: '按参数精度取整后不能达到允许偏差，请调整目标或允许偏差' }
  }
  return { ...result, parameters, predicted }
}
