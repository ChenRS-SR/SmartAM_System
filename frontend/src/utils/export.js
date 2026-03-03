import * as XLSX from 'xlsx'

/**
 * 导出 CSV
 * @param {Array} data - 数据数组
 * @param {Array} headers - 表头 { key, label }
 * @param {String} filename - 文件名
 */
export function exportCSV(data, headers, filename = 'export.csv') {
  // 创建 CSV 内容
  const headerRow = headers.map(h => h.label).join(',')
  const rows = data.map(row => {
    return headers.map(h => {
      const value = row[h.key]
      // 处理包含逗号或换行符的值
      if (typeof value === 'string' && (value.includes(',') || value.includes('\n'))) {
        return `"${value.replace(/"/g, '""')}"`
      }
      return value ?? ''
    }).join(',')
  })
  
  const csvContent = [headerRow, ...rows].join('\n')
  
  // 添加 BOM 以支持中文
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
  downloadFile(blob, filename)
}

/**
 * 导出 Excel
 * @param {Array} data - 数据数组
 * @param {Array} headers - 表头 { key, label }
 * @param {String} filename - 文件名
 * @param {Array} sheets - 多工作表配置 [{ name, data, headers }]
 */
export function exportExcel(data, headers, filename = 'export.xlsx', sheets = null) {
  const wb = XLSX.utils.book_new()
  
  if (sheets) {
    // 多工作表
    sheets.forEach(sheet => {
      const wsData = [
        sheet.headers.map(h => h.label),
        ...sheet.data.map(row => sheet.headers.map(h => row[h.key]))
      ]
      const ws = XLSX.utils.aoa_to_sheet(wsData)
      XLSX.utils.book_append_sheet(wb, ws, sheet.name)
    })
  } else {
    // 单工作表
    const wsData = [
      headers.map(h => h.label),
      ...data.map(row => headers.map(h => row[h.key]))
    ]
    const ws = XLSX.utils.aoa_to_sheet(wsData)
    
    // 设置列宽
    ws['!cols'] = headers.map(() => ({ wch: 20 }))
    
    XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
  }
  
  XLSX.writeFile(wb, filename)
}

/**
 * 导出 JSON
 * @param {Object} data - 数据对象
 * @param {String} filename - 文件名
 */
export function exportJSON(data, filename = 'export.json') {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  downloadFile(blob, filename)
}

/**
 * 下载文件
 * @param {Blob} blob - 文件 Blob
 * @param {String} filename - 文件名
 */
function downloadFile(blob, filename) {
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * 从 store 导出预测历史
 */
export function exportPredictionHistory(store) {
  const headers = [
    { key: 'time', label: '时间' },
    { key: 'flow_rate', label: '流量' },
    { key: 'feed_rate', label: '速度' },
    { key: 'z_offset', label: 'Z偏移' },
    { key: 'hotend', label: '温度' }
  ]
  
  const data = store.historyData.timestamps.map((time, i) => ({
    time,
    flow_rate: store.historyData.flowRateClasses[i],
    feed_rate: store.historyData.feedRateClasses[i],
    z_offset: store.historyData.zOffsetClasses[i],
    hotend: store.historyData.hotendClasses[i]
  }))
  
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
  exportExcel(data, headers, `prediction_history_${timestamp}.xlsx`)
}

/**
 * 导出调控记录
 */
export function exportRegulationHistory(records) {
  const headers = [
    { key: 'datetime', label: '时间' },
    { key: 'parameter', label: '参数' },
    { key: 'adjustment', label: '调整量' },
    { key: 'old_value', label: '原值' },
    { key: 'new_value', label: '新值' },
    { key: 'confidence', label: '置信度' },
    { key: 'success', label: '状态' }
  ]
  
  const data = records.map(r => ({
    ...r,
    success: r.success ? '成功' : '失败',
    confidence: (r.confidence * 100).toFixed(0) + '%'
  }))
  
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
  exportExcel(data, headers, `regulation_history_${timestamp}.xlsx`)
}

/**
 * 导出完整报告
 */
export function exportFullReport(store, regulationRecords) {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-')
  
  const sheets = [
    {
      name: '预测历史',
      headers: [
        { key: 'time', label: '时间' },
        { key: 'flow_rate', label: '流量' },
        { key: 'feed_rate', label: '速度' },
        { key: 'z_offset', label: 'Z偏移' },
        { key: 'hotend', label: '温度' },
        { key: 'nozzle_temp', label: '喷嘴温度' },
        { key: 'bed_temp', label: '热床温度' }
      ],
      data: store.historyData.timestamps.map((time, i) => ({
        time,
        flow_rate: store.historyData.flowRateClasses[i],
        feed_rate: store.historyData.feedRateClasses[i],
        z_offset: store.historyData.zOffsetClasses[i],
        hotend: store.historyData.hotendClasses[i],
        nozzle_temp: store.historyData.nozzleTemps[i],
        bed_temp: store.historyData.bedTemps[i]
      }))
    },
    {
      name: '调控记录',
      headers: [
        { key: 'datetime', label: '时间' },
        { key: 'parameter', label: '参数' },
        { key: 'adjustment', label: '调整量' },
        { key: 'new_value', label: '新值' },
        { key: 'confidence', label: '置信度' }
      ],
      data: regulationRecords.map(r => ({
        datetime: r.datetime,
        parameter: r.parameter,
        adjustment: r.adjustment,
        new_value: r.new_value,
        confidence: (r.confidence * 100).toFixed(0) + '%'
      }))
    }
  ]
  
  exportExcel(null, null, `smartam_report_${timestamp}.xlsx`, sheets)
}
