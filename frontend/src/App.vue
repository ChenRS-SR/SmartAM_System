<template>
  <div class="app-wrapper">
    <!-- 侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="logo">
        <el-icon size="32"><Cpu /></el-icon>
        <span v-show="!isCollapsed" class="logo-text">SmartAM</span>
      </div>
      
      <nav class="nav-menu">
        <router-link 
          v-for="item in menuItems" 
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
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
    <main class="main-content">
      <header class="header">
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
      
      <div class="page-container">
        <router-view />
      </div>
    </main>
    
    <!-- 移动端遮罩层 -->
    <div 
      v-if="isMobile && !isCollapsed" 
      class="mobile-overlay"
      @click="isCollapsed = true"
    ></div>
    
    <!-- 告警通知 -->
    <AlertList v-if="store.alerts.length > 0" :alerts="store.alerts" />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
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

const menuItems = [
  { name: '仪表盘', path: '/', icon: 'Monitor' },
  { name: '数据分析', path: '/analysis', icon: 'TrendCharts' },
  { name: '系统控制', path: '/control', icon: 'SetUp' },
  { name: '设置', path: '/settings', icon: 'Setting' },
]

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
}

const logout = () => {
  router.push('/login')
}

onMounted(async () => {
  // 连接 WebSocket 数据流
  store.connectWebSocket()
  
  // 延迟 3 秒后自动连接设备（等待服务完全启动）
  setTimeout(async () => {
    try {
      console.log('[App] 自动连接设备中...')
      const res = await deviceApi.connectAll()
      console.log('[App] 设备连接成功:', res.data)
    } catch (error) {
      console.log('[App] 设备连接失败（可能已连接或服务未就绪）:', error.message)
    }
  }, 3000)
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
