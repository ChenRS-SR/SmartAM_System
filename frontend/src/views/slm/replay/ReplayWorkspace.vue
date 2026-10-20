<template>
  <div class="replay-workspace">
    <header class="workspace-heading">
      <div><h1>{{ caseConfig.name }}</h1><p>{{ replay.manifest?.task.name }}</p></div>
      <router-link to="/slm/dashboard">返回设备群</router-link>
    </header>
    <div v-if="frame" class="replay-summary">
      <span>{{ replay.playing ? '采集中' : '采集暂停' }}</span>
      <span class="playback-time">{{ frame.time }}</span><span>第 {{ frame.layer }} 层 · {{ frame.phase }}</span>
      <router-link :to="{ path: '/slm/settings', query: { device: deviceId } }">系统设置</router-link>
    </div>
    <div v-if="replay.error" class="replay-error" role="alert">{{ replay.error }} <router-link :to="{ path: '/slm/settings', query: { device: deviceId } }">前往系统设置重试</router-link></div>
    <div v-if="!replay.manifest && !replay.error" class="waiting">正在接入设备数据…</div>
    <nav class="workspace-tabs" aria-label="设备功能页面">
      <router-link v-for="item in tabs" :key="item.key" :to="{ path: route.path, query: { tab: item.key } }" :class="{ active: tab === item.key }">{{ item.label }}</router-link>
    </nav>
    <template v-if="tab === 'status'">
      <section class="replay-card">
        <h2>设备状态参数 <small>{{ frame?.time }}</small></h2>
        <div v-if="frame" class="parameter-grid">
          <div v-for="p in frame.parameters" :key="p.name"><span>{{ p.name }}</span><strong>{{ format(p.value) }} <small>{{ p.unit }}</small></strong></div>
        </div>
        <p class="data-note">按时间取最近已到达的原始采样，零值保留原值。</p>
        <div v-if="frame" class="sample-times"><span v-for="(sample, key) in frame.samples" :key="key">{{ channelNames[key] }}：{{ sample ? `${sample.time}（${sample.age} 秒前更新）` : '暂无采样' }}</span></div>
      </section>
      <section class="replay-card">
        <h2>异常溯源分析</h2>
        <template v-if="frame?.trace"><p>第 {{ frame.trace.layer }} 层：{{ frame.trace.conclusion }}</p><p>支撑区域：{{ frame.trace.support.join('、') || '无' }}；{{ frame.trace.actions.join('；') || '暂无处置建议' }}</p></template>
        <p v-else>当前时刻尚无可用溯源结果。</p>
        <p class="data-note">装备健康评级暂无数据。</p>
      </section>
      <section class="replay-card">
        <h2>报警记录</h2>
        <div v-if="frame?.access.alarms.length" class="alarm-list"><div v-for="a in frame.access.alarms" :key="a.time + a.text"><time>{{ a.time }}</time><span>{{ a.text }}</span></div></div>
        <p v-else>当前暂无报警记录。</p>
      </section>
    </template>
    <template v-else-if="tab === 'control'">
      <section class="replay-card">
        <h2>调控分析依据 <small>当前分析结果</small></h2>
        <p>采集时间：{{ frame?.time || '等待数据…' }}；当前层：{{ frame?.layer ?? '—' }}</p>
        <p>识别：{{ frame?.recognition ? `第 ${frame.recognition.layer} 层 · ${frame.recognition.label}` : '等待数据到齐' }}</p>
        <p>溯源：{{ frame?.trace ? `第 ${frame.trace.layer} 层 · ${frame.trace.conclusion}` : '等待图像与参照层数据' }}</p>
        <p>处置建议：{{ frame?.trace?.actions.join('；') || '暂无' }}</p>
      </section>
      <SlmControlPanel v-if="frame" historical :replay-context="frame" />
    </template>
    <template v-else>
      <div v-if="frame" class="analysis-time">
        <span>当前采集：第 {{ frame.layer }} 层</span>
        <span v-if="tab !== 'access'">当前可用结果：{{ frame[tab] ? `第 ${frame[tab].layer} 层` : '尚未到达' }}</span>
      </div>
      <section v-if="replay.manifest && !replay.manifest.capabilities[tab]" class="replay-card"><h2>{{ tab === 'recognition' ? '异常识别' : '异常溯源' }}</h2><p>该设备尚未接入{{ tab === 'recognition' ? '识别' : '溯源' }}结果，采集数据可在数据接入页查看。</p></section>
      <div v-else class="forming-root forming-replay"><component :is="views[tab]" /></div>
    </template>
  </div>
</template>
<script setup>
import { computed, onMounted, provide } from 'vue'
import { useRoute } from 'vue-router'
import { useReplayStore, replayCaseForDevice } from '../../../stores/replay'
import { useSlmDeviceStore } from '../../../stores/slmDevices'
import Access from '../forming/views/Access.vue'
import Recognition from '../forming/views/Recognition.vue'
import Trace from '../forming/views/Trace.vue'
import SlmControlPanel from '../../../components/slm/SlmControlPanel.vue'
import '../forming/forming.css'
const props = defineProps({ deviceId: { type: String, required: true } })
const caseConfig = replayCaseForDevice(props.deviceId)
const replay = useReplayStore(caseConfig.id)
const devices = useSlmDeviceStore()
const route = useRoute()
const tabs = [{ key: 'status', label: '设备监测' }, { key: 'access', label: '数据接入' }, { key: 'recognition', label: '异常识别' }, { key: 'trace', label: '异常溯源' }, { key: 'control', label: '闭环调控' }]
const tab = computed(() => tabs.some(t => t.key === route.query.tab) ? route.query.tab : 'access')
const views = { access: Access, recognition: Recognition, trace: Trace }
const frame = computed(() => replay.snapshot)
const channelNames = { torque: '扭矩', env_a: '温度与压力', env_b: '氧含量与物位', env_c: '气体流量与风机' }
const format = value => value == null ? '—' : Number.isInteger(value) ? value : Number(value.toFixed(3))
provide('formingEmbedded', true)
provide('formingReplay', replay)
onMounted(() => {
  localStorage.setItem('slmSelectedDeviceId', props.deviceId)
  replay.open()
  if (!devices.getDeviceById(props.deviceId)) devices.loadDevicesFromBackend().catch(e => { replay.error = e.message })
})
</script>
<style scoped>
.replay-workspace { display: flex; flex-direction: column; gap: 16px; max-width: 1600px; margin: auto; min-width: 0; }
.workspace-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
h1 { font-size: 24px; margin: 0; } h2 { margin: 0 0 14px; font-size: 18px; }
p { line-height: 1.7; } .workspace-heading p { font-size: 13px; color: var(--am-text-2); margin: 6px 0 0; }
a { color: var(--am-accent); }
.replay-card { padding: 16px; border: 1px solid var(--am-card-border); background: var(--am-card-bg); border-radius: 6px; min-width: 0; }
.workspace-tabs { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
button, select { border: 1px solid var(--am-card-border); background: var(--am-card-bg); color: var(--am-text); padding: 7px 10px; font: inherit; font-size: 13px; border-radius: 3px; cursor: pointer; }
button:disabled { opacity: .5; cursor: default; }
button.primary, .workspace-tabs .active { background: var(--am-accent); color: white; border-color: var(--am-accent); }
.playback-row label, .playback-row > span { font-size: 13px; }
.playback-time { font-variant-numeric: tabular-nums; margin-left: auto; }
.timeline { width: 100%; margin: 16px 0; accent-color: var(--am-accent); }
.segment-row { color: var(--am-text-2); font-size: 12px; }
.segment-row .selected { border-color: var(--am-accent); color: var(--am-accent); }
.workspace-tabs a { padding: 8px 14px; border: 1px solid var(--am-card-border); text-decoration: none; font-size: 14px; }
.replay-summary { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; font-size: 13px; color: var(--am-text-2); }
.replay-summary .playback-time { margin-left: 0; }
.replay-summary a { margin-left: auto; }
.analysis-time { display: flex; flex-wrap: wrap; gap: 16px; color: var(--am-text-2); font-size: 13px; }
.forming-replay { min-width: 0; width: 100%; }
.parameter-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.parameter-grid > div { display: flex; flex-direction: column; gap: 12px; padding: 14px; background: var(--am-card-bg-2); border: 1px solid var(--am-card-border-2); }
.parameter-grid span { color: var(--am-text-2); font-size: 13px; }
.parameter-grid strong { font-size: 22px; font-variant-numeric: tabular-nums; }
small, .data-note, .sample-times { font-size: 12px; font-weight: 400; color: var(--am-text-2); }
.sample-times { display: flex; flex-wrap: wrap; gap: 8px 20px; }
.alarm-list > div { display: flex; flex-wrap: wrap; gap: 10px 20px; padding: 12px 0; border-bottom: 1px solid var(--am-card-border-2); font-size: 14px; }
.alarm-list time { color: var(--am-text-2); flex: none; }
.replay-error { color: var(--am-danger); padding: 12px; border: 1px solid var(--am-danger); }
.waiting { padding: 30px; text-align: center; }
@media (max-width: 600px) { .workspace-heading { align-items: flex-start; } h1 { font-size: 20px; } .playback-time { margin-left: 0; } }
</style>
