<template>
  <div class="slm-settings">
    <h2 class="page-title">系统设置</h2>
    <ReplaySettings :key="contextDeviceId" :device-id="contextDeviceId" />

    <!-- 数据源列表与设备群和工作区保持一致。 -->
    <el-card class="settings-card" shadow="never" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>设备数据源</span>
          <el-button size="small" :loading="slmDeviceStore.loading" @click="refreshDeviceSources">刷新列表</el-button>
        </div>
      </template>
      <div class="settings-content">
        <el-table :data="deviceSourceRows" row-key="id" border size="small" v-loading="slmDeviceStore.loading">
          <el-table-column prop="name" label="设备" min-width="180">
            <template #default="{ row }">
              <div>{{ row.name }} <span v-if="row.id === contextDeviceId" class="current-device">当前设备</span></div>
              <small>{{ row.serial }}</small>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="数据源" min-width="100" />
          <el-table-column prop="content" label="数据内容" min-width="200" />
          <el-table-column prop="location" label="资源位置" min-width="220" show-overflow-tooltip />
          <el-table-column prop="status" label="资源状态" min-width="160" />
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <router-link class="device-source-link" :to="{ name: 'SLMDeviceDashboard', params: { deviceId: row.id }, query: { tab: 'access' } }">进入设备</router-link>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import { useSlmDeviceStore } from '../../stores/slmDevices'
import { deviceSourceRow } from '../../utils/slmDeviceSources'
import ReplaySettings from '../../components/slm/ReplaySettings.vue'

const route = useRoute()
const contextDeviceId = computed(() => typeof route.query.device === 'string'
  ? route.query.device : localStorage.getItem('slmSelectedDeviceId') || '')
const slmDeviceStore = useSlmDeviceStore()
const deviceSourceRows = computed(() => slmDeviceStore.devices.map(deviceSourceRow))

// 设置页仅加载设备目录与当前回放，不再探测旧实验台硬件或修改标定、ROI。
async function refreshDeviceSources() {
  try {
    await slmDeviceStore.loadDevicesFromBackend()
  } catch (error) {
    ElMessage.error(error.message)
  }
}
onMounted(refreshDeviceSources)
</script>

<style scoped>
.current-device { margin-left: 6px; color: var(--am-accent); font-size: 12px; }
.device-source-link { color: var(--am-accent); text-decoration: none; }
.device-source-link:hover { text-decoration: underline; }
.slm-settings { padding: 0; }
.page-title { font-size: 24px; font-weight: 600; color: var(--am-text); margin: 0 0 20px; }
.card-header { justify-content: space-between; }
</style>
<style scoped src="../../styles/device-settings.css"></style>
