<template>
  <div v-if="d" class="page analysis-page trace-page">
    <div class="row-top" :class="{ 'replay-metadata': replaySession }">
      <Region kind="input" title="监测数据" class="r-input">
        <div class="fields">
          <div class="field"><span class="k">设备</span>
            <select class="sel" :value="replaySession ? d.device.id : state.device" :disabled="embedded || stepper.running.value" @change="switchDevice($event.target.value)">
              <option v-for="x in devs" :key="x.id" :value="x.id">{{ x.name }}</option></select></div>
          <div class="field"><span class="k">成形任务</span><select class="sel" disabled><option>{{ d.task.name }}</option></select></div>
          <div class="field"><span class="k">成形层</span>
            <select class="sel" :value="d.layer" :disabled="!!replaySession || stepper.running.value || layers.length < 2" @change="run(+$event.target.value)">
              <option v-if="replaySession" :value="d.layer">第 {{ d.layer ?? '—' }} 层</option>
              <option v-for="L in layers" :key="L" :value="L">第 {{ L }} 层</option></select></div>
          <div class="field"><span class="k">参照层</span><select class="sel" disabled><option>第 {{ d.refLayer ?? '—' }} 层</option></select></div>
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
      <Region v-if="!replaySession" kind="op" title="操作" class="r-op">
        <div class="ops">
          <button class="btn primary" :disabled="busy || stepper.running.value" @click="run(d.layer)">单层溯源</button>
          <button class="btn" :disabled="replay" @click="toggleStep">{{ stepper.running.value ? '停止溯源' : '逐层溯源' }}</button>
        </div>
      </Region>
    </div>

    <Region kind="vis" class="r-vis">
      <div class="vis-grid">
        <div class="card c-img">
          <div class="card-title">异常溯源</div>
          <svg v-if="d.image.url" class="overlay" :viewBox="viewBox" preserveAspectRatio="xMidYMid meet">
            <image :href="imgUrl" x="0" y="0" :width="d.image.width" :height="d.image.height" />
            <polygon v-for="(c, i) in band" :key="'b' + i" :points="c" class="band" />
            <polygon v-for="(c, i) in part" :key="'p' + i" :points="c" class="part" />
          </svg><div v-else class="image-pending">铺粉后图像未接入</div>
          <div class="img-legend">
            <span><i class="sw sw-part"></i>零件区</span>
            <span><i class="sw sw-band"></i>边缘邻域</span>
            <span><i class="sw sw-powder"></i>粉床区</span>
          </div>
        </div>

        <div class="card c-res" :class="{ dense: d.mode === 'dual' }">
          <div class="card-title">故障诊断</div>
          <EquipmentDiagnosis :trace="d" :recognition="replaySession?.snapshot?.recognition" />
          <div class="diagnosis-details">
          <div class="prob" v-for="p in probs" :key="p.name">
            <div class="p-head"><span>{{ p.name }}</span><b>{{ fmtPct(p.v) }}</b></div>
            <div class="track"><div class="fill" :style="{ width: p.v * 100 + '%', background: p.color }"></div></div>
          </div>
          <div v-if="d.actions.length" class="check-advice">
            <span>检查建议</span>
            <p>{{ d.actions.join('；') }}</p>
          </div>
          </div>
        </div>

        <div class="card c-curve">
          <div class="card-title">因果因子贡献溯源</div>
          <EChart :option="curveOption" class="chart" />
        </div>

      </div>
    </Region>
  </div>
  <div v-else class="loading">正在读取诊断数据…</div>
</template>

<script setup>
import { pendingAnalysis } from '../../workspace/analysisPresentation'
import { computed, inject, onMounted, ref, watch } from 'vue'
import Region from '../components/Region.vue'
import EChart from '../components/EChart.vue'
import EquipmentDiagnosis from '../components/EquipmentDiagnosis.vue'
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
if (replaySession) watch(() => replaySession.snapshot, frame => { d.value = frame?.trace || pendingAnalysis(frame, 'trace') }, { immediate: true })
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
const probs = computed(() => [
  ...(d.value.factors.proc ? [{ name: '工艺问题', v: d.value.factors.proc.prob, color: 'var(--proc)' }] : []),
  { name: '设备问题', v: d.value.factors.dev.prob, color: 'var(--dev)' },
])
const visibleFactors = computed(() => layerWindow(factorCurveRows(d.value), d.value.layer))
const curveStart = computed(() => visibleFactors.value[0]?.layer ?? Math.max(1, (d.value.layer ?? TRACE_WINDOW_SIZE) - TRACE_WINDOW_SIZE + 1))
const hasProcessCurve = computed(() => visibleFactors.value.some(r => r.proc !== null))

const curveOption = computed(() => {
  const P = pal.value
  const C = P
  const axisFont = { fontSize: 13, color: P.axis }
  const cv = d.value.curve
  const lo = curveStart.value
  const hi = d.value.layer ?? TRACE_WINDOW_SIZE
  const cur = { silent: true, symbol: 'none', data: [{ xAxis: d.value.layer, lineStyle: { color: P.ink, width: 1.4 },
    label: { show: true, color: P.text, formatter: '当前层', fontSize: 12, position: 'insideEndTop', distance: 6 } }] }
  const lim = (name, v, color, type) => ({ name, type: 'line', symbol: 'none', z: 5, lineStyle: { width: 1.8, color, type }, itemStyle: { color },
    data: [[lo === hi ? lo - 1 : lo, v], [lo === hi ? hi + 1 : hi, v]] })
  const factors = visibleFactors.value
  // 首个有效结果尚不能连成线，仍需显示数据点；缺失层继续保留为空。
  const series = [
        { name: '工艺侧', type: 'line', showSymbol: true, symbol: 'circle', symbolSize: 6, z: 8, lineStyle: { width: 1.6, color: C.proc }, itemStyle: { color: C.proc },
          data: factors.map((x) => [x.layer, x.proc]), connectNulls: false },
        { name: '设备侧', type: 'line', showSymbol: true, symbol: 'circle', symbolSize: 6, z: 8, lineStyle: { width: 1.6, color: C.dev }, itemStyle: { color: C.dev },
          data: factors.map((x) => [x.layer, x.dev]), markLine: Number.isFinite(d.value.layer) ? cur : undefined },
        ...(hasProcessCurve.value ? [lim('工艺上限水平', cv.upper.proc, P.upperProc, 'dashed')] : []),
        ...(Number.isFinite(cv.upper.dev) ? [lim('设备上限水平', cv.upper.dev, P.upperDev, 'dotted')] : []),
      ]
  return {
    animation: false,
    tooltip: { trigger: 'axis', confine: true },
    // 图例固定分成曲线/上限两行，单独预留空间，避免窄列自动换行压住坐标轴。
    grid: { left: 8, right: 16, top: 88, bottom: 42, containLabel: true },
    legend: { top: 4, left: 'center', itemWidth: 18, itemHeight: 8, itemGap: 12,
      data: ['工艺侧', '设备侧', '', ...series.slice(2).map(s => s.name)],
      textStyle: { fontSize: 13, color: P.text } },
    xAxis: { type: 'value', min: lo === hi ? lo - 1 : lo, max: lo === hi ? hi + 1 : hi, name: '层号', nameLocation: 'middle', nameGap: 26,
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
.vis-grid { height: 100%; display: grid; grid-template-columns: minmax(280px, 1fr) minmax(0, 2fr); grid-template-rows: auto auto; gap: 12px; }
.card { padding: 8px 12px; }
.overlay { flex: 1; min-height: 0; width: 100%; }
.part { fill: rgba(178, 49, 46, 0.30); stroke: #b2312e; stroke-width: 0.6; vector-effect: non-scaling-stroke; }
.band { fill: rgba(178, 49, 46, 0.10); stroke: #b2312e; stroke-width: 0.5; stroke-dasharray: 2.2 1.6; vector-effect: non-scaling-stroke; }
.img-legend { display: flex; gap: 16px; font-size: 15px; color: var(--text-2); margin-top: 4px; }
.sw { display: inline-block; width: 16px; height: 12px; margin-right: 5px; vertical-align: -1px; border-radius: 2px; }
.sw-part { background: rgba(178, 49, 46, 0.45); border: 1px solid #b2312e; }
.sw-band { background: rgba(178, 49, 46, 0.12); border: 1px dashed #b2312e; }
.sw-powder { background: var(--powder-sw); border: 1px solid var(--powder-sw-border); }
.prob { margin-top: 6px; }
.p-head { display: flex; justify-content: space-between; font-size: 16px; }
.p-head b { font-size: 17px; }
.track { height: 8px; background: var(--track); border-radius: 4px; overflow: hidden; margin-top: 2px; }
.fill { height: 100%; border-radius: 4px; }
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
.c-curve { grid-column: 1; grid-row: 2; }
.diagnosis-details { margin-top: 12px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 16px; }
.check-advice { grid-column: 1 / -1; margin-top: 6px; padding: 12px 16px; text-align: center; border: 1px solid var(--border); border-top: 3px solid var(--dev); border-radius: 4px; background: var(--dev-soft); line-height: 1.6; }
.check-advice span { font-size: 13px; font-weight: 600; color: var(--text-2); }
.check-advice p { margin: 4px 0 0; font-size: 17px; font-weight: 600; color: var(--text); overflow-wrap: anywhere; }
/* 同行证据与诊断卡片等高，缺图时占用与图像相同的画布尺寸。 */
.vis-grid > .card { align-self: stretch; }
</style>
