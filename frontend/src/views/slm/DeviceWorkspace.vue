<template>
  <!-- 所有设备共享相同模块结构，仅由数据适配器区分数据来源。 -->
  <DeviceWorkspaceContent :key="route.params.deviceId" :device-id="route.params.deviceId" />
</template>
<script setup>
import { useRoute } from 'vue-router'
import { watch } from 'vue'
import DeviceWorkspaceContent from './workspace/DeviceWorkspaceContent.vue'
import { REPLAY_CASES, useReplayStore } from '../../stores/replay'
const route = useRoute()
const sessions = REPLAY_CASES.map(item => ({ deviceId: item.deviceId, store: useReplayStore(item.id) }))
watch([() => route.params.deviceId, ...sessions.map(s => () => s.store.playing)], ([id]) => {
  // 离开工作区时路由参数已清空，不能因此暂停设备群或系统设置中的播放。
  if (route.name !== 'SLMDeviceDashboard') return
  for (const session of sessions) if (id !== session.deviceId && session.store.playing) session.store.suspend()
}, { immediate: true })
</script>
