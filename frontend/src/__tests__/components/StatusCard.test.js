import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatusCard from '../../components/StatusCard.vue'

describe('StatusCard', () => {
  it('renders with props correctly', () => {
    const wrapper = mount(StatusCard, {
      props: {
        icon: 'Printer',
        label: '打印机状态',
        value: 'Printing',
        unit: '%',
        subValue: 'Progress: 50%'
      }
    })
    
    expect(wrapper.find('.card-label').text()).toBe('打印机状态')
    expect(wrapper.find('.card-value').text()).toContain('Printing')
    expect(wrapper.find('.card-unit').text()).toBe('%')
    expect(wrapper.find('.card-sub').text()).toBe('Progress: 50%')
  })

  it('applies custom colors', () => {
    const wrapper = mount(StatusCard, {
      props: {
        icon: 'Cpu',
        label: '温度',
        value: '200',
        iconBg: 'rgba(255, 0, 0, 0.2)',
        iconColor: '#ff0000',
        valueColor: '#ff6600'
      }
    })
    
    const iconEl = wrapper.find('.card-icon')
    expect(iconEl.attributes('style')).toContain('background: rgba(255, 0, 0, 0.2)')
  })

  it('renders without optional props', () => {
    const wrapper = mount(StatusCard, {
      props: {
        icon: 'View',
        label: '进度',
        value: '75'
      }
    })
    
    expect(wrapper.find('.card-unit').exists()).toBe(false)
    expect(wrapper.find('.card-sub').exists()).toBe(false)
  })
})
