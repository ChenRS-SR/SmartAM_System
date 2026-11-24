// 缺结果时保留模块结构，所有未知量均为空；这里只生成展示状态，不写回快照或导出接口。
export function pendingAnalysis(frame, kind) {
  if (!frame) return null
  const context = { device: frame.access.device, task: frame.access.task, layer: frame.layer, time: frame.time, available: false }
  const source = frame.access.images.before
  if (kind === 'recognition') return {
    ...context, model: { name: '等待结果' }, params: { threshold: null, modalities: [] },
    image: { url: source?.url, w: source?.w || 224, h: source?.h || 224, box: null },
    prob: { def: null, vis: null, tq: null, proc: null, dev: null }, label: '等待结果',
    weights: { vis: null, tq: null }, singles: [], records: [], torque: frame.access.torque,
  }
  const factor = name => ({ name, upper: null, total: null, prob: null,
    zones: [{ key: 'part', name: '零件区', v: null, over: null }, { key: 'powder', name: '粉床区', v: null, over: null }] })
  return { ...context, mode: 'dual', params: { bandPx: null }, refLayer: null, refMode: null,
    image: { url: source?.url, width: source?.w || 224, height: source?.h || 224, content: [0, 0, 1, 1] },
    partContours: [], bandContours: [], factors: { proc: factor('工艺问题'), dev: factor('设备问题') },
    conclusion: frame.tracePending || '等待诊断结果', actions: [], records: [], curve: { layers: [], upper: { proc: null, dev: null } },
  }
}
