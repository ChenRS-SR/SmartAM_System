import { ref } from 'vue'
import { defineStore } from 'pinia'
import catalog from '../../../backend/replay_cases/catalog.json'

export const REPLAY_DEVICE_ID = 'slm-b17-replay'
export const REPLAY_CASE_ID = 'blt-s430-20240828'
export const REPLAY_CASES = catalog.cases
export const replayCaseForDevice = id => REPLAY_CASES.find(item => item.deviceId === id)
const definitions = new Map()

// 每台设备独立保存时钟、快照和播放位置，切换设备不复用上一台的数据。
export function useReplayStore(caseId = REPLAY_CASE_ID) {
  if (!definitions.has(caseId)) definitions.set(caseId, defineStore(`caseReplay:${caseId}`, () => {
  const BASE = `/api/slm/replay/cases/${caseId}`
  const KEY = `smartam-replay-${caseId}`
  const manifest = ref(null)
  const snapshot = ref(null)
  const playing = ref(false)
  // 默认直接播放封存结果；设置开关只作用于当前设备。
  const realProcessing = ref(false)
  const speed = ref(10)
  const error = ref('')
  const loading = ref(false)
  let timer, controller, revision = 0, anchorOffset = 0, anchorClock = 0, opening = null
  const position = () => Math.min(manifest.value.duration, anchorOffset + (playing.value ? (performance.now() - anchorClock) / 1000 * speed.value : 0))

  async function read(path, signal) {
    const response = await fetch(`${BASE}/${path}`, { signal })
    if (!response.ok) throw new Error(`设备数据读取失败（${response.status}）`)
    return response.json()
  }
  function persist() {
    localStorage.setItem(KEY, JSON.stringify({ offset: snapshot.value.offset, speed: speed.value, realProcessing: realProcessing.value }))
  }
  // 只提交整份同游标快照；暂停、跳转后的旧请求不得覆盖新状态。
  async function refresh(version = revision) {
    const requested = position()
    const request = new AbortController()
    controller = request
    try {
      const next = await read(`snapshot?offset=${requested}&processing=${realProcessing.value ? 'real' : 'archive'}`, request.signal)
      if (version !== revision) return
      snapshot.value = next
      if (next.processing && !next.processing.real) realProcessing.value = false
      error.value = ''
      if (next.offset >= manifest.value.duration) {
        playing.value = false
        anchorOffset = next.offset
      }
      persist()
    } catch (e) {
      if (version !== revision || e.name === 'AbortError') return
      playing.value = false
      anchorOffset = snapshot.value?.offset ?? requested
      error.value = e.message
    } finally {
      if (version === revision) {
        loading.value = false
        if (playing.value) timer = setTimeout(() => refresh(version), 250)
      }
    }
  }
  async function move(offset, run = playing.value, clear = true) {
    revision += 1
    clearTimeout(timer)
    controller?.abort()
    anchorOffset = Math.max(0, Math.min(offset, manifest.value.duration))
    anchorClock = performance.now()
    playing.value = run
    if (clear) snapshot.value = null
    loading.value = true
    await refresh(revision)
  }
  async function open() {
    if (manifest.value) return
    if (opening) return opening
    opening = (async () => {
      loading.value = true
      try {
        manifest.value = await read('manifest')
        const saved = localStorage.getItem(KEY)
        const previous = saved ? JSON.parse(saved) : null
        if (previous && Number.isFinite(previous.offset) && [1, 5, 10, 30, 60].includes(previous.speed)) {
          speed.value = previous.speed
          realProcessing.value = previous.realProcessing === true
          anchorOffset = Math.min(previous.offset, manifest.value.duration)
        } else anchorOffset = manifest.value.defaultOffset
        await move(anchorOffset, true)
      } catch (e) {
        error.value = e.message
        manifest.value = null
        loading.value = false
      } finally { opening = null }
    })()
    return opening
  }
  async function setRealProcessing(value) {
    realProcessing.value = value
    return move(snapshot.value?.offset ?? anchorOffset, playing.value, true)
  }
  const pause = () => move(position(), false, false)
  const play = () => move(snapshot.value?.offset >= manifest.value.duration ? 0 : anchorOffset, true, false)
  const seek = (offset) => move(Number(offset))
  const seekLayer = (layer) => seek(manifest.value.layers.find(r => r.layer === Number(layer)).offset)
  function setSpeed(value) {
    const offset = position()
    speed.value = Number(value)
    return move(offset, playing.value, false)
  }
  function step(direction) {
    const rows = manifest.value.layers
    const i = rows.findIndex(r => r.layer === snapshot.value?.layer)
    return seek(rows[Math.max(0, Math.min(rows.length - 1, i + direction))].offset)
  }
  return { caseId, realProcessing, setRealProcessing, manifest, snapshot, playing, speed, error, loading, open, pause, play, seek, seekLayer, setSpeed, step }
}))
  return definitions.get(caseId)()
}
