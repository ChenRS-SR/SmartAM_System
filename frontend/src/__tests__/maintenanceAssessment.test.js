import { describe, it, expect } from 'vitest'
import data from '../assets/maintenance-assessments.json'
import { maintenanceRecords, initialMaintenanceTask, maintenanceMeasurements, maintenanceStatus, riskPosition } from '../utils/maintenanceAssessment'
describe('案例二维护评估', () => {
  it('保留四设备全部113条记录及七类子系统，不生成PLP风险值', () => {
    expect(Object.values(data.devices).map(rows => rows.length)).toEqual([7,30,28,48])
    for (const rows of Object.values(data.devices)) for (const row of rows) {
      expect(row.systems).toHaveLength(7)
      for (const system of row.systems.filter(s => s.model === 'PLP')) expect(system.w).toBeUndefined()
    }
  })
  it.each([['slm-b10','20250509-07-47'],['slm-b15','20250107-20-02'],['slm-b17-replay','20240827-09-33'],['slm-b44','20250321-09-20']])('设备%s使用自己的评估历史', (id,task) => {
    expect(initialMaintenanceTask(id)).toBe(task)
    const detail = maintenanceMeasurements(maintenanceRecords(id),task,'filter')
    expect(detail.task).toBe(task)
    expect(detail.duration.at(-1)).toBe(task)
    expect(detail.duration.every(value => value <= task)).toBe(true)
    expect(detail.history.at(-1).w).toBe(detail.w)
  })
  it('保持原表精度和负风险值，条形位置始终有效', () => {
    const scraper = data.devices.B10[0].systems.find(s=>s.key==='powder')
    expect(scraper.w).toBe(-0.2994786798)
    expect(scraper.wl).toBe(-0.0317819120980343)
    for (const rows of Object.values(data.devices)) for(const row of rows) for(const s of row.systems.filter(s=>s.model==='PHM')) for(const key of ['w','wl','wr','wu']) {
      expect(riskPosition(s,s[key])).toBeGreaterThanOrEqual(0)
      expect(riskPosition(s,s[key])).toBeLessThanOrEqual(100)
    }
  })
  it('依据真实阈值和各子系统Rmin判定，缺失值不补零', () => {
    const base = {model:'PHM',w:-4,wl:-3,wr:2,wu:4,reliability:.99,rmin:.98}
    expect(maintenanceStatus(base).rank).toBe(0)
    expect(maintenanceStatus({...base,w:-3}).rank).toBe(1)
    expect(maintenanceStatus({...base,w:2}).rank).toBe(2)
    expect(maintenanceStatus({...base,w:4}).label).toBe('达到维修上限')
    expect(maintenanceStatus({...base,reliability:.95}).rank).toBe(2)
    expect(maintenanceStatus({...base,w:null}).rank).toBe(-1)
    expect(maintenanceStatus({model:'PLP',reliability:.89,rmin:.9}).rank).toBe(2)
    expect(maintenanceRecords('slm-unknown')).toEqual([])
    expect(maintenanceMeasurements([], 'missing', 'filter')).toBeNull()
  })
})
