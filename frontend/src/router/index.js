import { createRouter, createWebHistory } from 'vue-router'

// SLM 页面
import SLMDeviceGroup from '../views/slm/DeviceGroup.vue'
import SLMDashboard from '../views/slm/Dashboard.vue'
import SLMSettings from '../views/slm/Settings.vue'

// SLS 页面
import SLSDeviceGroup from '../views/sls/DeviceGroup.vue'
import SLSDashboard from '../views/sls/Dashboard.vue'
import SLSSettings from '../views/sls/Settings.vue'

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
  
  // SLM 路由
  {
    path: '/slm/dashboard',
    name: 'SLMDeviceGroup',
    component: SLMDeviceGroup,
    meta: { title: '设备群监测', device: 'slm' }
  },
  {
    path: '/slm/device/:deviceId?',
    name: 'SLMDeviceDashboard',
    component: SLMDashboard,
    meta: { title: '打印状态监测', device: 'slm' }
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
    name: 'SLSDeviceGroup',
    component: SLSDeviceGroup,
    meta: { title: '设备群监测', device: 'sls' }
  },
  {
    path: '/sls/device/:deviceId?',
    name: 'SLSDeviceDashboard',
    component: SLSDashboard,
    meta: { title: '打印状态监测', device: 'sls' }
  },
  {
    path: '/sls/settings',
    name: 'SLSSettings',
    component: SLSSettings,
    meta: { title: '设置', device: 'sls' }
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
    path: '/fdm/:pathMatch(.*)*',
    redirect: '/'
  },
  {
    path: '/slm/analysis',
    redirect: '/slm/dashboard'
  },
  {
    path: '/slm/control',
    redirect: '/slm/dashboard'
  },
  {
    path: '/sls/analysis',
    redirect: '/sls/dashboard'
  },
  {
    path: '/sls/control',
    redirect: '/sls/dashboard'
  },
  {
    path: '/analysis',
    redirect: '/'
  },
  {
    path: '/control',
    redirect: '/'
  },
  {
    path: '/settings',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - SmartAM` : 'SmartAM System'

  const savedDeviceType = localStorage.getItem('deviceType')
  const targetDevice = to.meta.device

  // 设备选择页面 - 如果有保存的设备类型但目标是不同设备，清除缓存
  if (to.path === '/') {
    // 正常显示设备选择页
    next()
    return
  }

  // 通过一键脚本或远程端口直接打开 /slm/...、/sls/... 时，
  // 自动同步当前设备类型，避免新浏览器上下文因缺少 localStorage 而被踢回首页。
  if (targetDevice) {
    if (savedDeviceType !== targetDevice) {
      localStorage.setItem('deviceType', targetDevice)
    }
  }

  // 现场监控页默认作为局域网入口开放；只有显式标记 requiresAuth 的页面才要求登录。
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
