// 用户授权的状态参数展示：仅补缺失采样，不参与模型、故障分类和控制方案计算。
const definitions = [
  ['scraper_torque','刮刀扭矩','%',18,2], ['platform_torque','加工平台扭矩','%',12,1.5],
  ['oxygen','成形室氧含量','%',.012,.002,'成形室氧含量ppm',10000],
  ['ambient_oxygen','环境氧含量','%',20.9,.08],
  ['chamber_temperature','成形室温度','℃',35,1.2,'成形室温度'],
  ['chamber_pressure','成形室压力','mBar',8,.5,'成形室压力'],
  ['bed_temperature','加热板温度','℃',80,1.5,'加热板温度'],
  ['gas_flow','循环气体流量','m3/h',420,12,'循环气体实时流量'],
  ['fan_speed','风机转速','%',65,2,'风机转速'],
  ['gas_pressure','气源压力','Bar',4.8,.15,'气源压力'],
  ['powder_level','储粉桶物位','mm',150,3,'储粉桶物位计'],
  ['medium_filter_resistance','中效滤芯阻力','mBar',12,.8],
  ['high_filter_resistance','高效滤芯阻力','mBar',8,.5],
  ['compressed_air_pressure','压缩空气压力','Bar',5,.15],
  ['servo_temperature_x','X轴伺服温度','℃',38,1],['servo_temperature_y','Y轴伺服温度','℃',39,1],
  ['galvo_temperature_x','X轴振镜温度','℃',32,.8],['galvo_temperature_y','Y轴振镜温度','℃',33,.8],
  ['output_current_x','X轴输出电流','mA',260,8],['output_current_y','Y轴输出电流','mA',265,8],
]
const present = value => value !== null && value !== undefined && String(value).trim() !== '' && Number.isFinite(Number(value))
export function createParameterDemo(frame, deviceId) {
  const seed = [...deviceId].reduce((n,c)=>(n*31+c.charCodeAt(0))>>>0,7)
  const params = frame.parameters || (frame.parameters = [])
  const env = frame.access?.env
  const targets = definitions.flatMap((def,index) => {
    const [id,name,unit,base,amplitude,envKey,scale=1] = def
    let param = params.find(p => p.id === id || p.name === name)
    const parameterMissing = !param || !present(param.value)
    const envMissing = env && envKey && !present(env[envKey])
    if (!parameterMissing && !envMissing) return []
    if (!param) { param = {id,name,unit,value:null}; params.push(param); param = params[params.length - 1] }
    // 任一真实通道存在时用于补全同一量的显示，避免两个面板数值矛盾。
    if (parameterMissing && envKey && present(env?.[envKey])) { param.value = env[envKey]/scale; return [] }
    if (!parameterMissing) { if(envMissing) env[envKey] = Number(param.value)*scale; return [] }
    return [{param,base,amplitude,envKey,scale,index}]
  })
  frame.demonstration = {kind:'generated-missing-status-parameters', parameterIds:targets.map(t=>t.param.id)}
  let tick = 0
  return {
    enabled:targets.length>0,
    update() {
      tick += 1
      for (const t of targets) {
        const phase = (seed%1000)*.013+t.index*1.71
        const value = Number((t.base + t.amplitude*(.65*Math.sin(tick*.73+phase)+.35*Math.sin(tick*1.19+phase))).toFixed(t.param.unit==='%' && t.base<1 ? 4 : 2))
        t.param.value = value
        t.param.source = 'generated-demo'
        if (env && t.envKey) env[t.envKey] = Number((value*t.scale).toFixed(4))
      }
      frame.demonstration.updatedAt = new Date().toISOString()
    }
  }
}
