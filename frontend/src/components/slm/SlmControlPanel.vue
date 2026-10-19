<template>
  <div class="slm-control">
    <div class="control-panel">
      <div class="panel-header">
        <span class="panel-title">🎛️ SLM 参数监控 · 闭环反馈</span>
        <div class="header-actions">
          <el-tag v-if="partsOffline" type="warning" effect="dark" size="small">试验台离线</el-tag>
          <el-tag v-if="partsFallback" type="info" effect="dark" size="small">样例零件</el-tag>
        </div>
      </div>

      <!-- 状态 / 控制栏 -->
      <div class="control-bar">
        <span class="status-dot" :class="statusDotClass"></span>
        <span class="status-text" :class="statusTextClass">{{ statusText }}</span>
        <span class="bar-meta">层号: {{ displayLayer }}</span>
        <span class="bar-meta">任务: {{ displayJob }}</span>
        <div class="bar-actions">
          <el-button :type="ready ? 'danger' : 'success'" size="small" @click="toggleReady">
            {{ ready ? '⏹ 停止' : '▶ 准备' }}
          </el-button>
          <el-button size="small" :disabled="!ready || requestDisabled" @click="requestUpdate">
            {{ requestDisabled ? '请求中…' : '请求更新' }}
          </el-button>
        </div>
      </div>

      <!-- 试验台事件 read.json -->
      <div class="section-title">📡 试验台事件 read.json</div>
      <div class="event-grid">
        <div class="event-item" v-for="f in eventFields" :key="f.key">
          <span class="event-label">{{ f.label }}</span>
          <span class="event-value" :class="{ 'layer': f.key === 'layer' }">{{ eventValue(f.key) }}</span>
        </div>
      </div>

      <!-- 参数修改 -->
      <div class="section-title">⚙️ 参数修改</div>
      <div class="params-panel">
        <div class="parts-row">
          <el-select
            v-model="selectedPartId"
            placeholder="请选择零件..."
            size="small"
            class="parts-select"
            :disabled="!ready"
            @change="onPartSelect"
          >
            <el-option
              v-for="p in parts"
              :key="p.part_id"
              :label="`${p.part_id}: ${p.name || '?'}`"
              :value="p.part_id"
            />
          </el-select>
          <el-button size="small" :loading="partsLoading" @click="fetchParts">🔄 刷新</el-button>
          <span class="part-info" :class="partInfoClass">{{ partInfoText }}</span>
        </div>

        <div class="param-row" v-for="key in paramKeys" :key="key">
          <div class="param-name">
            {{ safeRanges[key]?.description || key }}
            <span class="param-unit">({{ safeRanges[key]?.unit || '' }})</span>
          </div>
          <div class="param-bar">
            <div class="bar-bg">
              <div class="bar-fill" :style="{ width: barRatio(key) + '%', background: barColor(key) }"></div>
            </div>
            <div class="bar-scale">
              <span>{{ safeRanges[key]?.min ?? 0 }}</span>
              <span>{{ safeRanges[key]?.max ?? 0 }}</span>
            </div>
          </div>
          <div class="param-cur">当前: {{ formatVal(currentParams[key]) }} {{ safeRanges[key]?.unit || '' }}</div>
          <el-input-number
            v-model="inputValues[key]"
            :min="safeRanges[key]?.min"
            :max="safeRanges[key]?.max"
            :step="paramDefs[key]?.step || 1"
            :precision="paramDefs[key]?.precision ?? 0"
            :controls="false"
            size="small"
            class="param-input"
          />
        </div>

        <div class="extra-row">
          <div class="extra-item">
            <span class="extra-label">铺粉量</span>
            <el-input-number v-model="powderAmount" :min="0" :step="0.01" :precision="3" :controls="false" size="small" />
            <span class="extra-unit">mm</span>
          </div>
          <div class="extra-item">
            <span class="extra-label">送粉倍率</span>
            <el-input-number v-model="powderMult" :min="0.5" :max="2.0" :step="0.1" :precision="1" :controls="false" size="small" />
            <span class="extra-unit">x</span>
          </div>
        </div>

        <div class="score-row">
          <span class="score-label">综合评分 (VED)</span>
          <div class="score-bar">
            <div class="bar-bg">
              <div class="bar-fill" :style="{ width: scoreRatio + '%', background: scoreColor }"></div>
            </div>
          </div>
          <span class="score-text" :style="{ color: scoreColor }">{{ scoreText }}</span>
        </div>
        <div class="score-suggestion">{{ scoreSuggestion }}</div>
        <div class="params-source">参数来源: {{ paramsSource }}</div>

        <div class="msg-row">
          <span class="msg-label">调整说明</span>
          <el-input v-model="message" size="small" placeholder="手动调整参数" class="msg-input" />
        </div>

        <div class="action-row">
          <el-button type="primary" size="small" :disabled="!ready || !selectedPartId" @click="sendAdjustment">
            发送调整参数
          </el-button>
          <el-button type="danger" size="small" :disabled="!ready" @click="emergencyStop">紧急停止</el-button>
          <el-button size="small" @click="resetDefaults">恢复默认</el-button>
        </div>
        <div v-if="sendStatus" class="send-status" :class="sendStatusClass">{{ sendStatus }}</div>
      </div>

      <!-- 最新反馈 feedback.json -->
      <div class="section-title">📥 最新反馈 feedback.json</div>
      <div class="feedback-panel">
        <div class="fb-action" :style="{ color: fbActionColor }">{{ fbActionText }}</div>
        <div class="fb-time">{{ fbData.result_time || '' }}</div>
        <div class="fb-line">
          <span class="fb-label">参数补偿:</span>
          <span v-for="key in compKeys" :key="key" class="fb-comp">{{ compText(key) }}</span>
        </div>
        <div class="fb-line">
          <span class="fb-label">送粉倍率:</span>
          <span :style="{ color: powderColor }">{{ powderText }}</span>
        </div>
        <div class="fb-line">
          <span class="fb-label">消息:</span>
          <span class="fb-msg">{{ fbData.message || '--' }}</span>
        </div>
        <div class="fb-json-title">feedback.json JSON:</div>
        <pre class="fb-json">{{ feedbackJson }}</pre>
      </div>

      <!-- 日志 -->
      <div class="log-panel">
        <div class="log-col">
          <div class="log-header">事件日志</div>
          <div class="log-body">
            <div v-for="(l, i) in eventLog" :key="i" class="log-line">
              <span class="log-time">[{{ l.time }}]</span>
              <span :class="'log-' + l.tag">{{ l.msg }}</span>
            </div>
          </div>
        </div>
        <div class="log-col">
          <div class="log-header">发送日志</div>
          <div class="log-body">
            <div v-for="(l, i) in sendLog" :key="i" class="log-line">
              <span class="log-time">[{{ l.time }}]</span>
              <span :class="'log-' + l.tag">{{ l.msg }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, h } from 'vue'
import axios from 'axios'
import { ElMessageBox } from 'element-plus'

const BASE = '/api/slm/control'

const paramKeys = ['fill_power', 'fill_speed', 'scan_spacing', 'powder_feed_rate']
const paramDefs = {
  fill_power: { step: 10, precision: 0 },
  fill_speed: { step: 50, precision: 0 },
  scan_spacing: { step: 0.01, precision: 2 },
  powder_feed_rate: { step: 0.5, precision: 1 },
}
const compKeys = ['fill_power', 'fill_speed', 'scan_spacing']
const eventFields = [
  { key: 'trigger', label: '触发类型' },
  { key: 'event', label: '事件名称' },
  { key: 'layer', label: '当前层号' },
  { key: 'device_id', label: '设备ID' },
  { key: 'job_name', label: '任务名称' },
  { key: 'timestamp', label: '触发时间' },
  { key: 'source', label: '来源' },
]

// ---- 状态 ----
const ready = ref(false)
const requestDisabled = ref(false)
const partsLoading = ref(false)
const partsOffline = ref(false)
const partsFallback = ref(false)

const safeRanges = ref({})
const energyWindow = ref({ min: 50, max: 120 })

const event = ref(null)
const feedback = ref(null)
const parts = ref([])
const selectedPartId = ref(null)
const partInfoText = ref('')
const partInfoClass = ref('')

const currentParams = reactive({ fill_power: 200, fill_speed: 1000, scan_spacing: 0.1, powder_feed_rate: 5.0 })
const inputValues = reactive({ fill_power: 200, fill_speed: 1000, scan_spacing: 0.1, powder_feed_rate: 5.0 })
const paramsSource = ref('默认值')

const powderAmount = ref(0.06)
const powderMult = ref(1.0)
const message = ref('手动调整参数')

const sendStatus = ref('')
const sendStatusClass = ref('')

const eventLog = ref([])
const sendLog = ref([])

let lastLayer = -1
let pollTimer = null

// ---- 计算属性 ----
const statusText = computed(() => {
  if (!ready.value) return '⏸ 未就绪'
  return event.value ? '● 监听中' : '● 等待数据...'
})
const statusTextClass = computed(() => {
  if (!ready.value) return 'idle'
  return event.value ? 'ok' : 'wait'
})
const statusDotClass = computed(() => {
  if (!ready.value) return 'dot-idle'
  return event.value ? 'dot-ok' : 'dot-wait'
})
const displayLayer = computed(() => (event.value ? event.value.layer : '--'))
const displayJob = computed(() => (event.value ? event.value.job_name : '--'))

const fbData = computed(() => (feedback.value && feedback.value.data) || {})

const fbActionText = computed(() => {
  if (!feedback.value) return '等待检测...'
  const d = fbData.value
  if (d.stop_print || d.action === 'stop') return 'STOP - 停止打印'
  if (d.action === 'continue') return 'CONTINUE - 继续打印'
  return `动作: ${d.action}`
})
const fbActionColor = computed(() => {
  if (!feedback.value) return 'var(--am-warn)'
  const d = fbData.value
  if (d.stop_print || d.action === 'stop') return 'var(--am-danger)'
  if (d.action === 'continue') return 'var(--am-ok)'
  return 'var(--am-warn)'
})
const powderText = computed(() => `${fbData.value.powder_multiplier ?? 1.0}x`)
const powderColor = computed(() => {
  const pm = fbData.value.powder_multiplier ?? 1.0
  if (pm !== 1.0) return pm > 1.15 ? 'var(--am-warn)' : 'var(--am-ok)'
  return 'var(--am-ok)'
})
const feedbackJson = computed(() => (feedback.value ? JSON.stringify(feedback.value, null, 2) : ''))

// ---- VED 评分（currentParams + 铺粉量） ----
const ved = computed(() => {
  const p = Number(currentParams.fill_power)
  const s = Number(currentParams.fill_speed)
  const h = Number(currentParams.scan_spacing)
  const t = Number(powderAmount.value)
  if (!(p && s && h && t)) return null
  const denom = s * h * t
  if (denom <= 0) return null
  return p / denom
})
const scoreStatus = computed(() => {
  if (ved.value == null) return 'unknown'
  if (ved.value < energyWindow.value.min) return 'low'
  if (ved.value > energyWindow.value.max) return 'high'
  return 'ok'
})
const scoreText = computed(() => {
  switch (scoreStatus.value) {
    case 'ok': return `✓ 适中 (${ved.value.toFixed(1)} J/mm³)`
    case 'low': return `↓ 过低 (${ved.value.toFixed(1)} J/mm³)`
    case 'high': return `↑ 过高 (${ved.value.toFixed(1)} J/mm³)`
    default: return '--'
  }
})
const scoreColor = computed(() => {
  switch (scoreStatus.value) {
    case 'ok': return 'var(--am-ok)'
    case 'low': return 'var(--am-danger)'
    case 'high': return 'var(--am-warn)'
    default: return 'var(--am-text-3)'
  }
})
const scoreSuggestion = computed(() => {
  if (ved.value == null) return '参数不完整，无法计算体能量密度'
  if (ved.value < energyWindow.value.min) return '体能量密度偏低，建议提高功率或降低速度，避免未熔合缺陷'
  if (ved.value > energyWindow.value.max) return '体能量密度偏高，建议降低功率或提高速度，避免过熔/气孔'
  return '体能量密度在工艺窗口内，无需调整'
})
const scoreRatio = computed(() => {
  const barMax = energyWindow.value.max * 1.5
  if (ved.value == null || barMax <= 0) return 0
  return Math.max(0, Math.min(100, (ved.value / barMax) * 100))
})

// ---- 工具 ----
function now() { return new Date().toTimeString().slice(0, 8) }
function addEventLog(msg, tag = 'info') { eventLog.value.push({ time: now(), msg, tag }) }
function addSendLog(msg, tag = 'info') { sendLog.value.push({ time: now(), msg, tag }) }
function formatVal(v) { return v == null || v === '' ? '--' : v }
function eventValue(key) { return event.value ? (event.value[key] ?? '--') : '--' }
function compText(key) {
  const c = fbData.value.compensation
  return c && key in c ? `${key}: ${c[key]}` : ''
}

function setSendStatus(text, cls) {
  sendStatus.value = text
  sendStatusClass.value = cls
  if (text) {
    setTimeout(() => {
      if (sendStatus.value === text) { sendStatus.value = ''; sendStatusClass.value = '' }
    }, 5000)
  }
}

function barRatio(key) {
  const safe = safeRanges.value[key]
  if (!safe) return 0
  const val = Number(currentParams[key] ?? 0)
  if (safe.max <= safe.min) return 0
  return Math.max(0, Math.min(100, ((val - safe.min) / (safe.max - safe.min)) * 100))
}
function barColor(key) {
  const ratio = barRatio(key) / 100
  if (ratio < 0.1 || ratio > 0.9) return 'var(--am-danger)'
  if (ratio < 0.25 || ratio > 0.75) return 'var(--am-warn)'
  return 'var(--am-ok)'
}

// ---- 就绪 / 停止 ----
function toggleReady() {
  if (ready.value) stopMonitoring()
  else startMonitoring()
}
function startMonitoring() {
  ready.value = true
  lastLayer = -1
  addEventLog('开始监听 read.json...', 'ok')
  fetchParts()
  doRefresh()
  startPolling()
}
function stopMonitoring() {
  ready.value = false
  stopPolling()
  event.value = null
  lastLayer = -1
  addEventLog('已停止监听', 'warn')
}

// ---- 轮询 ----
function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => { if (ready.value) doRefresh() }, 1000)
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}
async function doRefresh() {
  await Promise.all([refreshEvent(), refreshFeedback()])
}

async function refreshEvent() {
  try {
    const { data } = await axios.get(`${BASE}/event`)
    event.value = data
    if (data) {
      if (data.trigger === 'pre_print' && data.event === 'parameter_sync' && data.parameters) {
        for (const [k, v] of Object.entries(data.parameters)) {
          if (k in currentParams) { currentParams[k] = v; inputValues[k] = v }
        }
        paramsSource.value = `试验台同步 (layer=${data.layer})`
        addEventLog(
          `参数同步: P=${data.parameters.fill_power ?? '?'}W v=${data.parameters.fill_speed ?? '?'}mm/s h=${data.parameters.scan_spacing ?? '?'}mm`,
          'ok'
        )
      }
      if (data.layer !== lastLayer && lastLayer !== -1) {
        addEventLog(`read.json 事件: ${data.trigger}/${data.event} layer=${data.layer}`, 'ok')
      }
      lastLayer = data.layer
    }
  } catch (e) { /* 读取失败保持原显示 */ }
}

async function refreshFeedback() {
  try {
    const { data } = await axios.get(`${BASE}/feedback`)
    feedback.value = data
  } catch (e) { /* 忽略 */ }
}

// ---- 零件 ----
async function fetchParts() {
  partsLoading.value = true
  try {
    const { data } = await axios.get(`${BASE}/parts`)
    parts.value = data.parts || []
    partsOffline.value = !!data.offline
    partsFallback.value = !!data.fallback
    if (parts.value.length) {
      partInfoText.value = `共 ${parts.value.length} 个零件可用`
      partInfoClass.value = 'ok'
      addEventLog(`零件列表已加载: ${parts.value.length} 个零件`, 'ok')
      addSendLog(`零件列表已加载: ${parts.value.length} 个零件`, 'ok')
    } else {
      partInfoText.value = '未获取到零件列表'
      partInfoClass.value = 'warn'
      addEventLog('未能获取零件列表，请检查试验台连接', 'warn')
      addSendLog('未能获取零件列表', 'warn')
    }
  } catch (e) {
    partInfoText.value = '未获取到零件列表'
    partInfoClass.value = 'warn'
  } finally {
    partsLoading.value = false
  }
}

async function onPartSelect(partId) {
  if (!partId) return
  try {
    const { data } = await axios.post(`${BASE}/parts/select`, { part_id: partId })
    if (data.ok && data.part) {
      const p = data.part
      partInfoText.value = `已选择: ${p.name || '?'}`
      partInfoClass.value = 'ok'
      if (p.fill_power != null) {
        currentParams.fill_power = p.fill_power
        currentParams.fill_speed = p.fill_speed
        currentParams.scan_spacing = p.scan_spacing
        inputValues.fill_power = p.fill_power
        inputValues.fill_speed = p.fill_speed
        inputValues.scan_spacing = p.scan_spacing
        paramsSource.value = `试验台读取 (part_id=${partId})`
        addEventLog(`选中零件: part_id=${partId}, name=${p.name}`, 'ok')
        addSendLog(`选中零件: [${partId}] ${p.name}`, 'ok')
        addSendLog(`读取参数 [${partId}]: P=${p.fill_power}W v=${p.fill_speed}mm/s h=${p.scan_spacing}mm`, 'ok')
        setSendStatus('就绪，可发送参数', 'ok')
      }
    } else {
      partInfoText.value = '无效零件'
      partInfoClass.value = 'error'
      setSendStatus('无效零件', 'error')
    }
  } catch (e) {
    partInfoText.value = '选择失败'
    partInfoClass.value = 'error'
  }
}

// ---- 请求更新 ----
async function requestUpdate() {
  if (!ready.value || requestDisabled.value) return
  requestDisabled.value = true
  try {
    const { data } = await axios.post(`${BASE}/request`, { action: 'request_status' })
    if (data.ok) {
      addEventLog('已向试验台发送状态请求 (request.json)', 'ok')
      setSendStatus('请求已发送', 'accent')
    } else {
      addEventLog('发送请求失败', 'error')
      setSendStatus('请求发送失败', 'error')
    }
  } catch (e) {
    setSendStatus('请求发送失败', 'error')
  }
  setTimeout(() => { requestDisabled.value = false }, 2000)
}

// ---- 发送调整参数 ----
async function sendAdjustment() {
  if (!selectedPartId.value) { setSendStatus('请先选择 SLC 零件', 'warn'); return }

  const p = {}
  for (const key of paramKeys) {
    const val = Number(inputValues[key])
    const safe = safeRanges.value[key]
    if (!safe || !(safe.min <= val && val <= safe.max)) {
      addEventLog(`参数越界: ${key}=${val} 不在 [${safe?.min}, ${safe?.max}] 范围内`, 'error')
      setSendStatus(`参数越界: ${key}`, 'error')
      return
    }
    p[key] = val
  }
  const amount = Number(powderAmount.value)
  if (!(amount > 0)) { setSendStatus('铺粉量必须大于 0', 'error'); return }
  const mult = Number(powderMult.value)
  if (!(0.5 <= mult && mult <= 2.0)) { setSendStatus('送粉倍率应在 0.5~2.0', 'error'); return }

  const msg = message.value || '手动调整参数'
  const partName = parts.value.find(x => x.part_id === selectedPartId.value)?.name || '?'

  const lines = [
    `零件: [${selectedPartId.value}] ${partName}`,
    `填充功率: ${p.fill_power} W`,
    `填充速度: ${p.fill_speed} mm/s`,
    `扫描间距: ${p.scan_spacing} mm`,
    `送粉速率: ${p.powder_feed_rate} g/min`,
    `铺粉量: ${amount} mm`,
    `送粉倍率: ${mult}x`,
    `说明: ${msg}`,
  ]
  try {
    await ElMessageBox.confirm(h('div', lines.map(t => h('div', { style: 'line-height:1.8' }, t))), '确认发送参数', {
      type: 'warning',
      confirmButtonText: '发送',
      cancelButtonText: '取消',
    })
  } catch (e) {
    addEventLog('用户取消发送', 'info')
    addSendLog('用户取消发送', 'info')
    return
  }

  const body = {
    part_id: selectedPartId.value,
    fill_power: p.fill_power,
    fill_speed: p.fill_speed,
    scan_spacing: p.scan_spacing,
    powder_feed_rate: p.powder_feed_rate,
    powder_amount: amount,
    powder_multiplier: mult,
    message: msg,
  }
  setSendStatus('正在发送...', 'accent')
  try {
    const { data } = await axios.post(`${BASE}/send`, body)

    if (data.steps?.fill_params_api) addSendLog(`填充参数(API) ✓ P=${p.fill_power}W v=${p.fill_speed}mm/s h=${p.scan_spacing}mm`, 'ok')
    else addSendLog('填充参数(API) ✗ 发送失败', 'error')
    if (data.steps?.powder_amount_api) addSendLog(`铺粉量(API) ✓ amount=${amount}mm`, 'ok')
    else addSendLog('铺粉量(API) ✗ 发送失败', 'error')
    if (data.steps?.feedback_file) addSendLog(`feedback.json ✓ 送粉速率=${p.powder_feed_rate}g/min 倍率=${mult}x`, 'ok')
    else addSendLog('feedback.json ✗ 写入失败', 'error')

    if (data.ok) {
      for (const key of paramKeys) currentParams[key] = p[key]
      paramsSource.value = `API+文件 (part_id=${body.part_id})`
      addEventLog(
        `发送成功: part=${body.part_id}:${partName} P=${p.fill_power}W v=${p.fill_speed}mm/s h=${p.scan_spacing}mm feed=${p.powder_feed_rate}g/min mult=${mult}x`,
        'ok'
      )
      addSendLog(`✓ 发送成功 [${body.part_id}:${partName}]`, 'ok')
      setSendStatus('参数已发送', 'ok')
    } else {
      addEventLog(`部分发送失败: ${data.errors?.join(', ')}`, 'error')
      addSendLog(`✗ 发送失败: ${data.errors?.join(', ')}`, 'error')
      setSendStatus(`失败: ${data.errors?.join(', ')}`, 'error')
    }
    refreshFeedback()
  } catch (e) {
    addSendLog('✗ 发送请求失败', 'error')
    setSendStatus('发送失败', 'error')
  }
}

// ---- 紧急停止 ----
async function emergencyStop() {
  try {
    await ElMessageBox.confirm('确认写入紧急停止指令到 feedback.json？', '紧急停止', {
      type: 'error',
      confirmButtonText: '确认停止',
      cancelButtonText: '取消',
    })
  } catch (e) {
    return
  }
  try {
    const { data } = await axios.post(`${BASE}/stop`)
    if (data.ok) {
      addEventLog(`紧急停止已发送 layer=${data.layer} (feedback.json)`, 'warn')
      addSendLog(`✗ 紧急停止 layer=${data.layer} | 已写入 feedback.json`, 'warn')
      setSendStatus('紧急停止已写入 feedback.json', 'error')
      refreshFeedback()
    } else {
      addSendLog('✗ 紧急停止发送失败', 'error')
      setSendStatus('发送失败', 'error')
    }
  } catch (e) {
    addSendLog('✗ 紧急停止发送失败', 'error')
    setSendStatus('发送失败', 'error')
  }
}

// ---- 恢复默认 ----
function resetDefaults() {
  for (const key of paramKeys) {
    const d = safeRanges.value[key]?.default ?? 0
    inputValues[key] = d
    currentParams[key] = d
  }
  powderAmount.value = 0.06
  powderMult.value = 1.0
  message.value = '手动调整参数'
  paramsSource.value = '默认值'
  addEventLog('参数输入已恢复默认值（未发送）', 'info')
  addSendLog('参数已恢复默认值（未发送）', 'info')
  setSendStatus('已恢复默认值，点击发送生效', 'accent')
}

// ---- 生命周期 ----
onMounted(async () => {
  try {
    const { data } = await axios.get(`${BASE}/config`)
    safeRanges.value = data.safe_ranges || {}
    energyWindow.value = data.energy_density_window || { min: 50, max: 120 }
  } catch (e) { /* 使用内置默认值 */ }
})

onUnmounted(stopPolling)
</script>

<style scoped>
.slm-control { display: flex; flex-direction: column; gap: 16px; }
.control-panel { background: var(--am-card-bg); border: 1px solid var(--am-card-border); border-radius: 8px; overflow: hidden; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: var(--am-card-bg-2); border-bottom: 1px solid var(--am-card-border-2); }
.panel-title { font-size: 14px; font-weight: 600; color: var(--am-text); }
.header-actions { display: flex; align-items: center; gap: 8px; }

.control-bar { display: flex; align-items: center; gap: 14px; padding: 12px 16px; border-bottom: 1px solid var(--am-card-border-2); }
.status-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--am-text-3); flex-shrink: 0; }
.status-dot.dot-ok { background: var(--am-ok); }
.status-dot.dot-wait { background: var(--am-warn); animation: pulse 1.5s infinite; }
.status-dot.dot-idle { background: var(--am-text-3); }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
.status-text { font-size: 13px; font-weight: 600; }
.status-text.ok { color: var(--am-ok); }
.status-text.wait { color: var(--am-warn); }
.status-text.idle { color: var(--am-warn); }
.bar-meta { font-size: 12px; color: var(--am-text-2); }
.bar-actions { margin-left: auto; display: flex; gap: 8px; }

.section-title { font-size: 13px; font-weight: 600; color: var(--am-text-2); padding: 12px 16px 8px; }

.event-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 0 16px 12px; }
.event-item { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px; background: var(--am-card-bg-2); border: 1px solid var(--am-card-border-2); border-radius: 6px; }
.event-label { font-size: 11px; color: var(--am-text-3); }
.event-value { font-size: 13px; font-weight: 600; color: var(--am-text); word-break: break-all; }
.event-value.layer { color: var(--am-accent); }

.params-panel { padding: 0 16px 14px; display: flex; flex-direction: column; gap: 10px; }
.parts-row { display: flex; align-items: center; gap: 10px; }
.parts-select { width: 260px; }
.part-info { font-size: 12px; color: var(--am-text-2); }
.part-info.ok { color: var(--am-ok); }
.part-info.warn { color: var(--am-warn); }
.part-info.error { color: var(--am-danger); }

.param-row { display: grid; grid-template-columns: 120px 1fr 120px 150px; gap: 10px; align-items: center; }
.param-name { font-size: 12px; color: var(--am-text); }
.param-unit { font-size: 11px; color: var(--am-text-3); }
.param-bar { display: flex; flex-direction: column; gap: 2px; }
.bar-bg { height: 8px; background: var(--am-card-bg-2); border: 1px solid var(--am-card-border-2); border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s, background 0.3s; }
.bar-scale { display: flex; justify-content: space-between; font-size: 10px; color: var(--am-text-3); }
.param-cur { font-size: 12px; color: var(--am-text-2); }
.param-input { width: 150px; }

.extra-row { display: flex; gap: 24px; }
.extra-item { display: flex; align-items: center; gap: 8px; }
.extra-label { font-size: 12px; color: var(--am-text); }
.extra-unit { font-size: 12px; color: var(--am-text-3); }

.score-row { display: grid; grid-template-columns: 120px 1fr 180px; gap: 10px; align-items: center; }
.score-label { font-size: 12px; color: var(--am-text); }
.score-bar .bar-bg { height: 10px; }
.score-text { font-size: 13px; font-weight: 600; text-align: right; }
.score-suggestion { font-size: 12px; color: var(--am-text-2); }
.params-source { font-size: 12px; color: var(--am-text-3); }

.msg-row { display: flex; align-items: center; gap: 10px; }
.msg-label { font-size: 12px; color: var(--am-text); flex-shrink: 0; }
.msg-input { flex: 1; }

.action-row { display: flex; gap: 10px; }
.send-status { font-size: 12px; font-weight: 600; }
.send-status.ok { color: var(--am-ok); }
.send-status.warn { color: var(--am-warn); }
.send-status.error { color: var(--am-danger); }
.send-status.accent { color: var(--am-accent); }

.feedback-panel { padding: 0 16px 14px; display: flex; flex-direction: column; gap: 8px; }
.fb-action { font-size: 15px; font-weight: 700; }
.fb-time { font-size: 11px; color: var(--am-text-3); text-align: right; }
.fb-line { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--am-text); }
.fb-label { color: var(--am-text-2); }
.fb-comp { color: var(--am-warn); margin-right: 14px; }
.fb-msg { color: var(--am-text-2); }
.fb-json-title { font-size: 11px; color: var(--am-text-3); }
.fb-json { margin: 0; padding: 10px; background: var(--am-card-bg-2); border: 1px solid var(--am-card-border-2); border-radius: 6px; font-family: Consolas, Monaco, monospace; font-size: 11px; color: var(--am-text-2); max-height: 220px; overflow: auto; white-space: pre-wrap; }

.log-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 0 16px 16px; }
.log-col { border: 1px solid var(--am-card-border-2); border-radius: 6px; overflow: hidden; }
.log-header { padding: 6px 12px; font-size: 12px; font-weight: 600; color: var(--am-text); background: var(--am-card-bg-2); border-bottom: 1px solid var(--am-card-border-2); }
.log-body { height: 120px; overflow-y: auto; padding: 6px 12px; background: var(--am-card-bg); font-family: Consolas, Monaco, monospace; font-size: 11px; line-height: 1.7; }
.log-line { color: var(--am-text-2); }
.log-time { color: var(--am-text-3); }
.log-info { color: var(--am-text-2); }
.log-warn { color: var(--am-warn); }
.log-error { color: var(--am-danger); }
.log-ok { color: var(--am-ok); }

@media (max-width: 1200px) { .event-grid { grid-template-columns: repeat(2, 1fr); } .param-row, .score-row { grid-template-columns: 1fr; } }
@media (max-width: 768px) { .event-grid { grid-template-columns: 1fr; } .log-panel { grid-template-columns: 1fr; } }
</style>
