<template>
  <el-card class="maintenance-panel" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">
          <el-icon><FirstAidKit /></el-icon>
          视情维护可视化
        </span>
        <div class="header-tags">
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
        role="button"
        tabindex="0"
        :aria-label="`${system.name}维护详情`"
        @keydown.enter="handleSystemClick(system)"
        @keydown.space.prevent="handleSystemClick(system)"
        :class="{ 'risk-warning': system.riskPercent > 50 && system.riskPercent <= 80, 'risk-danger': system.riskPercent > 80 }"
        @click="handleSystemClick(system)"
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
              v-if="Number.isFinite(system.thresholdPercent)" class="risk-threshold-mark"
              :style="{ left: Math.min(system.thresholdPercent, 100) + '%' }"
            >
              <div class="threshold-line"></div>
              <div class="threshold-tooltip">阈值</div>
            </div>
          </div>
          <div class="risk-labels">
            <span class="risk-current" :style="{ color: getRiskColor(system.riskPercent) }">
              当前: {{ fmt(system.riskValue) }}
            </span>
            <span class="risk-threshold">阈值: {{ fmt(system.thresholdValue) }}</span>
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
            <el-icon><CircleCheck v-if="system.reliability >= 0.7" /><Warning v-else-if="Number.isFinite(system.reliability)" /></el-icon>
          </div>
          <div class="rel-content">
            <span class="rel-name">{{ system.name }}</span>
            <span
              class="rel-value"
              :style="{ color: getReliabilityColor(system.reliability) }"
            >
              {{ Number.isFinite(system.reliability) ? (system.reliability * 100).toFixed(1) + '%' : '—' }}
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
            暂无已接入的维修建议。
          </p>
        </div>
      </div>
    </div>

    <!-- 底部统计信息 -->
    <p v-if="statisticsError" role="alert">{{ statisticsError }}</p>
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
        <div class="stat-icon" style="background: var(--am-accent-soft); color: var(--am-accent);">
          <el-icon><FirstAidKit /></el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-label">维护记录次数</span>
          <span class="stat-value">{{ displayStats.preventiveRepairs }}</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: var(--am-ok-soft); color: var(--am-ok);">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <span class="stat-label">故障任务率</span>
          <span class="stat-value">{{ displayStats.rateText }}%</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useMaintenanceStatistics } from '../../composables/useMaintenanceStatistics'
import { FirstAidKit, Odometer, Warning, CircleCheck } from '@element-plus/icons-vue'

const props = defineProps({
  deviceId: {type:String,default:''},
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

const emit = defineEmits(['system-click'])

const handleSystemClick = (system) => {
  emit('system-click', { key: system.key, name: system.name })
}

// 只固定系统结构，风险与可靠性必须来自该设备的计算结果。
const systemDefinitions = [
  ['filter', '高效滤芯'], ['argon', '氩气循环系统'], ['powder', '铺粉成型系统（刮刀）'],
  ['feeder', '落粉轴系统'], ['laser', '激光器'], ['fan', '风机']
]
const fmt = value => Number.isFinite(value) ? value.toFixed(2) : '—'

const {statistics:apiStats, error:statisticsError} = useMaintenanceStatistics(() => props.deviceId ? [props.deviceId] : null)

const displaySystems = computed(() => systemDefinitions.map(([key, name]) => ({
  key, name, riskValue: null, thresholdValue: null, riskPercent: null, thresholdPercent: null, reliability: null,
  ...props.systems.find(system => system.key === key)
})))
const displayStats = computed(() => ({ ...apiStats.value, ...props.statistics }))
const adviceLines = computed(() => props.advice)

const overallStatus = computed(() => {
  if (displaySystems.value.some(s => !Number.isFinite(s.riskPercent))) return {type:'info', label:'评估数据未齐备'}
  const maxRisk = Math.max(...displaySystems.value.map(s => s.riskPercent))
  if (maxRisk > 80) return { type: 'danger', label: '高风险' }
  if (maxRisk > 50) return { type: 'warning', label: '中风险' }
  return { type: 'success', label: '低风险' }
})

const getRiskColor = (percent) => {
  if (!Number.isFinite(percent)) return '#87919d'
  if (percent > 80) return '#ef4444'
  if (percent > 50) return '#f59e0b'
  return '#22c55e'
}

const getRiskTagType = (percent) => {
  if (!Number.isFinite(percent)) return 'info'
  if (percent > 80) return 'danger'
  if (percent > 50) return 'warning'
  return 'success'
}

const getRiskLabel = (percent) => {
  if (!Number.isFinite(percent)) return '未接入'
  if (percent > 80) return '超阈值'
  if (percent > 50) return '预警'
  return '正常'
}

const getReliabilityColor = (value) => {
  if (!Number.isFinite(value)) return '#87919d'
  if (value >= 0.85) return '#22c55e'
  if (value >= 0.60) return '#f59e0b'
  return '#ef4444'
}
</script>

<style scoped>
.maintenance-panel {
  background: var(--am-card-bg);
  border: 1px solid var(--am-card-border);
  color: var(--am-text);
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
  color: var(--am-text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-tags {
  display: flex;
  gap: 8px;
}

/* 6个系统网格 */
.systems-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.system-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  background: var(--am-card-bg-2);
  border-radius: 4px;
  border: 1px solid var(--am-card-border-2);
  transition: border-color .15s ease;
}

.system-card:hover {
  border-color: color-mix(in srgb, var(--am-accent) 30%, transparent);

  cursor: pointer;
}

.system-card::after {
  content: '查看详情';
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 2px 6px;
  font-size: 10px;
  color: var(--am-accent);
  background: color-mix(in srgb, var(--am-accent) 13%, transparent);
  border: 1px solid color-mix(in srgb, var(--am-accent) 20%, transparent);
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.system-card:focus-visible::after, .system-card:hover::after {
  opacity: 1;
}

.system-card.risk-warning {
  border-color: color-mix(in srgb, var(--am-warn) 40%, transparent);
  background: color-mix(in srgb, var(--am-warn) 8%, transparent);
}

.system-card.risk-danger {
  border-color: color-mix(in srgb, var(--am-danger) 50%, transparent);
  background: color-mix(in srgb, var(--am-danger) 11%, transparent);

}



.system-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--am-text);
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
  background: var(--am-card-bg-2);
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
    var(--am-accent) 0px,
    var(--am-accent) 3px,
    transparent 3px,
    transparent 6px
  );
}

.threshold-tooltip {
  position: absolute;
  top: -16px;
  font-size: 10px;
  color: var(--am-accent);
  background: var(--am-card-bg);
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
  border: 1px solid color-mix(in srgb, var(--am-accent) 30%, transparent);
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
  color: var(--am-text-2);
}

.system-status {
  display: flex;
  justify-content: center;
}

/* 可靠性区域 */
.reliability-section {
  margin-bottom: 20px;
  padding: 16px;
  background: var(--am-card-bg-2);
  border-radius: 4px;
  border: 1px solid var(--am-card-border-2);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--am-text);
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
  background: var(--am-card-bg-2);
  border-radius: 8px;
  border: 1px solid var(--am-card-border-2);
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
  color: var(--am-text-2);
  line-height: 1.3;
}

.rel-value {
  font-size: 18px;
  font-weight: 700;
}

.rel-bar-bg {
  width: 100%;
  height: 4px;
  background: var(--am-card-bg-2);
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
  background: var(--am-card-bg-2);
  border-radius: 4px;
  border: 1px solid var(--am-card-border);
  min-height: 80px;
}

.advice-label {
  position: absolute;
  top: -10px;
  left: 12px;
  padding: 2px 10px;
  background: var(--am-card-bg);
  border: 1px solid color-mix(in srgb, var(--am-accent) 40%, transparent);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--am-accent);
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
  color: var(--am-text);
  line-height: 1.6;
}

.advice-priority {
  flex-shrink: 0;
  margin-top: 1px;
}

.advice-empty {
  margin: 0;
  font-size: 13px;
  color: var(--am-text-2);
  text-align: center;
  padding: 12px 0;
}

/* 底部统计 */
.statistics-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--am-card-border-2);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--am-card-bg-2);
  border-radius: 4px;
  border: 1px solid var(--am-card-border-2);
}

.stat-icon {
  width: 42px;
  height: 42px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: color-mix(in srgb, var(--am-warn) 22%, transparent);
  color: var(--am-warn);
  flex-shrink: 0;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 12px;
  color: var(--am-text-2);
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--am-text);
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
