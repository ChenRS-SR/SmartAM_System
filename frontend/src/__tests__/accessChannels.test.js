import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAccessChannels } from '../stores/accessChannels'

beforeEach(() => { localStorage.clear(); setActivePinia(createPinia()) })
describe('设备采集通道显示设置', () => {
  it('通道选择按设备隔离，并在重新进入后恢复，包括全部隐藏', () => {
    const channels = ['铺粉后图像', '熔化后图像', '刮刀扭矩', '加工平台扭矩', '设备状态参数']
    const store = useAccessChannels()
    store.setVisible('replay:A', channels, false)
    expect(store.forDevice('replay:A')['刮刀扭矩']).toBe(false)
    expect(store.forDevice('device:B')['刮刀扭矩']).toBeUndefined()
    setActivePinia(createPinia())
    const restored = useAccessChannels()
    expect(channels.every(name => restored.forDevice('replay:A')[name] === false)).toBe(true)
    restored.setVisible('replay:A', ['刮刀扭矩'], true)
    expect(restored.forDevice('replay:A')['刮刀扭矩']).toBe(true)
    expect(restored.forDevice('replay:A')['加工平台扭矩']).toBe(false)
  })
})

it('默认显示两路可见光，勾选可立即启用其他通道', () => {
  const store = useAccessChannels()
  expect(store.isVisible('B44', '铺粉后图像')).toBe(true)
  expect(store.isVisible('B44', '熔化后图像')).toBe(true)
  expect(store.isVisible('B44', '铺粉后红外图像')).toBe(false)
  expect(store.isVisible('B44', '熔化后红外图像')).toBe(false)
  expect(store.isVisible('B44', '刮刀扭矩')).toBe(true)
  store.setVisible('B44', ['铺粉后红外图像'], true)
  expect(store.isVisible('B44', '铺粉后红外图像')).toBe(true)
  store.setVisible('B44', ['铺粉后图像'], false)
  expect(store.isVisible('B44', '铺粉后图像')).toBe(false)
})
