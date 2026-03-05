<template>
  <div class="analysis">
    <h2 class="page-title">数据分析</h2>
    
    <div class="analysis-content">
      <!-- 历史曲线 -->
      <el-card class="chart-card" v-loading="loading" element-loading-text="加载数据中...">
        <template #header>
          <div class="card-header">
            <span>预测历史</span>
            <el-button type="primary" text @click="exportData">
              <el-icon><Download /></el-icon>
              导出数据
            </el-button>
          </div>
        </template>
        <div ref="historyChartRef" class="history-chart" :style="{ height: chartHeight + 'px' }"></div>
      </el-card>
      
      <!-- 调控记录 -->
      <el-card class="record-card">
        <template #header>
          <div class="card-header">
            <span>调控记录</span>
            <el-button type="primary" text @click="loadRegulationHistory">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>
        <el-table :data="regulationHistory" stripe height="400">
          <el-table-column prop="datetime" label="时间" width="160" />
          <el-table-column prop="parameter" label="参数" width="100" />
          <el-table-column prop="adjustment" label="调整量" width="100">
            <template #default="scope">
              <span :class="scope.row.adjustment > 0 ? 'positive' : 'negative'">
                {{ scope.row.adjustment > 0 ? '+' : '' }}{{ scope.row.adjustment }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="old_value" label="原值" width="80" />
          <el-table-column prop="new_value" label="新值" width="80" />
          <el-table-column prop="confidence" label="置信度" width="100">
            <template #default="scope">
              {{ (scope.row.confidence * 100).toFixed(0) }}%
            </template>
          </el-table-column>
          <el-table-column prop="success" label="状态" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.success ? 'success' : 'danger'" size="small">
                {{ scope.row.success ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { controlApi } from '../../utils/api'
import { useDataStore } from '../../stores/data'
import { useResponsive } from '../../composables/useResponsive'
import { darkTheme } from '../../utils/echarts-theme'
import { exportPredictionHistory, exportRegulationHistory, exportFullReport } from '../../utils/export'

const store = useDataStore()
const { chartHeight } = useResponsive()
const historyChartRef = ref(null)
const regulationHistory = ref([])
const loading = ref(true)
let chart = null

const initChart = () => {
  if (!historyChartRef.value) return
  
  chart = echarts.init(historyChartRef.value, null, { renderer: 'canvas' })
  
  const option = {
    backgroundColor: darkTheme.backgroundColor,
    color: ['#ff6b6b', '#00d4ff', '#ffc107', '#00ff88'],
    textStyle: darkTheme.textStyle,
    grid: {
      top: 50,
      left: 60,
      right: 40,
      bottom: 50
    },
    tooltip: {
      trigger: 'axis',
      ...darkTheme.tooltip
    },
    legend: {
      data: ['流量', '速度', 'Z偏移', '温度'],
      ...darkTheme.legend,
      top: 10
    },
    xAxis: {
      type: 'category',
      data: store.historyData.timestamps,
      ...darkTheme.categoryAxis
    },
    yAxis: {
      type: 'value',
      name: '预测类别',
      min: -1.5,
      max: 1.5,
      nameTextStyle: { color: '#a0aec0' },
      axisLabel: {
        color: '#a0aec0',
        formatter: (value) => {
          const labels = { '-1': 'Low', '0': 'Normal', '1': 'High' }
          return labels[value] || ''
        }
      },
      ...darkTheme.valueAxis
    },
    series: [
      {
        name: '流量',
        type: 'line',
        data: store.historyData.flowRateClasses,
        step: 'middle',
        lineStyle: { width: 2 }
      },
      {
        name: '速度',
        type: 'line',
        data: store.historyData.feedRateClasses,
        step: 'middle',
        lineStyle: { width: 2 }
      },
      {
        name: 'Z偏移',
        type: 'line',
        data: store.historyData.zOffsetClasses,
        step: 'middle',
        lineStyle: { width: 2 }
      },
      {
        name: '温度',
        type: 'line',
        data: store.historyData.hotendClasses,
        step: 'middle',
        lineStyle: { width: 2 }
      }
    ]
  }
  
  chart.setOption(option)
  
  const resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(historyChartRef.value)
}

const loadRegulationHistory = async () => {
  loading.value = true
  try {
    const res = await controlApi.getHistory(50)
    regulationHistory.value = res.data.records || []
  } catch (e) {
    ElMessage.error('加载调控历史失败')
  } finally {
    loading.value = false
  }
}

const exportData = () => {
  exportFullReport(store, regulationHistory.value)
  ElMessage.success('报告导出成功')
}

onMounted(() => {
  initChart()
  loadRegulationHistory()
})

onUnmounted(() => {
  chart?.dispose()
})
</script>

<style scoped>
.analysis {
  padding: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 20px;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-card,
.record-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-chart {
  min-height: 250px;
}

.positive {
  color: #00ff88;
}

.negative {
  color: #ff4d4f;
}
</style>
