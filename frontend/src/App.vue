<template>
  <div class="app-wrapper">
    <AppSidebar
      v-if="showSidebar"
      :collapsed="isCollapsed"
      :connected="store.connected"
      @navigate="closeMobileNavigation"
    />

    <!-- 主内容区 -->
    <main class="main-content" :class="{ 'full-width': !showSidebar }">
      <header v-if="showSidebar" class="header">
        <div class="header-left">
          <el-button
            text
            :aria-label="isCollapsed ? '展开导航' : '收起导航'"
            :aria-expanded="!isCollapsed"
            aria-controls="primary-sidebar"
            @click="isCollapsed = !isCollapsed"
          >
            <el-icon size="20"><Fold v-if="!isCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <span class="page-title">{{ currentPageTitle }}</span>
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
import AppSidebar from './components/AppSidebar.vue'
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

// 标签切换也同步顶栏标题，明确当前所在的功能页面。
const currentPageTitle = computed(() => {
  const labels = {
    status: '设备监测', control: '闭环调控',
    access: '数据接入', recognition: '异常识别', trace: '异常溯源'
  }
  if (route.path.startsWith('/slm/device')) return labels[route.query.tab || 'status'] || route.meta.title
  return route.meta.title || 'SmartAM'
})
const closeMobileNavigation = () => {
  if (isMobile.value) isCollapsed.value = true
}
// 包括页面内跳转在内，移动端完成导航后关闭抽屉。
watch(() => route.fullPath, closeMobileNavigation)

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
  
  // 工作区切换仅负责导航，硬件连接与采集由设备页显式触发。
})
</script>

<style scoped>
/* 清除浏览器默认外边距，让应用外框完整贴合视口。 */
:global(body) { margin: 0; }
.app-wrapper {
  display: flex;
  height: 100vh;
  background: var(--am-page-bg);
  color: var(--am-text);
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
  font-size: 16px;
  font-weight: 600;
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
@media (max-width: 767px) {
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
