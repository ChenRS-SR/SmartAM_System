import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const STORAGE_KEY = 'smartam-sls-devices-v2'
const BACKEND_DEVICES_ENDPOINT = '/api/sls/device-group/devices'
const BACKEND_SYNC_ENDPOINT = '/api/sls/device-group/sync'
const THUMBNAIL_WIDTH = 360
const THUMBNAIL_HEIGHT = 220
const PARAMETER_SCHEMA = [
  { id: 'current_layer', name: '当前层', unit: '层' },
  { id: 'sequence', name: '数据序号', unit: '' },
  { id: 'record_status', name: '状态参数', unit: '' },
  { id: 'data_time', name: '采集时间', unit: '' },
  { id: 'scraper_torque', name: '刮刀扭矩', unit: '%' },
  { id: 'oxygen', name: '成形室氧含量', unit: '%' },
  { id: 'ambient_oxygen', name: '环境氧含量', unit: '%' },
  { id: 'chamber_temperature', name: '成形室温度', unit: '℃' },
  { id: 'gas_flow', name: '循环气体流量', unit: 'm3/h' },
  { id: 'fan_speed', name: '风机转速', unit: '%' },
  { id: 'medium_filter_resistance', name: '中效滤芯阻力', unit: 'mBar' },
  { id: 'high_filter_resistance', name: '高效滤芯阻力', unit: 'mBar' },
  { id: 'gas_pressure', name: '气源压力', unit: 'Bar' },
  { id: 'compressed_air_pressure', name: '压缩空气压力', unit: 'Bar' },
  { id: 'servo_temperature_x', name: 'X轴伺服温度', unit: '℃' },
  { id: 'servo_temperature_y', name: 'Y轴伺服温度', unit: '℃' },
  { id: 'galvo_temperature_x', name: 'X轴振镜温度', unit: '℃' },
  { id: 'galvo_temperature_y', name: 'Y轴振镜温度', unit: '℃' },
  { id: 'output_current_x', name: 'X轴输出电流', unit: 'mA' },
  { id: 'output_current_y', name: 'Y轴输出电流', unit: 'mA' }
]
const statusTextMap = {
  '-1': '未开机',
  '0': '健康运行',
  '1': '铺粉/刮刀异常',
  '2': '激光系统异常',
  '3': '温度监测异常',
  '4': '复合故障'
}

const statusNameMap = {
  '-1': 'power_off',
  '0': 'healthy',
  '1': 'powder_fault',
  '2': 'laser_fault',
  '3': 'temp_fault',
  '4': 'compound_fault'
}

const encodeSvg = (svg) => `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`

const createGeneratedThumbnail = (seed, accent = '#2dd4bf') => {
  const serial = String(seed).padStart(2, '0')
  const svg = `
<svg xmlns="http://www.w3.org/2000/svg" width="${THUMBNAIL_WIDTH}" height="${THUMBNAIL_HEIGHT}" viewBox="0 0 ${THUMBNAIL_WIDTH} ${THUMBNAIL_HEIGHT}">
  <rect width="360" height="220" fill="#0f172a"/>
  <rect x="42" y="24" width="276" height="172" rx="8" fill="#111827" stroke="${accent}" stroke-width="3"/>
  <rect x="72" y="48" width="216" height="102" rx="6" fill="#1e293b"/>
  <path d="M92 118 L160 82 L206 105 L265 70" fill="none" stroke="${accent}" stroke-width="4" stroke-linecap="round"/>
  <rect x="92" y="160" width="176" height="12" rx="6" fill="#475569"/>
  <circle cx="292" cy="42" r="8" fill="${accent}"/>
  <text x="54" y="206" font-family="Arial, sans-serif" font-size="13" fill="#cbd5e1">SLS-${serial}</text>
</svg>`
  return encodeSvg(svg)
}

const buildHealthData = (statusCode, labels = []) => {
  const code = Number(statusCode)
  const statusLabels = labels.length ? labels : [statusTextMap[String(code)] || '未知状态']
  const healthData = {
    status: statusNameMap[String(code)] || 'compound_fault',
    status_code: code,
    status_labels: statusLabels,
    laser_system: { status: 'healthy', message: '健康' },
    powder_system: { status: 'healthy', message: '健康' },
    temp_system: { status: 'healthy', message: '健康' }
  }

  if (code === -1) {
    healthData.laser_system = { status: 'unknown', message: '未检测' }
    healthData.powder_system = { status: 'unknown', message: '未检测' }
    healthData.temp_system = { status: 'unknown', message: '未检测' }
  } else if (code === 1) {
    healthData.powder_system = { status: 'fault', message: '铺粉/刮刀系统异常' }
  } else if (code === 2) {
    healthData.laser_system = { status: 'fault', message: '激光器/水冷机异常' }
  } else if (code === 3) {
    healthData.temp_system = { status: 'fault', message: '温度监测系统异常' }
  } else if (code === 4) {
    healthData.laser_system = { status: 'fault', message: '需检查' }
    healthData.powder_system = { status: 'fault', message: '需检查' }
    healthData.temp_system = { status: 'fault', message: '需检查' }
  }
  return healthData
}

const cloneHealthData = (healthData = {}) => ({
  ...healthData,
  status_labels: [...(healthData.status_labels || [])],
  laser_system: { ...(healthData.laser_system || {}) },
  powder_system: { ...(healthData.powder_system || {}) },
  temp_system: { ...(healthData.temp_system || {}) }
})

const normalizeParameterValue = (value) => {
  if (value === undefined || value === null || value === '') return '--'
  return String(value)
}

const normalizeParameters = (parameters = [], statusText = '--') => {
  const source = Array.isArray(parameters) ? parameters : []
  return PARAMETER_SCHEMA.map((schema) => {
    const matched = source.find((param) => param.id === schema.id || param.name === schema.name)
    const value = schema.id === 'record_status'
      ? normalizeParameterValue(matched?.value || statusText)
      : normalizeParameterValue(matched?.value)
    return {
      id: schema.id,
      name: schema.name,
      value,
      unit: matched?.unit ?? schema.unit
    }
  })
}

const cloneDevice = (device) => ({
  ...device,
  healthData: cloneHealthData(device.healthData),
  parameterSchema: PARAMETER_SCHEMA.map((param) => ({ ...param })),
  parameters: normalizeParameters(device.parameters, device.statusText),
  mockCase: device.mockCase ? JSON.parse(JSON.stringify(device.mockCase)) : null,
  mockVideo: device.mockVideo ? JSON.parse(JSON.stringify(device.mockVideo)) : null,
  diagnosis: device.diagnosis ? { ...device.diagnosis } : null,
  realData: device.realData ? { ...device.realData } : null
})

const normalizeDevice = (device, index) => {
  const sourceStatusCode = device.healthData?.status_code ?? (device.online === false ? -1 : 0)
  const statusCode = Number(sourceStatusCode)
  const online = device.online !== false
  const health = online ? (statusCode > 0 ? 'fault' : (statusCode === 0 ? 'healthy' : 'power_off')) : 'power_off'
  const healthData = device.healthData
    ? cloneHealthData(device.healthData)
    : buildHealthData(statusCode, device.statusText ? [device.statusText] : [])

  return {
    id: device.id || `sls-${Date.now()}-${index}`,
    tag: device.tag || '',
    dataTag: device.dataTag || device.tag || '',
    databaseTag: device.databaseTag || device.dataTag || device.tag || '',
    owner: device.owner || '华中数控',
    name: device.name || `SLS-${index + 1}`,
    model: device.model || '华中数控 SLS',
    serial: device.serial || `SLS-${String(index + 1).padStart(2, '0')}`,
    location: device.location || '未设置',
    online,
    health,
    statusText: device.statusText || statusTextMap[String(statusCode)] || '未知状态',
    thumbnail: device.thumbnail || createGeneratedThumbnail(index + 1),
    parameterSchema: PARAMETER_SCHEMA.map((param) => ({ ...param })),
    parameters: normalizeParameters(device.parameters, device.statusText || statusTextMap[String(statusCode)] || '--'),
    mockCase: device.mockCase || null,
    mockVideo: device.mockVideo || null,
    healthData,
    diagnosis: device.diagnosis || null,
    realData: device.realData || null,
    updatedAt: device.updatedAt || '',
    dataDirectory: device.dataDirectory || '',
    source: device.source || (device.dataTag ? 'SLS' : 'manual')
  }
}

const loadLocalDevices = () => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (!saved) return []
  const parsed = JSON.parse(saved)
  if (!Array.isArray(parsed)) return []
  return parsed.map(normalizeDevice).map(cloneDevice)
}

export const useSlsDeviceStore = defineStore('slsDevices', () => {
  const devices = ref(loadLocalDevices())
  const loading = ref(false)
  const lastLoadError = ref('')
  const sourceInfo = ref({
    sourceRoot: '',
    diagnosisPolicy: '',
    statusCodeMap: {},
    parameterSchema: PARAMETER_SCHEMA.map((param) => ({ ...param }))
  })

  const onlineCount = computed(() => devices.value.filter((device) => device.online).length)
  const faultCount = computed(() => devices.value.filter((device) => device.online && device.health === 'fault').length)
  const healthyCount = computed(() => devices.value.filter((device) => device.online && device.health === 'healthy').length)
  const firstDevice = computed(() => devices.value[0])

  const persist = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(devices.value))
  }

  const getDeviceById = (id) => devices.value.find((device) => device.id === id)

  const loadDevicesFromBackend = async () => {
    loading.value = true
    lastLoadError.value = ''
    try {
      const response = await fetch(BACKEND_DEVICES_ENDPOINT)
      if (!response.ok) {
        throw new Error(`设备群数据接口异常: ${response.status}`)
      }
      const payload = await response.json()
      if (!payload.success || !Array.isArray(payload.devices)) {
        throw new Error('设备群数据格式不正确')
      }

      sourceInfo.value = {
        sourceRoot: payload.sourceRoot || '',
        diagnosisPolicy: payload.diagnosisPolicy || '',
        statusCodeMap: payload.statusCodeMap || {},
        parameterSchema: Array.isArray(payload.parameterSchema) ? payload.parameterSchema : PARAMETER_SCHEMA
      }

      // 文件级数据库是页面设备列表的唯一权威来源，避免本地缓存重复追加手动设备。
      const backendDevices = payload.devices.map((device, index) => normalizeDevice({ ...device, source: device.source || 'SLS' }, index))
      devices.value = backendDevices.map(cloneDevice)
      persist()
      return devices.value
    } catch (error) {
      lastLoadError.value = error.message
      throw error
    } finally {
      loading.value = false
    }
  }

  const toPlainDevice = (device) => {
    const plainDevice = JSON.parse(JSON.stringify(device))
    delete plainDevice.mockVideo
    return plainDevice
  }

  const writeDeviceToBackend = async (device, method = 'PATCH') => {
    const url = method === 'POST'
      ? BACKEND_DEVICES_ENDPOINT
      : `${BACKEND_DEVICES_ENDPOINT}/${encodeURIComponent(device.id)}`
    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(toPlainDevice(device))
    })
    if (!response.ok) {
      const message = await response.text()
      throw new Error(message || `文件数据库写入失败: ${response.status}`)
    }
    const payload = await response.json()
    if (!payload.success || !payload.device) {
      throw new Error('文件数据库返回格式不正确')
    }
    return normalizeDevice(payload.device, devices.value.length)
  }

  const addDevice = async (payload) => {
    const nextIndex = devices.value.length + 1
    const online = payload.online !== false
    const statusCode = online ? (payload.health === 'fault' ? 4 : 0) : -1
    const device = normalizeDevice({
      id: `manual-sls-${Date.now()}`,
      model: '华中数控 SLS',
      owner: '华中数控',
      source: 'manual',
      online,
      healthData: buildHealthData(statusCode, [payload.statusText || statusTextMap[String(statusCode)]]),
      statusText: payload.statusText || statusTextMap[String(statusCode)],
      thumbnail: createGeneratedThumbnail(nextIndex),
      ...payload
    }, nextIndex)
    const savedDevice = await writeDeviceToBackend(device, 'POST')
    devices.value.push(cloneDevice(savedDevice))
    persist()
    return savedDevice.id
  }

  const updateDevice = async (id, patch) => {
    const index = devices.value.findIndex((device) => device.id === id)
    if (index === -1) return

    const shouldPatchHealth = 'online' in patch || 'health' in patch || 'statusText' in patch
    const patchOnline = patch.online !== undefined ? patch.online !== false : devices.value[index].online !== false
    const statusCode = !patchOnline
      ? -1
      : (patch.health === 'fault' ? (devices.value[index].healthData?.status_code > 0 ? devices.value[index].healthData.status_code : 4) : 0)
    const healthPatch = shouldPatchHealth
      ? { healthData: buildHealthData(statusCode, [patch.statusText || statusTextMap[String(statusCode)]]) }
      : {}
    const merged = normalizeDevice({ ...devices.value[index], ...patch, online: patchOnline, ...healthPatch }, index)
    const savedDevice = await writeDeviceToBackend(merged, 'PATCH')
    devices.value[index] = cloneDevice(savedDevice)
    persist()
  }

  const syncDevicesToBackend = async () => {
    const response = await fetch(BACKEND_SYNC_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ devices: devices.value.map(toPlainDevice) })
    })
    if (!response.ok) {
      const message = await response.text()
      throw new Error(message || `文件数据库同步失败: ${response.status}`)
    }
    const payload = await response.json()
    if (!payload.success) {
      throw new Error('文件数据库同步返回格式不正确')
    }
    await loadDevicesFromBackend()
    return payload
  }

  const updateDeviceHealth = (id, healthData) => {
    const device = getDeviceById(id)
    if (!device || !healthData) return

    const statusCode = Number(healthData.status_code ?? -1)
    device.healthData = cloneHealthData(healthData)
    device.online = device.online !== false
    device.health = statusCode > 0 ? 'fault' : (statusCode === 0 ? 'healthy' : 'power_off')
    device.statusText = statusCode > 0
      ? (healthData.status_labels || [statusTextMap[String(statusCode)] || '故障']).join('、')
      : (statusTextMap[String(statusCode)] || '未开机')
    device.parameters = normalizeParameters(device.parameters, device.statusText)
    persist()
  }

  const updateDeviceParameters = (id, parameters) => {
    const device = getDeviceById(id)
    if (!device || !Array.isArray(parameters)) return
    device.parameters = normalizeParameters(parameters, device.statusText)
    persist()
  }

  // 图片只保留固定尺寸缩略图，避免本地持久化数据过大。
  const compressImageFile = (file) => new Promise((resolve, reject) => {
    if (!file) {
      reject(new Error('未选择图片'))
      return
    }

    const image = new Image()
    const objectUrl = URL.createObjectURL(file)

    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = THUMBNAIL_WIDTH
      canvas.height = THUMBNAIL_HEIGHT
      const context = canvas.getContext('2d')

      const scale = Math.max(THUMBNAIL_WIDTH / image.width, THUMBNAIL_HEIGHT / image.height)
      const drawWidth = image.width * scale
      const drawHeight = image.height * scale
      const offsetX = (THUMBNAIL_WIDTH - drawWidth) / 2
      const offsetY = (THUMBNAIL_HEIGHT - drawHeight) / 2

      context.fillStyle = '#0f172a'
      context.fillRect(0, 0, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT)
      context.drawImage(image, offsetX, offsetY, drawWidth, drawHeight)
      URL.revokeObjectURL(objectUrl)
      resolve(canvas.toDataURL('image/jpeg', 0.82))
    }

    image.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error('图片读取失败'))
    }

    image.src = objectUrl
  })

  return {
    devices,
    loading,
    lastLoadError,
    sourceInfo,
    onlineCount,
    faultCount,
    healthyCount,
    firstDevice,
    loadDevicesFromBackend,
    syncDevicesToBackend,
    addDevice,
    updateDevice,
    updateDeviceHealth,
    updateDeviceParameters,
    getDeviceById,
    compressImageFile
  }
})
