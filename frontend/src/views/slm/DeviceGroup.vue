<template>
  <div class="device-group-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">设备群监测</h1>
        <div class="page-subtitle">
          {{ deviceStore.sourceInfo.diagnosisPolicy || 'SLM 设备群实时状态' }}
        </div>
      </div>
      <div class="header-actions">
        <el-button :loading="syncingDatabase" @click="syncFileDatabase">
          <el-icon><Refresh /></el-icon>
          同步文件数据库
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          导入设备
        </el-button>
      </div>
    </div>

    <section class="source-bar">
      <span>数据源</span>
      <strong>{{ deviceStore.sourceInfo.sourceRoot || '正在加载 7103 数据' }}</strong>
      <el-tag size="small" :type="isMockMode ? 'warning' : 'info'">
        {{ isMockMode ? '模拟模式' : '真实模式' }}
      </el-tag>
      <el-tag size="small" type="info">状态码 0-4</el-tag>
    </section>

    <section class="fleet-summary">
      <div class="summary-item">
        <span class="summary-label">设备总数</span>
        <strong>{{ displayDevices.length }}</strong>
      </div>
      <div class="summary-item">
        <span class="summary-label">在线</span>
        <strong>{{ fleetStats.online }}</strong>
      </div>
      <div class="summary-item">
        <span class="summary-label">健康</span>
        <strong>{{ fleetStats.healthy }}</strong>
      </div>
      <div class="summary-item danger">
        <span class="summary-label">故障</span>
        <strong>{{ fleetStats.fault }}</strong>
      </div>
    </section>

    <section v-loading="deviceStore.loading" class="device-grid">
      <article
        v-for="device in displayDevices"
        :key="device.id"
        class="device-card"
        :class="{ offline: !device.online, fault: device.online && device.health === 'fault' }"
        @click="openDeviceDashboard(device.id)"
      >
        <div class="thumbnail-wrap">
          <img :src="device.thumbnail" :alt="device.name" class="device-thumbnail" />
          <div v-if="device.dataTag" class="data-tag">{{ device.dataTag }}</div>
          <div class="status-chip" :class="statusClass(device)">
            <span class="status-dot"></span>
            {{ statusText(device) }}
          </div>
        </div>
        <div class="device-content">
          <div class="device-title-row">
            <div>
              <h2>{{ device.name }}</h2>
              <span>{{ device.model }}</span>
            </div>
            <el-tooltip content="编辑设备" placement="top">
              <el-button
                text
                class="icon-btn"
                @click.stop="openEditDialog(deviceStore.getDeviceById(device.id) || device)"
              >
                <el-icon><EditPen /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
          <div class="device-meta">
            <span>{{ device.location }}</span>
            <span>{{ device.serial }}</span>
          </div>
          <div class="parameter-preview">
            <div
              v-for="param in previewParameters(device)"
              :key="param.id || param.name"
              class="preview-item"
              :class="{ 'status-preview-item': param.id === 'record_status' || param.name === '状态参数' }"
              :title="param.id === 'record_status' || param.name === '状态参数' ? param.value : ''"
            >
              <span>{{ param.name }}</span>
              <strong>{{ param.value }}</strong>
              <em>{{ param.unit }}</em>
            </div>
          </div>
          <div class="device-footer">
            <el-tag v-if="device.databaseTag" type="warning" size="small">
              {{ device.databaseTag }}
            </el-tag>
            <el-tag
              v-if="isMockMode && getDeviceMockCase(device)"
              :type="device.mockCaseAvailable?.ready ? 'success' : 'info'"
              size="small"
            >
              {{ getDeviceMockCase(device).label }}
            </el-tag>
            <el-tag
              v-else-if="isMockMode && isStored7103MockDevice(device)"
              type="success"
              size="small"
            >
              7103存储数据
            </el-tag>
            <el-tag :type="device.online ? 'success' : 'info'" size="small">
              {{ device.online ? '在线' : '离线' }}
            </el-tag>
            <el-tag :type="healthTagType(device)" size="small">
              {{ device.statusText }}
            </el-tag>
            <el-tag v-if="device.healthData?.status_code !== undefined" type="info" size="small">
              状态码 {{ device.healthData.status_code }}
            </el-tag>
          </div>
        </div>
      </article>

      <button class="add-device-tile" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        <span>导入设备</span>
      </button>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="editingDeviceId ? '编辑设备' : '导入设备'"
      width="620px"
      destroy-on-close
    >
      <el-form :model="deviceForm" label-width="96px">
        <el-form-item label="设备名称">
          <el-input v-model="deviceForm.name" maxlength="32" />
        </el-form-item>
        <el-form-item label="设备型号">
          <el-input v-model="deviceForm.model" maxlength="32" />
        </el-form-item>
        <el-form-item label="设备归属">
          <el-input v-model="deviceForm.owner" maxlength="16" />
        </el-form-item>
        <el-form-item label="设备标签">
          <el-input v-model="deviceForm.databaseTag" maxlength="48" />
        </el-form-item>
        <el-form-item label="设备编号">
          <el-input v-model="deviceForm.serial" maxlength="32" />
        </el-form-item>
        <el-form-item label="安装位置">
          <el-input v-model="deviceForm.location" maxlength="48" />
        </el-form-item>
        <el-form-item label="接入状态">
          <el-radio-group v-model="deviceForm.online">
            <el-radio-button :label="true">在线</el-radio-button>
            <el-radio-button :label="false">离线</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="deviceForm.online" label="健康状态">
          <el-radio-group v-model="deviceForm.health">
            <el-radio-button label="healthy">健康</el-radio-button>
            <el-radio-button label="fault">故障</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态文本">
          <el-input v-model="deviceForm.statusText" maxlength="24" />
        </el-form-item>
        <el-form-item label="缩略图">
          <div class="thumbnail-editor">
            <img :src="deviceForm.thumbnail" alt="设备缩略图" class="thumbnail-preview" />
            <el-upload
              accept="image/*"
              :auto-upload="false"
              :show-file-list="false"
              :on-change="handleThumbnailChange"
            >
              <el-button>
                <el-icon><Upload /></el-icon>
                上传图片
              </el-button>
            </el-upload>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingDevice" @click="saveDevice">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { EditPen, Plus, Refresh, Upload } from '@element-plus/icons-vue'
import { useSlmDeviceStore } from '../../stores/slmDevices'
import { readSlmBenchSettings } from '../../utils/slmBenchSettings'
import { buildMockCaseHealthData, buildMockCaseStatusText, checkMockCaseMedia, getDeviceMockCase } from '../../utils/slmMockCases'

const router = useRouter()
const deviceStore = useSlmDeviceStore()

const dialogVisible = ref(false)
const editingDeviceId = ref('')
const savingDevice = ref(false)
const syncingDatabase = ref(false)
const benchSettings = ref(readSlmBenchSettings())
const realtimeSamples = ref({})
const mockCaseAvailability = ref({})
const deviceForm = reactive({
  name: '',
  model: '铂力特 S310',
  owner: '铂力特',
  databaseTag: '',
  serial: '',
  location: '',
  online: true,
  health: 'healthy',
  statusText: '待机',
  thumbnail: ''
})

let realtimePollTimer = null
let realtimePollingBusy = false
let mockCaseProbeSerial = 0
const REALTIME_POLL_INTERVAL_MS = 3000

const isMockMode = computed(() => benchSettings.value.use_mock)

const emptyParameters = (device, statusText = '待连接') => {
  const schema = Array.isArray(device.parameterSchema) && device.parameterSchema.length
    ? device.parameterSchema
    : (device.parameters || [])
  return schema.map((param) => ({
    id: param.id,
    name: param.name,
    value: param.id === 'record_status' || param.name === '状态参数' ? statusText : '--',
    unit: param.unit || ''
  }))
}

const createWaitingHealthData = () => ({
  status: 'power_off',
  status_code: -1,
  status_labels: ['等待数据传输'],
  laser_system: { status: 'unknown', message: '等待数据传输' },
  powder_system: { status: 'unknown', message: '等待数据传输' },
  gas_system: { status: 'unknown', message: '等待数据传输' }
})

const isDeviceOnline = (device) => device?.online !== false

const toOfflineDevice = (device, statusText = '离线') => ({
  ...device,
  online: false,
  health: 'power_off',
  statusText,
  healthData: createWaitingHealthData(),
  parameters: emptyParameters(device, statusText)
})

const toWaitingDevice = (device, statusText = '等待实时数据') => ({
  ...device,
  online: true,
  health: 'power_off',
  statusText,
  healthData: createWaitingHealthData(),
  parameters: emptyParameters(device, statusText)
})

const toRealtimeDevice = (device, sample) => {
  if (!isDeviceOnline(device)) return toOfflineDevice(device)
  if (!sample?.hasData) return toWaitingDevice(device)
  const healthData = sample.health || createWaitingHealthData()
  const statusCode = Number(healthData.status_code ?? -1)
  const statusText = (healthData.status_labels || []).filter(Boolean).join('、')
    || sample.diagnosis?.frontendStatusLabel
    || sample.diagnosis?.statusLabel
    || (statusCode === 0 ? '健康运行' : '故障')
  return {
    ...device,
    online: true,
    health: statusCode > 0 ? 'fault' : (statusCode === 0 ? 'healthy' : 'power_off'),
    statusText,
    healthData,
    parameters: Array.isArray(sample.parameters) && sample.parameters.length ? sample.parameters : emptyParameters(device, statusText),
    diagnosis: sample.diagnosis || device.diagnosis,
    updatedAt: sample.eventTime || sample.receivedAt || device.updatedAt,
    realData: sample
  }
}

const toMockWaitingDevice = (device, statusText) => ({
  ...toOfflineDevice(device, statusText),
  statusText,
  parameters: emptyParameters(device, statusText)
})

const cloneHealthData = (healthData = {}) => ({
  ...healthData,
  status_labels: [...(healthData.status_labels || [])],
  laser_system: { ...(healthData.laser_system || {}) },
  powder_system: { ...(healthData.powder_system || {}) },
  gas_system: { ...(healthData.gas_system || {}) }
})

const isStored7103MockDevice = (device) => !getDeviceMockCase(device) && device?.source === '7103'

const toStored7103MockDevice = (device) => {
  const healthData = cloneHealthData(device.healthData || createWaitingHealthData())
  const statusCode = Number(healthData.status_code ?? -1)
  const online = isDeviceOnline(device)
  const statusText = (healthData.status_labels || []).filter(Boolean).join('、')
    || device.statusText
    || (online ? '7103存储数据' : '无有效7103状态')

  return {
    ...device,
    online,
    health: online ? (statusCode > 0 ? 'fault' : 'healthy') : 'power_off',
    statusText,
    parameters: Array.isArray(device.parameters) && device.parameters.length
      ? device.parameters
      : emptyParameters(device, statusText),
    healthData
  }
}

const toMockDevice = (device) => {
  const mockCase = getDeviceMockCase(device)
  if (!mockCase && isStored7103MockDevice(device)) return toStored7103MockDevice(device)

  const availability = mockCaseAvailability.value[device.id] || { hasCase: Boolean(mockCase), ready: false, channels: {} }
  const statusText = buildMockCaseStatusText(mockCase, availability)
  if (!mockCase || !availability.ready) return toMockWaitingDevice(device, statusText)

  const healthData = buildMockCaseHealthData(mockCase) || device.healthData || createWaitingHealthData()
  const statusCode = Number(healthData.status_code ?? 0)
  return {
    ...device,
    online: true,
    health: statusCode > 0 ? 'fault' : 'healthy',
    statusText: (healthData.status_labels || []).filter(Boolean).join('、') || statusText,
    mockCase,
    mockCaseAvailable: availability,
    parameters: Array.isArray(device.parameters) && device.parameters.length
      ? device.parameters
      : emptyParameters(device, statusText),
    healthData
  }
}

const displayDevices = computed(() => {
  if (isMockMode.value) return deviceStore.devices.map(toMockDevice)
  return deviceStore.devices.map((device) => toRealtimeDevice(device, realtimeSamples.value[device.id]))
})

const fleetStats = computed(() => ({
  online: displayDevices.value.filter((device) => device.online).length,
  healthy: displayDevices.value.filter((device) => device.online && device.health === 'healthy').length,
  fault: displayDevices.value.filter((device) => device.online && device.health === 'fault').length
}))

const previewParameters = (device) => Array.isArray(device.parameters) ? device.parameters.slice(0, 3) : []

const statusClass = (device) => {
  if (!device.online) return 'offline'
  return device.health === 'fault' ? 'fault' : 'healthy'
}

const statusText = (device) => {
  return device.online ? '在线' : '离线'
}

const healthTagType = (device) => {
  if (!device.online) return 'info'
  return device.health === 'fault' ? 'danger' : 'success'
}

const resetForm = (device = null) => {
  editingDeviceId.value = device?.id || ''
  Object.assign(deviceForm, {
    name: device?.name || '',
    model: device?.model || '铂力特 S310',
    owner: device?.owner || '铂力特',
    databaseTag: device?.databaseTag || device?.dataTag || '',
    serial: device?.serial || '',
    location: device?.location || '',
    online: device?.online ?? true,
    health: device?.health === 'fault' ? 'fault' : 'healthy',
    statusText: device?.statusText || '待机',
    thumbnail: device?.thumbnail || deviceStore.firstDevice?.thumbnail || ''
  })
}

const openCreateDialog = () => {
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = (device) => {
  resetForm(device)
  dialogVisible.value = true
}

const openDeviceDashboard = (deviceId) => {
  localStorage.setItem('slmSelectedDeviceId', deviceId)
  router.push({ path: `/slm/device/${deviceId}`, query: { tab: 'status' } })
}

const handleThumbnailChange = async (uploadFile) => {
  try {
    deviceForm.thumbnail = await deviceStore.compressImageFile(uploadFile.raw)
    ElMessage.success('缩略图已压缩')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

const buildPatch = () => {
  const online = Boolean(deviceForm.online)
  const health = online ? deviceForm.health : 'power_off'
  const owner = deviceForm.owner.trim() || '铂力特'
  const model = deviceForm.model.trim()
  const serial = deviceForm.serial.trim()
  const fallbackTag = `${owner}-${model.replace(/^铂力特\s*/, '') || 'SLM'}-${serial || deviceForm.name.trim()}`
  return {
    name: deviceForm.name.trim(),
    model,
    owner,
    databaseTag: deviceForm.databaseTag.trim() || fallbackTag,
    serial,
    location: deviceForm.location.trim(),
    online,
    health,
    statusText: online ? (deviceForm.statusText.trim() || (health === 'fault' ? '故障' : '健康')) : '离线',
    thumbnail: deviceForm.thumbnail
  }
}

const saveDevice = async () => {
  if (!deviceForm.name.trim()) {
    ElMessage.warning('请输入设备名称')
    return
  }

  const patch = buildPatch()
  savingDevice.value = true
  try {
    if (editingDeviceId.value) {
      await deviceStore.updateDevice(editingDeviceId.value, patch)
    } else {
      await deviceStore.addDevice(patch)
    }
    dialogVisible.value = false
    ElMessage.success('设备信息已保存并同步到文件数据库')
  } catch (error) {
    ElMessage.error(error.message || '设备信息保存失败')
  } finally {
    savingDevice.value = false
  }
}

const syncFileDatabase = async () => {
  syncingDatabase.value = true
  try {
    const result = await deviceStore.syncDevicesToBackend()
    ElMessage.success(`文件数据库已同步，共 ${result.deviceCount} 台设备`)
  } catch (error) {
    ElMessage.error(error.message || '文件数据库同步失败')
  } finally {
    syncingDatabase.value = false
  }
}

const fetchRealtimeFleetSamples = async () => {
  if (isMockMode.value || !deviceStore.devices.length || realtimePollingBusy) return
  realtimePollingBusy = true

  try {
    const realtimeDevices = deviceStore.devices.filter(isDeviceOnline)
    const offlineSamples = Object.fromEntries(
      deviceStore.devices
        .filter((device) => !isDeviceOnline(device))
        .map((device) => [device.id, { hasData: false, offline: true }])
    )
    const results = await Promise.allSettled(realtimeDevices.map(async (device) => {
      const response = await fetch(`/api/slm/realtime/data/${encodeURIComponent(device.id)}`)
      if (!response.ok) throw new Error(`实时数据接口异常: ${response.status}`)
      const payload = await response.json()
      return [device.id, payload.sample || { hasData: false }]
    }))

    const nextSamples = { ...realtimeSamples.value, ...offlineSamples }
    results.forEach((result) => {
      if (result.status === 'fulfilled') {
        const [deviceId, sample] = result.value
        nextSamples[deviceId] = sample
      }
    })
    realtimeSamples.value = nextSamples
  } finally {
    realtimePollingBusy = false
  }
}

const refreshMockCaseAvailability = async () => {
  mockCaseProbeSerial += 1
  const serial = mockCaseProbeSerial
  if (!isMockMode.value || !deviceStore.devices.length) {
    mockCaseAvailability.value = {}
    return
  }

  const devicesWithVideoCase = deviceStore.devices.filter((device) => getDeviceMockCase(device))
  const results = await Promise.all(devicesWithVideoCase.map(async (device) => {
    const mockCase = getDeviceMockCase(device)
    const availability = await checkMockCaseMedia(mockCase)
    return [device.id, availability]
  }))
  if (serial !== mockCaseProbeSerial) return
  mockCaseAvailability.value = Object.fromEntries(results)
}

const stopRealtimePolling = () => {
  if (realtimePollTimer) {
    clearInterval(realtimePollTimer)
    realtimePollTimer = null
  }
}

const startRealtimePolling = () => {
  stopRealtimePolling()
  if (isMockMode.value) {
    realtimeSamples.value = {}
    refreshMockCaseAvailability().catch((error) => {
      console.error('[DeviceGroup] 检查模拟用例失败:', error)
    })
    return
  }
  fetchRealtimeFleetSamples().catch((error) => {
    console.error('[DeviceGroup] 获取实时设备群状态失败:', error)
  })
  realtimePollTimer = setInterval(() => {
    fetchRealtimeFleetSamples().catch((error) => {
      console.error('[DeviceGroup] 获取实时设备群状态失败:', error)
    })
  }, REALTIME_POLL_INTERVAL_MS)
}

const refreshBenchSettings = () => {
  const previousMode = benchSettings.value.use_mock
  benchSettings.value = readSlmBenchSettings()
  if (previousMode !== benchSettings.value.use_mock) {
    startRealtimePolling()
  } else if (benchSettings.value.use_mock) {
    refreshMockCaseAvailability().catch((error) => {
      console.error('[DeviceGroup] 刷新模拟用例失败:', error)
    })
  }
}

watch(() => deviceStore.devices.map((device) => device.id).join(','), () => {
  startRealtimePolling()
})

onMounted(async () => {
  try {
    await deviceStore.loadDevicesFromBackend()
  } catch (error) {
    ElMessage.error(error.message || '加载7103设备群数据失败')
  }

  refreshBenchSettings()
  startRealtimePolling()
  window.addEventListener('focus', refreshBenchSettings)
  window.addEventListener('storage', refreshBenchSettings)
})

onUnmounted(() => {
  stopRealtimePolling()
  window.removeEventListener('focus', refreshBenchSettings)
  window.removeEventListener('storage', refreshBenchSettings)
})
</script>

<style scoped>
.device-group-page {
  max-width: 1680px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
}

.page-subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: #94a3b8;
}

.source-bar {
  min-height: 44px;
  margin-bottom: 18px;
  padding: 10px 14px;
  border: 1px solid rgba(100, 116, 139, 0.26);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  gap: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.source-bar strong {
  color: #cbd5e1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fleet-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.summary-item {
  min-height: 76px;
  padding: 14px 16px;
  border: 1px solid rgba(100, 116, 139, 0.28);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.58);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.summary-item strong {
  font-size: 28px;
  color: #e2e8f0;
}

.summary-label {
  color: #94a3b8;
  font-size: 13px;
}

.summary-item.danger strong {
  color: #f87171;
}

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.device-card,
.add-device-tile {
  min-height: 390px;
  border: 1px solid rgba(100, 116, 139, 0.28);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.62);
}

.device-card {
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

.device-card:hover {
  border-color: rgba(45, 212, 191, 0.65);
  transform: translateY(-2px);
  background: rgba(15, 23, 42, 0.82);
}

.device-card.fault {
  border-color: rgba(239, 68, 68, 0.52);
}

.device-card.offline {
  opacity: 0.72;
}

.thumbnail-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 18 / 11;
  background: #0f172a;
  overflow: hidden;
}

.device-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.status-chip {
  position: absolute;
  top: 10px;
  right: 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 9px;
  border-radius: 999px;
  color: #e2e8f0;
  font-size: 12px;
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.28);
}

.data-tag {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 5px 9px;
  border-radius: 999px;
  color: #f8fafc;
  font-size: 12px;
  font-weight: 600;
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(251, 191, 36, 0.42);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.status-chip.healthy .status-dot {
  background: #22c55e;
  box-shadow: 0 0 8px #22c55e;
}

.status-chip.fault .status-dot {
  background: #ef4444;
  box-shadow: 0 0 8px #ef4444;
}

.status-chip.offline .status-dot {
  background: #64748b;
}

.device-content {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.device-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.device-title-row h2 {
  margin: 0 0 4px;
  color: #e2e8f0;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.25;
}

.device-title-row span,
.device-meta {
  color: #94a3b8;
  font-size: 12px;
}

.icon-btn {
  width: 32px;
  height: 32px;
  color: #cbd5e1;
}

.device-meta {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid rgba(100, 116, 139, 0.18);
  padding-bottom: 10px;
}

.parameter-preview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.preview-item {
  min-width: 0;
  min-height: 62px;
  padding: 8px;
  border: 1px solid rgba(100, 116, 139, 0.2);
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.48);
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
}

.preview-item span {
  color: #94a3b8;
  font-size: 12px;
}

.preview-item strong {
  display: block;
  max-width: 100%;
  min-width: 0;
  margin-top: 3px;
  color: #f8fafc;
  font-size: 18px;
  line-height: 1.1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-preview-item strong {
  font-size: 16px;
}

.preview-item em {
  color: #64748b;
  font-size: 11px;
  font-style: normal;
}

.device-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.add-device-tile {
  color: #94a3b8;
  border-style: dashed;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 10px;
  font-size: 15px;
  cursor: pointer;
  transition: border-color 0.2s ease, color 0.2s ease;
}

.add-device-tile .el-icon {
  font-size: 36px;
}

.add-device-tile:hover {
  color: #2dd4bf;
  border-color: rgba(45, 212, 191, 0.7);
}

.thumbnail-editor {
  display: flex;
  align-items: center;
  gap: 16px;
}

.thumbnail-preview {
  width: 180px;
  height: 110px;
  border-radius: 6px;
  object-fit: cover;
  border: 1px solid rgba(100, 116, 139, 0.28);
  background: #0f172a;
}

@media (max-width: 900px) {
  .fleet-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .device-group-page {
    padding: 12px;
  }

  .page-header,
  .source-bar,
  .thumbnail-editor {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
  }

  .fleet-summary {
    grid-template-columns: 1fr;
  }

  .device-grid {
    grid-template-columns: 1fr;
  }
}
</style>
