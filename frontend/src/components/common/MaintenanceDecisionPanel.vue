<template>
  <el-card class="maintenance-panel" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">
          <el-icon><FirstAidKit /></el-icon>
          视情维护可视化
        </span>
        <div class="header-tags">
          <el-tag type="success" size="small" effect="dark" class="benefit-tag">
            故障率降低30%
          </el-tag>
          <el-tag :type="overallStatus.type" size="small" effect="dark">
            {{ overallStatus.label }}
          </el-tag>
        </div>
      </div>
    </template>

    <!-- 6个系统风险可视化 -->
    <div class="systems-grid">
      <div
        v-for="system in displaySystems"
        :key="system.key"
        class="system-card"
        :class="{ 'risk-warning': system.riskPercent > 50 && system.riskPercent <= 80, 'risk-danger': system.riskPercent > 80 }"
      >
        <div class="system-title">{{ system.name }}</div>
        <div class="risk-visual">
          <div class="risk-bar-container">
            <div class="risk-bar-bg">
              <div
                class="risk-bar-fill"
                :style="{ width: Math.min(system.riskPercent, 100) + '%', background: getRiskColor(system.riskPercent) }"
              ></div>
            </div>
            <div
              class="risk-threshold-mark"
              :style="{ left: Math.min(system.thresholdPercent, 100) + '%' }"
            >
              <div class="threshold-line"></div>
              <div class="threshold-tooltip">阈值</div>
            </div>
          </div>
          <div class="risk-labels">
            <span class="risk-current" :style="{ color: getRiskColor(system.riskPercent) }">
              当前: {{ system.riskValue.toFixed(2) }}
            </span>
            <span class="risk-threshold">阈值: {{ system.thresholdValue.toFixed(2) }}</span>
          </div>
        </div>
        <div class="system-status">
          <el-tag :type="getRiskTagType(system.riskPercent)" size="small" effect="dark">
            {{ getRiskLabel(system.riskPercent) }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 可靠性计算值区域 -->
    <div class="reliability-section">
      <div class="section-header">
        <el-icon><Odometer /></el-icon>
        <span class="section-label">各系统当前可靠性计算值</span>
      </div>
      <div class="reliability-grid">
        <div
          v-for="system in displaySystems"
          :key="'rel-' + system.key"
          class="reliability-card"
        >
          <div
            class="rel-icon"
            :style="{
              background: getReliabilityColor(system.reliability) + '20',
              color: getReliabilityColor(system.reliability)
            }"
          >
            <el-icon><CircleCheck v-if="system.reliability >= 0.7" /><Warning v-else /></el-icon>
          </div>
          <div class="rel-content">
            <span class="rel-name">{{ system.name }}</span>
            <span
              class="rel-value"
              :style="{ color: getReliabilityColor(system.reliability) }"
            >
              {{ (system.reliability * 100).toFixed(1) }}%
            </span>
          </div>
          <div class="rel-bar-bg">
            <div
              class="rel-bar-fill"
              :style="{
                width: system.reliability * 100 + '%',
                background: getReliabilityColor(system.reliability)
              }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 维修建议框 -->
    <div class="advice-section">
      <div class="advice-box">
        <div class="advice-label">维修建议</div>
        <div class="advice-content">
          <p v-for="(line, idx) in adviceLines" :key="idx" class="advice-line">
            <el-tag size="small" :type="line.type" effect="dark" class="advice-priority">
              {{ line.priority }}
            </el-tag>
            {{ line.text }}
          </p>
          <p v-if="adviceLines.length === 0" class="advice-empty">
            当前各系统运行正常，暂无维修建议。建议继续保持定期巡检。
          </p>
        </div>
      </div>
    </div>

    <!-- 底部统计信息 -->
    <div class="statistics-section">
      <div class="stat-card">
        <div class="stat-icon">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-label">累计发生故障任务</span>
          <span class="stat-value">{{ displayStats.totalFaults }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(0, 212, 255, 0.2); color: #00d4ff;">
          <el-icon><FirstAidKit /></el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-label">提前维修决策次数</span>
          <span class="stat-value">{{ displayStats.preventiveRepairs }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: rgba(0, 255, 136, 0.2); color: #00ff88;">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-label">避免故障比例</span>
          <span class="stat-value">{{ displayStats.avoidanceRate.toFixed(1) }}%</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { FirstAidKit, Odometer, Warning, CircleCheck } from '@element-plus/icons-vue'

const props = defineProps({
  systems: {
    type: Array,
    default: () => []
  },
  statistics: {
    type: Object,
    default: () => ({})
  },
  advice: {
    type: Array,
    default: () => []
  }
})

// 默认6个系统数据
const defaultSystems = [
  { key: 'filter', name: '高效滤芯', riskValue: 0.32, thresholdValue: 0.80, riskPercent: 40, thresholdPercent: 80, reliability: 0.92 },
  { key: 'argon', name: '氩气循环系统', riskValue: 0.65, thresholdValue: 0.75, riskPercent: 87, thresholdPercent: 75, reliability: 0.58 },
  { key: 'powder', name: '铺粉成型系统（刮刀）', riskValue: 0.45, thresholdValue: 0.70, riskPercent: 64, thresholdPercent: 70, reliability: 0.78 },
  { key: 'feeder', name: '落粉轴系统', riskValue: 0.28, thresholdValue: 0.60, riskPercent: 47, thresholdPercent: 60, reliability: 0.85 },
  { key: 'laser', name: '激光器', riskValue: 0.15, thresholdValue: 0.55, riskPercent: 27, thresholdPercent: 55, reliability: 0.95 },
  { key: 'fan', name: '风机', riskValue: 0.52, thresholdValue: 0.65, riskPercent: 80, thresholdPercent: 65, reliability: 0.65 }
]

const defaultStats = {
  totalFaults: 12,
  preventiveRepairs: 28,
  avoidanceRate: 70.0
}

const defaultAdvice = [
  { priority: '高', type: 'danger', text: '氩气循环系统风险指标已超过阈值（87%），建议立即检查气体密封性及循环泵状态，防止氧含量超标影响打印质量。' },
  { priority: '中', type: 'warning', text: '风机当前可靠性仅为65%，振动噪声有增大趋势，建议下次停机时进行动平衡检测与轴承润滑保养。' },
  { priority: '低', type: 'info', text: '高效滤芯压差正常，但已运行480小时，建议预留备件并在下次维护周期更换。' }
]

const displaySystems = computed(() => props.systems.length > 0 ? props.systems : defaultSystems)
const displayStats = computed(() => ({ ...defaultStats, ...props.statistics }))
const adviceLines = computed(() => props.advice.length > 0 ? props.advice : defaultAdvice)

const overallStatus = computed(() => {
  const maxRisk = Math.max(...displaySystems.value.map(s => s.riskPercent))
  if (maxRisk > 80) return { type: 'danger', label: '高风险' }
  if (maxRisk > 50) return { type: 'warning', label: '中风险' }
  return { type: 'success', label: '低风险' }
})

const getRiskColor = (percent) => {
  if (percent > 80) return '#ef4444'
  if (percent > 50) return '#f59e0b'
  return '#22c55e'
}

const getRiskTagType = (percent) => {
  if (percent > 80) return 'danger'
  if (percent > 50) return 'warning'
  return 'success'
}

const getRiskLabel = (percent) => {
  if (percent > 80) return '超阈值'
  if (percent > 50) return '预警'
  return '正常'
}

const getReliabilityColor = (value) => {
  if (value >= 0.85) return '#22c55e'
  if (value >= 0.60) return '#f59e0b'
  return '#ef4444'
}
</script>

<style scoped>
.maintenance-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
  color: #e2e8f0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-tags {
  display: flex;
  gap: 8px;
}

.benefit-tag {
  background: linear-gradient(90deg, rgba(0, 255, 136, 0.2), rgba(0, 212, 255, 0.2)) !important;
  border-color: rgba(0, 255, 136, 0.4) !important;
  color: #00ff88 !important;
}

/* 6个系统网格 */
.systems-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.system-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 10px;
  border: 1px solid rgba(100, 116, 139, 0.2);
  transition: all 0.3s ease;
}

.system-card:hover {
  border-color: rgba(0, 212, 255, 0.3);
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.1);
}

.system-card.risk-warning {
  border-color: rgba(245, 158, 11, 0.4);
  background: rgba(245, 158, 11, 0.05);
}

.system-card.risk-danger {
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.08);
  animation: danger-pulse 2s infinite;
}

@keyframes danger-pulse {
  0%, 100% { box-shadow: 0 0 0 rgba(239, 68, 68, 0); }
  50% { box-shadow: 0 0 12px rgba(239, 68, 68, 0.2); }
}

.system-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  text-align: center;
}

/* 风险条形图 */
.risk-visual {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.risk-bar-container {
  position: relative;
  height: 24px;
}

.risk-bar-bg {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  transform: translateY(-50%);
  height: 10px;
  background: rgba(100, 116, 139, 0.2);
  border-radius: 5px;
  overflow: hidden;
}

.risk-bar-fill {
  height: 100%;
  border-radius: 5px;
  transition: width 0.6s ease, background 0.3s ease;
}

.risk-threshold-mark {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.threshold-line {
  width: 2px;
  height: 100%;
  background: repeating-linear-gradient(
    to bottom,
    #00d4ff 0px,
    #00d4ff 3px,
    transparent 3px,
    transparent 6px
  );
}

.threshold-tooltip {
  position: absolute;
  top: -16px;
  font-size: 10px;
  color: #00d4ff;
  background: rgba(15, 23, 42, 0.9);
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
  border: 1px solid rgba(0, 212, 255, 0.3);
}

.risk-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 0 2px;
}

.risk-current {
  font-weight: 600;
}

.risk-threshold {
  color: #94a3b8;
}

.system-status {
  display: flex;
  justify-content: center;
}

/* 可靠性区域 */
.reliability-section {
  margin-bottom: 20px;
  padding: 16px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 10px;
  border: 1px solid rgba(100, 116, 139, 0.15);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
}

.reliability-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}

.reliability-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px 8px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(100, 116, 139, 0.2);
  text-align: center;
}

.rel-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.rel-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rel-name {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.3;
}

.rel-value {
  font-size: 18px;
  font-weight: 700;
}

.rel-bar-bg {
  width: 100%;
  height: 4px;
  background: rgba(100, 116, 139, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.rel-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}

/* 维修建议框 */
.advice-section {
  margin-bottom: 20px;
}

.advice-box {
  position: relative;
  padding: 20px 16px 16px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 10px;
  border: 1px solid rgba(100, 116, 139, 0.25);
  min-height: 80px;
}

.advice-label {
  position: absolute;
  top: -10px;
  left: 12px;
  padding: 2px 10px;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(0, 212, 255, 0.4);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #00d4ff;
}

.advice-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.advice-line {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0;
  font-size: 13px;
  color: #cbd5e1;
  line-height: 1.6;
}

.advice-priority {
  flex-shrink: 0;
  margin-top: 1px;
}

.advice-empty {
  margin: 0;
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
  padding: 12px 0;
}

/* 底部统计 */
.statistics-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(100, 116, 139, 0.2);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 10px;
  border: 1px solid rgba(100, 116, 139, 0.2);
}

.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: rgba(245, 158, 11, 0.2);
  color: #f59e0b;
  flex-shrink: 0;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #e2e8f0;
  font-family: 'Courier New', monospace;
}

/* 响应式 */
@media (max-width: 1200px) {
  .systems-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .reliability-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .systems-grid {
    grid-template-columns: 1fr;
  }
  .reliability-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .statistics-section {
    grid-template-columns: 1fr;
  }
  .header-tags {
    width: 100%;
  }
}
</style>
