<template>
  <aside id="primary-sidebar" class="sidebar" :class="{ collapsed }" aria-label="系统侧边栏">
    <div v-if="!collapsed" class="brand" title="增材制造自适应调控与智能运维平台 v1.0">
      <div class="brand-copy">
        <strong>增材制造自适应调控<br />与智能运维平台</strong>
        <span>v1.0</span>
      </div>
    </div>

    <div class="workspace-context">
      <el-tooltip content="切换设备类型" placement="right" :disabled="!collapsed">
        <button class="workspace-switch" aria-label="切换设备类型" @click="switchWorkspace">
          <span class="workspace-code">{{ deviceType.toUpperCase() }}</span>
          <span v-if="!collapsed" class="workspace-label">设备工作区</span>
          <span v-if="!collapsed" class="switch-label">切换</span>
        </button>
      </el-tooltip>
      <div v-if="!collapsed" class="device-context" :title="contextName">
        <span class="context-label">{{ isDevicePage ? '当前设备' : '当前位置' }}</span>
        <span class="context-value">{{ contextName }}</span>
      </div>
    </div>

    <!-- 所有功能均为直达链接；收起时使用短名称，保留完整入口与文字提示。 -->
    <nav class="nav-menu" aria-label="主导航">
        <el-tooltip v-for="item in navItems" :key="item.key" :content="item.name" placement="right" :disabled="!collapsed">
          <router-link
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item) }"
            :aria-label="item.name"
            :aria-current="isActive(item) ? 'page' : undefined"
            @click="$emit('navigate')"
          >
            <span>{{ collapsed ? item.shortName : item.name }}</span>
          </router-link>
        </el-tooltip>
    </nav>

    <div class="sidebar-footer">
      <el-tooltip content="系统设置" placement="right" :disabled="!collapsed">
        <router-link
          :to="settingsLink"
          class="nav-item"
          :class="{ active: route.path === settingsPath }"
          :aria-current="route.path === settingsPath ? 'page' : undefined"
          aria-label="系统设置"
          @click="$emit('navigate')"
        >
          <span>{{ collapsed ? '设置' : '系统设置' }}</span>
        </router-link>
      </el-tooltip>
      <!-- 此状态只描述数据通道，不代表设备在线或正在运行。 -->
      <div class="connection-status" role="status" :title="connectionText" :aria-label="connectionText">
        <span class="status-dot" :class="{ connected }" aria-hidden="true"></span>
        <template v-if="!collapsed">
          <span>数据通道</span>
          <span class="connection-value">{{ connected ? '已连接' : '未连接' }}</span>
        </template>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSlmDeviceStore } from '../stores/slmDevices'
import { useSlsDeviceStore } from '../stores/slsDevices'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  connected: { type: Boolean, default: false }
})
defineEmits(['navigate'])
const route = useRoute()
const router = useRouter()
const slmDevices = useSlmDeviceStore()
const slsDevices = useSlsDeviceStore()
const deviceType = computed(() => String(route.meta.device || ''))
const isDevicePage = computed(() => route.path.startsWith(`/${deviceType.value}/device`))
const devices = computed(() => deviceType.value === 'slm' ? slmDevices : slsDevices)

// 路由参数优先，设备群和设置页的入口沿用上次选中的设备。
const selectedId = computed(() => {
  if (isDevicePage.value && route.params.deviceId) return String(route.params.deviceId)
  if (typeof route.query.device === 'string') return route.query.device
  return localStorage.getItem(`${deviceType.value}SelectedDeviceId`) || ''
})
const contextName = computed(() => {
  if (!isDevicePage.value) return route.path === settingsPath.value ? '系统设置' : '设备群总览'
  const device = devices.value.getDeviceById(selectedId.value)
  return device?.name || selectedId.value || '尚未选择设备'
})
const settingsPath = computed(() => `/${deviceType.value}/settings`)
const settingsLink = computed(() => deviceType.value === 'slm' && selectedId.value
  ? { path: settingsPath.value, query: { device: selectedId.value } } : settingsPath.value)
const devicePath = (tab) => {
  const suffix = selectedId.value ? `/${encodeURIComponent(selectedId.value)}` : ''
  return `/${deviceType.value}/device${suffix}?tab=${tab}`
}
// 导航采用单层平铺结构，收起后以短名称显示，避免引入额外分类层级。
const navItems = computed(() => {
  const items = [
    { key: 'fleet', name: '设备群总览', shortName: '总览', path: `/${deviceType.value}/dashboard` },
    deviceType.value === 'slm'
      ? { key: 'status', name: '设备监测', shortName: '监测', path: devicePath('status'), tab: 'status' }
      : { key: 'device', name: '设备状态监测', shortName: '监测', path: devicePath('status') }
  ]
  // 成形监测目前只有 SLM 实现，SLS 不展示尚未接入的功能。
  if (deviceType.value === 'slm') items.push(
    { key: 'access', name: '数据接入', shortName: '接入', path: devicePath('access'), tab: 'access' },
    { key: 'recognition', name: '异常识别', shortName: '识别', path: devicePath('recognition'), tab: 'recognition' },
    { key: 'trace', name: '异常溯源', shortName: '溯源', path: devicePath('trace'), tab: 'trace' },
    { key: 'control', name: '闭环调控', shortName: '调控', path: devicePath('control'), tab: 'control' }
  )
  return items
})
const isActive = (item) => {
  if (item.tab) return isDevicePage.value && (route.query.tab || 'status') === item.tab
  if (item.key === 'device') return isDevicePage.value
  return route.path === item.path
}
const connectionText = computed(() => `WebSocket 数据通道${props.connected ? '已连接' : '未连接'}；不代表设备运行状态`)
const switchWorkspace = () => {
  localStorage.removeItem('deviceType')
  router.push('/')
}
</script>

<style scoped>
/* 参照设备总览展示图：深蓝底色、纯文字导航、通栏选中背景与金色定位条。
 * 配色限定在侧边栏内，避免影响论文展示页和首页。 */
.sidebar, .sidebar *, .sidebar *::before { box-sizing: border-box; }
.sidebar {
  --am-nav-bg: #1d3557;
  --am-nav-bg-active: #2e4d75;
  --am-nav-hover: #264264;
  --am-nav-text: #dbe4f0;
  --am-nav-text-2: #a6b8cf;
  --am-nav-line: rgba(219, 228, 240, 0.15);
  --sidebar-marker: #f4b942;
  width: 224px;
  flex: none;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--am-nav-bg);
  color: var(--am-nav-text);
  border-right: 1px solid var(--am-nav-line);
  transition: width 160ms ease;
}
.sidebar.collapsed { width: 64px; }
.brand { min-height: 122px; padding: 22px 12px 18px; border-bottom: 1px solid var(--am-nav-line); }
.brand-copy { display: flex; flex-direction: column; align-items: center; gap: 10px; text-align: center; white-space: nowrap; }
.brand-copy strong { font-size: 16px; line-height: 1.6; font-weight: 600; color: #f0f4f8; }
.brand-copy span { padding: 2px 8px; border: 1px solid #9f8038; border-radius: 8px; font-size: 12px; line-height: 1.4; color: var(--sidebar-marker); letter-spacing: 0.4px; }
.workspace-context { padding: 12px 18px 14px; border-bottom: 1px solid var(--am-nav-line); }
.workspace-switch { width: 100%; display: flex; align-items: center; gap: 8px; min-height: 32px; padding: 4px 6px; border: 1px solid var(--am-nav-line); border-radius: 2px; background: transparent; color: inherit; cursor: pointer; font: inherit; }
.workspace-switch:hover { background: var(--am-nav-hover); }
.workspace-code { font-size: 12px; font-weight: 600; letter-spacing: 0.8px; color: #e2eaf2; }
.workspace-label { font-size: 12px; color: var(--am-nav-text-2); }
.switch-label { margin-left: auto; font-size: 11px; color: var(--am-nav-text-2); }
.device-context { margin: 12px 6px 0; display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.context-label { font-size: 11px; color: var(--am-nav-text-2); }
.context-value { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.nav-menu { flex: 1; min-height: 0; overflow-y: auto; padding: 8px 0; }
.nav-item { position: relative; display: flex; align-items: center; min-height: 48px; margin: 0; padding: 12px 24px; border-radius: 0; text-decoration: none; color: var(--am-nav-text); font-size: 15px; line-height: 1.6; white-space: nowrap; transition: background 120ms ease; }
.nav-item:hover { background: var(--am-nav-hover); color: #fff; }
.nav-item.active { background: var(--am-nav-bg-active); color: #fff; font-weight: 600; }
.nav-item.active::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--sidebar-marker); }
.nav-item:focus-visible, .workspace-switch:focus-visible { outline: 2px solid #a8c9e8; outline-offset: -2px; }
.sidebar-footer { padding: 4px 0; border-top: 1px solid var(--am-nav-line); }
.connection-status { display: flex; align-items: center; gap: 8px; padding: 12px 24px; font-size: 11px; color: var(--am-nav-text-2); }
.connection-value { margin-left: auto; }
.status-dot { width: 6px; height: 6px; flex: none; border-radius: 50%; background: #9aabbc; }
.status-dot.connected { background: #79b49b; }
.collapsed .workspace-context { padding: 12px 8px; }
.collapsed .workspace-switch { justify-content: center; padding: 4px 0; }
.collapsed .nav-item { justify-content: center; padding: 10px 0; font-size: 12px; }
.collapsed .connection-status { justify-content: center; }
@media (max-width: 767px) {
  .sidebar { position: fixed; inset: 0 auto 0 0; z-index: 1000; width: 224px; }
  .sidebar.collapsed { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .sidebar, .nav-item { transition: none; }
}
</style>
