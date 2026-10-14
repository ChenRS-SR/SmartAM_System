// 各页面共享的选择状态：当前设备、各设备当前查看的层、识别与溯源参数。
import { reactive } from 'vue'
import { api } from './api.js'

const KEY = 'forming.state'
let saved = {}
try { saved = JSON.parse(localStorage.getItem(KEY) || '{}') } catch { saved = {} }

export const state = reactive({
  device: saved.device || 'blt-s430',
  layer: {},                       // 设备id -> 层号（缺省时由后端取当前接入层）
  recog: { threshold: 50, modalities: ['vis', 'tq'] },
  trace: { bandPx: null, refMode: 'prev_normal', refLayer: null },
  devices: [],
  status: null,
})

export function selectDevice(id) {
  state.device = id
  try { localStorage.setItem(KEY, JSON.stringify({ device: id })) } catch { /* 无痕模式等情况下不保存 */ }
}

export async function loadDevices() {
  if (!state.devices.length) state.devices = await api.devices()
  if (!state.devices.find((d) => d.id === state.device)) selectDevice(state.devices[0].id)
  return state.devices
}

export async function loadStatus() {
  if (!state.status) state.status = await api.status()
  return state.status
}

// 支持某模块的设备；当前设备不支持时切到第一台支持的设备
export function devicesFor(module) {
  const list = state.devices.filter((d) => d.modules.includes(module))
  if (list.length && !list.find((d) => d.id === state.device)) selectDevice(list[0].id)
  return list
}
