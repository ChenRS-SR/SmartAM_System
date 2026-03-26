import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router, { removeToken } from './router'
import App from './App.vue'
import i18n from './i18n'

// 每次应用启动时清除 token，确保需要重新登录
removeToken()

// 全局样式
import './styles/variables.css'
import './styles/light-theme.css'

// Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// ECharts
import VueECharts from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, GaugeChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, BarChart, GaugeChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.component('v-chart', VueECharts)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.use(i18n)

// 初始化主题（延迟到应用挂载后）
import { useThemeStore } from './stores/theme'

app.mount('#app')

// 在挂载后初始化主题
const themeStore = useThemeStore()
themeStore.applyTheme()
