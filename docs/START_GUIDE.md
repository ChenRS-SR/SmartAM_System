# SmartAM System - 启动指南

## 三种启动方式

### 方式一：纯前端模式（推荐用于 UI 开发）

**特点**：
- ⚡ 启动最快（无需后端）
- 🎨 界面完全可用
- 📺 Canvas 模拟视频流
- 📊 JavaScript 生成模拟数据

**启动命令**：
```bash
start_frontend_only.bat
```

**访问地址**：http://localhost:5173

**适用场景**：
- 界面开发和调试
- 功能演示
- 无后端环境下的测试

---

### 方式二：完整模拟模式

**特点**：
- 🖥️ 需要启动后端服务
- 🐍 Python 生成模拟图像
- 💾 支持数据保存
- 🔧 更接近真实环境

**启动命令**：
```bash
start_simulation_full.bat
```

**访问地址**：
- 前端：http://localhost:5173
- 后端：http://localhost:8000

**适用场景**：
- 完整功能测试
- API 调试
- 数据流程验证

---

### 方式三：真实硬件模式

**特点**：
- ✅ 连接真实相机和打印机
- 📷 真实图像数据
- 🌡️ 真实温度数据
- 💯 生产环境使用

**启动命令**：
```bash
start_all.bat
```

**前置条件**：
- IDS 相机已连接
- 旁轴相机已连接
- Fotric 热像仪已连接（可选）
- OctoPrint 已运行并连接打印机

---

## 快速诊断

### 问题：前端报错 "Network Error"

**原因**：前端无法连接到后端

**解决**：
1. 使用纯前端模式：`start_frontend_only.bat`
2. 或确保后端已启动：`start_simulation_full.bat`

### 问题：视频流加载失败

**纯前端模式**：
- 使用 Canvas 模拟动画，无需后端
- 显示 `[MOCK]` 标识

**其他模式**：
- 检查后端是否运行
- 检查端口 8000 是否被占用

### 问题：温度/位置数据不更新

**纯前端模式**：
- 数据由 JavaScript 生成
- 自动更新，无需配置

**其他模式**：
- 检查 WebSocket 连接
- 查看后端日志

---

## 模式切换

### 切换到纯前端模式

```bash
# 删除后端配置，启用前端模拟
cd frontend
echo VITE_MOCK_MODE=true > .env.local
npm run dev
```

### 切换到真实后端

```bash
# 删除前端模拟配置
cd frontend
del .env.local

# 启动后端
cd ../backend
python main.py
```

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `start_frontend_only.bat` | 纯前端模式启动 |
| `start_simulation_full.bat` | 完整模拟模式（需后端）|
| `start_all.bat` | 真实硬件模式 |
| `frontend/.env.local` | 前端本地配置（模拟模式开关）|
| `backend/.env` | 后端配置（模拟模式开关）|

---

## 模拟数据说明

### 纯前端模式

| 数据类型 | 来源 | 更新频率 |
|---------|------|---------|
| 视频流 | Canvas 动画 | 60 FPS |
| 温度 | JS 生成 | 1 秒 |
| 位置 | JS 生成 | 实时 |
| 预测 | JS 生成 | 1 秒 |

### 完整模拟模式

| 数据类型 | 来源 | 更新频率 |
|---------|------|---------|
| 视频流 | Python OpenCV | 30 FPS |
| 温度 | Python 生成 | 1 秒 |
| 位置 | Python 生成 | 实时 |
| 预测 | Python 生成 | 1 秒 |

---

## 推荐开发流程

1. **UI 开发**：使用 `start_frontend_only.bat`
   - 快速迭代界面
   - 即时预览效果

2. **功能联调**：使用 `start_simulation_full.bat`
   - 测试 API 调用
   - 验证数据流程

3. **硬件测试**：使用 `start_all.bat`
   - 连接真实设备
   - 验证采集效果

---

**现在开始**：双击 `start_frontend_only.bat` 启动纯前端模式！
