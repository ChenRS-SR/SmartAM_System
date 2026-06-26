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
