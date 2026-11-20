// 仅规范显示名称，不改设备 ID、采集文件夹及历史数据索引。
export function standardDeviceName(value) {
  return String(value || '').replace(/(?:BLT[-\s]*|铂力特[-\s]*)(S\d+(?:-NEO)?)(?:[-\s]+(B\d+))?/gi,
    (_, model, serial) => `铂力特 ${model.toUpperCase()}${serial ? ` ${serial.toUpperCase()}` : ''}`)
}

export function standardDevice(device) {
  const model = standardDeviceName(device.model)
  // 导入清单曾将 7103 的 B17 错写为“华科SLM B17”，以型号与实际编号恢复名称。
  const serial = String(device.name || '').match(/\bB\d+\b/i)?.[0]
  const name = model.startsWith('铂力特 ') && serial ? `${model} ${serial.toUpperCase()}` : standardDeviceName(device.name)
  return { ...device, name, model, ...(model.startsWith('铂力特 ') ? {owner:'铂力特'} : {}) }
}
