<template>
  <el-card class="health-status-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">SLM设备健康状态</span>
        <el-tag 
          :type="healthTagType" 
          size="small"
          effect="dark"
        >
          {{ healthStatusText }}
        </el-tag>
      </div>
    </template>
    
    <div class="health-content">
      <!-- 左侧：设备状态图 -->
      <div class="status-image-section">
        <div class="status-image-container">
          <img 
            :src="currentStatusImage" 
            alt="SLM Equipment Status"
            class="status-image"
          />
          <div v-if="isCompoundFault" class="fault-overlay">
            <el-icon :size="48" color="#ef4444"><Warning /></el-icon>
          </div>
        </div>
        
        <!-- 状态图例 -->
        <div class="image-legend">
          <div 
            v-for="(item, key) in statusImages" 
            :key="key"
            class="legend-item"
            :class="{ 'active': currentStatus === key }"
          >
            <div class="legend-dot" :style="{ background: item.color }"></div>
            <span class="legend-label">{{ item.label }}</span>
          </div>
        </div>
      </div>
      
      <!-- 右侧：文字状态介绍 -->
      <div class="status-text-section">
        <!-- 主要状态 -->
        <div class="main-status">
          <h3 class="status-title" :style="{ color: currentStatusColor }">
            {{ healthData.status_labels?.join(' + ') || '系统正常' }}
          </h3>
          <p class="status-description">
            {{ currentStatusDescription }}
          </p>
        </div>
        
        <!-- 子系统状态 -->
        <div class="subsystems-status">
          <h4 class="subsection-title">子系统状态</h4>
          
          <!-- 光路与激光系统 -->
          <div class="subsystem-item" :class="{ 'fault': isLaserFault }">
            <div class="subsystem-header">
              <div class="subsystem-icon" :class="{ 'fault': isLaserFault }">
                <el-icon><Sunny /></el-icon>
              </div>
              <div class="subsystem-info">
                <span class="subsystem-name">光路与激光系统</span>
                <span class="subsystem-status" :class="{ 'fault': isLaserFault }">
                  {{ healthData.laser_system?.message || '未检测' }}
                </span>
              </div>
              <el-tag 
                :type="isLaserFault ? 'danger' : 'success'" 
                size="small"
                effect="isLaserFault ? 'dark' : 'light'"
              >
                {{ isLaserFault ? '异常' : '健康' }}
              </el-tag>
            </div>
            <div v-if="isLaserFault" class="subsystem-detail">
              <el-alert type="error" :closable="false" show-icon>
                <template #title>
                  检测到激光功率衰减或波动，建议检查激光器状态
                </template>
              </el-alert>
            </div>
          </div>
          
          <!-- 铺粉运动系统 -->
          <div class="subsystem-item" :class="{ 'fault': isPowderFault }">
            <div class="subsystem-header">
              <div class="subsystem-icon" :class="{ 'fault': isPowderFault }">
                <el-icon><FirstAidKit /></el-icon>
              </div>
              <div class="subsystem-info">
                <span class="subsystem-name">铺粉运动系统</span>
                <span class="subsystem-status" :class="{ 'fault': isPowderFault }">
                  {{ healthData.powder_system?.message || '未检测' }}
                </span>
              </div>
              <el-tag 
                :type="isPowderFault ? 'danger' : 'success'" 
                size="small"
                effect="isPowderFault ? 'dark' : 'light'"
              >
                {{ isPowderFault ? '异常' : '健康' }}
              </el-tag>
            </div>
            <div v-if="isPowderFault" class="subsystem-detail">
              <el-alert type="error" :closable="false" show-icon>
                <template #title>
                  检测到刮刀磨损，建议检查并更换刮刀
                </template>
              </el-alert>
            </div>
          </div>
          
          <!-- 保护氛围系统 -->
          <div class="subsystem-item" :class="{ 'fault': isGasFault }">
            <div class="subsystem-header">
              <div class="subsystem-icon" :class="{ 'fault': isGasFault }">
                <el-icon><WindPower /></el-icon>
              </div>
              <div class="subsystem-info">
                <span class="subsystem-name">保护氛围系统</span>
                <span class="subsystem-status" :class="{ 'fault': isGasFault }">
                  {{ healthData.gas_system?.message || '未检测' }}
                </span>
              </div>
              <el-tag 
                :type="isGasFault ? 'danger' : 'success'" 
                size="small"
                effect="isGasFault ? 'dark' : 'light'"
              >
                {{ isGasFault ? '异常' : '健康' }}
              </el-tag>
            </div>
            <div v-if="isGasFault" class="subsystem-detail">
              <el-alert type="error" :closable="false" show-icon>
                <template #title>
                  检测到舱内气体异常，建议检查气体供应系统
                </template>
              </el-alert>
            </div>
          </div>
        </div>
        
        <!-- 状态标签 -->
        <div class="status-tags-section">
          <h4 class="subsection-title">状态标签</h4>
          <div class="status-tags">
            <el-tag 
              v-for="(label, index) in healthData.status_labels" 
              :key="index"
              type="danger"
              effect="dark"
              size="small"
              class="status-tag"
            >
              {{ label }}
            </el-tag>
            <el-tag 
              v-if="!healthData.status_labels?.length"
              type="success"
              effect="light"
              size="small"
            >
              系统运行正常
            </el-tag>
          </div>
        </div>
        
        <!-- 状态码信息 -->
        <div class="status-code-info">
          <span class="code-label">状态码:</span>
          <el-tag type="info" size="small">{{ healthData.status_code || 0 }}</el-tag>
          <span class="code-hint">（0=健康, 1/2=刮刀磨损, 3=激光异常, 4=气体异常）</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { Warning, Sunny, FirstAidKit, WindPower } from '@element-plus/icons-vue'

const props = defineProps({
  healthData: {
    type: Object,
    default: () => ({
      status: 'power_off',
      status_code: 0,
      status_labels: [],
      laser_system: { status: 'unknown', message: '未检测' },
      powder_system: { status: 'unknown', message: '未检测' },
      gas_system: { status: 'unknown', message: '未检测' }
    })
  }
})

// 状态图片配置
const statusImages = {
  power_off: {
    src: '/state_picture/power_off.png',
    label: '未开机',
    color: '#64748b'
  },
  healthy: {
    src: '/state_picture/power_on.png',
    label: '全系统正常',
    color: '#22c55e'
  },
  laser_fault: {
    src: '/state_picture/fault_laser.png',
    label: '激光系统异常',
    color: '#ef4444'
  },
  powder_fault: {
    src: '/state_picture/fault_powder.png',
    label: '铺粉系统异常',
    color: '#ef4444'
  },
  gas_fault: {
    src: '/state_picture/fault_gas.png',
    label: '保护气体异常',
    color: '#ef4444'
  },
  compound_fault: {
    src: '/state_picture/power_on.png',  // 使用power_on作为基础图
    label: '复合故障',
    color: '#dc2626'
  }
}

// 当前状态
const currentStatus = computed(() => {
  return props.healthData.status || 'power_off'
})

// 当前状态图片
const currentStatusImage = computed(() => {
  return statusImages[currentStatus.value]?.src || statusImages.power_off.src
})

// 是否复合故障
const isCompoundFault = computed(() => {
  return currentStatus.value === 'compound_fault' || 
         (props.healthData.status_labels?.length > 1)
})

// 各子系统故障状态
const isLaserFault = computed(() => {
  return props.healthData.laser_system?.status === 'fault' ||
         currentStatus.value === 'laser_fault'
})

const isPowderFault = computed(() => {
  return props.healthData.powder_system?.status === 'fault' ||
         currentStatus.value === 'powder_fault'
})

const isGasFault = computed(() => {
  return props.healthData.gas_system?.status === 'fault' ||
         currentStatus.value === 'gas_fault'
})

// 健康状态文本
const healthStatusText = computed(() => {
  const statusMap = {
    'power_off': '未开机',
    'healthy': '系统健康',
    'laser_fault': '激光系统异常',
    'powder_fault': '铺粉系统异常',
    'gas_fault': '保护气体异常',
    'compound_fault': '复合故障'
  }
  return statusMap[currentStatus.value] || '未知状态'
})

// 健康标签类型
const healthTagType = computed(() => {
  const typeMap = {
    'power_off': 'info',
    'healthy': 'success',
    'laser_fault': 'danger',
    'powder_fault': 'danger',
    'gas_fault': 'danger',
    'compound_fault': 'danger'
  }
  return typeMap[currentStatus.value] || 'info'
})

// 当前状态颜色
const currentStatusColor = computed(() => {
  const colorMap = {
    'power_off': '#64748b',
    'healthy': '#22c55e',
    'laser_fault': '#ef4444',
    'powder_fault': '#ef4444',
    'gas_fault': '#ef4444',
    'compound_fault': '#dc2626'
  }
  return colorMap[currentStatus.value] || '#64748b'
})

// 当前状态描述
const currentStatusDescription = computed(() => {
  const descMap = {
    'power_off': '设备未开机，请启动设备后查看状态',
    'healthy': '所有系统运行正常，设备处于良好工作状态',
    'laser_fault': '检测到激光系统异常，可能存在激光功率衰减或波动，建议检查激光器状态',
    'powder_fault': '检测到铺粉运动系统异常，可能存在刮刀磨损，建议检查并更换刮刀',
    'gas_fault': '检测到保护氛围系统异常，舱内气体可能存在异常，建议检查气体供应系统',
    'compound_fault': '检测到多个系统异常，请立即检查设备状态并采取相应措施'
  }
  return descMap[currentStatus.value] || '设备状态未知'
})
</script>

<style scoped>
.health-status-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
}

.health-content {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 24px;
}

/* 状态图区域 */
.status-image-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-image-container {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: rgba(30, 41, 59, 0.5);
  border: 2px solid rgba(100, 116, 139, 0.2);
}

.status-image {
  width: 100%;
  height: auto;
  display: block;
  transition: all 0.3s ease;
}

.fault-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(239, 68, 68, 0.2);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.5;
  }
  50% {
    opacity: 0.8;
  }
}

.image-legend {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.3);
  transition: all 0.3s ease;
}

.legend-item.active {
  background: rgba(100, 116, 139, 0.3);
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-label {
  font-size: 12px;
  color: #94a3b8;
}

/* 文字状态区域 */
.status-text-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.main-status {
  padding: 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border-left: 4px solid v-bind('currentStatusColor');
}

.status-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.status-description {
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.6;
}

.subsection-title {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  margin-bottom: 12px;
}

/* 子系统状态 */
.subsystems-status {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.subsystem-item {
  padding: 12px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 8px;
  border: 1px solid rgba(100, 116, 139, 0.2);
  transition: all 0.3s ease;
}

.subsystem-item.fault {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.subsystem-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.subsystem-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  transition: all 0.3s ease;
}

.subsystem-icon.fault {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.subsystem-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.subsystem-name {
  font-size: 13px;
  font-weight: 500;
  color: #e2e8f0;
}

.subsystem-status {
  font-size: 12px;
  color: #22c55e;
}

.subsystem-status.fault {
  color: #ef4444;
}

.subsystem-detail {
  margin-top: 10px;
}

/* 状态标签区域 */
.status-tags-section {
  padding: 12px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 8px;
}

.status-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-tag {
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}

/* 状态码信息 */
.status-code-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 6px;
  font-size: 12px;
}

.code-label {
  color: #94a3b8;
}

.code-hint {
  color: #64748b;
  font-size: 11px;
}

@media (max-width: 968px) {
  .health-content {
    grid-template-columns: 1fr;
  }
  
  .status-image-container {
    max-width: 400px;
    margin: 0 auto;
  }
}
</style>
