# SmartAM_System 前端 (Vue)

## 技术栈
- **框架**: Vue 3 (或 Vue 2，根据课题组要求)
- **组件库**: Element Plus (Vue 3) / Element UI (Vue 2)
- **图表库**: ECharts
- **HTTP 客户端**: Axios
- **状态管理**: Pinia (Vue 3) / Vuex (Vue 2)

## 目录结构

```
src/
├── assets/          # 静态资源
├── components/      # 通用组件
│   ├── VideoPlayer.vue    # 视频流播放组件
│   ├── SensorChart.vue    # 传感器数据图表
│   └── ControlPanel.vue   # 控制面板
├── views/           # 页面视图
│   ├── Dashboard.vue      # 主监控界面
│   ├── Settings.vue       # 参数设置
│   └── History.vue        # 历史记录
├── store/           # 状态管理
├── api/             # API 接口封装
├── utils/           # 工具函数
└── App.vue
```

## 快速开始

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建
npm run build
```

## 关键功能

### 1. 视频流显示
```vue
<template>
  <img src="http://localhost:8000/video_feed" alt="视频流">
</template>
```

### 2. WebSocket 实时数据
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/sensor_data');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  updateCharts(data);
};
```

### 3. API 调用
```javascript
import axios from 'axios';

// 获取系统状态
const status = await axios.get('http://localhost:8000/api/status');

// 发送控制指令
await axios.post('http://localhost:8000/api/printer/command', {
  command: 'G1 X10 Y10',
  parameters: {}
});
```
