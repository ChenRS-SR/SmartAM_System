<template>
  <div class="theme-toggle">
    <el-dropdown trigger="click" @command="handleCommand">
      <el-button text class="theme-btn">
        <el-icon size="20">
          <Sunny v-if="themeStore.isLight" />
          <Moon v-else />
        </el-icon>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="light" :class="{ active: themeStore.themeMode === 'light' }">
            <el-icon><Sunny /></el-icon>
            <span>浅色主题</span>
          </el-dropdown-item>
          <el-dropdown-item command="dark" :class="{ active: themeStore.themeMode === 'dark' }">
            <el-icon><Moon /></el-icon>
            <span>深色主题</span>
          </el-dropdown-item>
          <el-dropdown-item command="auto" :class="{ active: themeStore.themeMode === 'auto' }">
            <el-icon><Monitor /></el-icon>
            <span>跟随系统</span>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { useThemeStore } from '../stores/theme'

const themeStore = useThemeStore()

const handleCommand = (command) => {
  themeStore.setTheme(command)
}
</script>

<style scoped>
.theme-toggle {
  display: inline-flex;
}

.theme-btn {
  color: var(--text-secondary);
  transition: all 0.3s;
}

.theme-btn:hover {
  color: #00d4ff;
  transform: rotate(15deg);
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
}

:deep(.el-dropdown-menu__item.active) {
  color: #00d4ff;
  background: rgba(0, 212, 255, 0.1);
}
</style>
