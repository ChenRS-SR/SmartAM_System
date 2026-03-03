import { ref } from 'vue'
import { ElNotification } from 'element-plus'

const notifications = ref([])

// 通知类型配置
const notificationConfig = {
  success: {
    type: 'success',
    icon: 'CircleCheck',
    color: '#00ff88'
  },
  warning: {
    type: 'warning',
    icon: 'Warning',
    color: '#ffc107'
  },
  error: {
    type: 'error',
    icon: 'CircleClose',
    color: '#ff4d4f'
  },
  info: {
    type: 'info',
    icon: 'InfoFilled',
    color: '#00d4ff'
  }
}

// 打印事件通知映射
const printEventMap = {
  'PrintStarted': { title: '打印开始', message: '打印任务已开始', type: 'info' },
  'PrintFailed': { title: '打印失败', message: '打印任务失败', type: 'error' },
  'PrintDone': { title: '打印完成', message: '打印任务已完成', type: 'success' },
  'PrintCancelled': { title: '打印取消', message: '打印任务已取消', type: 'warning' },
  'PrintPaused': { title: '打印暂停', message: '打印任务已暂停', type: 'warning' },
  'PrintResumed': { title: '打印恢复', message: '打印任务已恢复', type: 'info' }
}

// 闭环调控通知
const controlEventMap = {
  'regulation_applied': { title: '参数已调节', type: 'success' },
  'threshold_exceeded': { title: '检测到异常', type: 'warning' },
  'emergency_stop': { title: '紧急停止', type: 'error' }
}

export function useNotification() {
  // 显示通知
  const show = (options) => {
    const { type = 'info', title, message, duration = 3000 } = options
    
    ElNotification({
      type,
      title,
      message,
      duration,
      position: 'top-right',
      showClose: true,
      customClass: 'smartam-notification'
    })

    // 保存到历史
    notifications.value.unshift({
      id: Date.now(),
      timestamp: new Date().toISOString(),
      type,
      title,
      message
    })

    // 限制历史数量
    if (notifications.value.length > 100) {
      notifications.value = notifications.value.slice(0, 100)
    }
  }

  // 快捷方法
  const success = (message, title = '成功') => show({ type: 'success', title, message })
  const warning = (message, title = '警告') => show({ type: 'warning', title, message })
  const error = (message, title = '错误') => show({ type: 'error', title, message })
  const info = (message, title = '提示') => show({ type: 'info', title, message })

  // 处理打印事件
  const handlePrintEvent = (eventType, details = {}) => {
    const config = printEventMap[eventType]
    if (!config) return

    let message = config.message
    if (details.filename) {
      message += `: ${details.filename}`
    }
    if (details.progress !== undefined) {
      message += ` (${details.progress.toFixed(1)}%)`
    }

    show({
      type: config.type,
      title: config.title,
      message,
      duration: config.type === 'success' ? 5000 : 4000
    })
  }

  // 处理闭环调控事件
  const handleControlEvent = (eventType, data = {}) => {
    const config = controlEventMap[eventType]
    if (!config) return

    let message = ''
    if (data.parameter && data.adjustment !== undefined) {
      const sign = data.adjustment > 0 ? '+' : ''
      message = `${data.parameter}: ${sign}${data.adjustment}`
    }

    show({
      type: config.type,
      title: config.title,
      message,
      duration: 4000
    })
  }

  // 处理预测告警
  const handlePredictionAlert = (prediction) => {
    const abnormal = []
    
    if (prediction.flow_rate?.label !== 'Normal') {
      abnormal.push(`流量${prediction.flow_rate.label === 'Low' ? '过低' : '过高'}`)
    }
    if (prediction.feed_rate?.label !== 'Normal') {
      abnormal.push(`速度${prediction.feed_rate.label === 'Low' ? '过低' : '过高'}`)
    }
    if (prediction.z_offset?.label !== 'Normal') {
      abnormal.push(`Z偏移${prediction.z_offset.label === 'Low' ? '过低' : '过高'}`)
    }
    if (prediction.hot_end?.label !== 'Normal') {
      abnormal.push(`温度${prediction.hot_end.label === 'Low' ? '过低' : '过高'}`)
    }

    if (abnormal.length > 0) {
      warning(
        `检测到异常: ${abnormal.join(', ')}`,
        '质量预警'
      )
    }
  }

  // 清除历史
  const clearHistory = () => {
    notifications.value = []
  }

  return {
    notifications,
    show,
    success,
    warning,
    error,
    info,
    handlePrintEvent,
    handleControlEvent,
    handlePredictionAlert,
    clearHistory
  }
}

export default useNotification
