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

后端固定监听 `0.0.0.0:8000`；同一局域网的电脑可使用服务器 IP 访问，无需修改前端配置。页面、API 和 WebSocket 默认共用地址栏中的主机与端口，兼容 VS Code 内置浏览器和端口转发；HTTPS 页面会使用 WSS。使用开发服务时访问 `http://<SmartAM服务器IP>:5173`，Vite 在服务器端代理 API 和实时连接到后端。不要把 `0.0.0.0` 当作浏览器访问地址。

默认保持 `VITE_API_BASE_URL` 未设置。仅在明确需要独立后端时设置此构建变量；该变量同时作用于 HTTP 和 WebSocket。页面入口禁用缓存，刷新会加载当前构建。

停止服务：

```bat
stop_slm.bat
```

## 仓库随附设备案例

`feature/GJW_Contribution` 包含可直接播放的设备案例。正常 `git clone` / `git pull` 会取得全部分卷，不需要 Git LFS、模型权重或开发者电脑上的论文数据目录。首次打开设备时，后端校验 SHA-256 并解包到 `backend/data/replay_runtime/`；该目录是可重建的运行缓存，不提交。

| 设备入口 | 随附完整层数 | 数据内容 |
| --- | ---: | --- |
| BLT-S430 B17 | 402 | 铺粉/熔化图像、扭矩、设备参数、已封存识别与双因素溯源结果 |
| 铂力特 S430 B44 | 26 | 铺粉/熔化图像、扭矩、设备参数、报警 |
| 铂力特 S310 B10 | 252 | 铺粉/熔化图像、扭矩、设备参数、报警 |
| 铂力特 S310 B15 | 101 | 铺粉/熔化图像、扭矩、设备参数、报警 |

设备群总览和监测页面按采集工作流显示；播放、暂停、倍速和定位层统一在对应设备的系统设置中操作。普通设备的回放设置禁用。每台案例设备使用独立的播放进度、采集通道显示选项与本地调控方案记录。

B44/B10/B15 尚未封存逐层识别与溯源结果，相关页面明确显示未接入，不使用其他设备的结果或数据标签填充。案例设备不会初始化相机、PLC 或下发控制指令；闭环调控页只保存方案。

发布数据位于 `backend/replay_cases/`，合计约 274 MiB，各分卷小于 40 MiB。完整目录和分卷哈希记录在 `catalog.json`；各包内另有文件校验清单与来源记录。传感器数值、秒级时间及同秒采样顺序保留；图像是最长边 1200 像素的展示版本，原图文件名、尺寸与 SHA-256 记录在 `provenance.json`，不用于重新推理。原始采集缺口按明确分段跳过。

设备卡片照片在 `frontend/public/device-images/`。S310 使用用户提供的同型设备图，S430 使用用户提供的已打码现场图，作为展示替代图，不表示拍摄对象与每台设备编号一一对应。

### 新环境启动

使用 Python 3.10+、Node.js 18+。除已有一键启动脚本外，也可手动启动：

```bash
python -m pip install -r backend/requirements.txt
npm install --prefix frontend
npm run build --prefix frontend
cd backend
python main.py
```

打开 `http://localhost:8000/slm/dashboard`，点击设备卡片进入设备监测，或点击“成形监测”进入数据接入。Linux 已配置 `pytorch_env` 环境时也可运行 `./start_slm_complete.sh`。

验证案例完整性及时间对齐：

```bash
cd backend
python -m pytest tests -q
```

重建发布包仅供维护者使用，需要原始封存案例、现场数据集和逐层索引；普通使用者不需要执行。示例：

```bash
python scripts/build_portable_replays.py \
  --raw-root /path/to/7103_factory_dataset_v1 \
  --pre-root /path/to/7103 \
  --current-case /path/to/blt-s430-20240828
```
