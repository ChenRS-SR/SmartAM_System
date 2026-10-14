<template>
  <div v-if="d" class="page">
    <div class="row-top">
      <Region kind="input" title="识别对象" class="r-input">
        <div class="fields">
          <div class="field"><span class="k">设备</span>
            <select class="sel" :value="state.device" :disabled="embedded || stepper.running.value" @change="switchDevice($event.target.value)">
              <option v-for="x in devs" :key="x.id" :value="x.id">{{ x.name }}</option></select></div>
          <div class="field"><span class="k">成形任务</span><select class="sel" disabled><option>{{ d.task.name }}</option></select></div>
          <div class="field"><span class="k">识别模型</span><select class="sel" disabled><option>{{ d.model.name }}</option></select></div>
          <div class="field"><span class="k">成形层</span>
            <select class="sel" :value="d.layer" :disabled="stepper.running.value" @change="run(+$event.target.value)">
              <option v-for="L in layers" :key="L" :value="L">第 {{ L }} 层</option></select></div>
        </div>
      </Region>
      <Region kind="param" title="识别参数" class="r-param">
        <div class="fields">
          <div class="field wide"><span class="k">判定阈值</span>
            <input class="inp" type="number" min="1" max="99" step="1" v-model.number="state.recog.threshold" @change="run(d.layer)" /><span class="k">%</span></div>
          <div class="field wide"><span class="k">输入模态</span>
            <span v-for="m in MODS" :key="m.key" class="ch" @click="toggle(m.key)"><i class="ck" :class="{ off: !state.recog.modalities.includes(m.key) }">✓</i>{{ m.label }}</span></div>
        </div>
      </Region>
      <Region kind="op" title="操作" class="r-op">
        <div class="ops">
          <button class="btn primary" :disabled="busy || stepper.running.value" @click="run(d.layer)">单层识别</button>
          <button class="btn" @click="toggleStep">{{ stepper.running.value ? '停止识别' : '逐层识别' }}</button>
        </div>
      </Region>
    </div>

    <Region kind="vis" class="r-vis">
      <div class="grid">
        <div class="card c-img">
          <div class="card-title">铺粉后图像<span class="tm">虚线框为成形区</span></div>
          <svg class="img" :viewBox="`0 0 ${d.image.w} ${d.image.h}`" preserveAspectRatio="xMidYMid meet">
            <image :href="imgUrl" x="0" y="0" :width="d.image.w" :height="d.image.h" />
            <rect :x="d.image.box[0]" :y="d.image.box[1]" :width="d.image.box[2] - d.image.box[0]" :height="d.image.box[3] - d.image.box[1]"
              fill="none" stroke="#f4b942" stroke-width="14" stroke-dasharray="48 28" />
          </svg>
        </div>

        <div class="card c-res">
          <div class="card-title">识别结果<span class="tm">第 {{ d.layer }} 层</span></div>
          <div class="vc">
            <div class="verdict" :class="{ nor: d.label !== '异常' }">{{ d.label }}</div>
            <div class="prob-row"><span>异常概率</span><b>{{ fmtPct(d.prob.def) }}</b></div>
            <div class="pbar"><div class="pfill" :style="{ width: d.prob.def * 100 + '%' }"></div><i class="th" :style="{ left: d.params.threshold * 100 + '%' }"></i></div>
            <div class="prob-row"><span>正常概率</span><b>{{ fmtPct(1 - d.prob.def) }}</b></div>
          </div>
        </div>

        <div class="card c-mod">
          <div class="card-title">各模态的作用</div>
          <div class="vc">
            <div class="m-sub">模态权重<span class="m-hint">融合时各模态所占比重</span></div>
            <div class="wbar">
              <div class="wseg w-vis" :style="{ width: d.weights.vis * 100 + '%' }"><span v-if="d.weights.vis > 0.3">铺粉后图像 {{ (d.weights.vis * 100).toFixed(1) }}%</span></div>
              <div class="wseg w-tq" :style="{ width: d.weights.tq * 100 + '%' }"><span v-if="d.weights.tq > 0.3">刮刀与平台扭矩 {{ (d.weights.tq * 100).toFixed(1) }}%</span></div>
            </div>
            <div class="w-legend"><span><i class="sw w-vis"></i>铺粉后图像 {{ (d.weights.vis * 100).toFixed(1) }}%</span>
              <span><i class="sw w-tq"></i>刮刀与平台扭矩 {{ (d.weights.tq * 100).toFixed(1) }}%</span></div>
            <div class="m-sub second">单模态判断<span class="m-hint">只用该模态时的异常概率</span></div>
            <div class="single" v-for="m in d.singles" :key="m.key" :class="{ unused: !m.used }">
              <span class="s-name">{{ m.name }}</span>
              <div class="s-track"><div class="s-fill" :style="{ width: m.p * 100 + '%' }"></div><i class="s-th" :style="{ left: d.params.threshold * 100 + '%' }"></i></div>
              <span class="s-p">{{ (m.p * 100).toFixed(1) }}%</span>
              <span class="tag" :class="m.label === '异常' ? 't-def' : 't-nor'">{{ m.label }}</span>
            </div>
          </div>
        </div>

        <div class="card c-torque">
          <div class="card-title">当前层铺粉段扭矩</div>
          <EChart :option="torqueOption" class="chart" />
        </div>

        <div class="card c-rec">
          <div class="card-title">逐层识别记录</div>
          <table class="tbl">
            <thead><tr><th>层号</th><th>异常概率</th><th>识别结果</th></tr></thead>
            <tbody>
              <tr v-for="r in d.records" :key="r.layer" :class="{ cur: r.layer === d.layer }" @click="!stepper.running.value && run(r.layer)">
                <td>{{ r.layer }}</td><td>{{ fmtPct(r.p) }}</td>
                <td><span class="tag" :class="r.label === '异常' ? 't-def' : 't-nor'">{{ r.label }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </Region>
  </div>
  <div v-else class="loading">正在识别…</div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue'
import Region from '../components/Region.vue'
import EChart from '../components/EChart.vue'
import { api, mediaUrl } from '../api.js'
import { devicesFor, selectDevice, state } from '../state.js'
import { fmtPct, useCall, useStepper } from '../composables.js'
import { pal } from '../theme.js'

const MODS = [{ key: 'vis', label: '铺粉后图像' }, { key: 'tq', label: '扭矩' }]
const embedded = inject('formingEmbedded', false)
const { busy, call, report } = useCall()
const stepper = useStepper(1200)
const d = ref(null)
const layers = ref([])
const devs = computed(() => devicesFor('recognition'))
const imgUrl = computed(() => mediaUrl(d.value.image.url, 1200))

async function run(layer) {
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
function toggle(k) {
  const m = state.recog.modalities
  if (m.includes(k)) { if (m.length === 1) { report(new Error('至少选择一种输入模态')); return } state.recog.modalities = m.filter((x) => x !== k) }
  else state.recog.modalities = ['vis', 'tq'].filter((x) => x === k || m.includes(x))
  if (d.value) run(d.value.layer)
}
function toggleStep() {
  if (stepper.running.value) stepper.stop()
  else stepper.start(layers.value, d.value.layer, (L) => run(L))
}
function switchDevice(id) { selectDevice(id); d.value = null; layers.value = []; run() }
onMounted(() => run())

const torqueOption = computed(() => {
  const P = pal.value
  const axisFont = { fontSize: 16, color: P.axis }
  const t = d.value.torque
  return {
    animation: false,
    grid: { left: 50, right: 14, top: 34, bottom: 44 },
    legend: { top: 0, right: 0, itemWidth: 24, itemHeight: 4, icon: 'rect', textStyle: { fontSize: 15, color: P.text } },
    xAxis: { type: 'value', name: '铺粉段时间/s', nameLocation: 'middle', nameGap: 26, nameTextStyle: axisFont, axisLabel: axisFont,
      min: 0, max: Math.ceil(t.t[t.t.length - 1]), splitLine: { show: false } },
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
.r-input { flex: 520 0 520px; }
.r-param { flex: 396 1 396px; min-width: 0; }
.r-op { flex: 250 0 250px; }
.r-vis { flex: 1; }
.grid { height: 100%; display: grid; grid-template-columns: minmax(0, 330fr) minmax(0, 300fr) minmax(0, 510fr); grid-template-rows: minmax(0, 300fr) minmax(0, 260fr); gap: 12px; }
.img { width: 100%; flex: 1; min-height: 0; }
.vc { flex: 1; display: flex; flex-direction: column; justify-content: center; padding-bottom: 14px; }
.verdict { font-size: 30px; font-weight: 800; color: #fff; background: var(--warn); border-radius: 6px; padding: 8px 10px; text-align: center; margin-bottom: 16px; }
.verdict.nor { background: var(--ok); }
.prob-row { display: flex; justify-content: space-between; font-size: 17px; margin-top: 10px; }
.prob-row b { font-size: 18px; }
.pbar { position: relative; height: 12px; background: var(--track-2); border-radius: 6px; margin: 4px 0 8px; }
.pfill { height: 100%; background: var(--warn); border-radius: 6px; }
.th { position: absolute; top: -4px; width: 2px; height: 20px; background: var(--ink); }
.c-torque { grid-column: 1 / 3; }
.m-sub { font-size: 17px; font-weight: 700; margin-top: 4px; }
.m-sub.second { margin-top: 18px; }
.m-hint { font-size: 14px; font-weight: 400; color: var(--text-2); margin-left: 10px; }
.wbar { display: flex; height: 30px; border-radius: 6px; overflow: hidden; margin-top: 8px; background: var(--track); }
.wseg { height: 100%; display: flex; align-items: center; padding-left: 12px; color: #fff; font-size: 16px; font-weight: 700; white-space: nowrap; overflow: hidden; }
.w-vis { background: var(--nav-bg); }
.w-tq { background: var(--tq-weight); }
.w-legend { display: flex; gap: 22px; font-size: 15px; color: var(--text-2); margin-top: 6px; }
.sw { display: inline-block; width: 14px; height: 12px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
.single { display: grid; grid-template-columns: 140px 1fr 64px 58px; align-items: center; gap: 10px; margin-top: 10px; font-size: 16px; }
.single.unused { opacity: .45; }
.s-name { white-space: nowrap; }
.s-track { position: relative; height: 12px; background: var(--track); border-radius: 6px; }
.s-fill { height: 100%; background: var(--warn); border-radius: 6px; }
.s-th { position: absolute; top: -4px; width: 2px; height: 20px; background: var(--ink); }
.s-p { text-align: right; font-weight: 700; }
.tag { text-align: center; }
</style>
