<template>
  <div v-if="d" class="page analysis-page trace-page">
    <div class="row-top">
      <Region kind="input" title="监测数据" class="r-input">
        <div class="fields">
          <div class="field"><span class="k">设备</span>
            <select class="sel" :value="replaySession ? d.device.id : state.device" :disabled="embedded || stepper.running.value" @change="switchDevice($event.target.value)">
              <option v-for="x in devs" :key="x.id" :value="x.id">{{ x.name }}</option></select></div>
          <div class="field"><span class="k">成形任务</span><select class="sel" disabled><option>{{ d.task.name }}</option></select></div>
          <div class="field"><span class="k">成形层</span>
            <select class="sel" :value="d.layer" :disabled="!!replaySession || stepper.running.value || layers.length < 2" @change="run(+$event.target.value)">
              <option v-if="replaySession" :value="d.layer">第 {{ d.layer }} 层</option>
              <option v-for="L in layers" :key="L" :value="L">第 {{ L }} 层</option></select></div>
          <div class="field"><span class="k">参照层</span><select class="sel" disabled><option>第 {{ d.refLayer }} 层</option></select></div>
        </div>
      </Region>
      <Region kind="param" title="溯源参数" class="r-param">
        <div class="fields one">
          <div class="field"><span class="k">零件区边缘邻域</span>
            <input class="inp" type="number" min="0" max="40" step="1" :value="d.params.bandPx" :disabled="replay || d.mode === 'dual'" @change="setBand($event.target.value)" />
            <span class="k">像素</span></div>
          <div class="field"><span class="k">参照层选取</span>
            <select class="sel" :value="d.mode === 'dual' ? d.refMode : state.trace.refMode" :disabled="replay || d.mode === 'dual'" @change="setRefMode($event.target.value)">
              <option value="prev_normal">前序最近正常层</option><option value="manual">指定层</option></select>
            <input v-if="d.mode !== 'dual' && state.trace.refMode === 'manual'" class="inp ref-inp" type="number" :value="state.trace.refLayer ?? d.refLayer"
              @change="setRefLayer($event.target.value)" /></div>
        </div>
      </Region>
      <Region kind="op" title="操作" class="r-op">
        <div v-if="replaySession" class="ops replay-ops">
          <span>{{ replaySession.playing ? '采集中' : '采集暂停' }}</span><span>随采集数据更新</span>
        </div>
        <div v-else class="ops">
          <button class="btn primary" :disabled="busy || stepper.running.value" @click="run(d.layer)">单层溯源</button>
          <button class="btn" :disabled="replay" @click="toggleStep">{{ stepper.running.value ? '停止溯源' : '逐层溯源' }}</button>
        </div>
      </Region>
    </div>

    <Region kind="vis" class="r-vis">
      <div class="vis-grid">
        <div class="card c-img">
          <div class="card-title">铺粉后图像与因果因子</div>
          <svg class="overlay" :viewBox="viewBox" preserveAspectRatio="xMidYMid meet">
            <image :href="imgUrl" x="0" y="0" :width="d.image.width" :height="d.image.height" />
            <polygon v-for="(c, i) in band" :key="'b' + i" :points="c" class="band" />
            <polygon v-for="(c, i) in part" :key="'p' + i" :points="c" class="part" />
          </svg>
          <div class="img-legend">
            <span><i class="sw sw-part"></i>零件区</span>
            <span><i class="sw sw-band"></i>边缘邻域</span>
            <span><i class="sw sw-powder"></i>粉床区</span>
          </div>
        </div>

        <div class="card c-contrib">
          <div class="card-title">因果因子贡献
            <span class="lg"><i class="lim-sw"></i>上限水平 {{ upperText }}</span></div>
          <div class="grp" v-for="g in groups" :key="g.key">
            <div class="g-head"><span class="g-name">{{ g.name }}上的贡献</span><span class="g-sum">总改变量 <b>{{ g.total.toFixed(2) }}</b></span></div>
            <div class="zrow" v-for="z in g.zones" :key="z.key">
              <span class="z-name">{{ z.name }}</span>
              <div class="z-track">
                <div class="z-fill" :class="['f-' + z.key, { dim: !z.over }]" :style="{ width: z.w + '%' }"></div>
                <i class="z-lim" :style="{ left: g.wTh + '%' }"></i>
              </div>
              <b class="z-val" :class="{ over: z.over }">{{ z.v.toFixed(2) }}</b>
              <span class="z-tag" :class="z.over ? 'on' : 'off'">{{ z.over ? '超过' : '未超过' }}</span>
            </div>
          </div>
          <div v-if="replaySession && d.mode !== 'dual'" class="replay-note">工艺侧分析暂无数据，当前显示设备侧分析。</div>
          <div class="hint">各侧分别与对应上限比较；贡献超限为支撑证据，同侧异常概率达到 50% 时确认归因。证据不一致时保留待复核状态。总改变量为两区贡献之和。</div>
        </div>

        <div class="card c-res" :class="{ dense: d.mode === 'dual' }">
          <div class="card-title">溯源结论</div>
          <div class="verdict" :class="verdictCls">{{ d.conclusion }}</div>
          <div class="prob" v-for="p in probs" :key="p.name">
            <div class="p-head"><span>{{ p.name }}</span><b>{{ fmtPct(p.v) }}</b></div>
            <div class="track"><div class="fill" :style="{ width: p.v * 100 + '%', background: p.color }"></div></div>
          </div>
          <div v-if="d.mode === 'dual'" class="kv ev"><span class="k">支撑区域</span>
            <div class="ev-lines"><div>工艺：<b>{{ zoneText(d.factors.proc.support) }}</b></div><div>设备：<b>{{ zoneText(d.factors.dev.support) }}</b></div></div></div>
          <div v-else class="kv"><span class="k">支撑区域</span><b class="t-zone">{{ zoneText(d.support) }}</b></div>
          <div class="act" :class="{ multi: d.actions.length > 1 }">
            <div class="act-k">处置对象</div>
            <div class="act-row">
              <div v-for="a in d.actions" :key="a" class="act-box" :class="{ two: d.actions.length > 1, proc: a.includes('工艺') }">
                <span class="act-t">{{ a }}</span><span v-if="d.actions.length === 1" class="act-st">待处理</span></div>
              <div v-if="!d.actions.length" class="act-box none"><span class="act-t">无需处置</span></div>
            </div>
          </div>
        </div>

        <div class="card c-curve">
          <div class="card-title">逐层工艺侧与设备侧因果贡献</div>
          <div class="curve-note">最近 {{ TRACE_WINDOW_SIZE }} 层（{{ curveStart }}–{{ d.layer }} 层） · 各侧取零件区与粉床区贡献的较大值。<template v-if="!hasProcessCurve">工艺侧暂无有效逐层结果，暂不绘制曲线。</template></div>
          <EChart :option="curveOption" class="chart" />
        </div>

        <div class="card c-rec">
          <div class="card-title">逐层溯源记录</div>
          <!-- 窄屏下仅记录表局部滚动，保留所有字段。 -->
          <div class="table-scroll" tabindex="0" role="region" aria-label="逐层溯源记录表格">
          <table class="tbl">
            <thead v-if="d.mode === 'dual'"><tr><th>层号</th><th>工艺较大区</th><th>设备较大区</th><th>结论</th></tr></thead>
            <thead v-else><tr><th>层号</th><th>零件区</th><th>粉床区</th><th>总改变量</th><th>结论</th></tr></thead>
            <tbody v-if="d.mode === 'dual'">
              <tr v-for="r in d.records" :key="r.layer" :class="{ cur: r.layer === d.layer }">
                <td>{{ r.layer }}</td><td>{{ mx(r.proc_part, r.proc_powder).toFixed(2) }}</td><td>{{ mx(r.dev_part, r.dev_powder).toFixed(2) }}</td>
                <td><span class="tag" :class="tagCls(r.conclusion)" :title="r.conclusion">{{ tagTxt(r.conclusion) }}</span></td>
              </tr>
            </tbody>
            <tbody v-else>
              <tr v-for="r in d.records" :key="r.layer" :class="{ cur: r.layer === d.layer }" @click="!replaySession && !stepper.running.value && run(r.layer)">
                <td>{{ r.layer }}</td><td :class="{ over: r.part >= upDev }">{{ r.part.toFixed(2) }}</td>
                <td :class="{ over: r.powder >= upDev }">{{ r.powder.toFixed(2) }}</td><td class="muted">{{ r.total.toFixed(2) }}</td>
                <td><span class="tag" :class="tagCls(r.conclusion)" :title="r.conclusion">{{ tagTxt(r.conclusion) }}</span></td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>
      </div>
    </Region>
  </div>
  <div v-else class="loading">{{ replaySession ? '当前时刻尚无可用溯源结果，等待完整层图像与正常参照层。' : '正在溯源…' }}</div>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from 'vue'
import Region from '../components/Region.vue'
import EChart from '../components/EChart.vue'
import { api, mediaUrl } from '../api.js'
import { devicesFor, selectDevice, state } from '../state.js'
import { fmtPct, useCall, useStepper } from '../composables.js'
import { pal } from '../theme.js'
import { factorCurveRows } from '../traceCurve.js'
import { layerWindow, TRACE_WINDOW_SIZE } from '../rollingWindow.js'

const embedded = inject('formingEmbedded', false)
const replaySession = inject('formingReplay', null)
const { busy, call, report } = useCall()
const stepper = useStepper(1500)
const d = ref(null)
// 回放设备从工作区共享快照读取，跳转时清空旧结果，不再启动页面各自的计时器。
if (replaySession) watch(() => replaySession.snapshot?.trace, value => { d.value = value || null }, { immediate: true })
const layers = ref([])
const devs = computed(() => replaySession ? (d.value ? [d.value.device] : []) : devicesFor('trace'))
const replay = computed(() => !!d.value.replay)

async function run(layer) {
  if (replaySession) return
  const t = state.trace
  const r = await call(() => api.trace({ device_id: state.device, layer: layer ?? state.layer[state.device] ?? null,
    band_px: t.bandPx, ref_mode: t.refMode, ref_layer: t.refMode === 'manual' ? t.refLayer : null, n_records: 5, n_curve: TRACE_WINDOW_SIZE }))
  if (!r) return false
  d.value = r
  state.layer[state.device] = r.layer
  if (!layers.value.length) layers.value = (await call(() => api.layers(state.device, r.task.id))) || [r.layer]
  return true
}
function setBand(v) {
  const n = Number(v)
  if (!Number.isInteger(n) || n < 0 || n > 40) { report(new Error('边缘邻域应为 0～40 的整数')); return }
  state.trace.bandPx = n
  run(d.value.layer)
}
function setRefMode(m) {
  state.trace.refMode = m
  if (m === 'manual') state.trace.refLayer = d.value.refLayer
  else run(d.value.layer)
}
function setRefLayer(v) { state.trace.refLayer = Number(v); run(d.value.layer) }
function toggleStep() {
  if (stepper.running.value) stepper.stop()
  else stepper.start(layers.value, d.value.layer, (L) => run(L))
}
function switchDevice(id) { selectDevice(id); d.value = null; layers.value = []; state.trace.bandPx = null; run() }
onMounted(() => { if (!replaySession) run() })

const imgUrl = computed(() => mediaUrl(d.value.image.url, 1200))
const viewBox = computed(() => {
  const { width: W, height: H, content: c } = d.value.image
  return `${c[0] * W} ${c[1] * H} ${c[2] * W} ${c[3] * H}`
})
const toPts = (cs, w, h) => cs.map((c) => c.map(([x, y]) => `${x * w},${y * h}`).join(' '))
const part = computed(() => toPts(d.value.partContours, d.value.image.width, d.value.image.height))
const band = computed(() => toPts(d.value.bandContours, d.value.image.width, d.value.image.height))
const groups = computed(() => {
  const f = d.value.factors
  const g = [{ key: 'dev', ...f.dev }, ...(f.proc ? [{ key: 'proc', ...f.proc }] : [])]
  const m = Math.max(...g.flatMap((q) => [...q.zones.map((z) => z.v), q.upper])) * 1.08
  const w = (v) => Math.max(v, 0) / m * 100
  return g.map((q) => ({ ...q, wTh: w(q.upper), zones: q.zones.map((z) => ({ ...z, w: w(z.v) })) }))
})
const upDev = computed(() => d.value.factors.dev.upper)
const upperText = computed(() => {
  const f = d.value.factors
  if (!f.proc) return f.dev.upper.toFixed(2)
  return f.dev.upper === f.proc.upper ? f.dev.upper.toFixed(2) : `工艺 ${f.proc.upper.toFixed(2)}　设备 ${f.dev.upper.toFixed(2)}`
})
const zoneText = (z) => (z && z.length ? z.join('、') : '无')
const mx = (a, b) => Math.max(a, b)
const probs = computed(() => [
  ...(d.value.factors.proc ? [{ name: '工艺诱发异常概率', v: d.value.factors.proc.prob, color: 'var(--proc)' }] : []),
  { name: '设备诱发异常概率', v: d.value.factors.dev.prob, color: 'var(--dev)' },
])
const verdictCls = computed(() => ({ '由二者共同诱发': 'v-both', '由工艺因素诱发': 'v-proc', '由设备因素诱发': 'v-dev', '已识别异常，归因待确认': 'v-pending', '贡献超限，待复核': 'v-pending' }[d.value.conclusion] || 'v-nor'))
const tagCls = (r) => ({ '由二者共同诱发': 't-both', '由工艺因素诱发': 't-proc', '由设备因素诱发': 't-dev', '已识别异常，归因待确认': 't-pending', '贡献超限，待复核': 't-pending' }[r] || 't-nor')
const tagTxt = (r) => ({ '由二者共同诱发': '二者共同', '由工艺因素诱发': '工艺因素', '由设备因素诱发': '设备因素', '已识别异常，归因待确认': '异常·待归因', '贡献超限，待复核': '超限·待复核' }[r] || r)
const visibleFactors = computed(() => layerWindow(factorCurveRows(d.value), d.value.layer))
const curveStart = computed(() => Math.max(1, d.value.layer - TRACE_WINDOW_SIZE + 1))
const hasProcessCurve = computed(() => visibleFactors.value.some(r => r.proc !== null))

const curveOption = computed(() => {
  const P = pal.value
  const C = P
  const axisFont = { fontSize: 16, color: P.axis }
  const cv = d.value.curve
  const lo = curveStart.value
  const hi = d.value.layer
  const cur = { silent: true, symbol: 'none', data: [{ xAxis: d.value.layer, lineStyle: { color: P.ink, width: 1.4 },
    label: { show: true, color: P.text, formatter: '当前层', fontSize: 15, position: 'end', distance: 2 } }] }
  const lim = (name, v, color, type) => ({ name, type: 'line', symbol: 'none', z: 5, lineStyle: { width: 1.8, color, type }, itemStyle: { color },
    data: [[lo, v], [hi, v]] })
  const factors = visibleFactors.value
  const series = [
        { name: '工艺侧', type: 'line', showSymbol: false, lineStyle: { width: 1.6, color: C.proc }, itemStyle: { color: C.proc },
          data: factors.map((x) => [x.layer, x.proc]), connectNulls: false },
        { name: '设备侧', type: 'line', showSymbol: false, lineStyle: { width: 1.6, color: C.dev }, itemStyle: { color: C.dev },
          data: factors.map((x) => [x.layer, x.dev]), markLine: cur },
        ...(hasProcessCurve.value ? [lim('工艺上限水平', cv.upper.proc, P.upperProc, 'dashed')] : []),
        lim('设备上限水平', cv.upper.dev, P.upperDev, 'dotted'),
      ]
  return {
    animation: false,
    grid: { left: 50, right: 24, top: 52, bottom: 46 },
    legend: { top: 0, left: 'center', itemWidth: 26, itemHeight: 10, textStyle: { fontSize: 16, color: P.text } },
    xAxis: { type: 'value', min: lo, max: hi, name: '层号', nameLocation: 'middle', nameGap: 26,
      minInterval: 1, nameTextStyle: axisFont, axisLabel: { ...axisFont, hideOverlap: true, formatter: (v) => String(v) }, splitLine: { show: false } },
    yAxis: { type: 'value', name: '贡献', nameTextStyle: { ...axisFont, align: 'left' }, nameGap: 10, axisLabel: axisFont, splitNumber: 4,
      splitLine: { lineStyle: { color: P.split } } },
    series,
  }
})
</script>

<style scoped>
.verdict.v-pending, .t-pending { color: #9a5900; background: rgba(185, 112, 8, .12); }
.r-input { flex: 600 0 600px; }
.r-param { flex: 276 1 276px; min-width: 0; }
.r-op { flex: 290 0 290px; }
.r-vis { flex: 1; }
.fields { gap: 8px 22px; }
.fields.one { grid-template-columns: auto; gap: 8px; }
.ref-inp { width: 80px; }
.btn { padding: 6px 14px; }
.vis-grid { height: 100%; display: grid; grid-template-columns: minmax(0, 300fr) minmax(0, 510fr) minmax(0, 330fr); grid-template-rows: minmax(0, 300fr) minmax(0, 260fr); gap: 12px; }
.card { padding: 8px 12px; }
.overlay { flex: 1; min-height: 0; width: 100%; }
.part { fill: rgba(178, 49, 46, 0.30); stroke: #b2312e; stroke-width: 0.6; vector-effect: non-scaling-stroke; }
.band { fill: rgba(178, 49, 46, 0.10); stroke: #b2312e; stroke-width: 0.5; stroke-dasharray: 2.2 1.6; vector-effect: non-scaling-stroke; }
.img-legend { display: flex; gap: 16px; font-size: 15px; color: var(--text-2); margin-top: 4px; }
.sw { display: inline-block; width: 16px; height: 12px; margin-right: 5px; vertical-align: -1px; border-radius: 2px; }
.sw-part { background: rgba(178, 49, 46, 0.45); border: 1px solid #b2312e; }
.sw-band { background: rgba(178, 49, 46, 0.12); border: 1px dashed #b2312e; }
.sw-powder { background: var(--powder-sw); border: 1px solid var(--powder-sw-border); }
.lg { font-size: 15px; font-weight: 400; color: var(--text-2); display: flex; align-items: center; gap: 6px; }
.lim-sw { display: inline-block; width: 3px; height: 16px; background: var(--ink); }
.grp { margin-top: 8px; }
.g-head { display: flex; justify-content: space-between; align-items: baseline; font-size: 17px; font-weight: 700; }
.g-sum { font-size: 15px; font-weight: 400; color: var(--text-2); }
.g-sum b { font-size: 17px; color: var(--text); }
.zrow { display: grid; grid-template-columns: 58px 1fr 54px 60px; align-items: center; gap: 8px; margin-top: 6px; font-size: 16px; }
.z-name { white-space: nowrap; }
.z-track { position: relative; height: 20px; background: var(--track); border-radius: 4px; }
.z-fill { height: 100%; border-radius: 4px; }
.z-fill.f-part { background: var(--proc); }
.z-fill.f-powder { background: var(--dev); }
.z-fill.dim { opacity: 0.35; }
.z-lim { position: absolute; top: -4px; width: 3px; height: 28px; background: var(--ink); margin-left: -1px; }
.z-val { text-align: right; font-weight: 400; color: var(--text-2); }
.z-val.over { font-weight: 700; color: var(--text); }
.z-tag { font-size: 14px; border-radius: 10px; padding: 0 8px; text-align: center; white-space: nowrap; }
.z-tag.on { background: var(--warn); color: #fff; font-weight: 700; }
.z-tag.off { background: var(--ok-soft); color: var(--ok); }
.hint { margin-top: auto; font-size: 14px; color: var(--text-3); line-height: 1.35; }
.verdict { font-size: 25px; font-weight: 800; color: #fff; border-radius: 6px; padding: 6px 10px; text-align: center; margin-bottom: 6px; }
.v-dev, .v-proc, .v-both { background: var(--warn); }
.v-nor { background: var(--ok); }
.prob { margin-top: 6px; }
.p-head { display: flex; justify-content: space-between; font-size: 16px; }
.p-head b { font-size: 17px; }
.track { height: 8px; background: var(--track); border-radius: 4px; overflow: hidden; margin-top: 2px; }
.fill { height: 100%; border-radius: 4px; }
.kv { display: flex; align-items: center; gap: 8px; margin-top: 10px; font-size: 16px; flex-wrap: nowrap; }
.kv.ev { align-items: flex-start; margin-top: 8px; }
.ev-lines { font-size: 16px; line-height: 1.4; }
.ev-lines b { font-size: 17px; }
.t-zone { color: var(--text); font-size: 18px; }
.act { margin-top: auto; padding-bottom: 2px; }
.act-k { font-size: 16px; color: var(--text-2); margin: 6px 0 4px; }
.act-row { display: flex; gap: 6px; }
.act-box { flex: 1; min-width: 0; display: flex; align-items: center; justify-content: space-between; gap: 8px;
  background: var(--warn-soft); border-left: 5px solid var(--warn); border-radius: 4px; padding: 6px 10px; }
.act-t { font-size: 20px; font-weight: 700; color: var(--warn-ink); white-space: nowrap; }
.act-st { font-size: 13px; color: #fff; background: var(--warn); border-radius: 10px; padding: 1px 8px; white-space: nowrap; }
.act.multi { display: flex; align-items: flex-start; gap: 8px; }
.act.multi .act-k { margin: 6px 0 0; white-space: nowrap; }
.act.multi .act-row { flex: 1; min-width: 0; flex-direction: column; gap: 4px; }
.act-box.two { padding: 3px 8px; border-left-width: 4px; }
.act-box.two .act-t { font-size: 16px; }
.act-box.none { background: var(--img-bg); border-left-color: var(--border); }
.act-box.none .act-t { color: var(--text-2); }
.c-res.dense .verdict { font-size: 23px; padding: 3px 10px; margin-bottom: 2px; }
.c-res.dense .prob { margin-top: 3px; }
.c-res.dense .kv.ev { margin-top: 5px; }
.c-res.dense .ev-lines { line-height: 1.3; }
.c-curve { grid-column: 1 / 3; }
.curve-note { font-size: 12px; color: var(--text-2); margin-bottom: 6px; }
.tbl { font-size: 15px; }
.tbl th { padding: 4px 3px; }
.tbl td { padding: 5px 3px; }
.tbl td.over { font-weight: 700; }
.tbl td.muted { color: var(--text-2); }
.tag { padding: 0 7px; font-size: 14px; }
</style>
