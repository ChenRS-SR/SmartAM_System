<template>
  <div class="alert-list">
    <div class="alert-header">
      <span class="alert-title">
        <el-icon><WarningFilled /></el-icon>
        告警通知 ({{ alerts.length }})
      </span>
      <el-button text size="small" @click="dismissAll">
        全部清除
      </el-button>
    </div>
    <div class="alert-items">
      <div 
        v-for="alert in alerts" 
        :key="alert.id"
        class="alert-item"
        :class="alert.level"
      >
        <div class="alert-icon">
          <el-icon size="16">
            <CircleCloseFilled v-if="alert.level === 'error'" />
            <WarningFilled v-else-if="alert.level === 'warning'" />
            <InfoFilled v-else />
          </el-icon>
        </div>
        <div class="alert-content">
          <div class="alert-message">{{ alert.message }}</div>
          <div class="alert-time">{{ formatTime(alert.timestamp) }}</div>
        </div>
        <el-button 
          text 
          size="small" 
          @click="dismiss(alert.id)"
          class="dismiss-btn"
        >
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { WarningFilled, CircleCloseFilled, InfoFilled, Close } from '@element-plus/icons-vue'
import { useDataStore } from '../stores/data'

const props = defineProps({
  alerts: { type: Array, default: () => [] }
})

const store = useDataStore()

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

const dismiss = (id) => {
  store.dismissAlert(id)
}

const dismissAll = () => {
  store.clearAlerts()
}
</script>

<style scoped>
.alert-list {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 360px;
  max-height: 400px;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 77, 79, 0.3);
  border-radius: 12px;
  overflow: hidden;
  z-index: 2000;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 77, 79, 0.1);
  border-bottom: 1px solid rgba(255, 77, 79, 0.2);
}

.alert-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ff4d4f;
  font-weight: 500;
}

.alert-items {
  max-height: 320px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  transition: background 0.2s;
}

.alert-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.alert-item.error {
  background: rgba(255, 77, 79, 0.05);
}

.alert-item.warning {
  background: rgba(255, 193, 7, 0.05);
}

.alert-item.info {
  background: rgba(0, 212, 255, 0.05);
}

.alert-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.alert-item.error .alert-icon {
  background: rgba(255, 77, 79, 0.2);
  color: #ff4d4f;
}

.alert-item.warning .alert-icon {
  background: rgba(255, 193, 7, 0.2);
  color: #ffc107;
}

.alert-item.info .alert-icon {
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
}

.alert-content {
  flex: 1;
  min-width: 0;
}

.alert-message {
  font-size: 13px;
  color: #e2e8f0;
  margin-bottom: 4px;
  word-wrap: break-word;
}

.alert-time {
  font-size: 11px;
  color: #64748b;
}

.dismiss-btn {
  opacity: 0.5;
  transition: opacity 0.2s;
}

.alert-item:hover .dismiss-btn {
  opacity: 1;
}
</style>
