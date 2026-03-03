<template>
  <div class="lang-switch">
    <el-dropdown trigger="click" @command="handleCommand">
      <el-button text class="lang-btn">
        <el-icon size="20"><Operation /></el-icon>
        <span class="lang-text">{{ currentLangLabel }}</span>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item 
            v-for="lang in languages" 
            :key="lang.value"
            :command="lang.value"
            :class="{ active: currentLang === lang.value }"
          >
            <span class="lang-flag">{{ lang.flag }}</span>
            <span>{{ lang.label }}</span>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLocale } from '../i18n'
import { Operation } from '@element-plus/icons-vue'

const { locale } = useI18n()

const languages = [
  { value: 'zh-CN', label: '简体中文', flag: '🇨🇳' },
  { value: 'en-US', label: 'English', flag: '🇺🇸' }
]

const currentLang = computed(() => locale.value)
const currentLangLabel = computed(() => {
  const lang = languages.find(l => l.value === locale.value)
  return lang?.flag || '🌐'
})

const handleCommand = (command) => {
  setLocale(command)
}
</script>

<style scoped>
.lang-switch {
  display: inline-flex;
}

.lang-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.lang-text {
  font-size: 14px;
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 140px;
}

:deep(.el-dropdown-menu__item.active) {
  color: #00d4ff;
  background: rgba(0, 212, 255, 0.1);
}

.lang-flag {
  font-size: 16px;
}
</style>
