<template>
  <div class="sls-settings">
    <h2 class="page-title">SLS 设置</h2>

    <!-- SLS实验台连接设置 -->
    <el-card class="settings-card" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon size="20"><Connection /></el-icon>
          <span>SLS 实验台连接设置</span>
          <el-tag :type="benchSettings.use_mock ? 'warning' : 'success'" size="small" effect="dark">
            {{ benchSettings.use_mock ? '模拟数据' : '真实硬件' }}
          </el-tag>
        </div>
      </template>

      <div class="settings-content">
        <el-alert
          title="连接参数由设备状态监测页启动采集时读取"
          description="这里集中维护 Fotric 热像仪、振动传感器、舵机控制器和调试模式；online:false 的设备在真实模式下不会接收采集信号。"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />

        <el-form :model="benchSettings" label-width="150px" size="default">
          <el-divider content-position="left">热像仪与串口</el-divider>
          <el-form-item label="Fotric IP">
            <el-input v-model="benchSettings.fotric_ip" style="width: 260px" />
          </el-form-item>
          <el-form-item label="振动传感器串口">
            <div class="port-row">
              <el-select v-model="benchSettings.vibration_com" style="width: 180px" :loading="portsLoading" filterable allow-create>
                <el-option
                  v-for="port in availableComPorts"
                  :key="`vib-${port.device}`"
                  :label="formatPortLabel(port)"
                  :value="port.device"
                />
              </el-select>
              <el-button type="primary" @click="fetchComPorts" :loading="portsLoading">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </el-form-item>
          <el-form-item label="舵机控制器串口">
            <el-select v-model="benchSettings.servo_com" style="width: 180px" :loading="portsLoading" filterable allow-create>
              <el-option
                v-for="port in availableComPorts"
                :key="`servo-${port.device}`"
                :label="formatPortLabel(port)"
                :value="port.device"
              />
            </el-select>
          </el-form-item>

          <el-divider content-position="left">振动检测</el-divider>
          <el-form-item label="触发阈值">
            <el-input-number v-model="benchSettings.vibration_threshold" :min="0" :step="0.01" :precision="2" />
          </el-form-item>
          <el-form-item label="检测算法">
            <el-select v-model="benchSettings.vibration_algorithm" style="width: 220px">
              <el-option label="综合判据" value="composite" />
              <el-option label="速度判据" value="velocity_based" />
              <el-option label="位移判据" value="displacement_based" />
              <el-option label="频率判据" value="frequency_based" />
              <el-option label="RMS" value="rms" />
              <el-option label="峰值" value="peak" />
              <el-option label="能量" value="energy" />
            </el-select>
          </el-form-item>

          <el-divider content-position="left">调试模式</el-divider>
          <el-form-item label="使用模拟数据">
            <el-switch v-model="benchSettings.use_mock" />
            <span class="form-hint inline-hint">
              开启后优先读取单台设备目录下的 mock_video/CH1..CH3
            </span>
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="saveBenchSettings">
              <el-icon><Check /></el-icon>
              保存连接设置
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <!-- 设备目录模拟视频扫描 -->
    <el-card class="settings-card" shadow="never" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <el-icon size="20"><VideoCamera /></el-icon>
          <span>设备模拟视频扫描</span>
          <el-tag type="info" size="small">由设备文件数据库决定</el-tag>
        </div>
      </template>

      <div class="settings-content">
        <el-alert
          title="模拟视频按设备目录自动扫描"
          description="在单台设备数据库目录下放入 mock_video/CH1、mock_video/CH2、mock_video/CH3 文件夹；每个通道文件夹内放一个支持格式的视频即可自动接入。"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />

        <el-table :data="mockCaseRows" border size="small" v-loading="slsDeviceStore.loading">
          <el-table-column prop="name" label="设备" min-width="180" />
          <el-table-column prop="caseLabel" label="扫描结果" min-width="160" />
          <el-table-column prop="folder" label="目录结构" min-width="280" />
          <el-table-column prop="status" label="状态" width="120" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Connection, Refresh, VideoCamera } from '@element-plus/icons-vue'
import { useSlsDeviceStore } from '../../stores/slsDevices'
import { getDeviceMockCase } from '../../utils/deviceMockMedia'
import { readSlsBenchSettings, writeSlsBenchSettings } from '../../utils/slsBenchSettings'

const slsDeviceStore = useSlsDeviceStore()

// SLS连接参数独立保存，避免误用SLM华科实验台的缓存键。
const benchSettings = reactive(readSlsBenchSettings())
const availableComPorts = ref([])
const portsLoading = ref(false)

const mockCaseRows = computed(() => slsDeviceStore.devices.map((device) => {
  const mockCase = getDeviceMockCase(device)
  return {
    id: device.id,
    name: device.name,
    caseLabel: mockCase?.label || '暂不支持接入',
    folder: mockCase ? `${device.dataDirectory}/mock_video/CH1..CH3` : `${device.dataDirectory || '--'}/mock_video/CH1..CH3`,
    status: mockCase?.supported ? '已接入' : '未接入'
  }
}))

function formatPortLabel(port) {
  return port.description ? `${port.device} (${port.description})` : port.device
}

async function fetchComPorts() {
  portsLoading.value = true
  try {
    const response = await fetch('/api/sls/com_ports')
    const result = await response.json()
    if (!result.success) {
      ElMessage.warning(result.message || '串口扫描失败')
      return
    }
    availableComPorts.value = result.ports || []
  } catch (error) {
    ElMessage.error(`串口扫描失败: ${error.message}`)
  } finally {
    portsLoading.value = false
  }
}

function saveBenchSettings() {
  writeSlsBenchSettings(benchSettings)
  ElMessage.success('SLS实验台连接设置已保存')
}

onMounted(() => {
  fetchComPorts()
  slsDeviceStore.loadDevicesFromBackend().catch((error) => {
    ElMessage.error(error.message || '加载SLS设备模拟视频扫描结果失败')
  })
})
</script>

<style scoped>
.sls-settings {
  padding: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0 0 20px 0;
}

.settings-card {
  border: none;
  background: rgba(15, 23, 42, 0.6);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  color: #e2e8f0;
}

.settings-content {
  padding: 10px 0;
}

.port-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.form-hint {
  font-size: 12px;
  color: #64748b;
  margin-top: 5px;
}

.inline-hint {
  margin-left: 10px;
  margin-top: 0;
}

:deep(.el-table) {
  background: rgba(15, 23, 42, 0.4);
}
</style>
