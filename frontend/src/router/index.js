import { createRouter, createWebHistory } from 'vue-router'

// FDM 页面
import FDMDashboard from '../views/fdm/Dashboard.vue'
import FDMAnalysis from '../views/fdm/Analysis.vue'
import FDMControl from '../views/fdm/Control.vue'
import FDMSettings from '../views/fdm/Settings.vue'

// SLM 页面
import SLMDashboard from '../views/slm/Dashboard.vue'
import SLMAnalysis from '../views/slm/Analysis.vue'
import SLMControl from '../views/slm/Control.vue'
import SLMSettings from '../views/slm/Settings.vue'

// 其他页面
import DeviceSelect from '../views/DeviceSelect.vue'
import Login from '../views/Login.vue'

const routes = [
  // 设备选择首页
  {
    path: '/',
    name: 'DeviceSelect',
    component: DeviceSelect,
    meta: { title: '选择设备', public: true }
  },
  
  // FDM 路由
  {
    path: '/fdm/dashboard',
    name: 'FDMDashboard',
    component: FDMDashboard,
    meta: { title: '仪表盘', device: 'fdm' }
  },
  {
    path: '/fdm/analysis',
    name: 'FDMAnalysis',
    component: FDMAnalysis,
    meta: { title: '数据分析', device: 'fdm' }
  },
  {
    path: '/fdm/control',
    name: 'FDMControl',
    component: FDMControl,
    meta: { title: '系统控制', device: 'fdm' }
  },
  {
    path: '/fdm/settings',
    name: 'FDMSettings',
    component: FDMSettings,
    meta: { title: '设置', device: 'fdm' }
  },
  
  // SLM 路由
  {
    path: '/slm/dashboard',
    name: 'SLMDashboard',
    component: SLMDashboard,
    meta: { title: '仪表盘', device: 'slm' }
  },
  {
    path: '/slm/analysis',
    name: 'SLMAnalysis',
    component: SLMAnalysis,
    meta: { title: '数据分析', device: 'slm' }
  },
  {
    path: '/slm/control',
    name: 'SLMControl',
    component: SLMControl,
    meta: { title: '系统控制', device: 'slm' }
  },
  {
    path: '/slm/settings',
    name: 'SLMSettings',
    component: SLMSettings,
    meta: { title: '设置', device: 'slm' }
  },
  
  // 登录
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录', public: true }
  },
  
  // 旧路由重定向（兼容）
  {
    path: '/analysis',
    redirect: '/fdm/analysis'
  },
  {
    path: '/control',
    redirect: '/fdm/control'
  },
  {
    path: '/settings',
    redirect: '/fdm/settings'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 使用 sessionStorage 替代 localStorage 存储 token
// 这样每次关闭浏览器后再次打开都需要重新登录
function getToken() {
  return sessionStorage.getItem('token')
}

function setToken(token) {
  sessionStorage.setItem('token', token)
}

function removeToken() {
  sessionStorage.removeItem('token')
}

// 导出供其他模块使用
export { getToken, setToken, removeToken }

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - SmartAM` : 'SmartAM System'
  
  const token = getToken()
  const savedDeviceType = localStorage.getItem('deviceType')
  const targetDevice = to.meta.device
  
  // 设备选择页面 - 如果有保存的设备类型但目标是不同设备，清除缓存
  if (to.path === '/') {
    // 正常显示设备选择页
    next()
    return
  }
  
  // 访问具体设备页面时，检查是否匹配
  if (targetDevice) {
    // 如果没有选择过设备，强制跳转到设备选择页（让用户手动选择）
    if (!savedDeviceType) {
      console.log(`[Router] 请先选择设备类型，当前访问: ${targetDevice}`)
      next('/')
      return
    }
    // 如果设备类型不匹配
    if (savedDeviceType !== targetDevice) {
      console.log(`[Router] 设备类型不匹配，已选 ${savedDeviceType}，请重新选择`)
      // 清除设备类型，让用户重新选择
      localStorage.removeItem('deviceType')
      next('/')
      return
    }
  }
  
  // 需要登录的页面
  if (!to.meta.public && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
