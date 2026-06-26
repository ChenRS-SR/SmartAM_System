# SmartAM SLM System

当前目录保留一个主启动脚本：

```bat
start_slm_complete.bat
```

该脚本会：

- 激活 Conda 环境 `pytorch_env`
- 释放后端 `8000` 和开发前端 `5173` 端口
- 构建前端静态页面
- 启动 FastAPI 后端并统一提供页面/API
- 打开 SLM 仪表盘页面（`8000` 端口）

## 使用方式

1. 确认已安装 Conda、Node.js 18+。
2. 确认 Conda 环境名为 `pytorch_env`。
3. 双击 `start_slm_complete.bat`。

访问地址：

- 系统界面：<http://localhost:8000/slm/dashboard>
- API 文档：<http://localhost:8000/docs>
- 局域网访问：`http://<SmartAM服务器IP>:8000/slm/dashboard`

停止服务：

```bat
stop_slm.bat
```
