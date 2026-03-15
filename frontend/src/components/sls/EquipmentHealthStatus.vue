<template>
  <el-card class="health-status-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">SLS设备健康状态</span>
        <div class="header-actions">
          <el-switch
            v-model="isMockMode"
            active-text="模拟"
            inactive-text="真实"
            size="small"
            @change="onMockModeChange"
          />
          <el-tag 
            :type="currentStatusConfig.tagType" 
            size="small"
            effect="dark"
            class="status-tag"
          >
            {{ currentStatusConfig.label }}
          </el-tag>
        </div>
      </div>
    </template>
    
    <!-- 模拟控制面板 -->
    <div v-if="isMockMode" class="mock-control-panel">
      <el-divider content-position="left">
        <el-icon><Setting /></el-icon> 模拟控制
      </el-divider>
      <div class="mock-controls">
        <div class="mock-item">
          <span class="mock-label">状态码:</span>
          <el-input-number 
            v-model="mockStatusCode" 
            :min="-1" 
            :max="4" 
            :step="1"
            size="small"
            @change="onMockStatusChange"
          />
          <span class="mock-hint">(-1=未开机, 0=健康, 1=铺粉异常, 2=激光异常, 3=温度异常, 4=复合故障)</span>
        </div>
        <div class="mock-item">
          <span class="mock-label">当前模拟:</span>
          <el-tag size="small" :type="currentStatusConfig.tagType">
            {{ currentStatusConfig.label }}
          </el-tag>
        </div>
      </div>
    </div>

    <div class="health-content">
      <!-- 左侧：设备状态图 -->
      <div class="status-image-section">
        <div class="status-image-container" :class="{ 'fault': isFaultStatus }">
          <img 
            :src="currentStatusConfig.image" 
            :alt="currentStatusConfig.label"
            class="status-image"
            @error="onImageError"
          />
          <div v-if="isFaultStatus" class="fault-overlay">
            <el-icon :size="48" color="#ef4444"><Warning /></el-icon>
            <span class="fault-text">{{ currentStatusConfig.label }}</span>
          </div>
        </div>
        
        <div class="current-status-bar" :style="{ background: currentStatusConfig.color + '20', borderColor: currentStatusConfig.color }">
          <div class="status-dot-large" :style="{ background: currentStatusConfig.color }"></div>
          <div class="status-info">
            <div class="status-name" :style="{ color: currentStatusConfig.color }">{{ currentStatusConfig.label }}</div>
            <div class="status-code">状态码: {{ displayStatusCode }}</div>
          </div>
        </div>
      </div>
      
      <!-- 右侧：文字状态介绍 -->
      <div class="status-text-section">
        <div class="main-status" :class="{ 'fault': isFaultStatus }" :style="{ borderLeftColor: currentStatusConfig.color }">
          <h3 class="status-title" :style="{ color: currentStatusConfig.color }">
            {{ currentStatusConfig.title }}
          </h3>
          <p class="status-description">
            {{ currentStatusConfig.description }}
          </p>
        </div>
        
        <!-- 子系统状态 -->
        <div class="subsystems-status">
          <h4 class="subsection-title">子系统状态</h4>
          
          <!-- 激光系统 -->
          <div class="subsystem-item" :class="{ 'fault': isLaserFault, 'disabled': !isRunning }">
            <div class="subsystem-header">
              <div class="subsystem-icon" :class="{ 'fault': isLaserFault, 'disabled': !isRunning }">
                <el-icon><Sunny /></el-icon>
              </div>
              <div class="subsystem-info">
                <span class="subsystem-name">激光烧结系统</span>
                <span class="subsystem-status" :class="{ 'fault': isLaserFault }">
                  {{ isRunning ? (isLaserFault ? '激光功率异常' : '工作正常') : '未检测' }}
                </span>
              </div>
              <el-tag :type="isLaserFault ? 'danger' : 'success'" size="small">
                {{ isLaserFault ? '异常' : '健康' }}
              </el-tag>
            </div>
          </div>
          
          <!-- 铺粉系统 -->
          <div class="subsystem-item" :class="{ 'fault': isPowderFault, 'disabled': !isRunning }">
            <div class="subsystem-header">
              <div class="subsystem-icon" :class="{ 'fault': isPowderFault, 'disabled': !isRunning }">
                <el-icon><FirstAidKit /></el-icon>
              </div>
              <div class="subsystem-info">
                <span class="subsystem-name">铺粉系统</span>
                <span class="subsystem-status" :class="{ 'fault': isPowderFault }">
                  {{ isRunning ? (isPowderFault ? '铺粉异常' : '工作正常') : '未检测' }}
                </span>
              </div>
              <el-tag :type="isPowderFault ? 'danger' : 'success'" size="small">
                {{ isPowderFault ? '异常' : '健康' }}
              </el-tag>
            </div>
          </div>
          
          <!-- 温度系统 (SLS特有，关注烧结温度) -->
          <div class="subsystem-item" :class="{ 'fault': isTempFault, 'disabled': !isRunning }">
            <div class="subsystem-header">
              <div class="subsystem-icon" :class="{ 'fault': isTempFault, 'disabled': !isRunning }">
                <el-icon><MostlyCloudy /></el-icon>
              </div>
              <div class="subsystem-info">
                <span class="subsystem-name">温度监测系统</span>
                <span class="subsystem-status" :class="{ 'fault': isTempFault }">
                  {{ isRunning ? (isTempFault ? '温度异常' : '工作正常') : '未检测' }}
                </span>
              </div>
              <el-tag :type="isTempFault ? 'danger' : 'success'" size="small">
                {{ isTempFault ? '异常' : '健康' }}
              </el-tag>
            </div>
          </div>
        </div>
        
        <!-- 状态标签 -->
        <div v-if="currentStatusConfig.statusLabels.length > 1" class="status-tags-section">
          <h4 class="subsection-title">复合故障标签</h4>
          <div class="status-tags">
            <el-tag 
              v-for="(label, index) in currentStatusConfig.statusLabels" 
              :key="index"
              type="danger"
              effect="dark"
              size="small"
              class="status-tag"
            >
              {{ label }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Warning, Sunny, FirstAidKit, MostlyCloudy, Setting } from '@element-plus/icons-vue'

const props = defineProps({
  healthData: {
    type: Object,
    default: () => ({
      status: 'power_off',
      status_code: -1,
      status_labels: [],
      laser_system: { status: 'unknown', message: '未检测' },
      powder_system: { status: 'unknown', message: '未检测' },
      gas_system: { status: 'unknown', message: '未检测' }
    })
  },
  isRunning: {
    type: Boolean,
    default: false
  }
})

const isMockMode = ref(false)
const mockStatusCode = ref(-1)

// SLS状态码映射（与SLM略有不同，3=温度异常而非气体异常）
const statusCodeMap = {
  '-1': {
    code: -1,
    status: 'power_off',
    label: '未开机',
    title: '系统未启动',
    description: '设备未开机，请启动设备后查看状态。启动后将自动检测各子系统健康状态。',
    image: '/state_picture/power_off.png',
    color: '#64748b',
    tagType: 'info',
    statusLabels: []
  },
  '0': {
    code: 0,
    status: 'healthy',
    label: '全系统正常',
    title: '系统运行健康',
    description: '所有系统运行正常，SLS烧结过程稳定。激光功率正常，铺粉均匀，温度监测正常。',
    image: '/state_picture/health.png',
    color: '#22c55e',
    tagType: 'success',
    statusLabels: ['系统健康']
  },
  '1': {
    code: 1,
    status: 'powder_fault',
    label: '铺粉系统异常',
    title: '铺粉异常',
    description: '检测到铺粉不均匀或刮刀异常。建议检查刮刀状态和粉末供应。',
    image: '/state_picture/fault_powder.png',
    color: '#ef4444',
    tagType: 'danger',
    statusLabels: ['铺粉异常']
  },
  '2': {
    code: 2,
    status: 'laser_fault',
    label: '激光系统异常',
    title: '激光功率异常',
    description: '检测到激光功率衰减或波动，可能影响烧结质量。建议检查激光器状态和光学系统。',
    image: '/state_picture/fault_laser.png',
    color: '#ef4444',
    tagType: 'danger',
    statusLabels: ['激光功率异常']
  },
  '3': {
    code: 3,
    status: 'temp_fault',
    label: '温度监测异常',
    title: '烧结温度异常',
    description: '检测到烧结区域温度异常，可能影响成型质量。建议检查热像仪和烧结参数。',
    image: '/state_picture/fault_temp.png',
    color: '#ef4444',
    tagType: 'danger',
    statusLabels: ['温度异常']
  },
  '4': {
    code: 4,
    status: 'compound_fault',
    label: '复合故障',
    title: '多系统复合故障',
    description: '检测到多个系统同时异常，请立即检查设备状态。建议停机进行全面检查。',
    image: '/state_picture/fault_multi.png',
    color: '#dc2626',
    tagType: 'danger',
    statusLabels: ['复合故障', '需立即处理']
  }
}

const displayStatusCode = computed(() => {
  if (isMockMode.value) return mockStatusCode.value
  return props.healthData?.status_code ?? -1
})

const currentStatusConfig = computed(() => {
  const code = String(displayStatusCode.value)
  return statusCodeMap[code] || statusCodeMap['-1']
})

const isFaultStatus = computed(() => displayStatusCode.value >= 1)

const isLaserFault = computed(() => {
  const code = displayStatusCode.value
  return code === 2 || code === 4
})

const isPowderFault = computed(() => {
  const code = displayStatusCode.value
  return code === 1 || code === 4
})

const isTempFault = computed(() => {
  const code = displayStatusCode.value
  return code === 3 || code === 4
})

const onMockModeChange = (val) => {
  if (val) mockStatusCode.value = props.healthData?.status_code ?? -1
}

const onMockStatusChange = (val) => {
  console.log(`[SLS EquipmentHealth] 模拟状态码切换为: ${val}`)
}

const onImageError = (e) => {
  e.target.src = '/state_picture/power_off.png'
}

watch(() => props.healthData?.status_code, (newCode) => {
  if (!isMockMode.value && newCode !== undefined) {
    console.log(`[SLS EquipmentHealth] 真实状态码更新: ${newCode}`)
  }
})
</script>

<style scoped>
/* 样式与SLM版本相同，省略以节省空间 */
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mock-control-panel {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px dashed rgba(100, 116, 139, 0.5);
}

.mock-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mock-item {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.mock-label {
  font-size: 13px;
  color: #94a3b8;
  min-width: 70px;
}

.mock-hint {
  font-size: 11px;
  color: #64748b;
}

.health-content {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 24px;
}

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

.status-image-container.fault {
  border-color: rgba(239, 68, 68, 0.5);
  animation: border-pulse 2s infinite;
}

@keyframes border-pulse {
  0%, 100% { border-color: rgba(239, 68, 68, 0.5); }
  50% { border-color: rgba(239, 68, 68, 0.8); }
}

.status-image {
  width: 100%;
  height: auto;
  display: block;
}

.fault-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(239, 68, 68, 0.2);
  animation: pulse 2s infinite;
}

.fault-text {
  font-size: 14px;
  font-weight: 600;
  color: #ef4444;
}

.current-status-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 4px solid;
  background: rgba(30, 41, 59, 0.5);
}

.status-dot-large {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  box-shadow: 0 0 8px currentColor;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.status-name {
  font-size: 14px;
  font-weight: 600;
}

.status-code {
  font-size: 11px;
  color: #64748b;
}

.status-text-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.main-status {
  padding: 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border-left: 4px solid;
}

.main-status.fault {
  background: rgba(239, 68, 68, 0.1);
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
}

.subsystem-item.fault {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.subsystem-item.disabled {
  opacity: 0.5;
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
}

.subsystem-icon.fault {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.subsystem-icon.disabled {
  background: rgba(100, 116, 139, 0.2);
  color: #64748b;
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

@media (max-width: 968px) {
  .health-content {
    grid-template-columns: 1fr;
  }
}
</style>
