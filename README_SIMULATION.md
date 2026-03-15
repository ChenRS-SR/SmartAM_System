# SmartAM System - 模拟模式说明

## 新增功能：无硬件调试模式

现在您可以在**没有连接任何传感器**的情况下运行系统，用于界面调试和功能测试！

### 快速启动模拟模式

```bash
# 方法1：一键启动（推荐）
start_with_simulation.bat

# 方法2：手动配置
1. 复制 backend/.env.example 为 backend/.env
2. 在 .env 中添加：SIMULATION_MODE=true
3. 运行 python backend/main.py
```

### 访问地址

- **前端界面**: http://localhost:5173 （需要 Node.js）
- **API 文档**: http://localhost:8000/docs
- **视频流**: http://localhost:8000/video_feed
- **系统状态**: http://localhost:8000/api/status

### 模拟数据内容

| 设备 | 模拟内容 |
|------|----------|
| **IDS 相机** | 打印头视角，带打印平台和运动效果 |
| **旁轴相机** | 整体视角，带打印机框架和打印件 |
| **红外热像** | 温度分布图，带热床和熔池热点 |
| **打印机位置** | 模拟打印头运动和 Z 轴上升 |
| **温度数据** | 热端 200°C，热床 60°C |

### 识别模拟模式

- 视频流左上角显示绿色 `[SIMULATION]` 标识
- API 返回 `simulation: true` 标记
- 日志显示 `[模拟模式] 已启用`

### 文件变更

新增文件：
- `backend/core/simulation.py` - 模拟数据生成器
- `backend/.env.example` - 环境变量配置模板
- `start_with_simulation.bat` - 模拟模式启动脚本
- `docs/模拟模式使用指南.md` - 详细使用文档

修改文件：
- `backend/core/data_acquisition.py` - 添加模拟模式支持
- `backend/main.py` - 视频流支持模拟数据

### 配置说明

在 `backend/.env` 文件中配置：

```ini
# 强制启用模拟模式
SIMULATION_MODE=true

# 硬件连接失败时自动切换到模拟
SIMULATION_AUTO_FALLBACK=true

# 控制各设备的连接尝试
IDS_ENABLE=true
SIDE_CAMERA_ENABLE=true
FOTRIC_ENABLE=true
```

详细说明请查看：`docs/模拟模式使用指南.md`

---

**现在可以在没有传感器的情况下开始开发和调试了！** 🎉
