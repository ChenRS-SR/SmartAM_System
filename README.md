# SmartAM SLM System

推荐独立部署入口为 `python start_platform.py`，支持 Windows 和 Linux，不需要安装 Codex、VS Code，也不需要配置 IP 或固定名称的 Conda 环境。首次准备环境见下文“新电脑独立部署”。

已有 `pytorch_env` 环境的电脑也可以继续使用 `start_slm_complete.bat`（Windows）或 `./start_slm_complete.sh`（Linux）。这两个旧脚本会：

- 激活 Conda 环境 `pytorch_env`
- 释放后端 `8000` 和开发前端 `5173` 端口
- 构建前端静态页面
- 启动 FastAPI 后端并统一提供页面/API
- 打开 SLM 仪表盘页面（`8000` 端口）

## 已有 Conda 环境的启动方式

1. 确认已安装 Conda、Node.js 18+。
2. 确认 Conda 环境名为 `pytorch_env`。
3. 双击 `start_slm_complete.bat`。

访问地址：

- 系统界面：<http://localhost:8000/slm/dashboard>
- API 文档：<http://localhost:8000/docs>
- 局域网访问：`http://<SmartAM服务器IP>:8000/slm/dashboard`

后端固定监听 `0.0.0.0:8000`；同一局域网的电脑可使用服务器 IP 访问，无需修改前端配置。页面、API 和 WebSocket 默认共用地址栏中的主机与端口，兼容 VS Code 内置浏览器和端口转发；HTTPS 页面会使用 WSS。使用开发服务时访问 `http://<SmartAM服务器IP>:5173`，Vite 在服务器端代理 API 和实时连接到后端。不要把 `0.0.0.0` 当作浏览器访问地址。

默认保持 `VITE_API_BASE_URL` 未设置。仅在明确需要独立后端时设置此构建变量；该变量同时作用于 HTTP 和 WebSocket。页面入口禁用缓存，刷新会加载当前构建。

通用入口使用 Ctrl+C 停止；旧 Windows 脚本可使用：

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

### 新电脑独立部署

1. 拉取本分支，安装 Python 3.10+、Node.js 18+；Linux 需要系统的 `ip` 命令（iproute2）。
2. 在项目根目录用所选 Python 环境安装后端依赖：`python -m pip install -r backend/requirements.txt`。
3. 运行 `python start_platform.py`。

启动器使用当前 Python 环境，首次安装前端依赖，每次构建正式页面，然后在 `0.0.0.0:8000` 启动服务，并列出本机网卡访问地址。端口占用会明确报错，不终止占用端口的程序。不需要 SSH 转发或修改 `.vscode` 设置；依赖安装完成后，日常启动不需要 Codex。使用 Ctrl+C 停止。

同一局域网的其他电脑打开 `http://<部署电脑IP>:8000/slm/dashboard`。更换电脑或 IP 后不需要修改源码；页面、API、图片和 WebSocket 使用同一访问地址。多网卡电脑应选访问方可达的地址，Docker/虚拟网卡地址不一定可达。

网络条件：部署电脑的防火墙需允许局域网访问 TCP 8000；访问方的代理需对该 IP 直连。这些是操作系统/网络设置，应用无法替客户端代理配置绕过规则。`Privoxy` 错误应检查访问方代理，不需要修改平台页面。

也可以手动构建和启动：

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
