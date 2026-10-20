<template>
  <div class="workspace-entry">
    <header class="platform-header">
      <div class="platform-brand">
        <span class="platform-name">增材制造自适应调控与智能运维平台</span>
        <span class="platform-version">v1.0</span>
      </div>
      <span class="header-caption">设备工作区</span>
    </header>

    <section class="entry-content" aria-labelledby="workspace-title">
      <div class="entry-heading">
        <div>
          <span class="section-label">工艺工作区</span>
          <h1 id="workspace-title">选择制造工艺</h1>
          <p>按工艺进入设备监测、过程调控与运维工作区。</p>
        </div>
        <el-dropdown trigger="click" placement="bottom-end" @command="handleProcessCommand">
          <button type="button" class="process-switch" aria-label="切换工艺">
            <span>切换工艺</span><span aria-hidden="true">⌄</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu class="process-menu">
              <el-dropdown-item
                v-for="(workspace, index) in workspaces"
                :key="workspace.type"
                :command="index"
                class="process-option"
                :class="{ selected: index === activeIndex }"
              >
                <span class="option-code">{{ workspace.code }}</span>
                <span>{{ workspace.name }}</span>
                <span class="option-mark" aria-hidden="true">{{ index === activeIndex ? '✓' : '' }}</span>
              </el-dropdown-item>
              <el-dropdown-item command="expand" divided class="process-option">
                <span class="option-code" aria-hidden="true">＋</span><span>扩展工艺</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div class="process-selector">
        <!-- 当前工艺居中完整展示，工艺切换与扩展操作统一收进选单。 -->
        <div
          id="process-track"
          ref="processTrack"
          class="process-track"
          tabindex="0"
          role="region"
          aria-label="已接入工艺，可使用左右方向键浏览"
          @scroll="updateActiveProcess"
          @keydown="handleTrackKey"
        >
          <article
            v-for="(workspace, index) in workspaces"
            :key="workspace.type"
            class="process-module"
            :aria-label="`${workspace.code} 工艺主展示`"
            :inert="index !== activeIndex"
            :aria-hidden="index !== activeIndex"
          >
            <div class="module-topline">
              <span class="module-index">当前工艺 · {{ String(index + 1).padStart(2, '0') }}</span>
              <span>{{ workspace.category }}</span>
            </div>
            <div class="process-code">{{ workspace.code }}</div>
            <h2>{{ workspace.name }}</h2>
            <p class="workspace-description">{{ workspace.description }}</p>
            <!-- 导航不触发硬件初始化或采集。 -->
            <router-link :to="`/${workspace.type}/dashboard`" class="workspace-action" :aria-label="`进入 ${workspace.code} 工作区`">
              <span>进入 {{ workspace.code }} 工作区</span><span aria-hidden="true">→</span>
            </router-link>
          </article>
        </div>
      </div>
      <div class="process-navigation" aria-label="工艺浏览控制">
        <button type="button" aria-label="向左浏览工艺" aria-controls="process-track" :disabled="activeIndex === 0" @click="scrollProcesses(-1)">←</button>
        <span class="process-count" aria-live="polite">{{ activeWorkspace.code }} · {{ activeIndex + 1 }} / {{ workspaces.length }}</span>
        <button type="button" aria-label="向右浏览工艺" aria-controls="process-track" :disabled="activeIndex === workspaces.length - 1" @click="scrollProcesses(1)">→</button>
      </div>
    </section>

    <el-dialog v-model="extensionVisible" title="扩展工艺" width="440px" class="process-extension-dialog" align-center>
      <p class="extension-copy">当前已接入 SLM 与 SLS。此处预留新工艺入口，完成接入后，可通过工艺选单或左右切换进入。</p>
      <template #footer><el-button @click="extensionVisible = false">关闭</el-button></template>
    </el-dialog>

    <footer class="platform-footer">
      <span>自适应调控 · 智能运维</span>
      <span>平台版本 v1.0</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const processTrack = ref(null)
const extensionVisible = ref(false)
const activeIndex = ref(0)
const activeWorkspace = computed(() => workspaces[activeIndex.value])
let resizeObserver

// 主展示一屏一个工艺，触摸/触控板滚动后同步选单与箭头状态。
function updateActiveProcess() {
  const track = processTrack.value
  activeIndex.value = Math.max(0, Math.min(workspaces.length - 1, Math.round(track.scrollLeft / track.clientWidth)))
}
function selectProcess(index) {
  const track = processTrack.value
  track.scrollTo({
    left: index * track.clientWidth,
    behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'
  })
}
function handleProcessCommand(command) {
  if (command === 'expand') extensionVisible.value = true
  else selectProcess(command)
}
function scrollProcesses(direction) {
  selectProcess(Math.max(0, Math.min(workspaces.length - 1, activeIndex.value + direction)))
}
function handleTrackKey(event) {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
  event.preventDefault()
  scrollProcesses(event.key === 'ArrowLeft' ? -1 : 1)
}
onMounted(() => {
  // 改变窗口尺寸时对齐当前工艺，避免再次出现半张卡片。
  resizeObserver = new ResizeObserver(() => {
    const track = processTrack.value
    track.scrollTo({ left: activeIndex.value * track.clientWidth, behavior: 'instant' })
  })
  resizeObserver.observe(processTrack.value)
})
onBeforeUnmount(() => resizeObserver.disconnect())

// 只列出当前已经接入的工作区能力，设备状态在进入设备群后查询。
const workspaces = [
  {
    type: 'slm', code: 'SLM', category: '金属粉末成形',
    name: '选择性激光熔化',
    description: '面向金属增材制造的设备监测、成形质量分析与闭环调控。',
  },
  {
    type: 'sls', code: 'SLS', category: '高分子粉末成形',
    name: '选择性激光烧结',
    description: '面向高分子增材制造的运行状态监测、健康诊断与维护管理。',
  }
]
</script>

<style scoped>
.workspace-entry, .workspace-entry * { box-sizing: border-box; }
.workspace-entry { min-height: 100dvh; display: flex; flex-direction: column; background: var(--am-page-bg); color: var(--am-text); }
.platform-header { display: flex; align-items: center; justify-content: space-between; gap: 24px; min-height: 76px; padding: 20px 40px; background: var(--am-nav-bg); color: var(--am-nav-text); border-bottom: 1px solid var(--am-nav-line); }
.platform-brand { display: flex; align-items: baseline; gap: 16px; }
.platform-name { font-size: 18px; line-height: 1.6; font-weight: 600; }
.platform-version, .header-caption { font-size: 12px; color: var(--am-nav-text-2); white-space: nowrap; }
.entry-content { width: min(960px, 100%); margin: auto; padding: 56px 40px; }
.entry-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 28px; }
.section-label { font-size: 12px; color: var(--am-text-2); letter-spacing: 1px; }
h1 { margin: 10px 0 12px; font-size: 28px; font-weight: 600; line-height: 1.4; }
.entry-heading p { margin: 0; font-size: 14px; color: var(--am-text-2); line-height: 1.8; }
.process-switch { display: flex; align-items: center; gap: 20px; min-height: 36px; padding: 8px 14px; border: 1px solid var(--am-card-border); border-radius: 2px; background: var(--am-card-bg); color: var(--am-text); font: inherit; font-size: 13px; cursor: pointer; white-space: nowrap; }
.process-switch:hover { border-color: var(--am-accent); color: var(--am-accent); }
:global(.process-menu .process-option) { min-height: 40px; gap: 12px; font-size: 13px; }
:global(.process-menu .process-option.selected) { color: var(--am-accent); background: var(--am-accent-soft); }
:global(.process-menu .option-code) { display: inline-block; min-width: 36px; font-weight: 500; }
:global(.process-menu .option-mark) { width: 14px; margin-left: auto; }
.process-navigation { display: flex; justify-content: center; align-items: center; gap: 20px; margin-top: 20px; }
.process-count { min-width: 88px; text-align: center; font-size: 12px; font-variant-numeric: tabular-nums; color: var(--am-text-2); }
.process-navigation button { width: 36px; height: 32px; background: transparent; border: 1px solid var(--am-card-border); color: var(--am-text); font-size: 18px; cursor: pointer; }
.process-navigation button:disabled { opacity: 0.35; cursor: default; }
.process-navigation button:not(:disabled):hover { border-color: var(--am-accent); color: var(--am-accent); }
.process-selector { min-width: 0; }
.process-track { display: flex; min-width: 0; overflow-x: auto; overscroll-behavior-x: contain; scroll-snap-type: x mandatory; scrollbar-width: none; }
.process-track::-webkit-scrollbar { display: none; }
/* 工艺卡片正文居中，顶部工艺编号和类别保留两端对齐。 */
.process-module { text-align: center; flex: 0 0 100%; min-width: 0; padding: 28px 32px; display: flex; flex-direction: column; min-height: 380px; background: var(--am-card-bg); border: 1px solid var(--am-card-border); border-top: 3px solid var(--am-accent); scroll-snap-align: start; scroll-snap-stop: always; }
.module-topline { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding-bottom: 18px; margin-bottom: 28px; border-bottom: 1px solid var(--am-card-border-2); font-size: 12px; color: var(--am-text-2); }
.module-index { font-variant-numeric: tabular-nums; letter-spacing: 1px; }
.process-code { font-size: 44px; font-weight: 500; letter-spacing: 2px; line-height: 1.2; color: var(--am-primary); }
h2 { font-size: 20px; font-weight: 600; margin: 16px 0 10px; }
.workspace-description { min-height: 48px; margin: 0 0 32px; font-size: 13px; line-height: 1.8; color: var(--am-text-2); }
.workspace-action { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: auto; align-self: center; min-width: 220px; padding: 12px 16px; background: var(--am-accent); font-size: 13px; font-weight: 500; color: var(--am-card-bg); text-decoration: none; }
.workspace-action:hover { background: var(--am-primary); }
.workspace-action:focus-visible, button:focus-visible, .process-track:focus-visible { outline: 2px solid var(--am-accent); outline-offset: -2px; }
.extension-copy { margin: 0; line-height: 1.9; color: var(--am-text); }
:global(.process-extension-dialog) { max-width: calc(100vw - 32px); }
.platform-footer { display: flex; justify-content: space-between; gap: 16px; padding: 20px 40px; border-top: 1px solid var(--am-card-border); color: var(--am-text-2); font-size: 12px; }
@media (max-width: 600px) {
  .platform-header { padding: 20px; }
  .platform-brand { flex-wrap: wrap; gap: 4px 12px; }
  .platform-name { font-size: 16px; }
  .header-caption { display: none; }
  .entry-content { padding: 32px 16px; }
  .entry-heading { align-items: flex-start; flex-direction: column; gap: 16px; margin-bottom: 20px; }
  h1 { font-size: 24px; }
  .process-module { padding: 24px; min-height: 360px; }
  .module-topline { gap: 8px; font-size: 11px; margin-bottom: 20px; }
  .process-code { font-size: 40px; }
  h2 { font-size: 18px; }
  .workspace-action { align-self: stretch; min-width: 0; padding: 12px; gap: 8px; font-size: 13px; }
  .platform-footer { padding: 20px 16px; }
}
</style>
