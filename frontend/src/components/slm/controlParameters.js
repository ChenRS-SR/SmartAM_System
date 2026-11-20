// 策略1的可见参数统一定义；设备协议的间距、送粉字段不进入此表单。
export const controlParameterDefs = {
  fill_power: { label: '激光功率', unit: 'W', step: 10, precision: 0 },
  fill_speed: { label: '填充速度', unit: 'mm/s', step: 50, precision: 0 },
  layer_wait_time: { label: '层间等待时间', unit: 's', step: .1, precision: 1 },
}
export const controlParameterKeys = Object.keys(controlParameterDefs)
export const controlParameters = values => Object.fromEntries(controlParameterKeys.map(key => [key, values[key]]))
