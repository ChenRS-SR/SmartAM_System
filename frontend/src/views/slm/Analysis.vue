<template>
  <div class="slm-analysis">
    <h2 class="page-title">SLM 数据分析</h2>
    
    <el-card class="placeholder-card" shadow="never">
      <div class="placeholder-content">
        <el-icon size="64" color="#00ff88"><DataLine /></el-icon>
        <h3>数据分析模块</h3>
        <p>SLM 数据分析功能开发中...</p>
        <p class="sub-text">将提供设备历史数据分析、健康趋势预测等功能</p>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.slm-analysis {
  padding: 0;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0 0 20px 0;
}

.placeholder-card {
  border: none;
  background: rgba(15, 23, 42, 0.6);
}

.placeholder-content {
  min-height: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #94a3b8;
}

.placeholder-content h3 {
  margin: 16px 0 8px 0;
  color: #e2e8f0;
}

.placeholder-content p {
  margin: 0;
}

.sub-text {
  font-size: 14px;
  color: #64748b;
  margin-top: 8px !important;
}
</style>
