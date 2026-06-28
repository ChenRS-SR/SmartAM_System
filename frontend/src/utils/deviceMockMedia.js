const CHANNEL_LABELS = {
  camera_ch1: 'CH1',
  camera_ch2: 'CH2',
  thermal: 'CH3'
}

const cloneJson = (value) => JSON.parse(JSON.stringify(value))

export function normalizeDeviceMockCase(mockCase) {
  if (!mockCase) return null
  return mockCase
}

const countAvailableChannels = (channels = {}) => (
  Object.keys(CHANNEL_LABELS).filter((channel) => channels[channel]?.available && channels[channel]?.url).length
)

export function getDeviceMockCase(device) {
  const mockVideo = device?.mockVideo
  if (!mockVideo?.supported) return null

  const rawCase = typeof device?.mockCase === 'object' && device.mockCase ? device.mockCase : {}
  const availableCount = countAvailableChannels(mockVideo.channels)
  const label = rawCase.label || (availableCount ? `目录模拟视频 ${availableCount}/3` : '目录模拟视频')

  return {
    id: rawCase.id || device?.id || 'device_directory_mock',
    name: rawCase.name || device?.name || 'Device Directory Mock',
    label,
    health: device?.healthData ? cloneJson(device.healthData) : null,
    channels: mockVideo.channels || {},
    correctedChannels: mockVideo.correctedChannels || {},
    supported: Boolean(mockVideo.supported),
    correctedSupported: Boolean(mockVideo.correctedSupported),
    sourceFolder: mockVideo.sourceFolder || 'mock_video',
    correctedSourceFolder: mockVideo.correctedSourceFolder || 'mock_video_corrected',
    message: mockVideo.message || '暂不支持接入'
  }
}

const selectChannelMap = (mockCase, options = {}) => {
  if (options.distortionCorrected && mockCase?.correctedSupported) {
    return mockCase.correctedChannels || {}
  }
  return mockCase?.channels || {}
}

export function getMockCaseVideoUrl(mockCase, channel, options = {}) {
  const normalized = normalizeDeviceMockCase(mockCase)
  const channelInfo = selectChannelMap(normalized, options)[channel]
  if (!channelInfo?.available || !channelInfo.url) return ''
  return channelInfo.url
}

export function buildMockCaseMedia(mockCase, streamKey = Date.now(), options = {}) {
  const normalized = normalizeDeviceMockCase(mockCase)
  if (!normalized) return {}

  return Object.keys(CHANNEL_LABELS).reduce((media, channel) => {
    const url = getMockCaseVideoUrl(normalized, channel, options)
    if (!url) return media
    media[channel] = {
      url: `${url}?t=${streamKey}`,
      media_type: 'video',
      channel: CHANNEL_LABELS[channel],
      case_id: normalized.id,
      case_name: normalized.label,
      distortion_corrected: Boolean(options.distortionCorrected && normalized.correctedSupported)
    }
    return media
  }, {})
}

export function buildMockCaseHealthData(mockCase) {
  const normalized = normalizeDeviceMockCase(mockCase)
  if (!normalized?.health) return null
  return cloneJson(normalized.health)
}

export async function checkMockCaseMedia(mockCase, options = {}) {
  const normalized = normalizeDeviceMockCase(mockCase)
  if (!normalized) {
    return { hasCase: false, ready: false, allReady: false, channels: {}, missing: [] }
  }

  const channels = {}
  const missing = []
  const channelMap = selectChannelMap(normalized, options)

  // 只探测后端扫描到的通道文件；没有文件或格式不支持时该通道保持未接入。
  await Promise.all(Object.keys(CHANNEL_LABELS).map(async (channel) => {
    const channelInfo = channelMap[channel]
    if (!channelInfo?.available || !channelInfo.url) {
      channels[channel] = false
      missing.push(channel)
      return
    }

    try {
      const response = await fetch(channelInfo.url, { method: 'HEAD', cache: 'no-store' })
      channels[channel] = response.ok
      if (!response.ok) missing.push(channel)
    } catch {
      channels[channel] = false
      missing.push(channel)
    }
  }))

  return {
    hasCase: true,
    ready: Object.values(channels).some(Boolean),
    allReady: Object.values(channels).every(Boolean),
    channels,
    missing
  }
}

export function buildMockCaseStatusText(mockCase, availability) {
  const normalized = normalizeDeviceMockCase(mockCase)
  if (!normalized) return '暂不支持接入'
  if (!availability?.ready) return `${normalized.label} 暂不支持接入`
  if (!availability.allReady) return `${normalized.label} 部分通道`
  return normalized.label
}
