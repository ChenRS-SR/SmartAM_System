<template>
  <section class="replay-settings" :class="{ unavailable: !enabled }" aria-label="历史回放设置">
    <div class="replay-heading"><h3>历史回放</h3><span>{{ enabled ? `当前设备：${caseConfig.name}` : '当前设备不支持历史回放' }}</span></div>
    <fieldset :disabled="locked" :aria-disabled="locked" aria-label="历史回放控制">
      <div class="playback-row">
        <button class="primary" @click="replay.playing ? replay.pause() : replay.play()">{{ enabled && replay.playing ? '暂停回放' : '播放回放' }}</button>
        <button :disabled="!frame" @click="replay.step(-1)">上一层</button>
        <button :disabled="!frame" @click="replay.step(1)">下一层</button>
        <label>倍速 <select :value="enabled ? replay.speed : 1" aria-label="回放倍速" @change="replay.setSpeed($event.target.value)"><option v-for="n in [1, 5, 10, 30, 60]" :key="n" :value="n">{{ n }}×</option></select></label>
        <label>定位层 <select aria-label="定位层" :value="frame?.layer" @change="replay.seekLayer($event.target.value)"><option v-for="r in replay.manifest?.layers || []" :key="r.layer" :value="r.layer">{{ r.layer }}</option></select></label>
        <span class="playback-time">{{ frame?.time || '—' }}</span>
        <span v-if="frame">第 {{ frame.layer }} 层 · {{ frame.phase }}</span>
      </div>
      <input class="timeline" aria-label="回放时间进度" type="range" min="0" :max="replay.manifest?.duration || 1" step="1" :value="frame?.offset ?? 0" @change="replay.seek($event.target.value)" />
      <div class="segment-row">
        <button v-for="(s, i) in replay.manifest?.segments || []" :key="s.firstLayer" :class="{ selected: frame?.segment === i }" @click="replay.seek(s.offset)">{{ s.firstLayer }}–{{ s.lastLayer }} 层</button>
      </div>
    </fieldset>
    <template v-if="enabled">
      <p class="replay-description">按历史时间播放，缺少完整数据的区段自动跳过；所有业务页面共用此处设置。</p>
      <details v-if="replay.manifest"><summary>数据时间说明</summary>{{ replay.manifest.timeNotes }}</details>
      <p v-if="replay.error" role="alert">{{ replay.error }} <button @click="replay.manifest ? replay.play() : replay.open()">重新加载</button></p>
      <router-link class="return-link" :to="`/slm/device/${deviceId}?tab=access`">返回当前设备</router-link>
    </template>
    <p v-else class="replay-description">仅在对应回放设备的系统设置中启用。</p>
  </section>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useReplayStore, REPLAY_CASE_ID, replayCaseForDevice } from '../../stores/replay'
const props = defineProps({ deviceId: { type: String, required: true } })
const caseConfig = computed(() => replayCaseForDevice(props.deviceId))
const replay = useReplayStore(caseConfig.value?.id || REPLAY_CASE_ID)
const enabled = computed(() => !!caseConfig.value)
const frame = computed(() => enabled.value ? replay.snapshot : null)
const locked = computed(() => !enabled.value || !replay.manifest || replay.loading)
// 设置页沿用设备时间轴；普通设备不能启动回放，也不会为它加载案例。
watch([enabled, () => replay.playing], ([active]) => {
  if (active) replay.open()
  else if (replay.playing) replay.pause()
}, { immediate: true })
</script>

<style scoped>
.replay-settings { padding: 20px; margin-bottom: 20px; border: 1px solid var(--am-card-border); background: var(--am-card-bg); border-radius: 4px; min-width: 0; }
.replay-heading { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin-bottom: 16px; }
h3 { margin: 0; font-size: 17px; }
.replay-heading span,.replay-description,details { color: var(--am-text-2); font-size: 12px; line-height: 1.7; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
fieldset:disabled { opacity: .45; }
.playback-row,.segment-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; font-size: 13px; }
button,select { border: 1px solid var(--am-card-border); background: var(--am-card-bg); color: var(--am-text); padding: 7px 10px; border-radius: 3px; font: inherit; cursor: pointer; }
button.primary { background: var(--am-accent); color: white; }
fieldset:disabled button,fieldset:disabled select,fieldset:disabled input { cursor: not-allowed; }
.timeline { width: 100%; margin: 16px 0; accent-color: var(--am-accent); }
.selected { border-color: var(--am-accent); }
.playback-time { margin-left: auto; font-variant-numeric: tabular-nums; }
.return-link { display: inline-block; margin-top: 16px; color: var(--am-accent); font-size: 13px; }
.unavailable h3 { color: var(--am-text-3); }
@media(max-width:600px) { .playback-time { margin-left: 0; } .replay-settings { padding: 12px; } }
</style>
