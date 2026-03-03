# SmartAM System 启动指南

## 一键启动

### 方法 1: 使用批处理脚本（推荐）

双击运行 `start_all.bat`，会自动：
1. 启动后端服务 (http://localhost:8000)
2. 启动前端服务 (http://localhost:5173)

打开浏览器访问 http://localhost:5173 即可使用。

### 方法 2: 手动启动

如果需要分别控制前后端：

**启动后端：**
```bash
cd backend
conda activate pytorch_env
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**启动前端（新终端）：**
```bash
cd frontend
npm run dev
```

## 停止服务

### 方法 1: 使用批处理脚本
双击运行 `stop_all.bat` 停止所有服务。

### 方法 2: 手动停止
直接关闭对应的命令行窗口即可。

## 常见问题

### 1. 端口被占用
如果提示端口 8000 或 5173 被占用：
```bash
# 查看占用 8000 端口的进程
netstat -ano | findstr :8000

# 结束对应进程（将 <PID> 替换为实际的进程ID）
taskkill /PID <PID> /F
```

### 2. 前端依赖缺失
如果前端启动失败，可能是 node_modules 缺失：
```bash
cd frontend
npm install
```

### 3. conda 环境未找到
确保 pytorch_env 环境存在：
```bash
conda env list

# 如果不存在，需要创建（参考项目 README）
conda create -n pytorch_env python=3.9
conda activate pytorch_env
pip install -r requirements.txt
```

## 访问地址

| 服务 | 地址 |
|-----|------|
| 前端界面 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| 设备状态 | http://localhost:8000/api/device/status |
| 打印机温度 | http://localhost:8000/api/printer/temperature |

## 配置修改

OctoPrint 配置在 `backend/.env` 文件中：
```env
OCTOPRINT_URL=http://127.0.0.1:5000
OCTOPRINT_API_KEY=你的API密钥
```

修改后需要重启后端服务。
