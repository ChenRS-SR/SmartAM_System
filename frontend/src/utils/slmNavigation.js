// 页面、侧栏和顶栏共享功能定义，避免同一个链接出现不同的默认页。
export const slmTabs = [
  { key: 'status', label: '状态监测', shortName: '监测' },
  { key: 'access', label: '数据接入', shortName: '接入' },
  { key: 'recognition', label: '缺陷识别', shortName: '识别' },
  { key: 'trace', label: '异常溯源', shortName: '溯源' },
  { key: 'control', label: '闭环调控', shortName: '调控' }
]
export const slmTab = value => slmTabs.find(item => item.key === value) || slmTabs[0]
