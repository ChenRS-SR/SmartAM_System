<template>
  <div class="device-select">
    <div class="header-section">
      <el-icon size="48" class="logo-icon"><Cpu /></el-icon>
      <h1 class="title">SmartAM</h1>
      <p class="subtitle">智能增材制造监控系统</p>
    </div>
    
    <div class="device-cards">
      <!-- FDM -->
      <div class="device-card" @click="selectDevice('fdm')">
        <div class="card-icon fdm">
          <el-icon size="48"><Printer /></el-icon>
        </div>
        <h2 class="card-title">FDM 熔融沉积成型</h2>
        <p class="card-desc">热塑性材料逐层堆积成型技术</p>
        <div class="card-features">
          <span class="feature-tag">温度监控</span>
          <span class="feature-tag">流量检测</span>
          <span class="feature-tag">缺陷预警</span>
        </div>
        <el-button type="primary" size="large" class="enter-btn">
          进入系统
          <el-icon class="btn-icon"><ArrowRight /></el-icon>
        </el-button>
      </div>
      
      <!-- SLS -->
      <div class="device-card" @click="selectDevice('sls')">
        <div class="card-icon sls">
          <el-icon size="48"><CopyDocument /></el-icon>
        </div>
        <h2 class="card-title">SLS 选择性激光烧结</h2>
        <p class="card-desc">高分子粉末激光烧结成型技术</p>
        <div class="card-features">
          <span class="feature-tag">振动监测</span>
          <span class="feature-tag">扑粉检测</span>
          <span class="feature-tag">双视觉</span>
        </div>
        <el-button type="warning" size="large" class="enter-btn">
          进入系统
          <el-icon class="btn-icon"><ArrowRight /></el-icon>
        </el-button>
      </div>
      
      <!-- SLM -->
      <div class="device-card" @click="selectDevice('slm')">
        <div class="card-icon slm">
          <el-icon size="48"><Lightning /></el-icon>
        </div>
        <h2 class="card-title">SLM 选择性激光熔化</h2>
        <p class="card-desc">金属粉末激光熔化成型技术</p>
        <div class="card-features">
          <span class="feature-tag">设备健康</span>
          <span class="feature-tag">状态监控</span>
          <span class="feature-tag">健康管理</span>
        </div>
        <el-button type="success" size="large" class="enter-btn">
          进入系统
          <el-icon class="btn-icon"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
    
    <div class="footer">
      <p>© 2024 SmartAM System. All rights reserved.</p>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const selectDevice = (type) => {
  localStorage.setItem('deviceType', type)
  router.push(`/${type}/dashboard`)
}
</script>

<style scoped>
.device-select {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  padding: 40px 20px;
}

.header-section {
  text-align: center;
  margin-bottom: 60px;
}

.logo-icon {
  color: #00d4ff;
  margin-bottom: 16px;
}

.title {
  font-size: 42px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 12px 0;
}

.subtitle {
  font-size: 18px;
  color: #94a3b8;
  margin: 0;
}

.device-cards {
  display: flex;
  gap: 40px;
  flex-wrap: wrap;
  justify-content: center;
  max-width: 1200px;
  width: 100%;
}

.device-card {
  flex: 1;
  min-width: 320px;
  max-width: 420px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 16px;
  padding: 40px 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.device-card:hover {
  transform: translateY(-8px);
  border-color: rgba(0, 212, 255, 0.5);
  box-shadow: 0 20px 40px rgba(0, 212, 255, 0.15);
}

.card-icon {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  color: #fff;
}

.card-icon.fdm {
  background: linear-gradient(135deg, #00d4ff, #0099cc);
  box-shadow: 0 8px 24px rgba(0, 212, 255, 0.3);
}

.card-icon.slm {
  background: linear-gradient(135deg, #00ff88, #00cc66);
  box-shadow: 0 8px 24px rgba(0, 255, 136, 0.3);
}

.card-icon.sls {
  background: linear-gradient(135deg, #ff9500, #ff5500);
  box-shadow: 0 8px 24px rgba(255, 149, 0, 0.3);
}

.device-card:nth-child(3) .feature-tag {
  background: rgba(0, 255, 136, 0.1);
  border-color: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.card-title {
  font-size: 24px;
  font-weight: 600;
  color: #e2e8f0;
  margin: 0 0 12px 0;
}

.card-desc {
  font-size: 14px;
  color: #94a3b8;
  margin: 0 0 20px 0;
  line-height: 1.6;
}

.card-features {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  margin-bottom: 28px;
}

.feature-tag {
  padding: 6px 14px;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 20px;
  font-size: 12px;
  color: #00d4ff;
}

.device-card:nth-child(2) .feature-tag {
  background: rgba(0, 255, 136, 0.1);
  border-color: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.enter-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
}

.btn-icon {
  margin-left: 8px;
}

.footer {
  margin-top: 60px;
  color: #64748b;
  font-size: 14px;
}

@media (max-width: 768px) {
  .title {
    font-size: 32px;
  }
  
  .device-card {
    min-width: 280px;
    padding: 32px 24px;
  }
}
</style>
