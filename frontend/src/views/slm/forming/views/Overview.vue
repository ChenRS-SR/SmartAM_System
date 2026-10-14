<template>
  <div v-if="d" class="page">
    <div class="crumb">
      <span class="switch">切换设备
        <select class="sel" :value="state.device" @change="switchTo($event.target.value)">
          <option v-for="x in state.devices" :key="x.id" :value="x.id">{{ x.name }}</option>
        </select></span>
    </div>
    <div class="top">
      <div class="photo">
        <img v-if="v.photo" :src="photoUrl" />
        <div v-else class="no-photo">{{ v.name }}</div>
        <span class="tag state" :class="{ idle: !online && !running }"><i class="led" :class="running ? 'run' : online ? 'on' : 'idle'"></i>{{ stateText }}</span>
      </div>
      <div class="info">
        <div class="name">{{ v.name }}</div>
        <div class="kind">{{ v.kind }}　{{ v.laser }}</div>
        <div class="sec">接入数据</div>
        <div class="groups">
          <div v-for="g in v.modalGroups" :key="g.g" class="grp">
            <span class="g-name" :class="{ main: g.g.startsWith('主'), st: g.g.startsWith('设备') }">{{ g.g }}</span>
            <span v-for="m in g.items" :key="m" class="mod"><i class="ok">●</i>{{ m }}</span>
          </div>
        </div>
        <div class="sec">最新结果<span v-if="d.latest" class="sec-sub">第 {{ d.latest.layer }} 层</span></div>
        <div v-if="d.latest" class="latest">
          <span class="res" :class="resCls(d.latest.label)">{{ d.latest.label }}</span><span class="detail">{{ d.latest.detail }}</span>
        </div>
        <div class="btns">
          <button v-for="(b, i) in buttons" :key="b.key" class="btn" :class="{ primary: i === 0 }" :disabled="!v.modules.includes(b.key)"
            @click="go(b.key)">{{ b.name }}</button>
        </div>
      </div>
    </div>
    <div class="card ev-card">
      <div class="card-title">最近事件</div>
      <table class="tbl ev">
        <thead><tr><th>时间</th><th>类型</th><th>内容</th></tr></thead>
        <tbody>
          <tr v-for="(e, i) in d.events.slice(0, 4)" :key="i" @click="e.layer && openEvent(e)"><td>{{ e.time }}</td>
            <td><span class="etag" :class="'e-' + e.type">{{ e.type }}</span></td><td>{{ e.text }}</td></tr>
        </tbody>
      </table>
      <div v-if="!d.events.length" class="empty">暂无事件</div>
    </div>
  </div>
  <div v-else class="loading">正在加载…</div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, mediaUrl } from '../api.js'
import { selectDevice, state } from '../state.js'
import { useCall } from '../composables.js'

const props = defineProps({ fleetPath: String, base: { type: String, default: '' } })
const router = useRouter()
const { call } = useCall()
const d = ref(null)
const v = computed(() => d.value.device)
const photoUrl = computed(() => mediaUrl(v.value.photo))
const running = computed(() => d.value.acquisition && d.value.acquisition.running)
// 运行状态文字随后端 modeLabel：显示为“在线”时设备显示在线，否则如实显示待机/结果回放
const online = computed(() => !!state.status && state.status.modeLabel === '在线')
const stateText = computed(() => (running.value ? '接入中' : online.value ? '在线' : d.value.acquisition ? '待机' : '结果回放'))
const buttons = [{ key: 'access', name: '数据接入' }, { key: 'recognition', name: '异常识别' }, { key: 'trace', name: '异常溯源' }]
const resCls = (l) => ({ '异常': 'r-dev', '由设备因素诱发': 'r-dev', '由工艺因素诱发': 'r-proc', '由二者共同诱发': 'r-both' }[l] || 'r-nor')

async function load() {
  const r = await call(() => api.overview(state.device))
  if (r) d.value = r
}
function switchTo(id) { selectDevice(id); d.value = null; load() }
function go(key) { router.push(`${props.base}/${key}`) }
function openEvent(e) {
  state.layer[state.device] = e.layer
  go(e.type === '异常溯源' ? 'trace' : e.type === '异常识别' ? 'recognition' : 'access')
}
onMounted(load)
</script>

<style scoped>
.page { gap: 12px; }
.crumb { font-size: 18px; display: flex; align-items: center; gap: 8px; flex: none; }
.link { color: var(--dev); text-decoration: none; }
.sep { color: var(--text-2); }
.switch { margin-left: auto; color: var(--text-2); font-size: 16px; display: flex; align-items: center; gap: 8px; }
.top { display: flex; gap: 16px; height: 400px; flex: none; }
.photo { position: relative; flex: 0 0 520px; border-radius: 10px; overflow: hidden; border: 1px solid var(--border); background: #e9edf2; }
.photo img { width: 100%; height: 100%; object-fit: cover; object-position: center 45%; display: block; }
.no-photo { height: 100%; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 700; color: #9aa5b1; }
.photo .state { position: absolute; top: 12px; right: 12px; }
.tag.state { font-size: 15px; background: rgba(231,245,236,.95); color: #2f7d4f; display: inline-flex; align-items: center; gap: 6px; font-weight: 700; padding: 1px 10px; }
.tag.state.idle { background: rgba(241,243,246,.95); color: #52606d; }
.info { flex: 1; background: #fff; border: 1px solid var(--border); border-radius: 10px; padding: 18px 24px; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.name { font-size: 32px; font-weight: 800; color: var(--nav-bg); }
.kind { font-size: 17px; color: var(--text-2); margin-top: -4px; }
.sec { font-size: 16px; color: var(--text-2); margin-top: 6px; }
.sec-sub { margin-left: 10px; font-size: 15px; }
.groups { display: flex; flex-direction: column; gap: 8px; }
.grp { display: flex; align-items: center; gap: 14px; font-size: 17px; }
.g-name { flex: 0 0 150px; font-size: 15px; font-weight: 700; color: #fff; background: #5d7290; border-radius: 5px; padding: 2px 10px; text-align: center; }
.g-name.main { background: var(--nav-bg); }
.g-name.st { background: #e8ecf1; color: var(--text-2); }
.mod { font-size: 17px; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.ok { color: #2fa35a; font-style: normal; font-size: 12px; }
.latest { display: flex; align-items: center; gap: 12px; }
.res { color: #fff; font-weight: 700; font-size: 19px; border-radius: 6px; padding: 2px 14px; white-space: nowrap; }
.r-dev { background: var(--warn); }
.r-proc { background: var(--warn); }
.r-both { background: var(--warn); }
.r-nor { background: var(--ok); }
.detail { font-size: 16px; color: var(--text-2); }
.btns { margin-top: auto; display: flex; gap: 10px; }
.btn { padding: 6px 16px; font-size: 17px; }
.ev-card { flex: 1; border-radius: 10px; padding: 12px 18px; border-color: var(--border); }
.ev-card .card-title { font-size: 20px; }
.tbl.ev { font-size: 17px; table-layout: fixed; }
.tbl.ev th { padding: 5px 8px; }
.tbl.ev th:nth-child(1) { width: 150px; } .tbl.ev th:nth-child(2) { width: 130px; }
.tbl.ev td { padding: 7px 8px; overflow: hidden; text-overflow: ellipsis; }
.etag { font-size: 15px; border-radius: 10px; padding: 1px 10px; color: #fff; }
.e-设备报警 { background: #c27c0e; }
.e-异常识别 { background: var(--warn); }
.e-异常溯源 { background: var(--warn); }
</style>
