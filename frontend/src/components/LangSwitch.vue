<template>
  <div class="lang-switch">
    <el-dropdown trigger="click" @command="handleCommand">
      <el-button text class="lang-btn">
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

const { locale } = useI18n()

const languages = [
  { value: 'zh-CN', label: '简体中文' },
  { value: 'en-US', label: 'English' }
]

const currentLang = computed(() => locale.value)
const currentLangLabel = computed(() => {
  const lang = languages.find(l => l.value === locale.value)
  return lang?.label || '简体中文'
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
  color: var(--am-accent);
  background: color-mix(in srgb, var(--am-accent) 13%, transparent);
}

</style>
