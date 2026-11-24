<template>
  <div v-if="d" class="page analysis-page recognition-page">
    <div class="row-top">
      <Region kind="input" title="识别对象" class="r-input">
        <div class="fields">
          <div class="field"><span class="k">设备</span>
            <select class="sel" :value="replaySession ? d.device.id : state.device" :disabled="embedded || busy" @change="switchDevice($event.target.value)">
              <option v-for="x in devs" :key="x.id" :value="x.id">{{ x.name }}</option></select></div>
          <div class="field"><span class="k">成形任务</span><select class="sel" disabled><option>{{ d.task.name }}</option></select></div>
          <div class="field"><span class="k">识别模型</span><select class="sel" disabled><option>{{ d.model.name }}</option></select></div>
          <div class="field"><span class="k">成形层</span>
            <select class="sel" :value="d.layer" :disabled="!!replaySession || busy" @change="run(+$event.target.value)">
              <option v-if="replaySession" :value="d.layer">第 {{ d.layer ?? '—' }} 层</option>
              <option v-for="L in layers" :key="L" :value="L">第 {{ L }} 层</option></select></div>
        </div>
      </Region>
    </div>

    <Region kind="vis" class="r-vis">
      <div class="grid">
        <div class="card c-img">
          <div class="card-title">铺粉后图像<span class="tm">{{ d.image.box ? '虚线框为成形区' : '' }}</span></div>
          <svg v-if="d.image.url" class="img" :viewBox="`0 0 ${d.image.w} ${d.image.h}`" preserveAspectRatio="xMidYMid meet">
            <image :href="imgUrl" x="0" y="0" :width="d.image.w" :height="d.image.h" />
            <!-- 以屏幕像素固定线宽，深浅双描边兼顾亮粉床与暗部，不随原图尺寸变粗。 -->
            <g v-if="d.image.box" class="build-region-outline">
              <rect v-for="stroke in ['roi-outline', 'roi-line']" :key="stroke" :class="stroke"
                :x="d.image.box[0]" :y="d.image.box[1]" :width="d.image.box[2] - d.image.box[0]" :height="d.image.box[3] - d.image.box[1]" />
            </g>
          </svg><div v-else class="image-pending">铺粉后图像未接入</div>
        </div>

        <div class="card c-res">
          <div class="card-title">异常识别<span class="tm">第 {{ d.layer ?? '—' }} 层</span></div>
          <div class="vc">
            <div class="verdict" :style="{background: probabilityColor(d.prob.def)}">{{ d.label }}</div>
            <div class="prob-row main-prob"><span>模型异常识别概率</span><b :style="{color: probabilityColor(d.prob.def)}">{{ fmtPct(d.prob.def) }}</b></div>
            <div class="pbar"><div class="pfill" :style="{ width: d.prob.def * 100 + '%', background: probabilityColor(d.prob.def) }"></div><i class="th" :style="{ left: d.params.threshold * 100 + '%' }"></i></div>
            <div class="prob-row"><span>正常概率</span><b>{{ fmtPct(Number.isFinite(d.prob.def) ? 1 - d.prob.def : null) }}</b></div>
          </div>
        </div>

        <div class="card c-mod">
          <div class="card-title">多模态数据接入分析</div>
          <div class="vc">
            <div class="m-sub">各模态识别概率</div>
            <div class="single" v-for="m in modalityResults" :key="m.key" :class="{ unused: !m.used }">
              <span class="s-name">{{ m.name }}</span>
              <div class="s-track"><div class="s-fill" :style="{ width: m.p * 100 + '%', background: probabilityColor(m.p) }"></div><i class="s-th" :style="{ left: d.params.threshold * 100 + '%' }"></i></div>
              <span class="s-p">{{ fmtPct(m.p) }}</span>
              <span class="tag" :style="{color:probabilityColor(m.p)}">{{ m.label }}</span>
            </div>
            <template v-if="!d.infrared">
              <div class="m-sub second">融合权重</div>
              <div v-for="m in weightedModalities" :key="m.key" class="weight-row" :class="{ dominant:m.dominant }">
                <div class="weight-heading"><span>{{ m.name }}</span><b>{{ fmtPct(m.weight) }}</b><span v-if="m.dominant" class="dominant-label">主导模态</span></div>
                <div class="weight-track"><div :style="{width: (m.weight ?? 0) * 100 + '%'}"></div></div>
              </div>
            </template>
          </div>
        </div>

        <div v-if="!d.infrared" class="card c-torque">
          <div class="card-title">{{ replaySession?.source === 'device-record' ? '已接入扭矩采样片段' : replaySession ? `实时采样扭矩 · 第 ${replaySession.snapshot.layer} 层` : '当前层铺粉段扭矩' }}</div>
          <div class="chart-window-note">{{ replaySession && replaySession.source !== 'device-record' ? '最近 50 个采样点 · 时间轴随采样滚动；识别结果使用完整铺粉段输入' : '最近 50 个采样点' }}</div>
          <EChart :option="torqueOption" class="chart" />
        </div>

        <div v-if="d.infrared" class="card c-torque c-infrared">
          <div class="card-title">铺粉后红外识别<span class="tm">第 {{ d.layer ?? '—' }} 层 · {{ d.infrared.image.time }}</span></div>
          <div class="infrared-content"><img class="img" :src="mediaUrl(d.infrared.image.url)" alt="铺粉后红外图像" />
            <div><div class="prob-row"><span>识别类别</span><b>{{ d.infrared.label }}</b></div>
              <div class="prob-row"><span>类别置信度</span><b>{{ fmtPct(d.infrared.confidence) }}</b></div>
              <div class="prob-row"><span>异常概率</span><b :style="{color:probabilityColor(d.infrared.anomalyProbability)}">{{ fmtPct(d.infrared.anomalyProbability) }}</b></div></div>
          </div>
        </div>

        <div class="card c-rec">
          <div class="card-title">逐层识别记录</div>
          <!-- 窄屏下仅记录表局部滚动，保留所有字段。 -->
          <div class="table-scroll" tabindex="0" role="region" aria-label="逐层识别记录表格">
          <table class="tbl">
            <thead><tr><th>层号</th><th>{{ d.infrared ? '可见光异常概率' : '异常概率' }}</th><th>识别结果</th></tr></thead>
            <tbody>
              <tr v-if="!d.records.length"><td colspan="3">暂无逐层识别结果</td></tr>
              <tr v-for="r in d.records" :key="r.layer" :class="{ cur: r.layer === d.layer, selectable: canSelectRecord }" :tabindex="canSelectRecord ? 0 : undefined" :aria-label="`查看第 ${r.layer} 层识别结果`" :aria-current="r.layer === d.layer ? 'true' : undefined" @click="selectRecord(r.layer)" @keydown.enter.prevent="selectRecord(r.layer)" @keydown.space.prevent="selectRecord(r.layer)">
                <td>{{ r.layer }}</td><td>{{ fmtPct(r.p) }}</td>
                <td><span class="tag" :style="{color:probabilityColor(r.p)}">{{ r.label }}</span></td>
              </tr>
            </tbody>
          </table>
          </div>
        </div>
      </div>
    </Region>
  </div>
  <div v-else class="loading">{{ replaySession ? '当前时刻尚无可用识别结果，等待图像和扭矩数据到齐。' : '正在识别…' }}</div>
</template>

<script setup>
import { probabilityColor } from '../../../../utils/probabilityStyle'
import { pendingAnalysis } from '../../workspace/analysisPresentation'
import { computed, inject, onMounted, ref, watch } from 'vue'
import Region from '../components/Region.vue'
import EChart from '../components/EChart.vue'
import { api, mediaUrl } from '../api.js'
import { devicesFor, selectDevice, state } from '../state.js'
import { fmtPct, useCall } from '../composables.js'
import { pal } from '../theme.js'
import { torqueWindow, replayTimeLabel } from '../rollingWindow.js'

const embedded = inject('formingEmbedded', false)
const replaySession = inject('formingReplay', null)
const { busy, call, report } = useCall()
const d = ref(null)
// 回放设备从工作区共享快照读取，跳转时清空旧结果，不再启动页面各自的计时器。
if (replaySession) watch(() => replaySession.snapshot, frame => { d.value = frame?.recognition || pendingAnalysis(frame, 'recognition') }, { immediate: true })
const layers = ref([])
const devs = computed(() => replaySession ? (d.value ? [d.value.device] : []) : devicesFor('recognition'))
const modalityResults = computed(() => d.value?.infrared ? [...d.value.singles, { key:'ir', name:'铺粉后红外', p:d.value.infrared.anomalyProbability, label:d.value.infrared.anomalyProbability >= .5 ? '异常' : '正常', used:true }] : d.value?.singles || [])
// 主导关系仅取模型实际融合权重，不把单模态异常概率当作贡献权重。
const weightedModalities = computed(() => {
  const rows = (d.value?.singles || []).filter(m => m.used).map(m => ({key:m.key, name:m.name, weight:d.value.weights[m.key]}))
  const weights = rows.map(m => m.weight).filter(Number.isFinite)
  const maximum = weights.length ? Math.max(...weights) : null
  const unique = maximum > 0 && rows.filter(m => m.weight === maximum).length === 1
  return rows.map(m => ({...m, dominant:unique && m.weight === maximum}))
})
const imgUrl = computed(() => mediaUrl(d.value.image.url, 1200))

const canSelectRecord = computed(() => replaySession ? typeof replaySession.seekRecognitionLayer === 'function' && !replaySession.loading : !busy.value)
async function selectRecord(layer) {
  if (!canSelectRecord.value) return
  if (replaySession) await replaySession.seekRecognitionLayer(layer)
  else await run(layer)
}

async function run(layer) {
  if (replaySession) return
  const th = Number(state.recog.threshold)
  if (!(th > 0 && th < 100)) { report(new Error('判定阈值应在 1～99% 之间')); return false }
  const r = await call(() => api.recognize({ device_id: state.device, layer: layer ?? state.layer[state.device] ?? null,
    threshold: th / 100, modalities: state.recog.modalities }))
  if (!r) return false
  d.value = r
  state.layer[state.device] = r.layer
  if (!layers.value.length) layers.value = (await call(() => api.layers(state.device, r.task.id))) || [r.layer]
  return true
}
function switchDevice(id) { selectDevice(id); d.value = null; layers.value = []; run() }
onMounted(() => { if (!replaySession) run() })

const torqueOption = computed(() => {
  const P = pal.value
  const axisFont = { fontSize: 16, color: P.axis }
  const live = replaySession?.snapshot?.liveTorque
  const t = torqueWindow(live || d.value.torque)
  return {
    animation: !!live && replaySession.playing, animationDuration: 0, animationDurationUpdate: 200, animationEasingUpdate: 'linear',
    grid: { left: 50, right: 14, top: 34, bottom: 44 },
    legend: { top: 0, right: 0, itemWidth: 24, itemHeight: 4, icon: 'rect', textStyle: { fontSize: 15, color: P.text } },
    xAxis: { type: 'value', name: live ? '采样时间' : '铺粉段时间/s', nameLocation: 'middle', nameGap: 26, nameTextStyle: axisFont,
      axisLabel: { ...axisFont, ...(live ? { formatter: replayTimeLabel } : {}) },
      min: t.min, max: t.max, splitLine: { show: false } },
    yAxis: { type: 'value', name: '扭矩/%', nameTextStyle: axisFont, axisLabel: axisFont, splitLine: { lineStyle: { color: P.split } } },
    series: [
      { name: '刮刀扭矩', type: 'line', showSymbol: false, lineStyle: { width: 1.8, color: P.scraper }, itemStyle: { color: P.scraper },
        data: t.t.map((x, i) => [x, t.scraper[i]]) },
      { name: '加工平台扭矩', type: 'line', showSymbol: false, lineStyle: { width: 1.8, color: P.platform }, itemStyle: { color: P.platform },
        data: t.t.map((x, i) => [x, t.platform[i]]) },
    ],
  }
})
</script>

<style scoped>
.build-region-outline rect { fill: none; vector-effect: non-scaling-stroke; stroke-dasharray: 8 5; stroke-linejoin: round; pointer-events: none; }
.roi-outline { stroke: #243b53; stroke-width: 2.75px; }
.roi-line { stroke: #fff; stroke-width: 1.25px; }

.c-rec .tbl { width: 100%; table-layout: fixed; }
.c-rec .tbl th:first-child { width: 22%; }
.c-rec .tbl th:last-child { width: 28%; }
.c-rec .tbl th:last-child, .c-rec .tbl td:last-child { text-align: right; }
.c-rec .tbl th, .c-rec .tbl td { padding: 8px 10px; }
.single .tag, .c-rec .tag { background: var(--card-bg); border: 1px solid currentColor; }

.main-prob { align-items: center; gap: 10px; flex-wrap: wrap; }
.c-res .main-prob b { font-size: 34px; color: var(--dev); }
.c-res { border-top: 3px solid var(--dev); }
.weight-row { margin-top: 10px; padding: 8px; border: 1px solid var(--border); }
.weight-row.dominant { border-color: var(--dev); background: var(--dev-soft); }
.weight-heading { display:flex; align-items:center; flex-wrap:wrap; gap:8px; font-size:13px; }
.weight-heading b { margin-left:auto; }
.dominant-label { color:var(--dev); font-weight:700; }
.weight-track { height:8px; margin-top:8px; background:var(--track); }
.weight-track > div { height:100%; background:var(--dev); }

/* 长记录只在表格内滚动，表头固定；点击记录复用设备共享回放游标。 */
.c-rec .table-scroll { max-height: 280px; overflow-y: auto; scrollbar-gutter: stable; }
.c-rec thead { position: sticky; top: 0; z-index: 1; background: var(--card-bg); }
.c-rec tr.selectable { cursor: pointer; }
.c-rec tr.selectable:hover, .c-rec tr.selectable:focus-visible { background: var(--dev-soft); outline: 2px solid var(--dev); outline-offset: -2px; }

.infrared-content { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }
@media(max-width:600px) { .infrared-content { grid-template-columns: minmax(0, 1fr); } }
.r-input { flex: 520 0 520px; }
.r-vis { flex: 1; }
.grid { height: 100%; display: grid; grid-template-columns: minmax(0, 330fr) minmax(0, 300fr) minmax(0, 510fr); grid-template-rows: minmax(0, 300fr) minmax(0, 260fr); gap: 12px; }
.img { width: 100%; flex: 1; min-height: 0; }
.vc { flex: 1; display: flex; flex-direction: column; justify-content: center; padding-bottom: 14px; }
.verdict { font-size: 30px; font-weight: 800; color: #fff; background: var(--am-text-3); border-radius: 6px; padding: 8px 10px; text-align: center; margin-bottom: 16px; }
.verdict.pending { background: var(--track); color: var(--text-2); }
.verdict.nor { background: var(--ok); }
.prob-row { display: flex; justify-content: space-between; font-size: 17px; margin-top: 10px; }
.prob-row b { font-size: 18px; }
.pbar { position: relative; height: 12px; background: var(--track-2); border-radius: 6px; margin: 4px 0 8px; }
.pfill { height: 100%; background: var(--am-text-3); border-radius: 6px; }
.th { position: absolute; top: -4px; width: 2px; height: 20px; background: var(--ink); }
.c-torque { grid-column: 1 / 3; }
.m-sub { font-size: 17px; font-weight: 700; margin-top: 4px; }
.m-sub.second { margin-top: 18px; }
.single { display: grid; grid-template-columns: 140px 1fr 64px 58px; align-items: center; gap: 10px; margin-top: 10px; font-size: 16px; }
.single.unused { opacity: .45; }
.s-name { white-space: nowrap; }
.s-track { position: relative; height: 12px; background: var(--track); border-radius: 6px; }
.s-fill { height: 100%; background: var(--am-text-3); border-radius: 6px; }
.s-th { position: absolute; top: -4px; width: 2px; height: 20px; background: var(--ink); }
.s-p { text-align: right; font-weight: 700; }
.tag { text-align: center; }
</style>
