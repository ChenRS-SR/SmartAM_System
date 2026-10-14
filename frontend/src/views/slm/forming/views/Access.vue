<template>
  <div v-if="d" class="page">
    <div class="row-top">
      <Region kind="input" title="接入对象" class="r-input">
        <div class="fields">
          <div class="field"><span class="k">设备</span>
            <select class="sel" :value="state.device" :disabled="acq.running" @change="switchDevice($event.target.value)">
              <option v-for="x in devs" :key="x.id" :value="x.id">{{ x.name }}</option></select></div>
          <div class="field"><span class="k">成形任务</span>
            <select class="sel" disabled><option>{{ d.task.name }}</option></select></div>
          <div class="field"><span class="k">接入方式</span>
            <select class="sel" disabled><option>{{ modeLabel }}</option></select></div>
          <div class="field"><span class="k">当前层</span>
            <select class="sel" :value="d.layer" :disabled="acq.running" @change="load(+$event.target.value)">
              <option v-for="L in layers" :key="L" :value="L">第 {{ L }} 层</option></select></div>
        </div>
      </Region>
      <Region kind="param" title="采集通道" class="r-param">
        <div class="chs">
          <span v-for="c in d.channels" :key="c.name" class="ch"><i class="ck">✓</i>{{ c.name }}</span>
        </div>
      </Region>
      <Region kind="op" title="操作" class="r-op">
        <div class="ops">
          <span class="state" :class="{ idle: !acq.running }"><i class="led" :class="acq.running ? 'run' : ''"></i>{{ acq.running ? '接入中' : '已连接' }}</span>
          <button class="btn primary" :disabled="acq.running || busy" @click="start">开始接入</button>
          <button class="btn" :disabled="!acq.running" @click="stop">暂停</button>
        </div>
      </Region>
    </div>

    <Region kind="vis" class="r-vis">
      <div class="grid">
        <div class="card c-img">
          <div class="card-title">铺粉后图像<span class="tm">{{ d.images.before.time }}</span></div>
          <img :src="img('before')" class="img" />
        </div>
        <div class="card c-img">
          <div class="card-title">熔化后图像<span class="tm">{{ d.images.after.time }}</span></div>
          <img :src="img('after')" class="img" />
        </div>
        <div class="card c-state">
          <div class="card-title">设备状态<span class="tm">{{ d.device.name }}</span></div>
          <div class="progress">
            <div class="pg-row"><span>成形进度</span><b>第 {{ d.progress.layer }} 层 / 共 {{ d.progress.total }} 层</b></div>
            <div class="bar"><div class="fill" :style="{ width: (d.progress.layer / d.progress.total * 100) + '%' }"></div></div>
          </div>
          <div class="env">
            <div v-for="e in envList" :key="e.k" class="env-item"><span class="ek">{{ e.k }}</span><b>{{ e.v }}</b><span class="eu">{{ e.u }}</span></div>
          </div>
          <div class="alarm" v-if="d.alarms.length"><span class="al-tag">最近报警</span>{{ d.alarms[0].time.slice(5, 16) }}　{{ d.alarms[0].text }}</div>
        </div>
        <div class="card c-torque">
          <div class="card-title">当前层刮刀扭矩与加工平台扭矩</div>
          <EChart :option="torqueOption" class="chart" />
        </div>
        <div class="card c-rec">
          <div class="card-title">逐层接入记录</div>
          <table class="tbl">
            <thead><tr><th>层号</th><th>层开始时间</th><th>铺粉用时/s</th><th>单层用时/s</th><th>扭矩采样点</th><th>图像</th><th>状态</th></tr></thead>
            <tbody>
              <tr v-for="r in d.records.slice(0, 6)" :key="r.layer" :class="{ cur: r.layer === d.layer }" @click="!acq.running && load(r.layer)">
                <td>{{ r.layer }}</td><td>{{ r.start }}</td><td>{{ r.recoat.toFixed(1) }}</td><td>{{ r.dur == null ? '—' : r.dur.toFixed(1) }}</td>
                <td>{{ r.torqueN }}</td><td>{{ r.images }}/2</td><td :class="r.complete ? 'ok' : 'bad'">{{ r.complete ? '完整' : '缺失' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </Region>
  </div>
  <div v-else class="loading">正在加载…</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import Region from '../components/Region.vue'
import EChart from '../components/EChart.vue'
import { api, mediaUrl } from '../api.js'
import { devicesFor, selectDevice, state } from '../state.js'
import { useCall } from '../composables.js'

const { busy, call } = useCall()
const d = ref(null)
const layers = ref([])
const acq = ref({ running: false })
const devs = computed(() => devicesFor('access'))
const modeLabel = computed(() => { const m = (state.status && state.status.modeLabel) || '在线'; return m === '在线' ? '在线接入' : m })
const img = (k) => mediaUrl(d.value.images[k].url, 1200)
let poll = null

async function load(layer) {
  const r = await call(() => api.access(state.device, layer ?? state.layer[state.device]))
  if (!r) return
  d.value = r
  acq.value = r.acquisition
  state.layer[state.device] = r.layer
  if (!layers.value.length) layers.value = (await call(() => api.layers(state.device, r.task.id))) || [r.layer]
  if (acq.value.running) watchAcq()
}
// 接入过程中每秒查询一次接入状态，层号变化时取新层数据（实时接入时同样适用）
function watchAcq() {
  clearInterval(poll)
  poll = setInterval(async () => {
    const s = await call(() => api.acquisition(state.device))
    if (!s) return
    if (s.layer !== d.value.layer) await load(s.layer)
    acq.value = s
    if (!s.running) clearInterval(poll)
  }, 1000)
}
async function start() {
  const s = await call(() => api.acqStart(state.device, { from_layer: d.value.layer }))
  if (s) { acq.value = s; watchAcq() }
}
async function stop() {
  clearInterval(poll)
  const s = await call(() => api.acqStop(state.device))
  if (s) { acq.value = s; if (s.layer !== d.value.layer) load(s.layer) }
}
function switchDevice(id) { selectDevice(id); d.value = null; layers.value = []; load() }
onMounted(() => load())
onBeforeUnmount(() => clearInterval(poll))

const envList = computed(() => {
  const e = d.value.env
  const f = (v, n) => (v == null ? '—' : v.toFixed(n))
  return [
    { k: '成形室氧含量', v: f(e['成形室氧含量ppm'], 2), u: 'ppm' },
    { k: '成形室压力', v: f(e['成形室压力'], 2), u: 'mbar' },
    { k: '成形室温度', v: f(e['成形室温度'], 1), u: '℃' },
    { k: '加热板温度', v: f(e['加热板温度'], 1), u: '℃' },
    { k: '氩气压力', v: f(e['氩气压力'], 2), u: 'bar' },
    { k: '循环气体流量', v: f(e['循环气体实时流量'], 1), u: 'm³/h' },
    { k: '风机转速', v: f(e['风机转速'], 1), u: '%' },
    { k: '储粉桶物位', v: f(e['储粉桶物位计'], 0), u: 'mm' },
  ]
})
const axisFont = { fontSize: 16, color: '#52606d' }
const torqueOption = computed(() => {
  const t = d.value.torque
  const sin = t.events.find((e) => e.name === '熔化开始')
  return {
    animation: false,
    grid: { left: 52, right: 18, top: 40, bottom: 46 },
    legend: { top: 0, right: 6, itemWidth: 26, itemHeight: 4, icon: 'rect', textStyle: { fontSize: 15 } },
    xAxis: { type: 'value', name: '相对铺粉开始的时间/s', nameLocation: 'middle', nameGap: 26, nameTextStyle: axisFont,
      axisLabel: axisFont, min: Math.floor(t.t[0]), max: Math.ceil(t.t[t.t.length - 1]), splitLine: { show: false } },
    yAxis: { type: 'value', name: '扭矩/%', nameTextStyle: axisFont, axisLabel: axisFont, splitLine: { lineStyle: { color: '#eef0f3' } } },
    series: [
      { name: '刮刀扭矩', type: 'line', showSymbol: false, lineStyle: { width: 1.8, color: '#3b6ba5' }, itemStyle: { color: '#3b6ba5' },
        data: t.t.map((x, i) => [x, t.scraper[i]]),
        markArea: { silent: true, itemStyle: { color: 'rgba(59,107,165,0.08)' }, label: { fontSize: 15, color: '#3b6ba5' },
          data: [[{ name: '铺粉', xAxis: 0 }, { xAxis: t.recoatDur }]] },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: '#555', type: 'dashed', width: 1.2 },
          label: { fontSize: 15, formatter: '熔化开始', position: 'end', distance: 2 }, data: sin ? [{ xAxis: sin.s }] : [] } },
      { name: '加工平台扭矩', type: 'line', showSymbol: false, lineStyle: { width: 1.8, color: '#7b8794' }, itemStyle: { color: '#7b8794' },
        data: t.t.map((x, i) => [x, t.platform[i]]) },
    ],
  }
})
</script>

<style scoped>
.r-input { flex: 0 0 470px; }
.r-param { flex: 1; min-width: 0; }
.r-op { flex: 0 0 280px; }
.r-vis { flex: 1; }
.fields { gap: 6px 14px; }
.chs { display: grid; grid-template-columns: repeat(3, auto); gap: 4px 8px; font-size: 15px; justify-content: start; }
.chs .ch { cursor: default; }
.state { font-size: 17px; white-space: nowrap; display: flex; align-items: center; gap: 6px; color: #2f7d4f; font-weight: 700; }
.state .led { width: 12px; height: 12px; }
.grid { height: 100%; display: grid; grid-template-columns: 300px 300px 1fr; grid-template-rows: 282px 1fr; gap: 12px; }
.img { width: 100%; flex: 1; min-height: 0; object-fit: contain; background: #f3f5f8; border-radius: 4px; }
.progress { margin-bottom: 8px; }
.pg-row { display: flex; justify-content: space-between; font-size: 16px; color: var(--text-2); }
.pg-row b { color: var(--text); }
.bar { height: 10px; background: #e6eaf0; border-radius: 5px; margin-top: 4px; overflow: hidden; }
.fill { height: 100%; background: var(--nav-bg); transition: width .4s; }
.env { display: grid; grid-template-columns: 1fr 1fr; gap: 5px 18px; }
.env-item { display: flex; align-items: baseline; gap: 6px; font-size: 16px; }
.ek { color: var(--text-2); flex: 1; white-space: nowrap; }
.env-item b { font-size: 17px; }
.eu { color: var(--text-2); font-size: 14px; width: 40px; }
.alarm { margin-top: auto; font-size: 15px; background: #fdf3e7; border: 1px solid #f1d3a8; border-radius: 5px; padding: 4px 8px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.al-tag { color: #b26a00; font-weight: 700; margin-right: 8px; }
.c-torque { grid-column: 1 / 3; }
.tbl { font-size: 15.5px; }
.tbl th, .tbl td { padding: 3px 6px; }
.ok { color: #2f7d4f; }
.bad { color: #a12622; }
</style>
