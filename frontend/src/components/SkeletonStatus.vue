<template>
  <div class="skeleton-status">
    <div class="skeleton-icon"></div>
    <div class="skeleton-content">
      <div class="skeleton-label"></div>
      <div class="skeleton-value"></div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-status {
  background: var(--am-card-bg);
  border: 1px solid color-mix(in srgb, var(--am-accent) 10%, transparent);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.skeleton-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 25%,
    color-mix(in srgb, var(--am-accent) 22%, transparent) 50%,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-label {
  width: 60px;
  height: 13px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 25%,
    color-mix(in srgb, var(--am-accent) 22%, transparent) 50%,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-value {
  width: 80px;
  height: 24px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 25%,
    color-mix(in srgb, var(--am-accent) 22%, transparent) 50%,
    color-mix(in srgb, var(--am-accent) 13%, transparent) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
