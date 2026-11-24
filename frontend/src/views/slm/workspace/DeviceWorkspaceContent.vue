<template>
  <div class="replay-workspace">
    <header class="workspace-heading">
      <div><h1>{{ device.name }}</h1><p>{{ replay.manifest?.task.name }}</p></div>
      <router-link to="/slm/dashboard">返回设备总览</router-link>
    </header>
    <div v-if="frame" class="replay-summary">
      <button v-if="!caseConfig" class="retry-button" :disabled="replay.loading" @click="replay.open()">刷新数据</button>
      <span>{{ replay.statusLabel || (replay.playing ? '采集中' : '采集暂停') }}</span>
      <span class="playback-time">{{ frame.time }}</span><span>第 {{ frame.layer ?? '—' }} 层 · {{ frame.phase }}</span>
      <router-link :to="{ path: '/slm/settings', query: { device: deviceId } }">系统设置</router-link>
    </div>
    <div v-if="replay.error" class="replay-error" role="alert">{{ replay.error }} <button class="retry-button" :disabled="replay.loading" @click="replay.open({ autoplay: true })">重新加载</button></div>
    <div v-if="!frame && !replay.error" class="waiting">正在接入设备数据…</div>
    <nav class="workspace-tabs" aria-label="设备功能页面">
      <router-link v-for="item in tabs" :key="item.key" :to="{ path: route.path, query: { tab: item.key } }" :class="{ active: tab === item.key }" :aria-current="tab === item.key ? 'page' : undefined">{{ item.label }}</router-link>
    </nav>
    <template v-if="frame && tab === 'status'">
      <div class="forming-root forming-replay"><Access /></div>
      <div class="status-details">
        <section class="replay-card">
          <h2>故障诊断</h2>
          <template v-if="frame?.trace"><p>{{ frame.trace.recordDiagnosis ? '设备档案：' : `第 ${frame.trace.layer} 层：` }}{{ diagnosis.conclusion }}</p><p>{{ diagnosisAdvice.join('；') || '暂无处置建议' }}</p></template>
          <p v-else>当前时刻尚无可用溯源结果。</p>
          </section>
        <section class="replay-card">
          <h2>报警记录</h2>
          <div v-if="frame?.access.alarms.length" class="alarm-list"><div v-for="a in frame.access.alarms" :key="a.time + a.text"><time>{{ a.time }}</time><span>{{ a.text }}</span></div></div>
          <p v-else>暂无已接入的报警记录。</p>
        </section>
      </div>
      <!-- 每台设备均提供维护面板，详情按当前设备与所属单位展示。 -->
      <MaintenanceDecisionPanel :device-id="deviceId" :device-name="device.name" :organization-label="device.owner === '华科' ? '华科' : '7103（铂力特）'" />
    </template>
    <template v-else-if="frame && tab === 'control'">
      <RegionControlPanel :frame="frame" :slice="currentSlice" :blocked="!!replay.error" />
    </template>
    <template v-else-if="frame">
      <div v-if="frame" class="analysis-time">
        <span>{{ replay.source === 'device-record' ? '档案采样' : '当前采集' }}：第 {{ frame.layer ?? '—' }} 层</span>
        <span>当前可用结果：{{ frame[tab]?.available === false ? '未接入' : frame[tab] ? `第 ${frame[tab].layer} 层` : '尚未到达' }}</span>
      </div>
      <div class="forming-root forming-replay"><component :is="views[tab]" /></div>
    </template>
  </div>
</template>
<script setup>
import { traceDiagnosis } from '../forming/traceDiagnosis'
import { slmTabs, slmTab } from '../../../utils/slmNavigation'
import { computed, onMounted, onUnmounted, provide } from 'vue'
import { useRoute } from 'vue-router'
import { useReplayStore, replayCaseForDevice } from '../../../stores/replay'
import { useSlmDeviceStore } from '../../../stores/slmDevices'
import Access from '../forming/views/Access.vue'
import Recognition from '../forming/views/Recognition.vue'
import Trace from '../forming/views/Trace.vue'
import { createRecordSession } from './recordSession'
import RegionControlPanel from '../../../components/slm/RegionControlPanel.vue'
import { regionSlice } from '../../../components/slm/regionControl'
import MaintenanceDecisionPanel from '../../../components/common/MaintenanceDecisionPanel.vue'
import '../forming/forming.css'
import './workspace.css'
const props = defineProps({ deviceId: { type: String, required: true } })
const caseConfig = replayCaseForDevice(props.deviceId)
const replay = caseConfig ? useReplayStore(caseConfig.id) : createRecordSession(props.deviceId)
const device = computed(() => caseConfig || replay.device || { name: props.deviceId, owner: '' })
onUnmounted(() => { if (!caseConfig) replay.dispose() })
const devices = useSlmDeviceStore()
const route = useRoute()
const tabs = slmTabs
const tab = computed(() => slmTab(route.query.tab).key)
const views = { recognition: Recognition, trace: Trace }
const frame = computed(() => replay.snapshot)
// 摘要与诊断页共用结论，不能再显示原始结果中的旧说明。
const diagnosis = computed(() => traceDiagnosis(frame.value?.trace))
const diagnosisAdvice = computed(() => (frame.value?.trace?.actions || []).filter(action => action.trim() !== '复核超限区域与识别结果'))
const currentSlice = computed(() => frame.value?.slice || regionSlice(frame.value))
provide('formingEmbedded', true)
provide('formingReplay', replay)
onMounted(() => {
  localStorage.setItem('slmSelectedDeviceId', props.deviceId)
  replay.open()
  if (!devices.getDeviceById(props.deviceId)) devices.loadDevicesFromBackend().catch(() => { /* 目录错误由设备目录展示，不覆盖已成功加载的工作区。 */ })
})
</script>
<style scoped>
.replay-workspace { display: flex; flex-direction: column; gap: 16px; max-width: 1600px; margin: auto; min-width: 0; }
.workspace-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
h1 { font-size: 24px; margin: 0; } h2 { margin: 0 0 14px; font-size: 16px; }
p { line-height: 1.7; } .workspace-heading p { font-size: 13px; color: var(--am-text-2); margin: 6px 0 0; }
a { color: var(--am-accent); }
.replay-card { padding: 16px; border: 1px solid var(--am-card-border); background: var(--am-card-bg); border-radius: 4px; min-width: 0; }
.workspace-tabs { display: none; flex-wrap: wrap; align-items: center; gap: 10px; }
.playback-time { font-variant-numeric: tabular-nums; margin-left: auto; }
.workspace-tabs a { padding: 8px 14px; border: 1px solid var(--am-card-border); text-decoration: none; font-size: 14px; }
.replay-summary { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; font-size: 13px; color: var(--am-text-2); }
.replay-summary .playback-time { margin-left: 0; }
.replay-summary a { margin-left: auto; }
.analysis-time { display: flex; flex-wrap: wrap; gap: 16px; color: var(--am-text-2); font-size: 13px; }
.forming-replay { min-width: 0; width: 100%; }
small, .data-note, .sample-times { font-size: 12px; font-weight: 400; color: var(--am-text-2); }
.alarm-list > div { display: flex; flex-wrap: wrap; gap: 10px 20px; padding: 12px 0; border-bottom: 1px solid var(--am-card-border-2); font-size: 14px; }
.alarm-list time { color: var(--am-text-2); flex: none; }
.replay-error { color: var(--am-danger); padding: 12px; border: 1px solid var(--am-danger); }
.waiting { padding: 30px; text-align: center; }
@media (max-width: 600px) { .workspace-heading { align-items: flex-start; } h1 { font-size: 20px; } .playback-time { margin-left: 0; } }
/* 桌面直接使用侧栏，窄屏保留页内入口，减少重复导航占位。 */
.workspace-tabs .active { color: white; background: var(--am-accent); border-color: var(--am-accent); }
.status-details { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.control-context dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin: 0; }
.control-context dt { color: var(--am-text-2); font-size: 12px; margin-bottom: 6px; }
.control-context dd { margin: 0; font-size: 14px; line-height: 1.6; overflow-wrap: anywhere; }
@media (max-width: 767px) {
  .workspace-tabs { display: flex; gap: 6px; }
  .workspace-tabs a { flex: 1 0 auto; text-align: center; padding: 8px 10px; font-size: 13px; }
  .status-details, .control-context dl { grid-template-columns: minmax(0, 1fr); }
  .workspace-heading { flex-wrap: wrap; }
}
</style>

<style scoped>
.retry-button { margin-left: 12px; padding: 5px 12px; background: var(--am-card-bg); border: 1px solid currentColor; color: inherit; cursor: pointer; }
</style>
