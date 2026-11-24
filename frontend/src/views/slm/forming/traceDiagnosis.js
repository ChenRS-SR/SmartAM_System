import { caseDiagnosisFor, demoFault } from './caseDiagnosis'
import { recordedFaults, processRecord, faultTypes } from './faultTypes'
// 图像和类型始终来自同一层或同一份档案，不使用新层识别给旧层溯源贴标签。
export function traceDiagnosis(trace) {
  const rule=caseDiagnosisFor(trace)
  if (rule?.health==='normal' && !Array.isArray(trace.faultTypes)) return {state:'normal',title:'正常',conclusion:'设备状态正常',faults:[],demoHealth:'normal',origin:'case-demo'}
  const marked=recordedFaults(trace)
  const demo=demoFault(trace)
  const faults=marked.length ? marked : demo ? faultTypes.filter(t=>t.key===demo) : []
  if (faults.length) return {state:'fault', title:trace?.factors?.proc?.prob>=.5 ? '工艺与设备问题' : '设备问题', conclusion:faults.map(f=>f.name).join('、'), faults, origin:demo ? 'case-demo' : 'record', source:trace.recordDiagnosis ? '设备档案' : null}
  const proc = processRecord(trace) || ['由工艺因素诱发','由二者共同诱发'].includes(trace?.conclusion)
  const dev = ['由设备因素诱发','由二者共同诱发'].includes(trace?.conclusion) || (trace?.recordDiagnosis?.state === 'fault' && !proc)
  if (proc) return {image:'power_off.png',state:'process',title:'工艺问题',conclusion:'工艺问题引发异常',faults:[],source:trace?.recordDiagnosis ? '设备档案' : null}
  if (dev) return {state:'unclassified',title:'设备问题',conclusion:'设备问题',faults:[]}
  if (trace?.conclusion === '未见异常') return {image:'health.png',state:'normal',title:'正常',conclusion:'未见异常',faults:[]}
  // 完整案例已有结果时显示参考偏离，不把已接入误写成无结果。
  if (rule && trace.available !== false && trace.conclusion === '贡献超限，待复核') return {state:'reference',title:'故障诊断',conclusion:'贡献偏离正常样本参考水平',faults:[]}
  return {state:'pending',title:'故障诊断',conclusion:'—',faults:[]}
}
