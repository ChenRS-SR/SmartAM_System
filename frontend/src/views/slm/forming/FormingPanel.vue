<template>
  <div class="forming-root forming-panel">
    <div v-if="msg" class="err" @click="msg = ''">{{ msg }}</div>
    <template v-if="ready">
      <component :is="view" v-if="matched" :key="matched.id + module" />
      <div v-else class="unlinked">
        <div class="u-title">该设备尚未接入成形监测</div>
        <div class="u-text">已接入的设备：{{ linkedNames || '无' }}。接入后可在此查看逐层数据接入、异常识别与异常溯源。</div>
      </div>
    </template>
    <div v-else class="loading">{{ loadErr || '正在连接成形监测服务…' }}</div>
  </div>
</template>

<script setup>
// 嵌入宿主系统（SmartAM 设备检测）的成形监测面板：由宿主传入当前设备编号与模块，设备选择由宿主决定。
import { computed, onMounted, provide, ref, watch } from 'vue'
import { loadDevices, loadStatus, selectDevice, state } from './state.js'
import Access from './views/Access.vue'
import Recognition from './views/Recognition.vue'
import Trace from './views/Trace.vue'
import Overview from './views/Overview.vue'
import './forming.css'

const props = defineProps({
  device: { type: String, default: '' },              // 宿主中的设备编号，如 slm-b17
  module: { type: String, default: 'recognition' },   // access / recognition / trace / overview
})
const VIEWS = { access: Access, recognition: Recognition, trace: Trace, overview: Overview }
const view = computed(() => VIEWS[props.module] || Recognition)
const ready = ref(false)
const loadErr = ref('')
const msg = ref('')
let timer = null
provide('formingEmbedded', true)
provide('formingError', (e) => {
  msg.value = e && e.message ? e.message : String(e)
  clearTimeout(timer)
  timer = setTimeout(() => { msg.value = '' }, 4000)
})
const matched = computed(() => state.devices.find((d) => (d.id === props.device || (d.aliases || []).includes(props.device))
  && (props.module === 'overview' || d.modules.includes(props.module))))
const linkedNames = computed(() => state.devices.filter((d) => (d.aliases || []).length).map((d) => d.name).join('、'))
watch(matched, (m) => { if (m && state.device !== m.id) selectDevice(m.id) }, { immediate: true })
onMounted(async () => {
  try {
    await Promise.all([loadDevices(), loadStatus()])
    if (matched.value) selectDevice(matched.value.id)
    ready.value = true
  } catch (e) {
    loadErr.value = `无法连接成形监测服务：${e.message}`
  }
})
</script>

<style scoped>
.forming-panel { position: relative; height: max(724px, calc(100vh - 300px)); min-width: 1100px; background: transparent; }
.unlinked { height: 220px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
  background: var(--card-bg); border: 1px dashed var(--border); border-radius: 8px; }
.u-title { font-size: 20px; font-weight: 700; color: var(--text); }
.u-text { font-size: 15px; color: var(--text-2); }
</style>
