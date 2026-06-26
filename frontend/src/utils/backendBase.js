/**
 * 生成前端访问后端的默认地址。
 *
 * 局域网部署时，远程浏览器中的 localhost 指向浏览器所在电脑，
 * 因此默认使用当前页面主机名并连接后端 8000 端口。
 */
export function resolveBackendBaseUrl() {
  const configured = import.meta.env.VITE_API_BASE_URL
  if (configured) {
    return configured.replace(/\/$/, '')
  }

  if (typeof window === 'undefined') {
    return 'http://localhost:8000'
  }

  const protocol = window.location.protocol || 'http:'
  const hostname = window.location.hostname || 'localhost'
  return `${protocol}//${hostname}:8000`
}
