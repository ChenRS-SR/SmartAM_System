// 成形监测路由。集成到 SmartAM 时：routes.push(formingRoute({ prefix: '/slm/forming', fleetPath: '/slm/dashboard', meta: { device: 'slm' } }))
import FormingShell from './FormingShell.vue'
import Overview from './views/Overview.vue'
import Access from './views/Access.vue'
import Recognition from './views/Recognition.vue'
import Trace from './views/Trace.vue'

export const FORMING_MODULES = [
  { key: 'overview', name: '设备总览', component: Overview },
  { key: 'access', name: '数据接入', component: Access },
  { key: 'recognition', name: '异常识别', component: Recognition },
  { key: 'trace', name: '异常溯源', component: Trace },
]

export function formingRoute({ prefix = '/slm/forming', fleetPath = null, meta = {} } = {}) {
  return {
    path: prefix || '/',
    component: FormingShell,
    redirect: `${prefix}/overview`,
    children: FORMING_MODULES.map((m) => ({
      path: m.key,
      name: `forming-${m.key}`,
      component: m.component,
      props: { fleetPath, base: prefix },
      meta: { ...meta, title: m.name, forming: m.key },
    })),
  }
}

// 菜单项（SmartAM App.vue 的 slmMenuItems 中加入这一项即成为“成形监测”的二级菜单）
export function formingMenu(prefix = '/slm/forming') {
  return {
    key: 'slm-forming', name: '成形监测', path: `${prefix}/overview`, icon: 'DataAnalysis',
    children: FORMING_MODULES.map((m) => ({ key: `slm-forming-${m.key}`, name: m.name, path: `${prefix}/${m.key}` })),
  }
}
