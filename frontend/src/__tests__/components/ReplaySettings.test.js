import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ReplaySettings from '../../components/slm/ReplaySettings.vue'
import { REPLAY_DEVICE_ID, useReplayStore } from '../../stores/replay'

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.restoreAllMocks())
describe('系统设置中的回放设备隔离', () => {
  it('普通设备显示灰色禁用控件且不加载案例', () => {
    const replay = useReplayStore()
    const open = vi.spyOn(replay, 'open').mockResolvedValue()
    const wrapper = mount(ReplaySettings, { props: { deviceId: 'slm-normal' }, global: { stubs: { RouterLink: true } } })
    expect(wrapper.get('fieldset').element.disabled).toBe(true)
    expect(wrapper.classes()).toContain('unavailable')
    expect(open).not.toHaveBeenCalled()
    wrapper.unmount()
  })
  it('对应设备恢复统一回放，切换普通设备后暂停并禁用', async () => {
    const replay = useReplayStore()
    const open = vi.spyOn(replay, 'open').mockResolvedValue()
    const pause = vi.spyOn(replay, 'pause').mockResolvedValue()
    replay.manifest = { duration: 100, layers: [], segments: [] }
    replay.playing = true
    const wrapper = mount(ReplaySettings, { props: { deviceId: REPLAY_DEVICE_ID }, global: { stubs: { RouterLink: true } } })
    expect(open).toHaveBeenCalledOnce()
    expect(wrapper.get('fieldset').element.disabled).toBe(false)
    await wrapper.setProps({ deviceId: 'slm-normal' })
    await flushPromises()
    expect(pause).toHaveBeenCalledOnce()
    expect(wrapper.get('fieldset').element.disabled).toBe(true)
    wrapper.unmount()
  })
  it('普通设备页也会停止晚到的异步回放启动', async () => {
    const replay = useReplayStore()
    vi.spyOn(replay, 'open').mockResolvedValue()
    const pause = vi.spyOn(replay, 'pause').mockResolvedValue()
    const wrapper = mount(ReplaySettings, { props: { deviceId: 'slm-normal' }, global: { stubs: { RouterLink: true } } })
    replay.playing = true
    await flushPromises()
    expect(pause).toHaveBeenCalledOnce()
    expect(wrapper.get('fieldset').element.disabled).toBe(true)
    wrapper.unmount()
  })
})
