<template>
  <div class="app-wrapper">
    <!-- 侧边栏（设备选择页不显示） -->
    <aside v-if="showSidebar" class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="logo">
        <el-icon size="32"><Cpu /></el-icon>
        <span v-show="!isCollapsed" class="logo-text">SmartAM</span>
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
        <router-link 
          v-for="item in menuItems" 
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon size="20">
            <component :is="item.icon" />
          </el-icon>
          <span v-show="!isCollapsed" class="nav-text">{{ item.name }}</span>
        </router-link>
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
    case 'fdm': return 'Printer'
    case 'sls': return 'CopyDocument'
    case 'slm': return 'Lightning'
    default: return 'Cpu'
  }
})

// FDM 菜单
const fdmMenuItems = [
  { name: '仪表盘', path: '/fdm/dashboard', icon: 'Monitor' },
  { name: '数据分析', path: '/fdm/analysis', icon: 'TrendCharts' },
  { name: '系统控制', path: '/fdm/control', icon: 'SetUp' },
  { name: '设置', path: '/fdm/settings', icon: 'Setting' },
]

// SLM 菜单
const slmMenuItems = [
  { name: '仪表盘', path: '/slm/dashboard', icon: 'Monitor' },
  { name: '数据分析', path: '/slm/analysis', icon: 'TrendCharts' },
  { name: '系统控制', path: '/slm/control', icon: 'SetUp' },
  { name: '设置', path: '/slm/settings', icon: 'Setting' },
]

// SLS 菜单
const slsMenuItems = [
  { name: '仪表盘', path: '/sls/dashboard', icon: 'Monitor' },
  { name: '数据分析', path: '/sls/analysis', icon: 'TrendCharts' },
  { name: '系统控制', path: '/sls/control', icon: 'SetUp' },
]

// 根据设备类型返回对应菜单
const menuItems = computed(() => {
  if (deviceType.value === 'slm') return slmMenuItems
  if (deviceType.value === 'sls') return slsMenuItems
  return fdmMenuItems
})

// 判断菜单项是否激活
const isActive = (path) => {
  return route.path === path
}

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
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #e2e8f0;
}

/* 侧边栏 */
.sidebar {
  width: 240px;
  background: rgba(15, 23, 42, 0.8);
  border-right: 1px solid rgba(0, 212, 255, 0.2);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
}

.sidebar.collapsed {
  width: 64px;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  color: #00d4ff;
}

.logo-text {
  font-size: 20px;
  font-weight: 600;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* 设备类型标识 */
.device-badge {
  margin: 12px 16px 0;
  padding: 6px 12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
}

.device-badge.fdm {
  background: rgba(0, 212, 255, 0.15);
  color: #00d4ff;
  border: 1px solid rgba(0, 212, 255, 0.3);
}

.device-badge.slm {
  background: rgba(0, 255, 136, 0.15);
  color: #00ff88;
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.device-badge.sls {
  background: rgba(255, 149, 0, 0.15);
  color: #ff9500;
  border: 1px solid rgba(255, 149, 0, 0.3);
}

/* 返回按钮区域 */
.back-section {
  padding: 8px 16px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.back-section .el-button {
  color: #94a3b8;
  width: 100%;
  justify-content: flex-start;
}

.back-section .el-button:hover {
  color: #00d4ff;
}

.nav-menu {
  flex: 1;
  padding: 16px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  color: #a0aec0;
  text-decoration: none;
  transition: all 0.3s ease;
}

.nav-item:hover {
  background: rgba(0, 212, 255, 0.1);
  color: #00d4ff;
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.2), transparent);
  color: #00d4ff;
  border-left: 3px solid #00d4ff;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(0, 212, 255, 0.2);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #ff4d4f;
}

.connection-status.connected {
  color: #00ff88;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff4d4f;
}

.connection-status.connected .status-dot {
  background: #00ff88;
  box-shadow: 0 0 8px #00ff88;
}

.connection-hint {
  font-size: 10px;
  color: #64748b;
  margin-top: 4px;
  padding-left: 16px;
}

/* 主内容区 */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-content.full-width {
  width: 100%;
}

.header {
  height: 64px;
  background: rgba(15, 23, 42, 0.6);
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 500;
  color: #e2e8f0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-container {
  flex: 1;
  padding: 24px;
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
