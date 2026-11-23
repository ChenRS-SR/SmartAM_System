import { computed, onUnmounted, ref, watch } from 'vue'
import { task4Api } from '../utils/task4Api'

export function useMaintenanceStatistics(deviceIds) {
  const data = ref(null)
  const error = ref('')
  let controller
  // null 表示尚未选设备；空数组表示查询全设备群。
  watch(deviceIds, async ids => {
    controller?.abort()
    data.value = null
    if (ids === null) return
    const pending = new AbortController()
    controller = pending
    try {
      const result = await task4Api('maintenance-statistics', ids.length ? {deviceIds:ids} : {}, pending.signal)
      if (!pending.signal.aborted) { data.value = result; error.value = '' }
    } catch (e) { if (e.name !== 'AbortError') error.value = e.message }
  }, {immediate:true})
  onUnmounted(() => controller?.abort())
  const statistics = computed(() => ({
    totalFaults:data.value?.faultTasks ?? '—', preventiveRepairs:data.value?.maintenanceCount ?? '—',
    rateText:data.value?.taskFaultRate == null ? '—' : (data.value.taskFaultRate * 100).toFixed(1)
  }))
  return {data, statistics, error}
}
