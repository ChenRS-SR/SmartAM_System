<template>
  <div class="prediction-panel">
    <div class="panel-header">
      <el-icon size="20" color="#00d4ff"><Cpu /></el-icon>
      <span class="panel-title">PacNet 预测结果</span>
      <el-tag v-if="prediction.inference_time_ms" size="small" type="info" effect="dark">
        {{ prediction.inference_time_ms.toFixed(1) }}ms
      </el-tag>
    </div>
    
    <div class="prediction-list">
      <div 
        v-for="item in predictionItems" 
        :key="item.key"
        class="prediction-item"
        :class="item.className"
      >
        <div class="item-info">
          <span class="item-name">{{ item.name }}</span>
          <span class="item-label" :style="{ color: item.color }">
            {{ item.label }}
          </span>
        </div>
        <div class="item-confidence">
          <el-progress 
            :percentage="item.confidence * 100" 
            :color="item.color"
            :stroke-width="8"
            :show-text="false"
          />
          <span class="confidence-value">{{ (item.confidence * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>
    
    <div v-if="!prediction.available" class="no-data">
      <el-icon size="32" color="#666"><Warning /></el-icon>
      <span>等待推理结果...</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  prediction: {
    type: Object,
    default: () => ({
      available: false,
      flow_rate: { label: 'Normal', confidence: 0 },
      feed_rate: { label: 'Normal', confidence: 0 },
      z_offset: { label: 'Normal', confidence: 0 },
      hot_end: { label: 'Normal', confidence: 0 },
      inference_time_ms: 0
    })
  }
})

const labelColors = {
  'Low': '#ffc107',      // 黄色
  'Normal': '#00ff88',   // 绿色
  'High': '#ff4d4f'      // 红色
}

const predictionItems = computed(() => {
  const items = [
    { key: 'flow_rate', name: '流量 (Flow Rate)', data: props.prediction.flow_rate },
    { key: 'feed_rate', name: '速度 (Feed Rate)', data: props.prediction.feed_rate },
    { key: 'z_offset', name: 'Z偏移 (Z Offset)', data: props.prediction.z_offset },
    { key: 'hot_end', name: '温度 (Hotend)', data: props.prediction.hot_end }
  ]
  
  return items.map(item => ({
    key: item.key,
    name: item.name,
    label: item.data?.label || 'Normal',
    confidence: item.data?.confidence || 0,
    color: labelColors[item.data?.label] || '#00ff88',
    className: item.data?.label?.toLowerCase() || 'normal'
  }))
})
</script>

<style scoped>
.prediction-panel {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  padding: 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.2);
}

.panel-title {
  font-size: 16px;
  font-weight: 500;
  color: #e2e8f0;
  flex: 1;
}

.prediction-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.prediction-item {
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border-left: 3px solid transparent;
  transition: all 0.3s;
}

.prediction-item.low {
  border-left-color: #ffc107;
  background: rgba(255, 193, 7, 0.1);
}

.prediction-item.normal {
  border-left-color: #00ff88;
  background: rgba(0, 255, 136, 0.1);
}

.prediction-item.high {
  border-left-color: #ff4d4f;
  background: rgba(255, 77, 79, 0.1);
}

.item-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-name {
  font-size: 13px;
  color: #a0aec0;
}

.item-label {
  font-size: 14px;
  font-weight: 600;
}

.item-confidence {
  display: flex;
  align-items: center;
  gap: 10px;
}

.item-confidence :deep(.el-progress) {
  flex: 1;
}

.confidence-value {
  font-size: 12px;
  color: #a0aec0;
  min-width: 40px;
  text-align: right;
}

.no-data {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #666;
  gap: 12px;
}
</style>
