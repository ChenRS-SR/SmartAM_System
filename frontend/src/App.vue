<template>
  <div class="app-wrapper">
    <!-- 侧边栏（设备选择页不显示） -->
    <aside v-if="showSidebar" class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="logo" :class="{ mini: isCollapsed }">
        <template v-if="!isCollapsed">
          <div class="brand-title"><span>增材制造</span><span>异常识别系统</span></div>
          <div class="brand-ver">v1.0</div>
        </template>
        <div v-else class="brand-mini">增材</div>
      </div>
      
      <!-- 设备类型标识 -->
      <div v-if="deviceType && !isCollapsed" class="device-badge" :class="deviceType">
        <el-icon size="14">
          <component :is="deviceTypeIcon" />
        </el-icon>
        <span>{{ deviceType.toUpperCase() }}</span>
      </div>
      
      <!-- 返回按钮 -->
      <div v-if="deviceType && !isCollapsed" class="back-section">
        <el-button text size="small" @click="backToDeviceSelect">
          <el-icon><ArrowLeft /></el-icon>
          切换设备
        </el-button>
      </div>
      
      <nav class="nav-menu">
        <div
          v-for="item in menuItems"
          :key="item.key || item.path"
          class="nav-group"
        >
          <router-link
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item) }"
          >
            <el-icon size="20">
              <component :is="item.icon" />
            </el-icon>
            <span v-show="!isCollapsed" class="nav-text">{{ item.name }}</span>
            <el-icon
              v-if="item.children?.length && !isCollapsed"
              class="nav-caret"
              :class="{ closed: !isGroupOpen(item) }"
              title="展开/收起"
              @click.prevent.stop="toggleGroup(item)"
            ><ArrowDown /></el-icon>
          </router-link>

          <div v-if="item.children?.length && !isCollapsed && isGroupOpen(item)" class="nav-children">
            <router-link
              v-for="child in item.children"
              :key="child.key || child.path"
              :to="child.path"
              class="nav-child"
              :class="{ active: isActive(child) }"
            >
              <span class="nav-child-dot"></span>
              <span class="nav-text">{{ child.name }}</span>
            </router-link>
          </div>
        </div>
      </nav>
      
      <div class="sidebar-footer">
        <div class="connection-status" :class="{ connected: store.connected }" title="WebSocket 实时数据流连接状态">
          <span class="status-dot"></span>
          <span v-show="!isCollapsed" class="status-text">
            {{ store.connected ? '数据流已连接' : '数据流断开' }}
          </span>
        </div>
        <div v-show="!isCollapsed" class="connection-hint">
          WebSocket {{ store.connected ? '实时数据正常' : '尝试重连中...' }}
        </div>
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="main-content" :class="{ 'full-width': !showSidebar }">
      <header v-if="showSidebar" class="header">
        <div class="header-left">
          <el-button text @click="isCollapsed = !isCollapsed">
            <el-icon size="20"><Fold v-if="!isCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <span class="page-title">{{ $route.meta.title || 'SmartAM System' }}</span>
        </div>
        <div class="header-right">
          <LangSwitch />
          <ThemeToggle />
          <el-tooltip content="全屏" placement="bottom">
            <el-button text @click="toggleFullscreen">
              <el-icon size="20"><FullScreen /></el-icon>
            </el-button>
          </el-tooltip>
          <el-dropdown>
            <el-button text>
              <el-icon size="20"><User /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人设置</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      
      <div class="page-container" :class="{ 'no-padding': !showSidebar }">
        <router-view />
      </div>
    </main>
    
    <!-- 移动端遮罩层 -->
    <div 
      v-if="showSidebar && isMobile && !isCollapsed" 
      class="mobile-overlay"
      @click="isCollapsed = true"
    ></div>
    
    <!-- 告警通知 -->
    <AlertList v-if="store.alerts.length > 0" :alerts="store.alerts" />
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { formingMenu } from './views/slm/forming/routes.js'
import { useRoute, useRouter } from 'vue-router'
import { useDataStore } from './stores/data'
import { useResponsive } from './composables/useResponsive'
import { useNotification } from './composables/useNotification'
import { deviceApi } from './utils/api'
import ThemeToggle from './components/ThemeToggle.vue'
import LangSwitch from './components/LangSwitch.vue'
import AlertList from './components/AlertList.vue'

const store = useDataStore()
const route = useRoute()
const router = useRouter()
const { isMobile, sidebarCollapsed } = useResponsive()
const { success } = useNotification()

const isCollapsed = ref(sidebarCollapsed.value)

// 是否显示侧边栏（设备选择页不显示）
const showSidebar = computed(() => route.path !== '/' && route.path !== '/login')

// 当前设备类型
const deviceType = computed(() => route.meta.device || localStorage.getItem('deviceType'))

// 设备类型图标
const deviceTypeIcon = computed(() => {
  switch (deviceType.value) {
    case 'sls': return 'CopyDocument'
    case 'slm': return 'Lightning'
    default: return 'Cpu'
  }
})

const slmSelectedDeviceId = computed(() => {
  if (route.path.startsWith('/slm/device') && route.params.deviceId) {
    return String(route.params.deviceId)
  }
  return localStorage.getItem('slmSelectedDeviceId') || ''
})

const slmDevicePath = (tab = 'status') => {
  const suffix = slmSelectedDeviceId.value ? `/${encodeURIComponent(slmSelectedDeviceId.value)}` : ''
  return `/slm/device${suffix}?tab=${tab}`
}

// SLM 菜单：设备检测作为具体设备的二级工作区，三个子页面由 tab 区分。
const slmMenuItems = computed(() => [
  { key: 'slm-fleet', name: '设备群总览', path: '/slm/dashboard', icon: 'Grid' },
  {
    key: 'slm-device',
    name: '设备检测',
    path: slmDevicePath('status'),
    icon: 'Monitor',
    children: [
      { key: 'slm-device-status', name: '实时状态信息', path: slmDevicePath('status'), tab: 'status' },
      { key: 'slm-device-control', name: '闭环调控', path: slmDevicePath('control'), tab: 'control' },
      { key: 'slm-device-health', name: '设备健康状态', path: slmDevicePath('health'), tab: 'health' },
    ]
  },
  // 成形监测：逐层数据接入、异常识别与异常溯源，四个子页面见 views/slm/forming/routes.js
  formingMenu('/slm/forming'),
  { key: 'slm-settings', name: '设置', path: '/slm/settings', icon: 'Setting' },
])

// SLS 菜单
const slsMenuItems = [
  { name: '设备群监测', path: '/sls/dashboard', icon: 'Grid' },
  { name: '设备状态监测', path: '/sls/device', icon: 'Monitor' },
  { name: '设置', path: '/sls/settings', icon: 'Setting' },
]

// 根据设备类型返回对应菜单
const menuItems = computed(() => {
  if (deviceType.value === 'slm') return slmMenuItems.value
  if (deviceType.value === 'sls') return slsMenuItems
  return []
})

// 判断菜单项是否激活
const isActive = (item) => {
  const path = item.path || ''
  if (item.tab) {
    const currentTab = route.query.tab || 'status'
    return route.path.startsWith('/slm/device') && currentTab === item.tab
  }
  if (path.startsWith('/slm/device') && route.path.startsWith('/slm/device')) {
    return true
  }
  if (path.startsWith('/sls/device') && route.path.startsWith('/sls/device')) {
    return true
  }
  if (item.key === 'slm-forming') {
    return route.path.startsWith('/slm/forming')
  }
  return route.path === path
}

// 二级菜单折叠：收起的分组记在 localStorage；进入某分组的页面时自动展开该分组
const closedGroups = ref(new Set(JSON.parse(localStorage.getItem('nav-closed-groups') || '[]')))
const saveClosedGroups = () => localStorage.setItem('nav-closed-groups', JSON.stringify([...closedGroups.value]))
const isGroupOpen = (item) => !closedGroups.value.has(item.key)
const toggleGroup = (item) => {
  const s = new Set(closedGroups.value)
  if (s.has(item.key)) s.delete(item.key)
  else s.add(item.key)
  closedGroups.value = s
  saveClosedGroups()
}
watch(() => route.fullPath, () => {
  const g = menuItems.value.find((item) => item.children?.length && (isActive(item) || item.children.some(isActive)))
  if (g && closedGroups.value.has(g.key)) toggleGroup(g)
})

// 返回设备选择页
const backToDeviceSelect = () => {
  localStorage.removeItem('deviceType')
  router.push('/')
}

// 监听响应式变化
watch(() => sidebarCollapsed.value, (val) => {
  isCollapsed.value = val
})

// 连接成功后通知
watch(() => store.connected, (connected) => {
  if (connected) {
    success('WebSocket 连接成功', '系统已连接')
  }
})

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('deviceType')
  router.push('/login')
}

onMounted(async () => {
  // 连接 WebSocket 数据流（仅用于基础状态）
  store.connectWebSocket()
  
  // 注意：设备初始化现在在 DeviceSelect.vue 中选择设备后执行
  // 不再自动连接 FDM 设备
})
</script>

<style scoped>
.app-wrapper {
  display: flex;
  height: 100vh;
  background: var(--am-page-bg);
  color: var(--am-text);
}

/* 侧边栏 */
.sidebar {
  width: 232px;
  background: var(--am-nav-bg);
  color: var(--am-nav-text);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  flex: none;
}

.sidebar.collapsed {
  width: 64px;
}

.logo {
  padding: 18px 16px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-bottom: 1px solid var(--am-nav-line);
}

.logo.mini {
  padding: 18px 0;
}

.brand-title {
  font-size: 19px;
  font-weight: 700;
  line-height: 1.4;
  color: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  white-space: nowrap;
}

.brand-ver {
  margin-top: 4px;
  font-size: 13px;
  color: var(--am-gold);
  border: 1px solid color-mix(in srgb, var(--am-gold) 60%, transparent);
  border-radius: 10px;
  padding: 0 8px;
}

.brand-mini {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  border: 1px solid color-mix(in srgb, var(--am-gold) 60%, transparent);
  border-radius: 6px;
  padding: 2px 4px;
}

/* 设备类型标识 */
.device-badge {
  margin: 12px 16px 0;
  padding: 4px 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--am-gold);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

/* 返回按钮区域 */
.back-section {
  padding: 6px 12px 10px;
  border-bottom: 1px solid var(--am-nav-line);
}

.back-section .el-button {
  color: var(--am-nav-text-2);
  width: 100%;
  justify-content: flex-start;
}

.back-section .el-button:hover {
  color: #fff;
  background: var(--am-nav-hover);
}

.nav-menu {
  flex: 1;
  padding: 10px 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.nav-group {
  display: flex;
  flex-direction: column;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px 12px 15px;
  color: var(--am-nav-text);
  text-decoration: none;
  font-size: 16px;
  border-left: 5px solid transparent;
  transition: background 0.2s ease, color 0.2s ease;
}

.sidebar.collapsed .nav-item {
  padding: 12px 0;
  justify-content: center;
}

.nav-item:hover {
  background: var(--am-nav-hover);
  color: #fff;
}

.nav-item.active {
  background: var(--am-nav-bg-active);
  color: #fff;
  border-left-color: var(--am-gold);
  font-weight: 700;
}

.nav-caret {
  margin-left: auto;
  font-size: 14px;
  padding: 3px;
  border-radius: 4px;
  color: var(--am-nav-text-2);
  transition: transform 0.2s ease;
}

.nav-caret:hover {
  color: #fff;
  background: var(--am-nav-hover);
}

.nav-caret.closed {
  transform: rotate(-90deg);
}

.nav-children {
  margin: 2px 0 6px 30px;
  padding-left: 10px;
  border-left: 1px solid var(--am-nav-line);
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.nav-child {
  min-height: 32px;
  padding: 6px 10px;
  border-radius: 5px;
  color: var(--am-nav-text-2);
  text-decoration: none;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  transition: color 0.2s ease, background 0.2s ease;
}

.nav-child:hover {
  color: #fff;
  background: var(--am-nav-hover);
}

.nav-child.active {
  color: #fff;
  background: var(--am-nav-hover);
  font-weight: 700;
}

.nav-child.active .nav-child-dot {
  background: var(--am-gold);
  opacity: 1;
}

.nav-child-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.7;
}

.sidebar-footer {
  padding: 14px 16px;
  border-top: 1px solid var(--am-nav-line);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #f08a87;
}

.connection-status.connected {
  color: #8fd3a9;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e0605c;
}

.connection-status.connected .status-dot {
  background: #2fa35a;
  box-shadow: 0 0 0 3px rgba(47, 163, 90, 0.25);
}

.connection-hint {
  font-size: 11px;
  color: var(--am-nav-text-2);
  margin-top: 4px;
  padding-left: 16px;
}

/* 主内容区 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.main-content.full-width {
  width: 100%;
}

.header {
  height: 58px;
  background: var(--am-header-bg);
  border-bottom: 1px solid var(--am-card-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header .el-button {
  color: var(--am-text-2);
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--am-text);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-container {
  flex: 1;
  padding: 16px 20px;
  overflow: auto;
}

.page-container.no-padding {
  padding: 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 1000;
    transform: translateX(-100%);
  }
  
  .sidebar:not(.collapsed) {
    transform: translateX(0);
  }
  
  .mobile-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 999;
  }
}

/* 平板适配 */
@media (max-width: 992px) {
  .page-container {
    padding: 16px;
  }
  
  .status-cards {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
</style>
