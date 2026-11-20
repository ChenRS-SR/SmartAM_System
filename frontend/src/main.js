import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import i18n from './i18n'

import 'element-plus/dist/index.css'

// 全局样式
import './styles/variables.css'
import './styles/light-theme.css'
import './styles/am-theme.css'

// Element Plus
import ElementPlus from 'element-plus'
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

// 挂载前应用主题，避免首次绘制出现颜色跳变。
import { useThemeStore } from './stores/theme'

useThemeStore().applyTheme()
app.mount('#app')
