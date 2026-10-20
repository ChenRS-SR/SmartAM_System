import { reactive } from 'vue'

// 仅保存本次会话的成功分析摘要；不保存图像，也不将分析结果自动转换为控制指令。
export const qualityContext = reactive({})

export function recordQualityResult(kind, result) {
  const id = result.device.id
  const previous = qualityContext[id]
  const sameLayer = previous?.task.id === result.task.id && previous?.layer === result.layer
  const entry = sameLayer ? previous : {
    device: result.device, task: result.task, layer: result.layer,
    recognition: null, trace: null
  }
  if (kind === 'recognition') {
    entry.recognition = { label: result.label, probability: result.prob.def }
    // 重新识别可能改变判定，旧溯源结论必须重新核对。
    entry.trace = null
  }
  if (kind === 'trace') {
    entry.trace = { conclusion: result.conclusion, actions: [...result.actions] }
  }
  qualityContext[id] = entry
}
