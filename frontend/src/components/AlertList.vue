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
  background: var(--am-card-bg);
  border: 1px solid color-mix(in srgb, var(--am-danger) 30%, transparent);
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
  background: color-mix(in srgb, var(--am-danger) 13%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--am-danger) 20%, transparent);
}

.alert-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--am-danger);
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
  background: color-mix(in srgb, var(--am-danger) 8%, transparent);
}

.alert-item.warning {
  background: color-mix(in srgb, var(--am-warn) 8%, transparent);
}

.alert-item.info {
  background: color-mix(in srgb, var(--am-accent) 8%, transparent);
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
  background: color-mix(in srgb, var(--am-danger) 22%, transparent);
  color: var(--am-danger);
}

.alert-item.warning .alert-icon {
  background: color-mix(in srgb, var(--am-warn) 22%, transparent);
  color: var(--am-warn);
}

.alert-item.info .alert-icon {
  background: color-mix(in srgb, var(--am-accent) 22%, transparent);
  color: var(--am-accent);
}

.alert-content {
  flex: 1;
  min-width: 0;
}

.alert-message {
  font-size: 13px;
  color: var(--am-text);
  margin-bottom: 4px;
  word-wrap: break-word;
}

.alert-time {
  font-size: 11px;
  color: var(--am-text-3);
}

.dismiss-btn {
  opacity: 0.5;
  transition: opacity 0.2s;
}

.alert-item:hover .dismiss-btn {
  opacity: 1;
}
</style>
