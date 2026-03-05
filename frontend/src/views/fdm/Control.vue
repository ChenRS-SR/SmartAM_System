<template>
  <div class="control-page">
    <h2 class="page-title">系统控制</h2>
    
    <div class="control-grid" :class="{ 'mobile-layout': isMobile }">
      <!-- 打印机控制 -->
      <el-card class="control-card">
        <template #header>
          <div class="card-header">
            <el-icon><Printer /></el-icon>
            <span>打印机控制</span>
          </div>
        </template>
        
        <div class="printer-actions">
          <el-button 
            type="success" 
            size="large"
            :disabled="store.latestData.printer.state === 'Printing'"
            @click="startPrint"
          >
            <el-icon><VideoPlay /></el-icon>
            开始打印
          </el-button>
          <el-button 
            type="warning" 
            size="large"
            :disabled="store.latestData.printer.state !== 'Printing'"
            @click="pausePrint"
          >
            <el-icon><VideoPause /></el-icon>
            暂停打印
          </el-button>
          <el-button 
            type="danger" 
            size="large"
            :disabled="store.latestData.printer.state === 'Operational'"
            @click="stopPrint"
          >
            <el-icon><CircleClose /></el-icon>
            停止打印
          </el-button>
          <el-button type="info" size="large" @click="emergencyStop">
            <el-icon><Warning /></el-icon>
            紧急停止
          </el-button>
        </div>
        
        <el-divider />
        
        <div class="file-select">
          <span class="label">选择文件:</span>
          <el-select v-model="selectedFile" placeholder="选择G-code文件" clearable>
            <el-option 
              v-for="file in files" 
              :key="file" 
              :label="file" 
              :value="file" 
            />
          </el-select>
        </div>
      </el-card>
      
      <!-- PID 控制 -->
      <el-card class="control-card">
        <template #header>
          <div class="card-header">
            <el-icon><SetUp /></el-icon>
            <span>PID 调参</span>
          </div>
        </template>
        
        <div class="pid-form">
          <div class="pid-row">
            <div class="pid-param">
              <span class="param-label">流量调节系数</span>
              <el-slider v-model="pidParams.flow_kp" :min="0" :max="2" :step="0.1" show-stops />
              <span class="param-value">{{ pidParams.flow_kp }}</span>
            </div>
          </div>
          
          <div class="pid-row">
            <div class="pid-param">
              <span class="param-label">速度调节系数</span>
              <el-slider v-model="pidParams.speed_kp" :min="0" :max="2" :step="0.1" show-stops />
              <span class="param-value">{{ pidParams.speed_kp }}</span>
            </div>
          </div>
          
          <div class="pid-row">
            <div class="pid-param">
              <span class="param-label">Z偏移步长</span>
              <el-slider v-model="pidParams.z_step" :min="0.01" :max="0.1" :step="0.01" show-stops />
              <span class="param-value">{{ pidParams.z_step }}</span>
            </div>
          </div>
          
          <div class="pid-row">
            <div class="pid-param">
              <span class="param-label">温度步长</span>
              <el-slider v-model="pidParams.temp_step" :min="1" :max="10" :step="1" show-stops />
              <span class="param-value">{{ pidParams.temp_step }}°C</span>
            </div>
          </div>
          
          <el-button type="primary" @click="applyPidParams" style="width: 100%">
            应用 PID 参数
          </el-button>
        </div>
      </el-card>
      
      <!-- 闭环调试 -->
      <el-card class="control-card" style="grid-column: span 2;">
        <template #header>
          <div class="card-header">
            <el-icon><Monitor /></el-icon>
            <span>闭环控制调试</span>
          </div>
        </template>
        
        <div class="debug-panel">
          <div class="debug-info">
            <h4>当前状态</h4>
            <pre>{{ JSON.stringify(store.closedLoopStatus, null, 2) }}</pre>
          </div>
          
          <div class="debug-actions">
            <h4>调试操作</h4>
            <el-form :inline="true">
              <el-form-item label="模拟预测类别">
                <el-select v-model="mockPrediction" placeholder="选择类别">
                  <el-option label="Low" :value="0" />
                  <el-option label="Normal" :value="1" />
                  <el-option label="High" :value="2" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button @click="testAddPrediction">添加预测</el-button>
              </el-form-item>
              <el-form-item>
                <el-button @click="testCalculateAdjustment">计算调节</el-button>
              </el-form-item>
              <el-form-item>
                <el-button type="danger" @click="testClearHistory">清空历史</el-button>
              </el-form-item>
            </el-form>
          </div>
        </div>
      </el-card>
      
      <!-- 数据采集控制 -->
      <el-card class="control-card" style="grid-column: span 2;">
        <template #header>
          <div class="card-header">
            <el-icon><VideoCamera /></el-icon>
            <span>{{ $t('acquisition.title') }}</span>
          </div>
        </template>
        <AcquisitionPanel />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { printerApi, controlApi } from '../../utils/api'
import { useDataStore } from '../../stores/data'
import { useNotification } from '../../composables/useNotification'
import { useResponsive } from '../../composables/useResponsive'
import AcquisitionPanel from '../../components/AcquisitionPanel.vue'

const store = useDataStore()
const { success, warning, error, info } = useNotification()
const { isMobile } = useResponsive()

const loading = ref(false)

const selectedFile = ref('')
const files = ref([])

const pidParams = ref({
  flow_kp: 0.5,
  speed_kp: 0.5,
  z_step: 0.02,
  temp_step: 5
})

const mockPrediction = ref(1)

const loadFiles = async () => {
  try {
    const res = await printerApi.getFiles()
    files.value = res.data.files
  } catch (e) {
    ElMessage.error('加载文件列表失败')
  }
}

const startPrint = async () => {
  if (!selectedFile.value) {
    warning('请先选择打印文件')
    return
  }
  loading.value = true
  try {
    await printerApi.startPrint(selectedFile.value)
    success('打印已启动')
  } catch (e) {
    error('启动打印失败')
  } finally {
    loading.value = false
  }
}

const pausePrint = async () => {
  try {
    await printerApi.pausePrint()
    info('打印已暂停')
  } catch (e) {
    error('暂停失败')
  }
}

const stopPrint = async () => {
  try {
    await printerApi.cancelPrint()
    success('打印已停止')
  } catch (e) {
    error('停止失败')
  }
}

const emergencyStop = () => {
  ElMessageBox.confirm('确定要执行紧急停止吗？打印机将立即停止运行。', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await printerApi.emergencyStop()
      ElMessage.success('紧急停止已执行')
    } catch (e) {
      ElMessage.error('执行失败')
    }
  }).catch(() => {})
}

const applyPidParams = async () => {
  try {
    await controlApi.updateConfig(pidParams.value)
    success('PID参数已更新')
  } catch (e) {
    error('更新失败')
  }
}

const testAddPrediction = async () => {
  try {
    await controlApi.addPrediction(mockPrediction.value, 0.85)
    ElMessage.success('测试预测已添加')
  } catch (e) {
    ElMessage.error('添加失败')
  }
}

const testCalculateAdjustment = async () => {
  try {
    const res = await controlApi.calculateAdjustment()
    info(`调节量: ${JSON.stringify(res.data)}`)
  } catch (e) {
    error('计算失败')
  }
}

const testClearHistory = async () => {
  try {
    await controlApi.clearHistory()
    success('历史已清空')
  } catch (e) {
    error('清空失败')
  }
}

onMounted(loadFiles)
</script>

<style scoped>
.control-page {
  padding: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 20px;
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.control-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  color: #00d4ff;
}

.printer-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.printer-actions .el-button {
  width: 100%;
}

.file-select {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.file-select .label {
  white-space: nowrap;
  color: #a0aec0;
}

.file-select .el-select {
  flex: 1;
}

.pid-row {
  margin-bottom: 20px;
}

.pid-param {
  display: flex;
  align-items: center;
  gap: 12px;
}

.param-label {
  width: 100px;
  font-size: 13px;
  color: #a0aec0;
}

.param-value {
  width: 80px;
  text-align: right;
  color: #00d4ff;
  font-weight: 600;
}

.pid-param :deep(.el-slider) {
  flex: 1;
}

.debug-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.debug-info h4,
.debug-actions h4 {
  color: #a0aec0;
  margin-bottom: 12px;
}

.debug-info pre {
  background: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 8px;
  color: #00ff88;
  font-size: 12px;
  overflow-x: auto;
}

@media (max-width: 1200px) {
  .control-grid {
    grid-template-columns: 1fr;
  }
  
  .debug-panel {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .control-grid.mobile-layout {
    grid-template-columns: 1fr;
  }
  
  .control-grid.mobile-layout .control-card:last-child {
    grid-column: span 1;
  }
  
  .printer-actions {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .printer-actions .el-button {
    padding: 8px;
    font-size: 13px;
  }
}
</style>
