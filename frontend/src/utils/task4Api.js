// 同源访问适用于 localhost 和局域网部署，不固定 IP 或端口。
export async function task4Api(endpoint, body, signal) {
  const response = await fetch(`/api/task4/${endpoint}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal
  })
  const result = await response.json()
  if (!response.ok || result.status !== 200) throw new Error(result.message || `接口请求失败（${response.status}）`)
  return result.data
}
