import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDataStore } from '../../stores/data.js'

describe('Data Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should initialize with default state', () => {
    const store = useDataStore()
    
    expect(store.connected).toBe(false)
    expect(store.sensorData).toEqual({})
    expect(store.prediction).toEqual({})
    expect(store.alerts).toEqual([])
  })

  it('should add alerts', () => {
    const store = useDataStore()
    
    store.addAlert({ message: 'Test alert', level: 'warning' })
    
    expect(store.alerts.length).toBe(1)
    expect(store.alerts[0].message).toBe('Test alert')
    expect(store.alerts[0].level).toBe('warning')
  })

  it('should dismiss alerts by id', () => {
    const store = useDataStore()
    
    store.addAlert({ message: 'Test', level: 'info' })
    const alertId = store.alerts[0].id
    
    store.dismissAlert(alertId)
    
    expect(store.alerts.length).toBe(0)
  })

  it('should clear all alerts', () => {
    const store = useDataStore()
    
    store.addAlert({ message: 'Test 1', level: 'info' })
    store.addAlert({ message: 'Test 2', level: 'warning' })
    
    store.clearAlerts()
    
    expect(store.alerts.length).toBe(0)
  })

  it('should limit alerts to 50', () => {
    const store = useDataStore()
    
    for (let i = 0; i < 55; i++) {
      store.addAlert({ message: `Alert ${i}`, level: 'info' })
    }
    
    expect(store.alerts.length).toBe(50)
  })

  it('should clear history data', () => {
    const store = useDataStore()
    
    // Simulate adding some history
    store.historyData.timestamps.push('2024-01-01')
    store.historyData.nozzleTemps.push(200)
    
    store.clearHistory()
    
    expect(store.historyData.timestamps).toEqual([])
    expect(store.historyData.nozzleTemps).toEqual([])
  })
})
