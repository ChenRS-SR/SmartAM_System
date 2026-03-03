<template>
  <div class="status-card">
    <div class="card-icon" :style="{ background: iconBg }">
      <el-icon :size="28" :color="iconColor">
        <component :is="icon" />
      </el-icon>
    </div>
    <div class="card-content">
      <div class="card-label">{{ label }}</div>
      <div class="card-value" :style="{ color: valueColor }">
        {{ value }}
        <span v-if="unit" class="card-unit">{{ unit }}</span>
      </div>
      <div v-if="subValue" class="card-sub">{{ subValue }}</div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  unit: { type: String, default: '' },
  subValue: { type: String, default: '' },
  iconBg: { type: String, default: 'rgba(0, 212, 255, 0.2)' },
  iconColor: { type: String, default: '#00d4ff' },
  valueColor: { type: String, default: '#e2e8f0' }
})
</script>

<style scoped>
.status-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.3s;
}

.status-card:hover {
  border-color: rgba(0, 212, 255, 0.4);
  transform: translateY(-2px);
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-content {
  flex: 1;
  min-width: 0;
}

.card-label {
  font-size: 13px;
  color: #a0aec0;
  margin-bottom: 4px;
}

.card-value {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
}

.card-unit {
  font-size: 14px;
  color: #a0aec0;
  margin-left: 4px;
}

.card-sub {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}
</style>
