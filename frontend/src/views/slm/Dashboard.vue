<template>
  <div class="slm-dashboard">
    <h2 class="page-title">SLM 设备状态监控</h2>
    
    <div class="status-cards">
      <StatusCard
        icon="Tools"
        label="振镜系统"
        value="正常"
        subValue="健康度: 98%"
        iconBg="rgba(0, 255, 136, 0.2)"
        iconColor="#00ff88"
      />
      <StatusCard
        icon="Lightning"
        label="激光器"
        value="运行中"
        subValue="功率: 400W"
        iconBg="rgba(0, 212, 255, 0.2)"
        iconColor="#00d4ff"
      />
      <StatusCard
        icon="Box"
        label="铺粉系统"
        value="正常"
        subValue="刮刀状态: 良好"
        iconBg="rgba(0, 255, 136, 0.2)"
        iconColor="#00ff88"
      />
      <StatusCard
        icon="Monitor"
        label="氧含量"
        value="0.02%"
        subValue="阈值: < 0.1%"
        iconBg="rgba(0, 255, 136, 0.2)"
        iconColor="#00ff88"
      />
    </div>
    
    <div class="main-content">
      <el-card class="health-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>设备健康状态概览</span>
            <el-tag type="success">整体健康度: 96%</el-tag>
          </div>
        </template>
        <div class="health-content">
          <div class="health-placeholder">
            <el-icon size="64" color="#00d4ff"><FirstAidKit /></el-icon>
            <p>设备健康监控模块开发中...</p>
            <p class="sub-text">将显示各部件健康度及异常预警</p>
          </div>
        </div>
      </el-card>
      
      <el-card class="component-list" shadow="never">
        <template #header>
          <div class="card-header">
            <span>关键部件列表</span>
          </div>
        </template>
        <el-table :data="componentList" stripe>
          <el-table-column prop="name" label="部件名称" />
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              <el-tag :type="row.status === '正常' ? 'success' : 'warning'">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="health" label="健康度">
            <template #default="{ row }">
              <el-progress 
                :percentage="row.health" 
                :color="getHealthColor(row.health)"
                :stroke-width="8"
              />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import StatusCard from '../../components/StatusCard.vue'

const componentList = ref([
  { name: '激光器', status: '正常', health: 98 },
  { name: '振镜系统', status: '正常', health: 96 },
  { name: '铺粉刮刀', status: '正常', health: 94 },
  { name: '供粉系统', status: '正常', health: 92 },
  { name: '惰性气体系统', status: '正常', health: 95 },
  { name: '过滤系统', status: '注意', health: 78 },
  { name: '冷却系统', status: '正常', health: 97 },
])

const getHealthColor = (health) => {
  if (health >= 90) return '#00ff88'
  if (health >= 70) return '#ffc107'
  return '#ff4d4f'
}
</script>

<style scoped>
.slm-dashboard {
  padding: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0 0 20px 0;
}

.status-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.main-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.health-card,
.component-list {
  border: none;
  background: rgba(15, 23, 42, 0.6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.health-content {
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.health-placeholder {
  text-align: center;
  color: #94a3b8;
}

.health-placeholder p {
  margin: 12px 0 0 0;
  font-size: 16px;
}

.sub-text {
  font-size: 14px !important;
  color: #64748b;
}

@media (max-width: 1200px) {
  .status-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .main-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .status-cards {
    grid-template-columns: 1fr;
  }
}
</style>
