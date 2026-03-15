<template>
  <div class="sls-analysis">
    <div class="page-header">
      <h1 class="page-title">SLS 数据分析</h1>
    </div>
    
    <el-card class="analysis-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>数据采集分析</span>
          <el-button type="primary" size="small" @click="refreshData">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <div class="analysis-content">
        <el-empty description="SLS数据分析功能开发中">
          <template #image>
            <el-icon :size="60" color="#909399"><DataAnalysis /></el-icon>
          </template>
          <p class="empty-desc">
            该模块将提供SLS烧结过程的数据分析功能，包括：<br>
            - 温度场分析<br>
            - 振动频谱分析<br>
            - 铺粉质量评估<br>
            - 烧结缺陷检测
          </p>
        </el-empty>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { Refresh, DataAnalysis } from '@element-plus/icons-vue'

const refreshData = () => {
  console.log('[SLS Analysis] 刷新数据')
}
</script>

<style scoped>
.sls-analysis {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0;
}

.analysis-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.analysis-content {
  padding: 40px 0;
}

.empty-desc {
  text-align: center;
  color: #64748b;
  line-height: 2;
  margin-top: 20px;
}
</style>
