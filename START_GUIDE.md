# SmartAM_System 启动指南

## 快速开始

### 首次使用（一键配置）

```bash
双击运行：setup.bat
```

这会：
1. 检查 Python 和 Node.js
2. 创建 Python 虚拟环境 (`venv/`)
3. 安装后端依赖（FastAPI、PyTorch、OpenCV等）
4. 安装前端依赖（Vue 3、Element Plus等）

### 日常使用（一键启动）

```bash
双击运行：start.bat
```

这会：
1. 自动激活虚拟环境
2. 启动后端服务 (http://localhost:8000)
3. 启动前端服务 (http://localhost:5173)
4. 自动打开浏览器

---

## 环境要求

### 必需
- **Python 3.8+**: https://python.org
  - 安装时勾选 **"Add Python to PATH"**

### 可选（推荐）
- **Node.js 16+**: https://nodejs.org
  - 用于运行前端界面
  - 不安装则只能使用后端 API

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `setup.bat` | 首次配置环境（安装依赖） |
| `start.bat` | 启动所有服务 |
| `setup.ps1` | 配置脚本核心（PowerShell） |
| `start.ps1` | 启动脚本核心（PowerShell） |
| `venv/` | Python 虚拟环境（自动创建） |

---

## 启动选项

### 跳过自动打开浏览器

```bash
start.bat -NoBrowser
```

### 只启动后端（不启动前端）

```bash
start.bat -SkipFrontend
```

### 重新创建虚拟环境

```bash
setup.bat -Force
```

### 跳过 Node.js 检查

```bash
setup.bat -SkipNode
```

---

## 服务地址

启动后访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:5173 | Vue 3 Web 界面 |
| API 文档 | http://localhost:8000/docs | FastAPI 自动文档 |
| 视频流 | http://localhost:8000/video_feed | MJPEG 实时视频 |

---

## 停止服务

关闭对应的 PowerShell 窗口即可：
- 后端服务窗口
- 前端服务窗口

---

## 常见问题

### 1. 端口被占用

如果看到端口占用警告：
```
[WARN] Port 8000 is already in use
```

说明已经有服务在运行，可以直接访问相应地址，或者关闭旧服务后重试。

### 2. Python 未找到

```
[ERROR] Python not found!
```

- 访问 https://python.org 下载 Python 3.8+
- **安装时务必勾选 "Add Python to PATH"**

### 3. Node.js 未找到

```
[WARN] Node.js not found!
```

可选安装，不影响后端运行。如果需要前端界面：
- 访问 https://nodejs.org
- 下载 LTS 版本安装
- 重启电脑后重新运行 `setup.bat`

### 4. pip 安装慢

可以手动配置国内镜像：

```bash
# 激活虚拟环境后
venv\Scripts\activate

# 配置清华镜像
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 重新安装依赖
pip install -r backend\requirements.txt
```

### 5. npm 安装慢

```bash
cd frontend
npm config set registry https://registry.npmmirror.com
npm install
```

---

## 手动操作

如果需要手动控制，可以：

```bash
# 激活虚拟环境
venv\Scripts\activate

# 手动启动后端
cd backend
python main.py

# 手动启动前端（另一个窗口）
cd frontend
npm run dev
```

---

## 项目结构

```
SmartAM_System/
├── setup.bat          # 环境配置入口
├── start.bat          # 服务启动入口
├── setup.ps1          # 配置脚本
├── start.ps1          # 启动脚本
├── venv/              # Python虚拟环境
│   ├── Scripts/
│   │   ├── python.exe
│   │   └── activate.bat
│   └── Lib/
├── backend/           # FastAPI后端
│   ├── main.py
│   └── requirements.txt
└── frontend/          # Vue3前端
    ├── package.json
    └── src/
```
