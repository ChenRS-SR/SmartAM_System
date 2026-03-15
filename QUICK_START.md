# SmartAM System - 快速开始指南

## 环境要求

- Python 3.9+
- Node.js 18+
- （可选）Anaconda/Miniconda

---

## 第一次安装

### 1. 安装 Python 依赖

```bash
# 如果已安装 Conda
conda activate pytorch_env
pip install -r backend/requirements.txt

# 或使用系统 Python
pip install -r backend/requirements.txt
```

### 2. 安装前端依赖

```bash
# Windows 一键安装
setup_frontend.bat

# 或手动
cd frontend
npm install
```

---

## 日常启动

### 方式一：完整模拟模式（推荐用于开发）

**无需任何硬件，即可调试界面和功能**

```bash
start_simulation_full.bat
```

访问：http://localhost:5173

### 方式二：真实硬件模式

**连接所有硬件后使用**

```bash
start_all.bat
```

### 方式三：分别启动

**终端 1 - 后端**：
```bash
cd backend
python main.py
```

**终端 2 - 前端**：
```bash
cd frontend
npm run dev
```

---

## 配置说明

### 模拟模式配置（`backend/.env`）

```ini
# 完整模拟（无需任何硬件）
SIMULATION_MODE=true
OCTOPRINT_SIMULATION=true

# 或仅 OctoPrint 模拟（有相机，无打印机）
SIMULATION_MODE=false
OCTOPRINT_SIMULATION=true

# 或优先真实硬件，失败时自动模拟
SIMULATION_MODE=false
SIMULATION_AUTO_FALLBACK=true
OCTOPRINT_SIMULATION=false
OCTOPRINT_SIMULATION_AUTO_FALLBACK=true
```

### OctoPrint 配置（`backend/.env`）

```ini
OCTOPRINT_URL=http://127.0.0.1:5000
OCTOPRINT_API_KEY=your_api_key_here
```

---

## 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 视频流 | http://localhost:8000/video_feed |
| 打印机测试 | http://localhost:8000/api/printer/test |

---

## 常见问题

### 1. 端口被占用

```bash
# 查看占用 8000 端口的进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F
```

### 2. npm install 很慢

```bash
# 使用淘宝镜像
npm config set registry https://registry.npmmirror.com
npm install
```

### 3. Python 包安装失败

```bash
# 使用清华镜像
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r backend/requirements.txt
```

### 4. 模拟模式不生效

- 检查 `backend/.env` 文件是否存在
- 确认配置项为 `true`（小写）
- 重启服务

---

## 项目结构

```
SmartAM_System/
├── backend/              # FastAPI 后端
│   ├── core/            # 核心业务逻辑
│   │   ├── simulation.py           # 相机模拟器
│   │   ├── octoprint_simulation.py # OctoPrint 模拟器
│   │   └── data_acquisition.py     # 数据采集
│   ├── api/             # API 路由
│   ├── .env             # 配置文件
│   └── main.py          # 入口
├── frontend/            # Vue 3 前端
│   ├── src/
│   └── package.json
└── docs/                # 文档
```

---

## 更多文档

- [模拟模式使用指南](docs/模拟模式使用指南.md)
- [API 文档](http://localhost:8000/docs)（启动后访问）

---

**开始使用**：运行 `start_simulation_full.bat` 即可！
