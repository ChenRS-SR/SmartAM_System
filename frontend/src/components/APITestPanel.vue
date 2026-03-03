<template>
  <div class="api-test-panel">
    <div class="panel-header">
      <div class="header-title">
        <el-icon size="20" color="#00d4ff"><Connection /></el-icon>
        <span>API 连接测试</span>
      </div>
      <div class="header-actions">
        <el-tag :type="summaryTagType" effect="dark" size="small">
          {{ summaryText }}
        </el-tag>
        <el-button 
          type="primary" 
          size="small" 
          :loading="testing"
          @click="runTests"
        >
          <el-icon><Refresh /></el-icon>
          重新测试
        </el-button>
      </div>
    </div>

    <div class="test-results" v-if="results.length > 0">
      <div 
        v-for="result in results" 
        :key="result.id"
        class="test-item"
        :class="result.status"
      >
        <div class="test-icon">
          <el-icon size="16" v-if="result.status === 'success'"><CircleCheck /></el-icon>
          <el-icon size="16" v-else-if="result.status === 'warning'"><Warning /></el-icon>
          <el-icon size="16" v-else><CircleClose /></el-icon>
        </div>
        <div class="test-content">
          <div class="test-name">{{ result.name }}</div>
          <div class="test-message">{{ result.message }}</div>
          <div v-if="result.details" class="test-details">
            <el-collapse>
              <el-collapse-item title="详细信息">
                <pre>{{ JSON.stringify(result.details, null, 2) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
        <div class="test-time">
          {{ formatTime(result.timestamp) }}
        </div>
      </div>
    </div>

    <div v-else-if="testing" class="testing-status">
      <el-icon class="loading-icon" size="32"><Loading /></el-icon>
      <span>正在测试 API 连接...</span>
    </div>

    <div v-else class="empty-status">
      <el-icon size="48" color="#666"><Connection /></el-icon>
      <span>点击"重新测试"检查 API 连接状态</span>
    </div>

    <!-- 测试摘要 -->
    <div v-if="summary.total > 0" class="test-summary">
      <el-divider />
      <div class="summary-content">
        <div class="summary-item success">
          <span class="summary-label">成功</span>
          <span class="summary-value">{{ summary.success }}</span>
        </div>
        <div class="summary-item warning">
          <span class="summary-label">警告</span>
          <span class="summary-value">{{ summary.warning }}</span>
        </div>
        <div class="summary-item error">
          <span class="summary-label">失败</span>
          <span class="summary-value">{{ summary.error }}</span>
        </div>
        <div class="summary-item total">
          <span class="summary-label">通过率</span>
          <span class="summary-value">{{ summary.passRate }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiTester, TestResult } from '../utils/api-test'
import { ElMessage } from 'element-plus'

const testing = ref(false)
const results = ref([])
const summary = ref({
  total: 0,
  success: 0,
  warning: 0,
  error: 0,
  passRate: 0,
  allPassed: false
})

const summaryText = computed(() => {
  if (summary.value.total === 0) return '未测试'
  if (summary.value.allPassed) return '全部通过'
  return `${summary.value.success}/${summary.value.total} 通过`
})

const summaryTagType = computed(() => {
  if (summary.value.total === 0) return 'info'
  if (summary.value.allPassed) return 'success'
  if (summary.value.error === 0) return 'warning'
  return 'danger'
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

const runTests = async () => {
  testing.value = true
  try {
    await apiTester.runAllTests()
    results.value = apiTester.getResults()
    summary.value = apiTester.getSummary()
    
    if (summary.value.allPassed) {
      ElMessage.success('所有 API 测试通过！')
    } else if (summary.value.error > 0) {
      ElMessage.warning(`${summary.value.error} 个测试失败，请检查后端服务`)
    }
  } catch (error) {
    ElMessage.error('测试执行失败: ' + error.message)
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  // 页面加载时自动运行一次测试
  runTests()
})
</script>

<style scoped>
.api-test-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  padding: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 500;
  color: #e2e8f0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.test-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.test-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2);
  border-left: 3px solid transparent;
}

.test-item.success {
  border-left-color: #00ff88;
  background: rgba(0, 255, 136, 0.1);
}

.test-item.warning {
  border-left-color: #ffc107;
  background: rgba(255, 193, 7, 0.1);
}

.test-item.error {
  border-left-color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
}

.test-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.test-item.success .test-icon {
  color: #00ff88;
}

.test-item.warning .test-icon {
  color: #ffc107;
}

.test-item.error .test-icon {
  color: #ff4d4f;
}

.test-content {
  flex: 1;
  min-width: 0;
}

.test-name {
  font-size: 14px;
  font-weight: 500;
  color: #e2e8f0;
  margin-bottom: 4px;
}

.test-message {
  font-size: 13px;
  color: #a0aec0;
}

.test-details {
  margin-top: 8px;
}

.test-details :deep(.el-collapse) {
  border: none;
}

.test-details :deep(.el-collapse-item__header) {
  background: transparent;
  border: none;
  color: #00d4ff;
  font-size: 12px;
}

.test-details :deep(.el-collapse-item__wrap) {
  background: rgba(0, 0, 0, 0.3);
  border: none;
}

.test-details pre {
  margin: 0;
  padding: 8px;
  font-size: 11px;
  color: #a0aec0;
  overflow-x: auto;
}

.test-time {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.testing-status,
.empty-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 12px;
  color: #666;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.test-summary {
  margin-top: 16px;
}

.summary-content {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.summary-item {
  text-align: center;
  padding: 12px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2);
}

.summary-item.success {
  background: rgba(0, 255, 136, 0.1);
}

.summary-item.warning {
  background: rgba(255, 193, 7, 0.1);
}

.summary-item.error {
  background: rgba(255, 77, 79, 0.1);
}

.summary-label {
  display: block;
  font-size: 12px;
  color: #a0aec0;
  margin-bottom: 4px;
}

.summary-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: #e2e8f0;
}

.summary-item.success .summary-value {
  color: #00ff88;
}

.summary-item.warning .summary-value {
  color: #ffc107;
}

.summary-item.error .summary-value {
  color: #ff4d4f;
}
</style>
