import { createParameterDemo } from './demoParameters'
import { reactive } from 'vue'
import { standardDevice } from '../../../utils/deviceNames'

// 档案与缺失参数演示分离；离开、重试时释放本设备计时器与请求。
export function createRecordSession(deviceId) {
  const session = reactive({ caseId: deviceId, manifest: null, snapshot: null, device: null,
    playing: false, loading: false, error: '', statusLabel: '档案已载入', source: 'device-record' })
  let demoTimer
  let controller
  let disposed = false
  session.open = async () => {
    clearInterval(demoTimer)
    controller?.abort()
    const request = new AbortController()
    controller = request
    session.loading = true
    session.error = ''
    let timedOut = false
    const timeout = setTimeout(() => { timedOut = true; request.abort() }, 15000)
    // 重试时撤下旧快照，避免请求失败后仍允许对旧区域提交方案。
    session.snapshot = null
    try {
      const response = await fetch(`/api/slm/workspace/devices/${encodeURIComponent(deviceId)}`, { signal: request.signal })
      if (!response.ok) throw new Error(`设备数据读取失败（${response.status}）`)
      const result = await response.json()
      if (result.schemaVersion !== 1 || result.manifest?.deviceId !== deviceId || result.snapshot?.caseId !== deviceId) {
        throw new Error('设备数据与当前工作区不匹配')
      }
      if (disposed || request.signal.aborted) return
      session.device = standardDevice(result.device)
      for (const name of ['access', 'recognition', 'trace']) result.snapshot[name].device.name = session.device.name
      session.manifest = result.manifest
      session.snapshot = result.snapshot
      const demo = createParameterDemo(session.snapshot, deviceId)
      if (demo.enabled) {
        demo.update()
        session.statusLabel = '状态更新中'
        demoTimer = setInterval(() => demo.update(), 1000)
      } else session.statusLabel = '档案已载入'
    } catch (e) {
      if (!disposed && controller === request) {
        if (timedOut) session.error = '设备数据读取超时，请重试'
        else if (!request.signal.aborted) session.error = e.message
      }
    } finally {
      clearTimeout(timeout)
      if (!disposed && controller === request) session.loading = false
    }
  }
  session.dispose = () => { disposed = true; clearInterval(demoTimer); controller?.abort() }
  return session
}
