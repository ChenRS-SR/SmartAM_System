<template>
  <div class="theme-toggle">
    <el-dropdown trigger="click" @command="handleCommand">
      <el-button text class="theme-btn" aria-label="切换主题">
        主题
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="light" :class="{ active: themeStore.themeMode === 'light' }">
            <span>浅色主题</span>
          </el-dropdown-item>
          <el-dropdown-item command="dark" :class="{ active: themeStore.themeMode === 'dark' }">
            <span>深色主题</span>
          </el-dropdown-item>
          <el-dropdown-item command="auto" :class="{ active: themeStore.themeMode === 'auto' }">
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
  color: var(--am-accent);

}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 120px;
}

:deep(.el-dropdown-menu__item.active) {
  color: var(--am-accent);
  background: color-mix(in srgb, var(--am-accent) 13%, transparent);
}
</style>
