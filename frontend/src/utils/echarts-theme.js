// ECharts 暗黑主题配置
export const darkTheme = {
  color: ['#00d4ff', '#00ff88', '#ffc107', '#ff6b6b', '#9d4edd', '#ff9f1c'],
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: 'Inter, system-ui, sans-serif'
  },
  title: {
    textStyle: {
      color: '#e2e8f0'
    },
    subtextStyle: {
      color: '#a0aec0'
    }
  },
  line: {
    smooth: true,
    symbol: 'circle',
    symbolSize: 6
  },
  categoryAxis: {
    axisLine: {
      lineStyle: {
        color: 'rgba(0, 212, 255, 0.3)'
      }
    },
    axisTick: {
      lineStyle: {
        color: 'rgba(0, 212, 255, 0.3)'
      }
    },
    axisLabel: {
      color: '#a0aec0'
    },
    splitLine: {
      lineStyle: {
        color: 'rgba(0, 212, 255, 0.1)'
      }
    }
  },
  valueAxis: {
    axisLine: {
      lineStyle: {
        color: 'rgba(0, 212, 255, 0.3)'
      }
    },
    axisTick: {
      lineStyle: {
        color: 'rgba(0, 212, 255, 0.3)'
      }
    },
    axisLabel: {
      color: '#a0aec0'
    },
    splitLine: {
      lineStyle: {
        color: 'rgba(0, 212, 255, 0.1)'
      }
    }
  },
  legend: {
    textStyle: {
      color: '#a0aec0'
    }
  },
  tooltip: {
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    borderColor: 'rgba(0, 212, 255, 0.3)',
    borderWidth: 1,
    textStyle: {
      color: '#e2e8f0'
    },
    padding: 12,
    borderRadius: 8,
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.5)'
  },
  grid: {
    left: 50,
    right: 30,
    top: 40,
    bottom: 30
  }
}

// 通用图表配置生成器
export const createChartOption = (type, config = {}) => {
  const baseOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: type === 'pie' ? 'item' : 'axis',
      ...darkTheme.tooltip
    }
  }

  if (type === 'line' || type === 'bar') {
    baseOption.grid = { ...darkTheme.grid }
    baseOption.xAxis = {
      type: 'category',
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: '#a0aec0' },
      ...config.xAxis
    }
    baseOption.yAxis = {
      type: 'value',
      axisLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.3)' } },
      axisLabel: { color: '#a0aec0' },
      splitLine: { lineStyle: { color: 'rgba(0, 212, 255, 0.1)' } },
      ...config.yAxis
    }
  }

  return { ...baseOption, ...config }
}

// 渐变色生成器
export const createGradient = (color1, color2) => {
  return {
    type: 'linear',
    x: 0, y: 0, x2: 0, y2: 1,
    colorStops: [
      { offset: 0, color: color1 },
      { offset: 1, color: color2 }
    ]
  }
}

// 预设渐变色
export const gradients = {
  blue: createGradient('rgba(0, 212, 255, 0.5)', 'rgba(0, 212, 255, 0.05)'),
  green: createGradient('rgba(0, 255, 136, 0.5)', 'rgba(0, 255, 136, 0.05)'),
  orange: createGradient('rgba(255, 193, 7, 0.5)', 'rgba(255, 193, 7, 0.05)'),
  red: createGradient('rgba(255, 77, 79, 0.5)', 'rgba(255, 77, 79, 0.05)')
}
