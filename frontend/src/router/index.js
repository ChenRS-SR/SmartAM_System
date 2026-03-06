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

// SLS 页面
import SLSDashboard from '../views/sls/Dashboard.vue'
import SLSAnalysis from '../views/sls/Analysis.vue'
import SLSControl from '../views/sls/Control.vue'

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
  
  // SLS 路由
  {
    path: '/sls/dashboard',
    name: 'SLSDashboard',
    component: SLSDashboard,
    meta: { title: '仪表盘', device: 'sls' }
  },
  {
    path: '/sls/analysis',
    name: 'SLSAnalysis',
    component: SLSAnalysis,
    meta: { title: '数据分析', device: 'sls' }
  },
  {
    path: '/sls/control',
    name: 'SLSControl',
    component: SLSControl,
    meta: { title: '系统控制', device: 'sls' }
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

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - SmartAM` : 'SmartAM System'
  
  const token = localStorage.getItem('token')
  
  // 检查是否是设备选择页面
  if (to.path === '/') {
    // 如果已登录且有设备类型，直接跳转到对应设备
    if (token) {
      const deviceType = localStorage.getItem('deviceType')
      if (deviceType) {
        next(`/${deviceType}/dashboard`)
        return
      }
    }
    next()
    return
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
