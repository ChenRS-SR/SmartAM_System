import { inject, onBeforeUnmount, ref } from 'vue'

// 包装接口调用：记录忙碌状态，出错时交给外壳统一提示
export function useCall() {
  const report = inject('formingError', (e) => console.error(e))
  const busy = ref(false)
  const call = async (fn) => {
    busy.value = true
    try { return await fn() } catch (e) { report(e); return null } finally { busy.value = false }
  }
  return { busy, call, report }
}

// 逐层运行：从给定层之后逐层调用 step(layer)，step 返回 false 时停止
export function useStepper(interval = 1200) {
  const running = ref(false)
  let timer = null
  const stop = () => { running.value = false; clearTimeout(timer) }
  const start = (layers, from, step) => {
    stop()
    let i = layers.indexOf(from)
    running.value = true
    const tick = async () => {
      if (!running.value) return
      i += 1
      if (i >= layers.length) { stop(); return }
      const ok = await step(layers[i])
      if (ok === false) { stop(); return }
      timer = setTimeout(tick, interval)
    }
    tick()
  }
  onBeforeUnmount(stop)
  return { running, start, stop }
}

export const fmtPct = (p, n = 2) => (p == null ? '—' : (p * 100).toFixed(n) + '%')
