# SmartAM SLM 批处理脚本使用说明

## 脚本列表

### 1. `start_slm_dashboard.bat` - 一键启动SLM仪表盘
**用途**: 同时启动后端API服务和前端界面
**使用方法**: 双击运行
```
功能:
- 检查Python和Node.js环境
- 配置代理 (127.0.0.1:7890)
- 启动FastAPI后端服务 (端口8000)
- 启动Vite前端服务 (端口5173)
- 自动打开新窗口显示服务日志
```

### 2. `start_slm_backend.bat` - 单独启动后端
**用途**: 仅启动Python后端服务
**适用场景**: 
- 只需要API服务
- 前端已在运行
- 调试后端代码

### 3. `start_slm_frontend.bat` - 单独启动前端
**用途**: 仅启动前端界面
**适用场景**:
- 后端已在运行
- 只修改了前端代码
- 调试界面

### 4. `check_slm_devices.bat` - 设备检测工具
**用途**: 检测所有SLM相关硬件
**检测内容**:
- 串口设备 (振动传感器)
- USB摄像头 (CH1/CH2)
- 红外热像仪SDK
- SLM数据采集模块

### 5. `configure_slm.bat` - 交互式配置工具
**用途**: 配置硬件参数后启动
**可配置项**:
- CH1摄像头索引 (默认2)
- CH2摄像头索引 (默认3)
- 振动传感器COM口 (默认COM5)
- 模拟模式开关

### 6. `stop_slm.bat` - 停止所有服务
**用途**: 一键停止所有SLM相关进程

---

## 快速开始

### 方式一：一键启动（推荐）
```bash
# 直接双击运行
start_slm_dashboard.bat
```
然后访问: http://localhost:5173

### 方式二：带配置启动
```bash
# 先配置再启动
configure_slm.bat

# 按提示设置参数，然后选择"启动SLM仪表盘"
```

### 方式三：分步启动（开发调试）
```bash
# 窗口1: 启动后端
start_slm_backend.bat

# 窗口2: 启动前端
start_slm_frontend.bat
```

---

## 默认配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| CH1摄像头 | 索引2 | 主摄像头 |
| CH2摄像头 | 索引3 | 副摄像头 |
| 振动传感器 | COM5 | WTVB02-485 |
| 红外热像仪 | SDK自动检测 | Optris PI450i |
| 后端端口 | 8000 | FastAPI |
| 前端端口 | 5173 | Vite |

---

## 常见问题

### Q: 提示"未找到Python"
**解决**: 安装Python 3.8+ 并添加到PATH
```bash
# 验证安装
python --version
```

### Q: 摄像头无法识别
**解决**: 
1. 运行 `check_slm_devices.bat` 查看可用摄像头索引
2. 在仪表盘页面的"设置"中修改索引
3. 或运行 `configure_slm.bat` 重新配置

### Q: 振动传感器连接失败
**解决**:
1. 运行 `check_slm_devices.bat` 查看可用COM口
2. 确认设备管理器中显示正常
3. 在配置中选择正确的COM口

### Q: 红外热像仪无图像
**解决**:
1. 确保PIX Connect软件已启动
2. 在PIX Connect中连接设备并启用IPC
3. 检查SDK路径是否正确

### Q: 如何切换到模拟模式（无硬件调试）
**解决**:
1. 运行 `configure_slm.bat`
2. 选择选项4"切换模拟模式"
3. 然后选择6"启动SLM仪表盘"

---

## API端点参考

启动后可通过以下地址访问:

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:5173 |
| API文档 | http://localhost:8000/docs |
| SLM状态 | http://localhost:8000/api/slm/status |
| CH1视频流 | http://localhost:8000/api/slm/stream/camera/CH1 |
| CH2视频流 | http://localhost:8000/api/slm/stream/camera/CH2 |
| 热像视频流 | http://localhost:8000/api/slm/stream/thermal |
| WebSocket | ws://localhost:8000/api/slm/ws/data |

---

## 更新日志

### 2026-03-08
- 创建SLM批处理脚本集合
- 支持一键启动/停止
- 添加设备检测工具
- 添加交互式配置工具
