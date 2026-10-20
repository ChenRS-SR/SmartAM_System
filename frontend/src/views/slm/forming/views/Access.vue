<template>
  <div v-if="d" class="page analysis-page access-page">
    <div class="row-top">
      <Region kind="input" title="接入对象" class="r-input">
        <div class="fields">
          <div class="field"><span class="k">设备</span>
            <span v-if="embedded" class="field-value">{{ d.device.name }}</span>
            <select v-else class="sel" :value="state.device" :disabled="acq.running" @change="switchDevice($event.target.value)">
              <option v-for="x in devs" :key="x.id" :value="x.id">{{ x.name }}</option></select></div>
          <div class="field"><span class="k">成形任务</span>
            <span class="field-value">{{ d.task.name }}</span></div>
          <div class="field"><span class="k">接入方式</span>
            <span class="field-value">{{ modeLabel }}</span></div>
          <div class="field"><span class="k">当前层</span>
            <span v-if="replaySession" class="field-value">第 {{ d.layer }} 层</span>
            <select v-else class="sel" :value="d.layer" :disabled="acq.running" @change="load(+$event.target.value)">
              <option v-for="L in layers" :key="L" :value="L">第 {{ L }} 层</option></select></div>
        </div>
      </Region>
      <Region kind="param" title="采集通道" class="r-param">
        <div class="chs">
          <label v-for="c in d.channels" :key="c.name" class="ch" :title="`${c.spec} · ${c.rate}`">
            <input type="checkbox" :checked="visible(c.name)" @change="setChannels([c.name], $event.target.checked)" />{{ c.name }}
          </label>
        </div>
        <div class="channel-actions"><button class="btn" @click="setChannels(d.channels.map(c => c.name), true)">全部显示</button><button class="btn" @click="setChannels(d.channels.map(c => c.name), false)">全部隐藏</button><span>勾选显示，不改变原始采集</span></div>
      </Region>
      <Region kind="op" title="操作" class="r-op">
        <div v-if="replaySession" class="ops replay-ops">
          <span>{{ replaySession.playing ? '采集中' : '采集暂停' }}</span>
          <router-link :to="{ path: '/slm/settings', query: { device: replaySession.manifest.deviceId } }">系统设置</router-link>
        </div>
        <div v-else class="ops">
          <span class="state" :class="{ idle: !acq.running }"><i class="led" :class="acq.running ? 'run' : ''"></i>{{ acq.running ? '接入中' : '已连接' }}</span>
          <button class="btn primary" :disabled="acq.running || busy" @click="start">开始接入</button>
          <button class="btn" :disabled="!acq.running" @click="stop">暂停</button>
        </div>
      </Region>
    </div>

    <Region kind="vis" class="r-vis">
      <div class="grid" :class="{ 'grid--filtered': filtered }" :style="{ '--access-columns': topColumns, '--access-columns-narrow': Math.min(2, topColumns) }">
        <div v-if="visible('铺粉后图像')" class="card c-img">
          <div class="card-title">铺粉后图像<span class="tm"><template v-if="d.images.before.layer">第 {{ d.images.before.layer }} 层 · </template>{{ d.images.before.time }}</span></div>
          <img v-if="d.images.before.url" :src="img('before')" class="img" /><div v-else class="image-pending">图像尚未到达</div>
        </div>
        <div v-if="visible('熔化后图像')" class="card c-img">
          <div class="card-title">熔化后图像<span class="tm"><template v-if="d.images.after.layer">第 {{ d.images.after.layer }} 层 · </template>{{ d.images.after.time }}</span></div>
          <img v-if="d.images.after.url" :src="img('after')" class="img" /><div v-else class="image-pending">图像尚未到达</div>
        </div>
        <div v-if="visible('设备状态参数')" class="card c-state">
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
        <div v-if="visible('刮刀扭矩') || visible('加工平台扭矩')" class="card c-torque">
          <div class="card-title">{{ torqueTitle }}{{ replaySession ? ' · 连续采样' : '' }}</div>
          <div class="chart-window-note">最近 50 个采样点 · 时间轴随采样滚动</div>
          <EChart :option="torqueOption" class="chart" />
        </div>
        <div v-if="allHidden" class="card channels-empty">当前通道均已隐藏，可在上方勾选需要显示的内容。</div>
        <div class="card c-rec">
          <div class="card-title">逐层接入记录</div>
          <!-- 窄屏下仅记录表局部滚动，保留所有字段。 -->
          <div class="table-scroll" tabindex="0" role="region" aria-label="逐层接入记录表格">
          <table class="tbl">
            <thead><tr><th>层号</th><th>层开始时间</th><th>铺粉用时/s</th><th>单层用时/s</th><th>扭矩采样点</th><th>图像</th><th>状态</th></tr></thead>
            <tbody>
              <tr v-for="r in d.records.slice(0, 6)" :key="r.layer" :class="{ cur: r.layer === d.layer }" @click="!replaySession && !acq.running && load(r.layer)">
                <td>{{ r.layer }}</td><td>{{ r.start }}</td><td>{{ r.recoat == null ? '—' : r.recoat.toFixed(1) }}</td><td>{{ r.dur == null ? '—' : r.dur.toFixed(1) }}</td>
                <td>{{ r.torqueN ?? '—' }}</td><td>{{ r.images }}/2</td><td :class="r.complete ? 'ok' : r.state === '接入中' ? 'pending' : 'bad'">{{ r.state || (r.complete ? '完整' : '缺失') }}</td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>
      </div>
    </Region>
  </div>
  <div v-else class="loading">{{ replaySession ? '正在接入设备数据…' : '正在加载…' }}</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import Region from '../components/Region.vue'
import EChart from '../components/EChart.vue'
import { api, mediaUrl } from '../api.js'
import { devicesFor, selectDevice, state } from '../state.js'
import { useCall } from '../composables.js'
import { pal } from '../theme.js'
import { torqueWindow, replayTimeLabel } from '../rollingWindow.js'
import { useAccessChannels } from '../../../../stores/accessChannels'

const embedded = inject('formingEmbedded', false)
const replaySession = inject('formingReplay', null)
const { busy, call } = useCall()
const d = ref(null)
const channelStore = useAccessChannels()
const channelKey = computed(() => replaySession ? `replay:${replaySession.snapshot.caseId}` : state.device)
const visible = name => channelStore.forDevice(channelKey.value)[name] !== false
const setChannels = (names, shown) => channelStore.setVisible(channelKey.value, names, shown)
const filtered = computed(() => d.value.channels.some(c => !visible(c.name)))
const allHidden = computed(() => d.value.channels.every(c => !visible(c.name)))
const topColumns = computed(() => Math.max(1, ['铺粉后图像', '熔化后图像', '设备状态参数'].filter(visible).length))
const torqueTitle = computed(() => ['刮刀扭矩', '加工平台扭矩'].filter(visible).join('与'))
// 回放设备从工作区共享快照读取，跳转时清空旧结果，不再启动页面各自的计时器。
if (replaySession) watch(() => replaySession.snapshot?.access, value => { d.value = value || null }, { immediate: true })
const layers = ref([])
const acq = ref({ running: false })
const devs = computed(() => replaySession ? (d.value ? [d.value.device] : []) : devicesFor('access'))
const modeLabel = computed(() => { if (replaySession) return '在线接入'; const m = (state.status && state.status.modeLabel) || '在线'; return m === '在线' ? '在线接入' : m })
const img = (k) => mediaUrl(d.value.images[k].url, 1200)
let poll = null

async function load(layer) {
  if (replaySession) return
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
onMounted(() => { if (!replaySession) load() })
onBeforeUnmount(() => clearInterval(poll))

const envList = computed(() => {
  const e = d.value.env
  // 按设备原始通道命名，B44/B15 的气源压力不标成 B17 的氩气压力。
  const pressureLabel = replaySession?.manifest.gasPressureLabel || '氩气压力'
  const f = (v, n) => (v == null ? '—' : v.toFixed(n))
  return [
    { k: '成形室氧含量', v: f(e['成形室氧含量ppm'], 2), u: 'ppm' },
    { k: '成形室压力', v: f(e['成形室压力'], 2), u: 'mbar' },
    { k: '成形室温度', v: f(e['成形室温度'], 1), u: '℃' },
    { k: '加热板温度', v: f(e['加热板温度'], 1), u: '℃' },
    { k: pressureLabel, v: f(e[pressureLabel], 2), u: 'bar' },
    { k: '循环气体流量', v: f(e['循环气体实时流量'], 1), u: 'm³/h' },
    { k: '风机转速', v: f(e['风机转速'], 1), u: '%' },
    { k: '储粉桶物位', v: f(e['储粉桶物位计'], 0), u: 'mm' },
  ]
})
const torqueOption = computed(() => {
  const P = pal.value
  const axisFont = { fontSize: 16, color: P.axis }
  const t = d.value.torque
  const live = replaySession?.snapshot?.liveTorque
  const window = torqueWindow(live || t)
  const recoatStart = live ? live.recoatStart : 0
  const recoatEnd = live ? live.recoatEnd : t.recoatDur
  const sin = live ? (live.cursor >= recoatEnd ? { s: recoatEnd } : null) : t.events.find((e) => e.name === '熔化开始')
  const areaStart = Math.max(window.min, recoatStart)
  const areaEnd = Math.min(window.max, recoatEnd)
  return {
    animation: !!live && replaySession.playing, animationDuration: 0, animationDurationUpdate: 200, animationEasingUpdate: 'linear',
    grid: { left: 52, right: 18, top: 40, bottom: 46 },
    legend: { top: 0, right: 6, itemWidth: 26, itemHeight: 4, icon: 'rect', textStyle: { fontSize: 15, color: P.text } },
    xAxis: { type: 'value', name: live ? '采样时间' : '相对铺粉开始的时间/s', nameLocation: 'middle', nameGap: 26, nameTextStyle: axisFont,
      axisLabel: { ...axisFont, ...(live ? { formatter: replayTimeLabel } : {}) }, min: window.min, max: window.max, splitLine: { show: false } },
    yAxis: { type: 'value', name: '扭矩/%', nameTextStyle: axisFont, axisLabel: axisFont, splitLine: { lineStyle: { color: P.split } } },
    series: [
      { name: '刮刀扭矩', type: 'line', showSymbol: false, lineStyle: { width: 1.8, color: P.scraper }, itemStyle: { color: P.scraper },
        data: window.t.map((x, i) => [x, window.scraper[i]]),
        markArea: { silent: true, itemStyle: { color: P.recoatArea }, label: { fontSize: 15, color: P.scraper },
          data: areaEnd > areaStart ? [[{ name: '铺粉', xAxis: areaStart }, { xAxis: areaEnd }]] : [] },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: P.mark, type: 'dashed', width: 1.2 },
          label: { fontSize: 15, color: P.text, formatter: '熔化开始', position: 'end', distance: 2 }, data: sin && sin.s >= window.min && sin.s <= window.max ? [{ xAxis: sin.s }] : [] } },
      { name: '加工平台扭矩', type: 'line', showSymbol: false, lineStyle: { width: 1.8, color: P.platform }, itemStyle: { color: P.platform },
        data: window.t.map((x, i) => [x, window.platform[i]]) },
    ].filter(series => visible(series.name)),
  }
})
</script>

<style scoped>
.r-input { flex: 470 0 470px; }
.r-param { flex: 416 1 416px; min-width: 0; }
.r-op { flex: 280 0 280px; }
.r-vis { flex: 1; }
.fields { gap: 6px 14px; }
.chs { display: grid; grid-template-columns: repeat(3, auto); gap: 4px 8px; font-size: 15px; justify-content: start; }
.chs .ch { cursor: pointer; display: flex; align-items: center; gap: 6px; }
.ch input { accent-color: var(--nav-bg); width: 15px; height: 15px; flex: none; cursor: pointer; }
.channel-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 12px; }
.channel-actions .btn { padding: 4px 9px; font-size: 12px; }
.channel-actions span { color: var(--text-2); font-size: 12px; }
.field-value { font-size: 15px; overflow-wrap: anywhere; }
.channels-empty { color: var(--text-2); padding: 24px; }
.state { font-size: 17px; white-space: nowrap; display: flex; align-items: center; gap: 6px; color: var(--ok); font-weight: 700; }
.state .led { width: 12px; height: 12px; }
.grid { height: 100%; display: grid; grid-template-columns: minmax(0, 300fr) minmax(0, 300fr) minmax(0, 540fr); grid-template-rows: minmax(0, 282fr) minmax(0, 278fr); gap: 12px; }
.img { width: 100%; flex: 1; min-height: 0; object-fit: contain; background: var(--img-bg); border-radius: 4px; }
.progress { margin-bottom: 8px; }
.pg-row { display: flex; justify-content: space-between; font-size: 16px; color: var(--text-2); }
.pg-row b { color: var(--text); }
.bar { height: 10px; background: var(--track-2); border-radius: 5px; margin-top: 4px; overflow: hidden; }
.fill { height: 100%; background: var(--nav-bg); transition: width .4s; }
.env { display: grid; grid-template-columns: 1fr 1fr; gap: 5px 18px; }
.env-item { display: flex; align-items: baseline; gap: 6px; font-size: 16px; }
.ek { color: var(--text-2); flex: 1; white-space: nowrap; }
.env-item b { font-size: 17px; }
.eu { color: var(--text-2); font-size: 14px; width: 40px; }
.alarm { margin-top: auto; font-size: 15px; background: var(--alarm-bg); border: 1px solid var(--alarm-border); border-radius: 5px; padding: 4px 8px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.al-tag { color: var(--alarm-ink); font-weight: 700; margin-right: 8px; }
.c-torque { grid-column: 1 / 3; }
.tbl { font-size: 15.5px; }
.tbl th, .tbl td { padding: 3px 6px; }
.ok { color: var(--ok); }
.bad { color: var(--danger-ink); }
.pending { color: var(--text-2); }
</style>
