# SmartAM System 启动脚本说明与 FDM 验证指南

## 一、启动脚本对比说明

### 📋 脚本分类总览

| 类别 | 脚本名称 | 用途 | 是否需要硬件 |
|------|----------|------|-------------|
| **完整启动** | `start_all.bat` | 启动前后端（真实硬件模式） | ✅ 需要 |
| | `start_all_with_simulation.bat` | 启动前后端（模拟模式） | ❌ 不需要 |
| **仅后端** | `start_with_simulation.bat` | 仅后端（模拟模式） | ❌ 不需要 |
| | `start_backend_only.bat` | 仅后端（系统Python） | ⚠️ 可选 |
| **仅前端** | `start_frontend_only.bat` | 仅前端（纯模拟，无后端） | ❌ 不需要 |
| | `start_frontend_mock.bat` | 仅前端（Mock模式） | ❌ 不需要 |
| **安装配置** | `install_env.bat` | 安装Conda环境和依赖 | - |
| | `setup_frontend.bat` | 安装前端依赖 | - |
| | `install_deps_only.bat` | 仅安装依赖 | - |
| **工具** | `kill_python.bat` | 停止所有Python进程 | - |
| | `stop_all.bat` | 停止所有服务 | - |

---

## 二、详细脚本说明

### 1. 完整启动脚本（前后端）

#### `start_all.bat` ⭐ **原版推荐**
```
用途：启动完整的真实硬件系统
特点：
- 使用 Conda 环境 (pytorch_env)
- 启动真实后端 + 前端
- 需要连接 FDM 打印机、IDS相机、Fotric等硬件
- 不启用任何模拟模式

适用场景：
✅ 实验室有完整硬件时日常使用
✅ 正式采集数据

硬件要求：
- IDS 相机已连接
- Fotric 热像仪已连接
- OctoPrint 已启动并配置
```

#### `start_all_with_simulation.bat` ⭐ **出差调试推荐**
```
用途：启动前后端，但使用模拟数据
特点：
- 后端自动生成模拟图像（假打印画面）
- 模拟温度数据（180-220°C范围变化）
- 模拟打印机位置（Z轴自动递增）
- 前端正常显示，但数据都是生成的

适用场景：
✅ 出差无法连接硬件时开发前端
✅ 测试新功能不影响真实设备
✅ 演示系统给领导看

配置方式：
自动在 .env 中添加：
  SIMULATION_MODE=true
  SIMULATION_AUTO_FALLBACK=true
```

### 2. 仅后端启动

#### `start_with_simulation.bat`
```
用途：仅启动后端（模拟模式）
特点：
- 只启动 Python 后端，不启动前端
- 生成模拟数据
- 可通过 http://localhost:8000 访问 API

适用场景：
✅ 只测试后端 API
✅ 前端单独开发时提供模拟数据源
```

#### `start_backend_only.bat`
```
用途：仅启动后端（系统Python，非Conda）
特点：
- 不依赖 Conda 环境
- 使用系统安装的 Python
- 自动检查并安装基本依赖

适用场景：
⚠️ 临时使用，不推荐
⚠️ Conda 环境损坏时应急
```

### 3. 仅前端启动

#### `start_frontend_only.bat` / `start_frontend_mock.bat`
```
用途：纯前端运行，完全不需要后端
特点：
- 前端自己生成所有模拟数据
- 不连接任何后端服务
- 连后端报错都不会有

适用场景：
✅ 纯 UI 开发调试
✅ 设计师调整界面样式
✅ 演示前端界面功能

数据流向：
前端 Mock 数据 → 界面显示
（完全不经过后端）
```

### 4. 安装配置脚本

#### `install_env.bat`
```
用途：一键安装完整环境
执行内容：
1. 创建 pytorch_env Conda 环境 (Python 3.11)
2. 安装后端依赖（FastAPI、PyTorch等）
3. 安装前端依赖（npm install）
4. 配置清华镜像源

⚠️ 注意：
- 脚本中 Conda 路径是硬编码的，需要根据实际情况修改
- 安装 PyTorch 可能需要较长时间
```

#### `setup_frontend.bat`
```
用途：仅安装前端依赖并启动
功能：
- 检查 Node.js
- npm install
- 启动前端
```

---

## 三、如何选择启动脚本？

### 决策树

```
你在什么场景？
│
├─ 在实验室，有完整硬件
│  └─ 使用：start_all.bat ⭐
│
├─ 出差/在家，没有硬件
│  ├─ 需要测试后端 API
│  │  └─ 使用：start_with_simulation.bat
│  │
│  └─ 需要看完整界面效果
│     └─ 使用：start_all_with_simulation.bat ⭐
│
├─ 只做前端开发/UI调整
│  └─ 使用：start_frontend_only.bat
│
└─ 环境出现问题，需要重装
   └─ 使用：install_env.bat
```

### 快速参考

| 你的需求 | 推荐脚本 |
|---------|----------|
| 日常实验采集 | `start_all.bat` |
| 出差调试系统 | `start_all_with_simulation.bat` |
| 只改前端界面 | `start_frontend_only.bat` |
| 测试后端逻辑 | `start_with_simulation.bat` |
| 第一次安装环境 | `install_env.bat` |

---

## 四、回实验室验证 FDM 功能指南

### ⚠️ 为什么需要验证？

cyber-dogy 的修改在 `data_acquisition.py` 中添加了模拟逻辑，虽然默认关闭，但需要确认：**真实硬件路径是否仍然正常工作**。

### 📋 验证检查清单

#### 步骤 1：切换回干净版本

```bash
# 查看当前分支
cd D:\College\Python_project\4Project\SmartAM_System
git branch

# 切换回 master 分支（你原来的稳定版本）
git checkout master

# 确认当前代码状态
git status
```

#### 步骤 2：基础功能验证

| 检查项 | 验证方法 | 通过标准 |
|--------|----------|----------|
| **后端启动** | 双击 `start_all.bat` | 无报错，显示 "Uvicorn running on http://0.0.0.0:8000" |
| **前端启动** | 自动启动或手动 `npm run dev` | 访问 http://localhost:5173 正常显示 |
| **设备状态** | 访问 http://localhost:8000/api/device/status | 返回 `{"ids": true, "fotric": true, ...}` |

#### 步骤 3：硬件连接验证

**IDS 相机：**
```bash
# 访问视频流
http://localhost:8000/video_feed

# 应该看到：
# - 实时打印画面
# - 不是模拟生成的网格图案
```

**Fotric 热像仪：**
```bash
# 访问热像状态
http://localhost:8000/api/thermal/status

# 应该看到：
# {
#   "available": true,
#   "connected": true,
#   "ip": "192.168.x.x",  // 真实IP，不是 "simulation"
#   "simulation": false
# }
```

**OctoPrint 打印机：**
```bash
# 访问打印机状态
http://localhost:8000/api/printer/status

# 应该看到：
# {
#   "connected": true,
#   "state": "Operational",  // 不是 "Printing (Simulation)"
#   "hotend_actual": 实际温度值,
#   "simulation": false  // 关键！必须是 false
# }
```

#### 步骤 4：数据采集验证

1. **启动采集**
   - 前端点击"开始采集"
   - 检查 `backend/data/` 目录是否生成新的 task 文件夹

2. **检查 CSV 数据**
   ```bash
   # 打开最新的 task 文件夹中的 print_message.csv
   # 检查：
   # - current_z 是否随打印变化（不是模拟的递增）
   # - hot_end 是否真实温度
   # - image_path 对应的图片是否真实拍摄
   ```

3. **检查图像**
   - 打开 `task_xxx/images/IDS_Camera/000000.jpg`
   - 确认是真实打印画面，不是模拟生成的网格

#### 步骤 5：控制功能验证

| 功能 | 操作 | 验证 |
|------|------|------|
| **温度设置** | 前端设置热端温度 210°C | 打印机实际温度变化，OctoPrint 显示新目标温度 |
| **流量调整** | 设置流量 110% | 听到挤出机声音变化 |
| **Z偏移** | 微调 Z +0.1mm | 打印层可见变化 |

### 🔴 关键验证点

**在 master 分支上必须确认：**

```python
# 1. 设备状态中没有 simulation 标记
curl http://localhost:8000/api/device/status
# 期望：{"simulation": false, ...}

# 2. 打印机状态不是模拟
curl http://localhost:8000/api/printer/status
# 期望：{"simulation": false, "state": "Operational"}

# 3. 图像数据是真实的
# 查看 video_feed，确认是实时画面
```

### 如果发现问题怎么办？

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| 显示 "simulation": true | .env 配置被修改 | 检查 `backend/.env`，删除 SIMULATION 相关行 |
| 图像是网格图案 | 进入了模拟分支 | 重启服务，检查硬件连接 |
| 无法连接设备 | 硬件未连接或驱动问题 | 检查 USB 连接，重启硬件 |

### 验证通过后

确认 master 分支工作正常后，你可以选择：

1. **保持分离**：
   - `master` = 稳定版（FDM 专用）
   - `feature/multi-device` = 开发版（模拟+SLM）

2. **合并功能**：
   - 将 `feature/multi-device` 合并到 `master`
   - 但保留 `SIMULATION_MODE=false` 默认配置

---

## 五、快速对比表

| 脚本 | 后端 | 前端 | 模拟数据 | 硬件要求 | 使用场景 |
|------|------|------|----------|----------|----------|
| `start_all.bat` | ✅ | ✅ | ❌ | ✅ 全部 | 实验室日常使用 |
| `start_all_with_simulation.bat` | ✅ | ✅ | ✅ | ❌ | 出差调试 |
| `start_with_simulation.bat` | ✅ | ❌ | ✅ | ❌ | 后端单独开发 |
| `start_backend_only.bat` | ✅ | ❌ | ❌ | ⚠️ 可选 | 应急使用 |
| `start_frontend_only.bat` | ❌ | ✅ | ✅(前端) | ❌ | UI开发 |
| `start_frontend_mock.bat` | ❌ | ✅ | ✅(前端) | ❌ | 纯前端演示 |

---

## 六、常见问题

### Q: 启动脚本太多，能否合并？
**A**: 建议保留 3 个核心脚本：
- `start_all.bat` - 真实硬件
- `start_all_with_simulation.bat` - 模拟模式
- `install_env.bat` - 环境安装
其他可以删除或移到 `scripts/legacy/`。

### Q: 如何快速知道当前是不是模拟模式？
**A**: 查看后端日志：
- 真实模式：`[设备] IDS相机初始化完成`
- 模拟模式：`[模拟模式] ========== 已启用 ==========`

### Q: feature/multi-device 分支能否在实验室使用？
**A**: 可以，但需要确保 `.env` 中：
```env
SIMULATION_MODE=false
SIMULATION_AUTO_FALLBACK=false
OCTOPRINT_SIMULATION=false
```
