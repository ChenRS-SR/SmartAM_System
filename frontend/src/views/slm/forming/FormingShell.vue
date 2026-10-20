<template>
  <div class="forming-root shell">
    <div v-if="msg" class="err" @click="msg = ''">{{ msg }}</div>
    <router-view v-if="ready" />
    <div v-else class="loading">{{ loadErr || '正在连接…' }}</div>
  </div>
</template>

<script setup>
// 成形监测各页面的外层：加载设备清单，提供统一的出错提示。集成到 SmartAM 时作为父路由组件。
import { onMounted, provide, ref } from 'vue'
import { loadDevices, loadStatus } from './state.js'
import './forming.css'

const ready = ref(false)
const loadErr = ref('')
const msg = ref('')
let timer = null
provide('formingError', (e) => {
  msg.value = e && e.message ? e.message : String(e)
  clearTimeout(timer)
  timer = setTimeout(() => { msg.value = '' }, 4000)
})
onMounted(async () => {
  try {
    await Promise.all([loadDevices(), loadStatus()])
    ready.value = true
  } catch (e) {
    loadErr.value = `无法连接成形监测服务：${e.message}`
  }
})
</script>

<style scoped>
.shell { position: relative; min-height: 720px; min-width: 0; width: 100%; background: var(--page-bg); }
</style>
