/**
 * 生成前端访问后端的默认地址。
 *
 * 默认返回空字符串，表示使用当前前端同源地址访问 /api、/video_feed 等路径。
 * 这样 SSH 端口转发只需要转发 5173，Vite 代理会在服务器侧转到后端 8000。
 */
export function resolveBackendBaseUrl() {
  const configured = import.meta.env.VITE_API_BASE_URL
  if (configured) {
    return configured.replace(/\/$/, '')
  }

  return ''
}

/** 与 HTTP 接口共用后端地址，保留局域网或 VS Code 转发后的端口。 */
export function resolveBackendWebSocketUrl(path) {
  const base = resolveBackendBaseUrl() || window.location.origin
  const url = new URL(`${base}${path}`, window.location.origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.href
}
