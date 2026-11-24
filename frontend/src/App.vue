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
            <span class="nav-label">{{ isCollapsed ? '展开导航' : '收起导航' }}</span><span class="nav-compact">导航</span>
          </el-button>
          <span class="page-title">{{ currentPageTitle }}</span>
        </div>
        <div class="header-right">
          <LangSwitch />
          <ThemeToggle />
          <el-tooltip content="全屏" placement="bottom">
            <el-button text aria-label="全屏显示" @click="toggleFullscreen">
              全屏
            </el-button>
          </el-tooltip>

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
import { ElMessage } from 'element-plus'
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useDataStore } from './stores/data'
import { useResponsive } from './composables/useResponsive'
import { slmTab } from './utils/slmNavigation'
import AppSidebar from './components/AppSidebar.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import LangSwitch from './components/LangSwitch.vue'
import AlertList from './components/AlertList.vue'

const store = useDataStore()
const route = useRoute()
const { isMobile, sidebarCollapsed } = useResponsive()

const isCollapsed = ref(sidebarCollapsed.value)

// 是否显示侧边栏（设备选择页不显示）
const showSidebar = computed(() => !!route.meta.device)

// 标签切换也同步顶栏标题，明确当前所在的功能页面。
const currentPageTitle = computed(() => {
  if (route.path.startsWith('/slm/device')) return slmTab(route.query.tab).label
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


const toggleFullscreen = async () => {
  try {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen()
    } else {
      await document.exitFullscreen()
    }
  } catch { ElMessage.info('当前浏览器不支持全屏显示') }
}


onMounted(() => {
  // 连接 WebSocket 数据流（仅用于基础状态）
  store.connectWebSocket()
  // 工作区切换仅负责导航，硬件连接与采集由设备页显式触发。
})
</script>

<style scoped>
/* 清除浏览器默认外边距，让应用外框完整贴合视口。 */

.app-wrapper {
  display: flex;
  height: 100vh;
  height: 100dvh;
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
  min-height: 0;
  scrollbar-gutter: stable;
  padding: 20px 24px;
  overflow: auto;
}

.page-container.no-padding {
  padding: 0;
}

.nav-compact { display: none; }
.header .page-title { white-space: nowrap; }
@media (max-width: 600px) {
  .nav-label { display: none; }
  .nav-compact { display: inline; }
  .header { padding: 0 12px; }
  .header-left, .header-right { gap: 4px; }
  .header :deep(.el-button) { padding-left: 6px; padding-right: 6px; }
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

}
</style>
