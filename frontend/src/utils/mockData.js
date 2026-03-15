/**
 * 前端模拟数据模块
 * ================
 * 用于无后端调试，提供模拟 API 响应数据
 */

// 模拟打印机状态
export const mockPrinterStatus = {
  connected: true,
  simulation: true,
  printing: true,
  progress: 45.5,
  nozzle_temp: 200.5,
  bed_temp: 60.2,
  nozzle_target: 200,
  bed_target: 60,
  position: { x: 100.5, y: 80.2, z: 12.5 },
  state: 'Printing (Frontend Mock)',
  filename: 'test_print.gcode',
  print_time: 1800,
  print_time_left: 2200
}

// 模拟温度数据（带历史）
export const mockTemperatureHistory = {
  success: true,
  simulation: true,
  timestamp: new Date().toISOString(),
  nozzle: {
    actual: 200 + Math.random() * 2 - 1,
    target: 200
  },
  bed: {
    actual: 60 + Math.random() * 1 - 0.5,
    target: 60
  }
}

// 模拟设备状态
export const mockDeviceStatus = {
  available: true,
  simulation: true,
  devices: {
    ids: true,
    side_camera: true,
    fotric: true,
    vibration: false,
    m114: true,
    octoprint: true,
    octoprint_simulation: true
  },
  message: '设备状态查询成功（前端模拟）'
}

// 模拟相机状态
export const mockCameraStatus = {
  ids: {
    available: true,
    connected: true,
    frame_count: 1523,
    simulation: true
  },
  side: {
    available: true,
    connected: true,
    frame_count: 1523,
    simulation: true
  }
}

// 模拟预测结果
export const mockPrediction = {
  available: true,
  flow_rate: {
    class: 1,
    label: 'Normal',
    confidence: 0.85
  },
  feed_rate: {
    class: 1,
    label: 'Normal',
    confidence: 0.82
  },
  z_offset: {
    class: 1,
    label: 'Normal',
    confidence: 0.88
  },
  hot_end: {
    class: 1,
    label: 'Normal',
    confidence: 0.90
  },
  inference_time_ms: 45
}

// 模拟闭环控制状态
export const mockControlStatus = {
  status: 'idle',
  enabled: false,
  threshold: 0.7,
  window_size: 0,
  predictions_count: 0,
  regulations_count: 0,
  current_params: {
    flow_rate: 100,
    feed_rate: 100,
    z_offset: 0,
    target_hotend: 200
  }
}

// 模拟系统状态
export const mockSystemStatus = {
  status: 'running',
  timestamp: new Date().toISOString(),
  service: 'SmartAM_System Backend (Mock)',
  daq_available: true,
  camera: {
    ids: { available: true },
    side: { available: true }
  }
}

// 模拟文件列表
export const mockFiles = {
  success: true,
  files: {
    local: [
      { name: 'test_cube.gcode', path: 'test_cube.gcode', size: 1234567, date: Date.now() / 1000, location: 'local' },
      { name: 'tower_test.gcode', path: 'tower_test.gcode', size: 2345678, date: Date.now() / 1000 - 3600, location: 'local' }
    ],
    sdcard: []
  },
  total: 2
}

// 模拟健康检查
export const mockHealth = {
  status: 'healthy',
  api_version: '1.0.0',
  modules: ['printer', 'camera', 'inference', 'control', 'data']
}

// 生成实时温度数据（带波动）
export function generateMockTemperature() {
  return {
    success: true,
    simulation: true,
    timestamp: new Date().toISOString(),
    nozzle: {
      actual: 200 + Math.sin(Date.now() / 5000) * 2 + Math.random() * 0.5,
      target: 200
    },
    bed: {
      actual: 60 + Math.sin(Date.now() / 8000) * 0.5 + Math.random() * 0.3,
      target: 60
    }
  }
}

// 生成实时位置数据（模拟运动）
export function generateMockPosition() {
  const t = Date.now() / 1000
  return {
    x: 100 + Math.sin(t * 0.5) * 50,
    y: 100 + Math.cos(t * 0.3) * 50,
    z: 5 + (t % 3600) * 0.01 // 缓慢上升
  }
}

// 生成 WebSocket 实时数据
export function generateMockWebSocketData() {
  const t = Date.now() / 1000
  return {
    timestamp: new Date().toISOString(),
    frame_id: Math.floor(t * 10),
    printer: {
      connected: true,
      state: 'Printing',
      temperature: {
        nozzle: 200 + Math.sin(t) * 2,
        bed: 60 + Math.sin(t * 0.7) * 0.5,
        nozzle_target: 200,
        bed_target: 60
      },
      position: generateMockPosition(),
      progress: (t % 3600) / 3600 * 100,
      filename: 'mock_print.gcode',
      print_time: Math.floor(t % 3600),
      print_time_left: Math.floor(3600 - t % 3600)
    },
    acquisition: {
      state: 'running',
      frame_count: Math.floor(t * 2),
      duration: Math.floor(t),
      fps: 2.0,
      save_directory: 'data/mock_session',
      current_params: {
        flow_rate: 100,
        feed_rate: 100,
        z_offset: 0,
        target_hotend: 200
      },
      current_z: 5 + (t % 3600) * 0.01,
      param_mode: 'fixed'
    },
    thermal: {
      available: true,
      min: 25 + Math.random() * 5,
      max: 200 + Math.random() * 50,
      avg: 100 + Math.random() * 20,
      melt_pool: 220 + Math.random() * 30
    },
    camera: {
      ids_available: true,
      ids_frame_count: Math.floor(t * 2),
      side_available: true,
      side_frame_count: Math.floor(t * 2)
    },
    prediction: {
      available: true,
      flow_rate: { class: 1, label: 'Normal', confidence: 0.8 + Math.random() * 0.15 },
      feed_rate: { class: 1, label: 'Normal', confidence: 0.8 + Math.random() * 0.15 },
      z_offset: { class: 1, label: 'Normal', confidence: 0.8 + Math.random() * 0.15 },
      hot_end: { class: 1, label: 'Normal', confidence: 0.8 + Math.random() * 0.15 },
      inference_time_ms: 40 + Math.random() * 20
    }
  }
}

// 模拟 API 延迟
export function mockDelay(ms = 300) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
