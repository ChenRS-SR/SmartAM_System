<template>
  <div class="file-manager">
    <div class="file-header">
      <h3 class="file-title">
        <el-icon><Folder /></el-icon>
        打印文件管理
      </h3>
      <el-button size="small" type="primary" :loading="loading" @click="refreshFiles">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <!-- 文件统计 -->
    <div class="file-stats">
      <el-tag size="small" type="info">共 {{ allFiles.length }} 个文件</el-tag>
      <el-tag v-if="selectedFile" size="small" type="success">已选择</el-tag>
    </div>
    
    <!-- 文件列表 -->
    <div class="file-list">
      <div
        v-for="file in allFiles"
        :key="file.path"
        class="file-item"
        :class="{ selected: selectedFile === file.path }"
        @click="selectFile(file)"
      >
        <div class="file-left">
          <el-icon class="file-icon" :size="24"><Document /></el-icon>
          <div class="file-info">
            <div class="file-name" :title="file.name">
              {{ file.displayName || file.name }}
              <el-tag v-if="file.location === 'sdcard'" size="small" type="warning" effect="dark">SD</el-tag>
            </div>
            <div class="file-path" :title="file.path">{{ file.path }}</div>
            <div class="file-meta">
              <span class="meta-item">
                <el-icon><DataLine /></el-icon>
                {{ formatSize(file.size) }}
              </span>
              <span class="meta-item">
                <el-icon><Clock /></el-icon>
                {{ formatDate(file.date) }}
              </span>
              <span v-if="file.estimatedPrintTime" class="meta-item time">
                <el-icon><Timer /></el-icon>
                预计 {{ formatDuration(file.estimatedPrintTime) }}
              </span>
            </div>
          </div>
        </div>
        
        <div class="file-actions">
          <el-button
            v-if="selectedFile === file.path"
            size="small"
            type="success"
            :loading="printing"
            @click.stop="startPrint(file)"
          >
            <el-icon><VideoPlay /></el-icon>
            开始打印
          </el-button>
          <el-icon v-else class="select-hint"><ArrowRight /></el-icon>
        </div>
      </div>
      
      <div v-if="allFiles.length === 0" class="file-empty">
        <el-icon :size="48"><FolderOpened /></el-icon>
        <p>暂无打印文件</p>
        <p class="file-hint">请将 G-code 文件上传到 OctoPrint 或 SD 卡</p>
      </div>
    </div>
    
    <!-- 打印控制 -->
    <div v-if="isPrinting" class="print-controls">
      <el-divider />
      <div class="controls-header">
        <div class="controls-title">
          <el-icon><Printer /></el-icon>
          正在打印
        </div>
        <div class="print-filename" :title="store.latestData.printer.filename">
          {{ store.latestData.printer.filename || '未知文件' }}
        </div>
      </div>
      
      <div class="print-progress">
        <el-progress 
          :percentage="Math.round(store.latestData.printer.progress)" 
          :status="progressStatus"
          :stroke-width="10"
        />
        <div class="progress-info">
          <span>{{ formatTime(store.latestData.printer.print_time) }} 已用</span>
          <span>{{ formatTime(store.latestData.printer.print_time_left) }} 剩余</span>
        </div>
      </div>
      
      <div class="controls-buttons">
        <el-button v-if="store.latestData.printer.state === 'Printing'" type="warning" size="small" @click="pausePrint">
          <el-icon><VideoPause /></el-icon>
          暂停
        </el-button>
        <el-button v-else-if="store.latestData.printer.state === 'Paused'" type="success" size="small" @click="resumePrint">
          <el-icon><VideoPlay /></el-icon>
          恢复
        </el-button>
        <el-button type="danger" size="small" @click="cancelPrint">
          <el-icon><CircleClose /></el-icon>
          取消
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { printerApi } from '../utils/api'
import { useDataStore } from '../stores/data'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useDataStore()

const loading = ref(false)
const printing = ref(false)
const allFiles = ref([])
const selectedFile = ref(null)

const isPrinting = computed(() => {
  return store.latestData.printer.state === 'Printing' || 
         store.latestData.printer.state === 'Paused'
})

const progressStatus = computed(() => {
  if (store.latestData.printer.state === 'Paused') return 'warning'
  return ''
})

const refreshFiles = async () => {
  loading.value = true
  try {
    const res = await printerApi.getFiles()
    if (res.data.success) {
      // 合并 SD 卡和本地文件，去重
      const files = new Map()
      
      // 先添加 SD 卡文件
      res.data.files.sdcard.forEach(f => {
        files.set(f.path, { ...f, location: 'sdcard', displayName: extractFilename(f.name) })
      })
      
      // 添加本地文件（如果路径不存在）
      res.data.files.local.forEach(f => {
        if (!files.has(f.path)) {
          files.set(f.path, { ...f, location: 'local', displayName: extractFilename(f.name) })
        }
      })
      
      // 转换为数组并按名称排序
      allFiles.value = Array.from(files.values()).sort((a, b) => a.name.localeCompare(b.name))
      
      ElMessage.success(`获取到 ${allFiles.value.length} 个文件`)
    } else {
      ElMessage.error(res.data.error || '获取文件失败')
    }
  } catch (e) {
    ElMessage.error('获取文件列表失败')
  } finally {
    loading.value = false
  }
}

const extractFilename = (path) => {
  // 从路径中提取文件名（保持原始格式）
  const parts = path.split('/')
  return parts[parts.length - 1]
}

const selectFile = (file) => {
  selectedFile.value = file.path
}

const startPrint = async (file) => {
  printing.value = true
  try {
    const res = await printerApi.startPrint(file.path, file.location)
    if (res.data.success) {
      ElMessage.success(res.data.message)
      selectedFile.value = null
    } else {
      ElMessage.error(res.data.error || '启动打印失败')
    }
  } catch (e) {
    ElMessage.error('启动打印失败')
  } finally {
    printing.value = false
  }
}

const pausePrint = async () => {
  try {
    const res = await printerApi.pauseJob()
    if (res.data.success) {
      ElMessage.success('打印已暂停')
    }
  } catch (e) {
    ElMessage.error('暂停失败')
  }
}

const resumePrint = async () => {
  try {
    const res = await printerApi.resumeJob()
    if (res.data.success) {
      ElMessage.success('打印已恢复')
    }
  } catch (e) {
    ElMessage.error('恢复失败')
  }
}

const cancelPrint = async () => {
  try {
    await ElMessageBox.confirm('确定要取消当前打印任务吗？', '确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const res = await printerApi.cancelJob()
    if (res.data.success) {
      ElMessage.success('打印已取消')
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('取消失败')
    }
  }
}

const formatSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (timestamp) => {
  if (!timestamp) return '未知'
  const date = new Date(timestamp * 1000)
  const now = new Date()
  const diff = now - date
  
  // 小于1小时显示相对时间
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000)
    return mins < 1 ? '刚刚' : `${mins} 分钟前`
  }
  // 小于24小时
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours} 小时前`
  }
  
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatDuration = (seconds) => {
  if (!seconds) return '--'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}小时${mins}分`
  }
  return `${mins}分钟`
}

const formatTime = (seconds) => {
  if (!seconds) return '--:--'
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`
}

onMounted(() => {
  refreshFiles()
})
</script>

<style scoped>
.file-manager {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 12px;
  padding: 16px;
}

.file-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.file-title {
  margin: 0;
  font-size: 16px;
  color: #00d4ff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.file-list {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2);
}

.file-list::-webkit-scrollbar {
  width: 6px;
}

.file-list::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.file-list::-webkit-scrollbar-thumb {
  background: rgba(0, 212, 255, 0.3);
  border-radius: 3px;
}

.file-list::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 212, 255, 0.5);
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  cursor: pointer;
  border-bottom: 1px solid rgba(0, 212, 255, 0.05);
  border-left: 3px solid transparent;
  transition: all 0.2s;
  user-select: none;
}

.file-item:hover {
  background: rgba(0, 212, 255, 0.08);
}

.file-item.selected {
  background: rgba(0, 212, 255, 0.15);
  border-left-color: #00d4ff;
}

.file-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.file-icon {
  color: #00d4ff;
  margin-top: 2px;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  color: #e2e8f0;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-path {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  gap: 12px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 4px;
}

.meta-item.time {
  color: #f59e0b;
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.select-hint {
  color: #64748b;
  font-size: 16px;
}

.file-empty {
  padding: 40px 20px;
  text-align: center;
  color: #64748b;
}

.file-empty p {
  margin: 8px 0;
}

.file-hint {
  font-size: 12px;
  opacity: 0.7;
}

.print-controls {
  margin-top: 16px;
}

.controls-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.controls-title {
  font-size: 13px;
  color: #00d4ff;
  display: flex;
  align-items: center;
  gap: 6px;
}

.print-filename {
  font-size: 12px;
  color: #94a3b8;
  max-width: 150px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.print-progress {
  margin-bottom: 12px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
}

.controls-buttons {
  display: flex;
  gap: 10px;
}
</style>
