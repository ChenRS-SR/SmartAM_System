<template>
  <div class="slm-control">
    <h2 class="page-title">SLM 系统控制</h2>
    
    <el-card class="placeholder-card" shadow="never">
      <div class="placeholder-content">
        <el-icon size="64" color="#00d4ff"><SetUp /></el-icon>
        <h3>系统控制模块</h3>
        <p>SLM 系统控制功能开发中...</p>
        <p class="sub-text">将提供设备控制、参数设置等功能</p>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.slm-control {
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
