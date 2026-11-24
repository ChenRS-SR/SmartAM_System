// 监测页固定通道槽位；缺失只影响内容，不影响设备之间的卡片布局。
export const monitoringImages = [
  {key:'before', name:'铺粉后图像'}, {key:'after', name:'熔化后图像'},
  {key:'ir_before', name:'铺粉后红外图像'}, {key:'ir_after', name:'熔化后红外图像'},
]
export function monitoringAccess(data) {
  if (!data) return null
  const images = {}, channels = []
  for (const slot of monitoringImages) {
    const source = data.channels.find(c => c.name === slot.name)
    images[slot.key] = data.images[source?.imageKey || slot.key] || {url:null, time:null, layer:null, available:false}
    channels.push({...source, name:slot.name, imageKey:slot.key, spec:source?.spec || '图像', rate:source?.rate || '未接入'})
  }
  for (const name of ['刮刀扭矩', '加工平台扭矩']) {
    channels.push(data.channels.find(c => c.name === name) || {name, spec:'采样', rate:'未接入'})
  }
  return {...data, images, channels}
}
