<template>
  <div class="slm-control">
    <div class="control-panel">
      <div class="panel-header">
        <span class="panel-title">输入能量调控与工艺参数</span>
        <div class="header-actions">
          <el-tag v-if="partsOffline" type="warning" effect="dark" size="small">试验台离线</el-tag>
          <el-tag v-if="partsFallback" type="info" effect="dark" size="small">样例零件</el-tag>
        </div>
      </div>

      <!-- 状态 / 控制栏 -->
      <div v-if="!historical" class="control-bar">
        <span class="status-dot" :class="statusDotClass"></span>
        <span class="status-text" :class="statusTextClass">{{ statusText }}</span>
        <span class="bar-meta">层号: {{ displayLayer }}</span>
        <span class="bar-meta">任务: {{ displayJob }}</span>
        <div class="bar-actions">
          <el-button :type="ready ? 'danger' : 'success'" size="small" @click="toggleReady">
            {{ ready ? '停止监听' : '开始监听' }}
          </el-button>
          <el-button size="small" :disabled="!ready || requestDisabled" @click="requestUpdate">
            {{ requestDisabled ? '请求中…' : '请求更新' }}
          </el-button>
        </div>
      </div>
      <div v-else class="control-bar replay-control-meta">
        <span>历史案例 · 调控方案</span>
        <span class="bar-meta">当前层：{{ replayContext?.layer ?? '—' }}</span>
        <span class="bar-meta">{{ replayContext?.time }}</span>
        <span class="bar-meta">参数初值来自配置，非历史实测；保存方案不下发设备。</span>
      </div>

      <!-- 试验台事件 read.json -->
      <template v-if="!historical">
      <div class="section-title">试验台事件</div>
      <div class="event-grid">
        <div class="event-item" v-for="f in eventFields" :key="f.key">
          <span class="event-label">{{ f.label }}</span>
          <span class="event-value" :class="{ 'layer': f.key === 'layer' }">{{ eventValue(f.key) }}</span>
        </div>
      </div>
      </template>

      <!-- 参数修改 -->
      <div class="section-title">工艺参数调整</div>
      <div class="params-panel">
        <div v-if="!historical" class="parts-row">
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
          <el-button size="small" :loading="partsLoading" @click="fetchParts">刷新</el-button>
          <span class="part-info" :class="partInfoClass">{{ partInfoText }}</span>
        </div>

        <div class="parameter-comparison">
          <section class="parameter-form current-form" aria-label="当前工艺参数">
            <h3>当前工艺参数</h3>
            <p class="form-description">{{ historical ? '填写回调前的工艺基准；本案例未记录历史设定值。' : '核对设备同步值，也可填写待评估的工艺基准。' }}</p>
            <div v-for="key in paramKeys" :key="key" class="parameter-field">
              <label :for="`current-${key}`">{{ safeRanges[key]?.description || key }} <span>{{ safeRanges[key]?.unit || '' }}</span></label>
              <el-input-number
                :id="`current-${key}`" v-model="inputValues[key]"
                :min="safeRanges[key]?.min" :max="safeRanges[key]?.max"
                :step="paramDefs[key].step" :precision="paramDefs[key].precision"
                :controls="false" :aria-label="`当前${safeRanges[key]?.description || key}`"
                @change="paramsSource = '手动填写（未下发）'"
              />
              <small>配置范围 {{ safeRanges[key]?.min ?? '—' }}–{{ safeRanges[key]?.max ?? '—' }} {{ safeRanges[key]?.unit || '' }}</small>
            </div>
            <p class="form-source">来源：{{ paramsSource }}</p>
          </section>
          <section class="parameter-form adjusted-form" aria-label="调控后参数（待执行）">
            <h3>调控后参数（待执行）</h3>
            <p class="form-description">根据当前参数与能量偏移计算，仅改变选定的回调参数。</p>
            <div v-for="key in paramKeys" :key="key" class="parameter-field">
              <label :for="`adjusted-${key}`">{{ safeRanges[key]?.description || key }} <span>{{ safeRanges[key]?.unit || '' }}</span></label>
              <el-input :id="`adjusted-${key}`" :model-value="executionParams ? executionParams[key].toFixed(paramDefs[key].precision) : ''"
                readonly placeholder="待设置调控目标" :aria-label="`调控后${safeRanges[key]?.description || key}`" />
              <small :class="{ changed: executionParams && executionParams[key] !== inputValues[key] }">{{ adjustmentDelta(key) }}</small>
            </div>
            <p class="form-source">随当前参数与调控目标更新；保存或发送后才形成调控记录。</p>
          </section>
        </div>

        <EnergyCorrectionControls :params="inputValues" :ranges="safeRanges" @plan="energyPlan = $event" />
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

        <div class="msg-row">
          <span class="msg-label">调整说明</span>
          <el-input v-model="message" size="small" placeholder="输入能量偏移调控" class="msg-input" />
        </div>

        <div class="action-row">
          <el-button v-if="historical" type="primary" size="small" :disabled="!replayContext || !!energyPlan?.error || !energyPlan" @click="saveReplayPlan">保存调控方案</el-button>
          <el-button v-else type="primary" size="small" :disabled="!ready || !selectedPartId || !executionParams" @click="sendAdjustment">
            发送调整参数
          </el-button>
          <el-button v-if="!historical" type="danger" size="small" :disabled="!ready" @click="emergencyStop">紧急停止</el-button>
          <el-button size="small" @click="resetDefaults">恢复默认</el-button>
        </div>
        <div v-if="sendStatus" class="send-status" :class="sendStatusClass">{{ sendStatus }}</div>
      </div>

      <section v-if="historical" class="saved-plans">
        <h3>调控方案记录</h3>
        <p v-if="!savedPlans.length">尚无保存方案。历史数据未包含调参执行反馈。</p>
        <article v-for="plan in savedPlans" :key="plan.savedAt">
          <b>第 {{ plan.layer }} 层 · {{ plan.historyTime }}</b>
          <p>目标 {{ plan.target }} J/mm³；方案 {{ plan.energy.toFixed(3) }} J/mm³；功率 {{ plan.parameters.fill_power }} W；速度 {{ plan.parameters.fill_speed }} mm/s</p>
          <span>方案已保存 · 未下发 · 无执行反馈</span>
        </article>
      </section>
      <template v-else>
      <!-- 最新反馈 feedback.json -->
      <div class="section-title">最新调控指令</div>
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
        <details class="feedback-details">
          <summary>查看原始反馈报文</summary>
          <pre class="fb-json">{{ feedbackJson }}</pre>
        </details>
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
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, h } from 'vue'
import axios from 'axios'
import { ElMessageBox } from 'element-plus'
import EnergyCorrectionControls from './EnergyCorrectionControls.vue'
import { energyDensity } from './energyCorrection'

const props = defineProps({
  historical: { type: Boolean, default: false },
  replayContext: { type: Object, default: null },
})
const energyPlan = ref(null)
// 调控结果直接随当前参数和目标更新，无推荐采纳状态；无效结果不可下发。
const executionParams = computed(() => energyPlan.value && !energyPlan.value.error ? energyPlan.value.parameters : null)
const savedPlans = ref([])
const PLAN_KEY = computed(() => `smartam-energy-plans-${props.replayContext.caseId}`)

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

const event = ref(null)
const feedback = ref(null)
const parts = ref([])
const selectedPartId = ref(null)
const partInfoText = ref('')
const partInfoClass = ref('')

const currentParams = reactive({ fill_power: 200, fill_speed: 1000, scan_spacing: 0.1, powder_feed_rate: 5.0 })
const inputValues = reactive({ fill_power: 200, fill_speed: 1000, scan_spacing: 0.1, powder_feed_rate: 5.0 })
const paramsSource = ref(props.historical ? '配置初值（方案编辑，非历史实测）' : '默认值')

const powderAmount = ref(0.06)
const powderMult = ref(1.0)
const message = ref('输入能量偏移调控')

const sendStatus = ref('')
const sendStatusClass = ref('')

const eventLog = ref([])
const sendLog = ref([])

let lastLayer = -1
let pollTimer = null

// ---- 计算属性 ----
const statusText = computed(() => {
  if (!ready.value) return '未监听'
  return event.value ? '监听中' : '等待数据...'
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
  if (!feedback.value) return '暂无调控指令'
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

// ---- 就绪 / 停止 ----
function toggleReady() {
  if (ready.value) stopMonitoring()
  else startMonitoring()
}
function startMonitoring() {
  if (props.historical) return
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
  if (props.historical || !executionParams.value) return
  if (!selectedPartId.value) { setSendStatus('请先选择 SLC 零件', 'warn'); return }

  const p = {}
  for (const key of paramKeys) {
    const val = Number(executionParams.value[key])
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

  const msg = message.value || '输入能量偏移调控'
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
      for (const key of paramKeys) { currentParams[key] = p[key]; inputValues[key] = p[key] }
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
  if (props.historical) return
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
  }
  powderAmount.value = 0.06
  powderMult.value = 1.0
  message.value = '输入能量偏移调控'
  paramsSource.value = props.historical ? '配置初值（方案编辑，非历史实测）' : '默认值'
  addEventLog('参数输入已恢复默认值（未发送）', 'info')
  addSendLog('参数已恢复默认值（未发送）', 'info')
  setSendStatus(props.historical ? '方案输入已恢复配置初值' : '已恢复默认值，点击发送生效', 'accent')
}

function adjustmentDelta(key) {
  if (!executionParams.value) return '设置有效的目标与层厚后生成'
  const delta = executionParams.value[key] - inputValues[key]
  if (delta === 0) return '保持当前值'
  return `较当前 ${delta > 0 ? '+' : ''}${delta.toFixed(paramDefs[key].precision)} ${safeRanges.value[key].unit}`
}

function saveReplayPlan() {
  if (!props.historical || !props.replayContext || !energyPlan.value || energyPlan.value.error) return
  for (const key of paramKeys) {
    const value = executionParams.value[key]
    const range = safeRanges.value[key]
    if (!Number.isFinite(value) || !range || value < range.min || value > range.max) {
      setSendStatus(`${range?.description || key}超出配置范围`, 'error')
      return
    }
  }
  if (!(powderAmount.value > 0) || !(powderMult.value >= 0.5 && powderMult.value <= 2)) {
    setSendStatus('请检查铺粉量与送粉倍率', 'error')
    return
  }
  const frame = props.replayContext
  const plan = {
    savedAt: new Date().toISOString(), layer: frame.layer, historyTime: frame.time,
    analysisLayer: frame.trace?.layer ?? null, conclusion: frame.trace?.conclusion ?? null,
    parameters: { ...executionParams.value }, baselineParameters: { ...inputValues },
    parameterSource: 'energy_offset_control', actuator: energyPlan.value.actuator,
    thickness: energyPlan.value.thickness,
    target: energyPlan.value.target, tolerance: energyPlan.value.tolerance,
    energy: energyDensity(executionParams.value, energyPlan.value.thickness),
    powderAmount: powderAmount.value, powderMultiplier: powderMult.value, message: message.value,
    status: 'draft',
  }
  // 方案与原始回放结果分开保存，绝不作为历史执行反馈。
  const plans = [plan, ...savedPlans.value].slice(0, 50)
  try {
    localStorage.setItem(PLAN_KEY.value, JSON.stringify(plans))
    savedPlans.value = plans
    setSendStatus('调控方案已保存，未下发设备', 'ok')
  } catch (e) {
    setSendStatus('本地保存失败，请检查浏览器存储空间', 'error')
  }
}

// ---- 生命周期 ----
onMounted(async () => {
  try {
    const { data } = await axios.get(`${BASE}/config`)
    safeRanges.value = data.safe_ranges || {}
    if (props.historical) {
      Object.assign(inputValues, data.defaults)
      const stored = localStorage.getItem(PLAN_KEY.value)
      if (stored) savedPlans.value = JSON.parse(stored)
    }
  } catch (e) { setSendStatus('参数配置或已存方案读取失败，请刷新重试', 'error') }
})

onUnmounted(stopPolling)
</script>

<style scoped>
.slm-control { display: flex; flex-direction: column; gap: 16px; }
.replay-control-meta { flex-wrap: wrap; }
.saved-plans { padding: 0 16px 16px; color: var(--am-text); }
.saved-plans h3 { font-size: 14px; }
.saved-plans p,.saved-plans span { font-size: 12px; line-height: 1.8; color: var(--am-text-2); }
.saved-plans article { padding: 12px 0; border-top: 1px solid var(--am-card-border); }
.saved-plans b { font-size: 13px; }
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
.parameter-comparison { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.parameter-form { padding: 18px; border: 1px solid var(--am-card-border); border-radius: 3px; min-width: 0; }
.parameter-form h3 { margin: 0 0 8px; font-size: 16px; color: var(--am-text); }
.adjusted-form { background: var(--am-card-bg-2); border-top: 3px solid var(--am-accent); padding-top: 16px; }
.form-description, .form-source { font-size: 12px; color: var(--am-text-2); line-height: 1.7; }
.form-description { min-height: 22px; margin: 0 0 16px; }
.form-source { margin: 16px 0 0; }
.parameter-field { display: grid; grid-template-columns: 132px minmax(0, 1fr); align-items: center; gap: 6px 14px; margin-bottom: 14px; }
.parameter-field label { font-size: 13px; color: var(--am-text); }
.parameter-field label span { color: var(--am-text-2); font-size: 12px; margin-left: 6px; }
.parameter-field .el-input-number, .parameter-field .el-input { width: 100%; min-width: 0; }
.parameter-field small { grid-column: 2; color: var(--am-text-3); font-size: 12px; }
.parameter-field small.changed { color: var(--am-accent); font-weight: 600; }
.adjusted-form :deep(.el-input__inner) { font-weight: 600; text-align: center; }
.parts-row { display: flex; align-items: center; gap: 10px; }
.parts-select { width: 260px; }
.part-info { font-size: 12px; color: var(--am-text-2); }
.part-info.ok { color: var(--am-ok); }
.part-info.warn { color: var(--am-warn); }
.part-info.error { color: var(--am-danger); }

.extra-row { display: flex; gap: 24px; }
.extra-item { display: flex; align-items: center; gap: 8px; }
.extra-label { font-size: 12px; color: var(--am-text); }
.extra-unit { font-size: 12px; color: var(--am-text-3); }

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
.feedback-details summary { cursor: pointer; font-size: 12px; color: var(--am-text-2); margin-bottom: 8px; }
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

@media (max-width: 1200px) { .event-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1000px) { .parameter-comparison { grid-template-columns: 1fr; } }
@media (max-width: 600px) { .parameter-field { grid-template-columns: minmax(0, 1fr); } .parameter-field small { grid-column: 1; } }
@media (max-width: 768px) { .event-grid { grid-template-columns: 1fr; } .log-panel { grid-template-columns: 1fr; } .extra-row, .control-bar, .parts-row, .action-row { flex-wrap: wrap; } .extra-item { flex-wrap: wrap; } .parts-select { max-width: 100%; } }
</style>
