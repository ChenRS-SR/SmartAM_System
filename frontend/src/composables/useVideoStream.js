/**
 * 视频流组合式函数
 * 支持真实后端流和模拟模式
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { FORCE_MOCK } from '@/utils/api'

// 生成模拟视频帧（使用 Canvas）
function generateMockFrame(type = 'combined') {
  const canvas = document.createElement('canvas')
  
  if (type === 'ids') {
    canvas.width = 640
    canvas.height = 480
  } else if (type === 'side') {
    canvas.width = 640
    canvas.height = 480
  } else {
    // combined layout
    canvas.width = 960
    canvas.height = 540
  }
  
  const ctx = canvas.getContext('2d')
  const t = Date.now() / 1000
  
  // 背景
  ctx.fillStyle = '#1a1a2e'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  
  // 网格线
  ctx.strokeStyle = '#333'
  ctx.lineWidth = 1
  for (let i = 0; i < canvas.width; i += 40) {
    ctx.beginPath()
    ctx.moveTo(i, 0)
    ctx.lineTo(i, canvas.height)
    ctx.stroke()
  }
  for (let i = 0; i < canvas.height; i += 40) {
    ctx.beginPath()
    ctx.moveTo(0, i)
    ctx.lineTo(canvas.width, i)
    ctx.stroke()
  }
  
  // 模拟打印头
  const x = canvas.width / 2 + Math.sin(t) * 100
  const y = canvas.height / 2 + Math.cos(t * 0.7) * 50
  
  // 喷嘴
  ctx.fillStyle = '#ff6b6b'
  ctx.beginPath()
  ctx.arc(x, y, 15, 0, Math.PI * 2)
  ctx.fill()
  
  // 发光效果
  const gradient = ctx.createRadialGradient(x, y, 0, x, y, 30)
  gradient.addColorStop(0, 'rgba(255, 100, 100, 0.8)')
  gradient.addColorStop(1, 'rgba(255, 100, 100, 0)')
  ctx.fillStyle = gradient
  ctx.beginPath()
  ctx.arc(x, y, 30, 0, Math.PI * 2)
  ctx.fill()
  
  // 丝材线
  ctx.strokeStyle = '#4ecdc4'
  ctx.lineWidth = 3
  ctx.beginPath()
  ctx.moveTo(x, y + 15)
  ctx.lineTo(x, canvas.height - 20)
  ctx.stroke()
  
  // 文字标识
  ctx.fillStyle = '#00ff00'
  ctx.font = 'bold 16px Arial'
  ctx.fillText('[MOCK] ' + type.toUpperCase(), 10, 25)
  ctx.font = '12px Arial'
  ctx.fillStyle = '#aaa'
  ctx.fillText('No Backend - Simulation Mode', 10, 45)
  ctx.fillText(`FPS: ${(Math.random() * 5 + 25).toFixed(1)}`, 10, 65)
  ctx.fillText(`Time: ${t.toFixed(1)}s`, 10, 85)
  
  return canvas.toDataURL('image/jpeg', 0.8)
}

export function useVideoStream(streamType = 'combined') {
  const streamUrl = ref('')
  const isConnected = ref(false)
  const isMock = ref(false)
  const error = ref(null)
  
  let mockInterval = null
  let objectUrl = null
  
  const startStream = async () => {
    // 如果强制模拟或后端不可用
    if (FORCE_MOCK) {
      console.log(`[VideoStream] ${streamType} 使用模拟模式`)
      isMock.value = true
      isConnected.value = true
      
      // 生成模拟帧
      mockInterval = setInterval(() => {
        const dataUrl = generateMockFrame(streamType)
        streamUrl.value = dataUrl
      }, 200) // 5 FPS
      
      return
    }
    
    // 尝试真实流
    try {
      const response = await fetch(`http://localhost:8000/video_feed/${streamType === 'combined' ? '' : streamType}`, {
        method: 'HEAD',
        mode: 'no-cors',
        cache: 'no-cache'
      })
      
      // 如果能连接，使用真实流
      streamUrl.value = `http://localhost:8000/video_feed${streamType === 'combined' ? '' : '/' + streamType}`
      isConnected.value = true
      isMock.value = false
    } catch (e) {
      // 连接失败，回退到模拟
      console.warn(`[VideoStream] 无法连接后端，使用模拟模式:`, e.message)
      isMock.value = true
      isConnected.value = true
      
      mockInterval = setInterval(() => {
        const dataUrl = generateMockFrame(streamType)
        streamUrl.value = dataUrl
      }, 200)
    }
  }
  
  const stopStream = () => {
    if (mockInterval) {
      clearInterval(mockInterval)
      mockInterval = null
    }
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl)
      objectUrl = null
    }
    isConnected.value = false
    streamUrl.value = ''
  }
  
  onMounted(startStream)
  onUnmounted(stopStream)
  
  return {
    streamUrl,
    isConnected,
    isMock,
    error,
    startStream,
    stopStream
  }
}

export default useVideoStream
