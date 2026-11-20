<template>
  <div class="device-group-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">设备总览</h1>
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
      <span>使用单位</span>
      <div class="org-selector">
        <el-select
          v-model="selectedOrg"
          placeholder="选择使用单位"
          size="large"
          class="org-select"
        >
          <el-option
            v-for="org in orgOptions"
            :key="org.value"
            :label="org.label"
            :value="org.value"
          />
        </el-select>
      </div>
      <span>数据源</span>
      <strong>{{ deviceStore.sourceInfo.sourceRoot || '正在加载 7103 数据' }}</strong>
      <el-tag size="small" type="info">状态码 0-4</el-tag>
    </section>

    <section class="fleet-summary">
      <div class="summary-item">
        <span class="summary-label">设备总数</span>
        <strong>{{ fleetStats.total }}</strong>
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
        v-for="device in filteredDevices"
        :key="device.id"
        class="device-card"
        tabindex="0"
        :aria-label="`进入${device.name}`"
        @keydown.enter.self="openDeviceDashboard(device.id)"
        @keydown.space.self.prevent="openDeviceDashboard(device.id)"
        :class="{ offline: !device.online, fault: device.online && device.health === 'fault' }"
        @click="openDeviceDashboard(device.id)"
      >
        <div class="thumbnail-wrap">
          <img :src="device.thumbnail" :alt="device.name" class="device-thumbnail" />
        </div>
        <div class="device-content">
          <div class="device-title-row">
            <div>
              <h2>{{ device.name }}</h2>
              <span>{{ device.model }}</span>
            </div>
            <el-tooltip v-if="!device.replayCase" content="编辑设备" placement="top">
              <el-button
                text
                class="icon-btn"
                @click.stop="openEditDialog(deviceStore.getDeviceById(device.id) || device)"
              >
                <el-icon><EditPen /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
          <div class="device-status-row">
            <span>设备状态</span>
            <strong :class="statusClass(device)"><i></i>{{ statusText(device) }}</strong>
          </div>
        </div>
      </article>

      <button class="add-device-tile" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>
        <span>导入设备</span>
      </button>
    </section>

    <!-- 装备群历史统计情况 -->
    <section class="maintenance-statistics-panel">
      <div class="panel-title">
        <el-icon><TrendCharts /></el-icon>
        装备群历史统计情况
      </div>
      <div class="maintenance-statistics-grid">
        <div class="maintenance-stat-card">
          <div class="maintenance-stat-icon faults">
            <el-icon><Warning /></el-icon>
          </div>
          <div class="maintenance-stat-content">
            <span class="maintenance-stat-label">累计发生故障任务</span>
            <span class="maintenance-stat-value">
              {{ maintenanceStats.totalFaults }}<span class="maintenance-stat-unit">次</span>
            </span>
          </div>
        </div>
        <div class="maintenance-stat-card">
          <div class="maintenance-stat-icon preventive">
            <el-icon><FirstAidKit /></el-icon>
          </div>
          <div class="maintenance-stat-content">
            <span class="maintenance-stat-label">提前维修决策次数</span>
            <span class="maintenance-stat-value">
              {{ maintenanceStats.preventiveRepairs }}<span class="maintenance-stat-unit">次</span>
            </span>
          </div>
        </div>
        <div class="maintenance-stat-card">
          <div class="maintenance-stat-icon reduction">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="maintenance-stat-content">
            <span class="maintenance-stat-label">避免故障比例</span>
            <span class="maintenance-stat-value">
              {{ maintenanceStats.avoidanceRate.toFixed(1) }}<span class="maintenance-stat-unit">%</span>
            </span>
          </div>
        </div>
      </div>
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
import { useReplayStore, REPLAY_CASES } from '../../stores/replay'
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { EditPen, Plus, Refresh, Upload, TrendCharts, Warning, FirstAidKit, CircleCheck } from '@element-plus/icons-vue'
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

// 使用单位选择
const selectedOrg = ref('all')
const orgOptions = [
  { label: '全部单位', value: 'all' },
  { label: '7103（铂力特）', value: '7103' },
  { label: '华科', value: 'huake' }
]
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

const caseSessions = new Map(REPLAY_CASES.map(item => [item.id, useReplayStore(item.id)]))
const displayDevices = computed(() => deviceStore.devices.map(device => {
  // 此设备使用独立共享数据流，不被其他设备的数据模式改写。
  if (device.replayCase) {
    const replay = caseSessions.get(device.replayCase)
    const frame = replay.snapshot
    // 状态卡沿用当前快照的异常判定；不展示内部数据来源和冗长告警。
    const probability = frame?.recognition?.prob
    const abnormal = probability && Math.max(probability.proc, probability.dev) >= .5
    const acquisitionStatus = replay.error ? '数据异常' : !frame ? '等待数据' : replay.playing ? '采集中' : '采集暂停'
    return { ...device, name: device.name, dataTag: '', databaseTag: '', online: !!frame && !replay.error,
      health: abnormal ? 'fault' : 'healthy', healthData: { status: abnormal ? 'fault' : 'healthy' }, statusText: acquisitionStatus,
      parameters: [
        { id: 'current_layer', name: '当前层', value: frame?.layer ?? '—', unit: '层' },
        { id: 'data_time', name: '采集时间', value: frame?.time ?? '等待数据', unit: '' },
        { id: 'record_status', name: '状态参数', value: acquisitionStatus, unit: '' }
      ] }

  }
  return isMockMode.value ? toMockDevice(device) : toRealtimeDevice(device, realtimeSamples.value[device.id])
}))

// 故障设备优先，随后完整案例；原始故障清单排序稳定，不随模拟波动跳动。
const orderedDevices = computed(() => [...displayDevices.value].sort((a, b) => Number(deviceStore.getDeviceById(b.id)?.health === 'fault') - Number(deviceStore.getDeviceById(a.id)?.health === 'fault') || Number(Boolean(b.replayCase)) - Number(Boolean(a.replayCase))))
const filteredDevices = computed(() => {
  if (selectedOrg.value === 'all') return orderedDevices.value
  return orderedDevices.value.filter((device) => {
    const owner = (device.owner || '').trim()
    const dataTag = (device.dataTag || '').trim()
    const databaseTag = (device.databaseTag || '').trim()
    const source = (device.source || '').trim()
    if (selectedOrg.value === '7103') {
      return owner.includes('铂力特')
        || dataTag.includes('7103')
        || databaseTag.includes('7103')
        || source === '7103'
    }
    if (selectedOrg.value === 'huake') {
      return owner.includes('华科')
        || owner.includes('华中数控')
        || dataTag.includes('华科')
        || databaseTag.includes('华科')
        || databaseTag.includes('huake')
        || source === 'huake'
    }
    return true
  })
})

const fleetStats = computed(() => ({
  total: filteredDevices.value.length,
  online: filteredDevices.value.filter((device) => device.online).length,
  healthy: filteredDevices.value.filter((device) => device.online && device.health === 'healthy').length,
  fault: filteredDevices.value.filter((device) => device.online && device.health === 'fault').length
}))

// 装备群历史统计（与设备状态监测界面的视情维护模块对应）
const maintenanceStats = computed(() => ({
  totalFaults: 40,
  preventiveRepairs: 28,
  avoidanceRate: 70.0
}))

const statusClass = (device) => {
  if (!device.online) return 'offline'
  return device.health === 'fault' ? 'fault' : 'healthy'
}

const statusText = (device) => {
  if (!device.online) return '离线'
  return device.health === 'fault' ? '异常' : '正常'
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
  router.push({ path: `/slm/device/${deviceId}`, query: { tab: 'status', org: selectedOrg.value } })
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
    await Promise.all(deviceStore.devices.filter(device => device.replayCase).map(device => caseSessions.get(device.replayCase).open({ autoplay: true })))
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

<style scoped src="../../styles/device-fleet.css"></style>
<style scoped>

.source-bar {
  min-height: 44px;
  margin-bottom: 18px;
  padding: 10px 14px;
  border: 1px solid var(--am-card-border);
  border-radius: 8px;
  background: var(--am-card-bg);
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--am-text-2);
  font-size: 12px;
  flex-wrap: wrap;
}

.org-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.org-select {
  width: 170px;
}

.org-select :deep(.el-input__wrapper) {
  background: var(--am-card-bg);
  border: 1px solid color-mix(in srgb, var(--am-accent) 30%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--am-accent) 30%, transparent) inset;
}

.org-select :deep(.el-input__inner) {
  color: var(--am-text);
}

.device-status-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; border-top: 1px solid var(--am-card-border); padding-top: 14px; margin-top: 14px; font-size: 14px; color: var(--am-text-2); }
.device-status-row strong { display: flex; align-items: center; gap: 8px; }
.device-status-row i { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.device-status-row .healthy { color: var(--am-ok); }
.device-status-row .fault { color: var(--am-danger); }
.device-status-row .offline { color: var(--am-text-3); }

/* 装备群历史统计 */
.maintenance-statistics-panel {
  margin-top: 18px;
  padding: 18px;
  border: 1px solid var(--am-card-border);
  border-radius: 10px;
  background: var(--am-card-bg);
}

.maintenance-statistics-panel .panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  font-size: 15px;
  font-weight: 600;
  color: var(--am-text);
}

.maintenance-statistics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.maintenance-stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--am-card-border);
  border-radius: 8px;
  background: var(--am-card-bg);
}

.maintenance-stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.maintenance-stat-icon.faults {
  background: color-mix(in srgb, var(--am-warn) 22%, transparent);
  color: var(--am-warn);
}

.maintenance-stat-icon.preventive {
  background: color-mix(in srgb, var(--am-accent) 22%, transparent);
  color: var(--am-accent);
}

.maintenance-stat-icon.reduction {
  background: color-mix(in srgb, var(--am-ok) 22%, transparent);
  color: var(--am-ok);
}

.maintenance-stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.maintenance-stat-label {
  font-size: 12px;
  color: var(--am-text-2);
}

.maintenance-stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--am-text);
  font-family: 'Courier New', monospace;
}

.maintenance-stat-unit {
  font-size: 13px;
  font-weight: 500;
  color: var(--am-text-2);
  margin-left: 4px;
}

@keyframes danger-pulse {
  0%, 100% { box-shadow: 0 0 0 color-mix(in srgb, var(--am-danger) 0%, transparent); }
  50% { box-shadow: 0 0 10px color-mix(in srgb, var(--am-danger) 25%, transparent); }
}

@media (max-width: 900px) {
  .fleet-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .maintenance-statistics-grid {
    grid-template-columns: 1fr;
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

  .maintenance-statistics-grid {
    grid-template-columns: 1fr;
  }


  .org-select {
    width: 140px;
  }

  .device-grid {
    grid-template-columns: 1fr;
  }
}
</style>
