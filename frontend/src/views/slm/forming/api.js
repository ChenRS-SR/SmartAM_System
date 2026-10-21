import { recordQualityResult } from './qualityContext'

// 成形监测接口封装。接口前缀默认 /api/slm/forming（与 SmartAM 后端挂载位置一致），可用 VITE_FORMING_API 覆盖。
const BASE = (import.meta.env.VITE_FORMING_API || '/api/slm/forming').replace(/\/$/, '')

async function req(method, path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const text = await r.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = null }
  if (!r.ok) {
    const msg = data && data.detail ? (typeof data.detail === 'string' ? data.detail : '请求参数有误') : `服务异常（${r.status}）`
    throw new Error(msg)
  }
  return data
}

// 接口返回的图像地址为相对路径（media/...），拼上接口前缀后使用
export const mediaUrl = (u, w) => (u?.startsWith('/api/slm/') ? u : (u ? `${BASE}/${u}${w ? `?w=${w}` : ''}` : null))

async function analyze(kind, path, body) {
  const result = await req('POST', path, body)
  recordQualityResult(kind, result)
  return result
}

export const api = {
  status: () => req('GET', '/status'),
  devices: () => req('GET', '/devices'),
  overview: (dev) => req('GET', `/devices/${dev}/overview`),
  tasks: (dev) => req('GET', `/devices/${dev}/tasks`),
  layers: (dev, task) => req('GET', `/devices/${dev}/tasks/${task}/layers`),
  access: (dev, layer) => req('GET', `/devices/${dev}/access${layer != null ? `?layer=${layer}` : ''}`),
  acquisition: (dev) => req('GET', `/devices/${dev}/acquisition`),
  acqStart: (dev, body = {}) => req('POST', `/devices/${dev}/acquisition/start`, body),
  acqStop: (dev) => req('POST', `/devices/${dev}/acquisition/stop`),
  recognize: (body) => analyze('recognition', '/recognition/infer', body),
  trace: (body) => analyze('trace', '/trace/analyze', body),
}
