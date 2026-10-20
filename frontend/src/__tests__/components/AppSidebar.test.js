import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as icons from '@element-plus/icons-vue'
import { beforeEach, describe, expect, it } from 'vitest'
import AppSidebar from '../../components/AppSidebar.vue'

// 使用真实路由验证设备上下文与功能入口，不启动采集或向设备下发指令。
async function setup(path, collapsed = false) {
  const page = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: page },
      ...['slm', 'sls'].flatMap(device => [
        { path: `/${device}/dashboard`, component: page, meta: { device } },
        { path: `/${device}/device/:deviceId?`, component: page, meta: { device } },
        { path: `/${device}/settings`, component: page, meta: { device } }
      ])
    ]
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(AppSidebar, {
    props: { collapsed },
    global: { plugins: [createPinia(), router, ElementPlus], components: icons }
  })
  return { wrapper, router }
}

beforeEach(() => localStorage.clear())

describe('工业工作区导航', () => {
  it('进入设备子页面时只有当前功能激活，跳转保留设备编号', async () => {
    const { wrapper, router } = await setup('/slm/device/machine-02?tab=recognition')
    expect(wrapper.findAll('[aria-current="page"]')).toHaveLength(1)
    expect(wrapper.get('[aria-current="page"]').attributes('aria-label')).toBe('异常识别')
    expect(wrapper.get('[aria-label="系统设置"]').attributes('href')).toBe('/slm/settings?device=machine-02')
    expect(wrapper.get('nav').findAll('a').map(a => a.attributes('aria-label')))
      .toEqual(['设备群总览', '设备监测', '数据接入', '异常识别', '异常溯源', '闭环调控'])
    await wrapper.get('[aria-label="闭环调控"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/slm/device/machine-02?tab=control')
    expect(wrapper.get('[aria-current="page"]').attributes('aria-label')).toBe('闭环调控')
    wrapper.unmount()
  })

  it('收起模式保留全部导航入口，并从总览恢复设备上下文', async () => {
    localStorage.setItem('slmSelectedDeviceId', 'machine-03')
    const { wrapper } = await setup('/slm/dashboard', true)
    expect(wrapper.findAll('.nav-item')).toHaveLength(7)
    expect(wrapper.get('[aria-label="设备监测"]').attributes('href')).toBe('/slm/device/machine-03?tab=status')
    expect(wrapper.find('[aria-label="设备健康"]').exists()).toBe(false)
    expect(wrapper.get('[aria-label="异常溯源"]').attributes('href')).toBe('/slm/device/machine-03?tab=trace')
    expect(wrapper.get('[aria-label="切换设备类型"]').exists()).toBe(true)
    expect(wrapper.get('[role="status"]').attributes('aria-label')).toContain('未连接')
    wrapper.unmount()
  })

  it('SLS 仅展示已有功能，切换设备类型返回选择页', async () => {
    const { wrapper, router } = await setup('/sls/device/sls-01')
    expect(wrapper.find('[aria-label="异常识别"]').exists()).toBe(false)
    expect(wrapper.get('[aria-current="page"]').attributes('aria-label')).toBe('设备状态监测')
    expect(wrapper.get('[aria-label="系统设置"]').attributes('href')).toBe('/sls/settings')
    await wrapper.get('[aria-label="切换设备类型"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/')
    wrapper.unmount()
  })
})
