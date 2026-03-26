<template>
  <div class="login-page">
    <div class="login-box">
      <div class="login-header">
        <el-icon size="48" color="#00d4ff"><Cpu /></el-icon>
        <h1>SmartAM System</h1>
        <p>智能增材制造监控系统</p>
      </div>
      
      <el-form :model="form" class="login-form">
        <el-form-item>
          <el-input 
            v-model="form.username" 
            placeholder="用户名"
            size="large"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="密码"
            size="large"
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button 
            type="primary" 
            size="large" 
            @click="handleLogin"
            :loading="loading"
            style="width: 100%"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <p>默认用户名: admin</p>
        <p>默认密码: admin</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { setToken } from '../router/index.js'

const router = useRouter()

const form = ref({
  username: '',
  password: ''
})

const loading = ref(false)

const handleLogin = () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  
  loading.value = true
  
  // 模拟登录验证
  setTimeout(() => {
    if (form.value.username === 'admin' && form.value.password === 'admin') {
      ElMessage.success('登录成功')
      setToken('demo-token')
      router.push('/')
    } else {
      ElMessage.error('用户名或密码错误')
    }
    loading.value = false
  }, 500)
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
}

.login-box {
  width: 400px;
  padding: 40px;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 16px;
  backdrop-filter: blur(10px);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 28px;
  color: #00d4ff;
  margin: 16px 0 8px;
  background: linear-gradient(90deg, #00d4ff, #00ff88);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.login-header p {
  color: #a0aec0;
  font-size: 14px;
}

.login-form :deep(.el-input__wrapper) {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 212, 255, 0.2);
  box-shadow: none;
}

.login-form :deep(.el-input__inner) {
  color: #e2e8f0;
}

.login-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 212, 255, 0.2);
  text-align: center;
}

.login-footer p {
  color: #64748b;
  font-size: 12px;
  margin: 4px 0;
}
</style>
