<template>
  <section class="missing-page">
    <span>404</span><h1>页面未找到</h1>
    <p>此地址不存在，请返回工艺工作区选择设备。</p>
    <router-link to="/">返回工艺工作区</router-link>
  </section>
</template>
<style scoped>
.missing-page { min-height: 100%; display: grid; place-content: center; gap: 16px; padding: 24px; text-align: center; }
.missing-page span { color: var(--am-text-3); font-size: 48px; }
h1,p { margin: 0; } p { color: var(--am-text-2); } a { color: var(--am-accent); }
</style>
