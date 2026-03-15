<template>
  <el-card class="servo-control-card" shadow="never">
    <template #header>
      <div class="card-header">
        <span class="header-title">
          <el-icon><Switch /></el-icon>
          舵机控制 (红外挡板)
        </span>
        <el-tag :type="servoStatus.isMoving ? 'warning' : (servoStatus.isOpen ? 'success' : 'info')" size="small">
          {{ servoStatus.isMoving ? '运动中' : (servoStatus.isOpen ? '已开启' : '已关闭') }}
        </el-tag>
      </div>
    </template>
    
    <div class="servo-content">
      <!-- 状态显示 -->
      <div class="servo-status-display">
        <div class="status-item">
          <span class="status-label">当前位置:</span>
          <span class="status-value">{{ servoStatus.position }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">目标位置:</span>
          <span class="status-value">{{ servoStatus.target }}</span>
        </div>
        <div class="status-item">
          <span class="status-label">挡板状态:</span>
          <el-tag 
            :type="servoStatus.isOpen ? 'success' : 'danger'" 
            size="small"
            effect="dark"
          >
            {{ servoStatus.isOpen ? '移开 (可拍摄)' : '遮挡 (保护)' }}
          </el-tag>
        </div>
      </div>
      
      <!-- 位置可视化 -->
      <div class="servo-visualization">
        <div class="position-bar">
          <div class="position-track">
            <div 
              class="position-indicator" 
              :style="{ left: `${positionPercentage}%` }"
            ></div>
          </div>
          <div class="position-labels">
            <span>关闭 (1500)</span>
            <span>中间 (2000)</span>
            <span>开启 (2500)</span>
          </div>
        </div>
      </div>
      
      <!-- 控制按钮 -->
      <div class="servo-controls">
        <el-button 
          type="danger" 
          size="large"
          :disabled="!isRunning || servoStatus.isMoving"
          @click="handleClose"
        >
          <el-icon><CircleClose /></el-icon>
          关闭挡板
        </el-button>
        
        <el-button 
          type="primary" 
          size="large"
          :disabled="!isRunning || servoStatus.isMoving"
          @click="handleToggle"
        >
          <el-icon><Switch /></el-icon>
          {{ servoStatus.isOpen ? '关闭' : '开启' }}
        </el-button>
        
        <el-button 
          type="success" 
          size="large"
          :disabled="!isRunning || servoStatus.isMoving"
          @click="handleOpen"
        >
          <el-icon><CircleCheck /></el-icon>
          开启挡板
        </el-button>
      </div>
      
      <!-- 精细控制 -->
      <div class="servo-fine-control">
        <el-divider content-position="left">精细控制</el-divider>
        <div class="slider-control">
          <span class="slider-label">位置:</span>
          <el-slider
            v-model="targetPosition"
            :min="1500"
            :max="2500"
            :step="10"
            :disabled="!isRunning || servoStatus.isMoving"
            show-input
            class="position-slider"
          />
          <el-button 
            type="primary" 
            size="small"
            :disabled="!isRunning || servoStatus.isMoving"
            @click="handleMove(targetPosition)"
          >
            移动
          </el-button>
        </div>
      </div>
      
      <!-- 预设位置 -->
      <div class="servo-presets">
        <el-divider content-position="left">预设位置</el-divider>
        <div class="preset-buttons">
          <el-button 
            v-for="preset in presets" 
            :key="preset.value"
            :type="preset.type"
            size="small"
            :disabled="!isRunning || servoStatus.isMoving"
            @click="handleMove(preset.value)"
          >
            {{ preset.label }} ({{ preset.value }})
          </el-button>
        </div>
      </div>
      
      <!-- 说明 -->
      <div class="servo-info">
        <el-alert
          type="info"
          :closable="false"
          show-icon
        >
          <template #title>
            舵机位置说明
          </template>
          <template #default>
            <ul>
              <li><strong>1500 (关闭):</strong> 挡板遮挡红外摄像头，保护镜头</li>
              <li><strong>2500 (开启):</strong> 挡板移开，红外摄像头可以正常拍摄</li>
              <li>激光烧结过程中建议保持关闭，需要拍摄时开启</li>
            </ul>
          </template>
        </el-alert>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Switch, CircleClose, CircleCheck } from '@element-plus/icons-vue'

const props = defineProps({
  isRunning: {
    type: Boolean,
    default: false
  },
  servoStatus: {
    type: Object,
    default: () => ({
      position: 1500,
      target: 1500,
      isOpen: false,
      isMoving: false
    })
  }
})

const emit = defineEmits(['servo-move', 'servo-toggle'])

const targetPosition = ref(2000)

// 预设位置
const presets = [
  { label: '完全关闭', value: 1500, type: 'danger' },
  { label: '半开', value: 2000, type: 'warning' },
  { label: '完全开启', value: 2500, type: 'success' }
]

// 位置百分比（用于可视化）
const positionPercentage = computed(() => {
  const pos = props.servoStatus.position
  // 将 1500-2500 映射到 0-100%
  return ((pos - 1500) / 1000) * 100
})

// 关闭挡板
const handleClose = () => {
  emit('servo-move', 1500)
}

// 开启挡板
const handleOpen = () => {
  emit('servo-move', 2500)
}

// 切换状态
const handleToggle = () => {
  emit('servo-toggle')
}

// 移动到指定位置
const handleMove = (position) => {
  targetPosition.value = position
  emit('servo-move', position)
}
</script>

<style scoped>
.servo-control-card {
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
  display: flex;
  align-items: center;
  gap: 8px;
}

.servo-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 状态显示 */
.servo-status-display {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding: 16px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.status-label {
  font-size: 12px;
  color: #94a3b8;
}

.status-value {
  font-size: 18px;
  font-weight: 600;
  color: #e2e8f0;
  font-family: 'Courier New', monospace;
}

/* 可视化 */
.servo-visualization {
  padding: 16px;
  background: rgba(30, 41, 59, 0.3);
  border-radius: 8px;
}

.position-bar {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.position-track {
  position: relative;
  height: 8px;
  background: linear-gradient(to right, #ef4444 0%, #f59e0b 50%, #22c55e 100%);
  border-radius: 4px;
}

.position-indicator {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 16px;
  height: 16px;
  background: #fff;
  border: 2px solid #3b82f6;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.5);
  transition: left 0.3s ease;
}

.position-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
}

/* 控制按钮 */
.servo-controls {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

/* 精细控制 */
.servo-fine-control {
  padding: 0 16px;
}

.slider-control {
  display: flex;
  align-items: center;
  gap: 16px;
}

.slider-label {
  font-size: 13px;
  color: #94a3b8;
  min-width: 40px;
}

.position-slider {
  flex: 1;
}

/* 预设按钮 */
.servo-presets {
  padding: 0 16px;
}

.preset-buttons {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* 说明 */
.servo-info {
  padding: 0 16px;
}

.servo-info ul {
  margin: 8px 0;
  padding-left: 20px;
}

.servo-info li {
  margin: 4px 0;
  font-size: 13px;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .servo-status-display {
    grid-template-columns: 1fr;
  }
  
  .servo-controls {
    flex-direction: column;
  }
  
  .slider-control {
    flex-direction: column;
    align-items: stretch;
  }
  
  .preset-buttons {
    flex-direction: column;
  }
}
</style>
