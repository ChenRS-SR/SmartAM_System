# SmartAM SLM System

当前目录保留一个主启动脚本：

```bat
start_slm_complete.bat
```

该脚本会：

- 激活 Conda 环境 `pytorch_env`
- 释放后端 `8000` 和前端 `5173` 端口
- 启动 FastAPI 后端
- 启动 Vite 前端
- 打开 SLM 仪表盘页面

## 使用方式

1. 确认已安装 Conda、Node.js 18+。
2. 确认 Conda 环境名为 `pytorch_env`。
3. 双击 `start_slm_complete.bat`。

访问地址：

- 前端：<http://localhost:5173>
- 后端：<http://localhost:8000>
- API 文档：<http://localhost:8000/docs>
- SLM 仪表盘：<http://localhost:5173/slm/dashboard>

停止服务：

```bat
stop_slm.bat
```
