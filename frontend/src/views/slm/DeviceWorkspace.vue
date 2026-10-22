<template>
  <!-- 案例设备使用独立只读数据流，不初始化硬件采集。 -->
  <ReplayWorkspace v-if="caseConfig" :key="route.params.deviceId" :device-id="route.params.deviceId" />
  <Dashboard v-else />
</template>
<script setup>
import { useRoute } from 'vue-router'
import { computed, watch } from 'vue'
import Dashboard from './Dashboard.vue'
import ReplayWorkspace from './replay/ReplayWorkspace.vue'
import { REPLAY_CASES, replayCaseForDevice, useReplayStore } from '../../stores/replay'
const route = useRoute()
const caseConfig = computed(() => replayCaseForDevice(route.params.deviceId))
const sessions = REPLAY_CASES.map(item => ({ deviceId: item.deviceId, store: useReplayStore(item.id) }))
watch([() => route.params.deviceId, ...sessions.map(s => () => s.store.playing)], ([id]) => {
  // 离开工作区时路由参数已清空，不能因此暂停设备群或系统设置中的播放。
  if (route.name !== 'SLMDeviceDashboard') return
  for (const session of sessions) if (id !== session.deviceId && session.store.playing) session.store.suspend()
}, { immediate: true })
</script>
