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
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.1);
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
    rgba(0, 212, 255, 0.1) 25%,
    rgba(0, 212, 255, 0.2) 50%,
    rgba(0, 212, 255, 0.1) 75%
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
    rgba(0, 212, 255, 0.1) 25%,
    rgba(0, 212, 255, 0.2) 50%,
    rgba(0, 212, 255, 0.1) 75%
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
    rgba(0, 212, 255, 0.1) 25%,
    rgba(0, 212, 255, 0.2) 50%,
    rgba(0, 212, 255, 0.1) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
