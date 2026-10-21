# SmartAM SLM System

Windows 目标电脑推荐双击根目录 **`deploy_windows.bat`**，自动检查并补齐环境、安装依赖、构建页面、配置局域网访问并启动。已有环境和未变化的构建会跳过，不依赖 Codex、VS Code 或固定名称的 Conda 环境。

跨平台手动入口为 `python start_platform.py`，首次准备环境见下文“新电脑独立部署”。

已有 `pytorch_env` 环境的电脑也可以继续使用 `start_slm_complete.bat`（Windows）或 `./start_slm_complete.sh`（Linux）。这两个旧脚本会：

- 激活 Conda 环境 `pytorch_env`
- 释放后端 `8000` 和开发前端 `5173` 端口
- 构建前端静态页面
- 启动 FastAPI 后端并统一提供页面/API
- 打开 SLM 仪表盘页面（`8000` 端口）

## Windows 一键部署（推荐）

适用 Windows 10/11 x64。将本分支完整下载或拉取到目标电脑，在解压后的项目根目录双击 `deploy_windows.bat`，不要在压缩包内直接运行。首次补齐环境和依赖需要联网；已有依赖且未更新时会跳过下载。

| 检查项 | 已满足时 | 缺失或变化时 |
| --- | --- | --- |
| Python | 复用 Python 3.10–3.13 x64 | 通过 WinGet 安装 Python 3.13 |
| 项目环境 | 验证并复用 `.venv` | 创建独立 `.venv`，不向系统 Python 安装项目依赖 |
| VC++ x64 运行库 | 根据安装记录跳过 | 通过 WinGet 安装 |
| Node.js / npm | 复用 20.19+、22.12+ 或 24+ 的兼容版本 | 通过 WinGet 安装 Node.js LTS |
| 后端依赖 | 核对 requirements 的版本约束及 `pip check` | 用 pip 补齐，再验证实际导入 |
| 前端依赖 | 核对锁文件、运行时和完整依赖树 | 使用仓库的 `package-lock.json` 执行 `npm ci` |
| 页面构建 | 输入和产物的 SHA-256 一致则跳过 | 重新构建，同源访问且不启用模拟接口 |
| 防火墙 | 本应用规则符合要求则跳过 | 请求 Windows 管理员确认，只放行专用/域网络、本地子网的 TCP 8000 |
| 服务 | 本项目已运行则直接打开页面 | 启动并等待健康检查成功后打开浏览器 |

缺少 WinGet 时，安装 Windows“应用安装程序”，或先手动安装上述运行环境再重运行；不从非官方镜像下载未知安装器。安装命令使用 [Microsoft WinGet 的精确包 ID](https://learn.microsoft.com/windows/package-manager/winget/install)。首次系统组件安装可能出现 Windows 权限确认，请允许后继续。脚本仅为本次 PowerShell 进程设置执行策略，不修改全局执行策略。

服务启动后控制台列出网卡地址，同一局域网访问 `http://<部署电脑IP>:8000/slm/dashboard`。保持窗口开启，Ctrl+C 停止。工厂可信局域网若被 Windows 标为“公用网络”，需要在 Windows 中改为“专用网络”；脚本不会自动更改网络类别。访问电脑的代理仍需让该 IP 直连。

重复双击时，安装阶段有互斥锁防止同时修改环境；本项目已运行时只打开原页面。8000 被其他服务占用则报错，不杀进程、不更换端口。更新仓库后先停止原服务，再双击脚本即可按变化补齐依赖和重建。环境损坏会明确报错，不自动删除 `.venv` 或个人文件。

部署成功状态保存在 `.deployment/`，日志在 `logs/deployment/`（保留最近 5 次）；两者不提交 Git。不要将另一台电脑的 `.venv`、`node_modules` 或 `.deployment` 一起复制过来。安装/构建失败不会写入该步骤的成功状态，解决错误后重复运行即可。

本脚本完成平台软件和仓库随附设备案例的部署。实体相机 SDK、PLC 地址和特定 GPU 驱动仍按目标硬件配置。当前已通过自动化逻辑检查和 PowerShell 解析/分支检查，目标 Windows 的安装与 UAC 流程需实机验收。

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

`feature/GJW_Contribution` 包含可直接播放的设备案例。正常 `git clone` / `git pull` 会取得全部分卷，不需要 Git LFS 或开发者电脑上的论文数据目录；可选真实处理用的权重也随仓库分发。首次打开设备时，后端校验 SHA-256 并解包到 `backend/data/replay_runtime/`；该目录是可重建的运行缓存，不提交。

| 设备入口 | 随附完整层数 | 数据内容 |
| --- | ---: | --- |
| BLT-S430 B17 | 402 | 铺粉/熔化图像、扭矩、设备参数、已封存识别与双因素溯源结果 |
| 铂力特 S430 B44 | 26 | 图像、扭矩、设备参数、报警、识别与双因素溯源 |
| 铂力特 S310 B10 | 252 | 图像、扭矩、设备参数、报警、识别与双因素溯源 |
| 铂力特 S310 B15 | 101 | 图像、扭矩、设备参数、报警、识别与双因素溯源 |
| 华科 CRPBFM130 | 815 | M130 牙冠任务的铺粉/熔化图像、识别与双因素溯源 |

设备群总览和监测页面按采集工作流显示；播放、暂停、倍速和定位层统一在对应设备的系统设置中操作。普通设备的回放设置禁用。每台案例设备使用独立的播放进度、采集通道显示选项与本地调控方案记录。

五台设备均提供数据接入、异常识别、异常溯源和闭环调控入口。案例设备不会初始化相机、PLC 或下发控制指令；闭环调控页依据当前层分析并保存独立的参数方案。

发布数据位于 `backend/replay_cases/`，合计约 406 MiB，各分卷小于 40 MiB。完整目录和分卷哈希记录在 `catalog.json`；各包内另有文件校验清单与来源记录。传感器数值、秒级时间及同秒采样顺序保留；图像是最长边 1200 像素的展示版本，原图文件名、尺寸与 SHA-256 记录在 `provenance.json`，不用于重新推理。原始采集缺口按明确分段跳过。

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

### 默认结果播放与可选真实处理

系统默认使用处理好的逐层结果。系统设置仅显示“真实模型处理”开关，首次进入为关闭状态；手动选择按设备保存，互不影响。普通设备的历史回放控制禁用。业务页面继续使用统一采集时间，识别、溯源、调控依据随当前层更新。前后跳转不会显示未来层结果，贡献曲线最多显示 50 个已到达层。

关闭开关时直接读 `backend/analysis_packages/<case>/results.json`，不创建推理器、不读取模型权重、不下载在线模型。打开时使用仓库内 `inference_models/` 权重和 `analysis_packages/` 的标准化输入，在 CPU 上实际执行网络及逐输出两区 Shapley，无需 CUDA。输入分卷与结果经过 SHA-256 校验；权重单独校验并使用 `weights_only=True` 加载。B17 默认继续使用原来封存的论文展示结果，打开开关才切换到本次集成的双输出模型。

直接跳转到后段时只重新处理当前显示窗口，正常参照使用该层封存的前序参照编号，并由当前模型复核其正常性；不会从第一层重跑整个任务。两区 Shapley 采用四种区域组合，BLT 扭矩保持该层实际输入。每个输出的贡献单位为 logit 改变量，双输出概率分别保留；识别总分取两侧概率较大值。新封存结果的处置方向由该侧概率达到 0.5 且至少一区贡献超过校准上限共同决定。

如果真实处理的依赖、权重或输入不满足条件，当前设备直接切回自己的封存结果，开关同步关闭。原因及异常堆栈仅记录在后端日志，设置页不显示原因或技术说明；README 保留这一约定。封存包损坏会明确报读取错误，不用其他案例替代。默认播放不要求实际推理可用，但平台其余原有功能仍有 PyTorch 等安装依赖，不能据此省略 `requirements.txt`。

数据与模型边界：

- BLT 使用 B17 源域训练的图像＋扭矩双输出模型，输入为实际成形区图像与两通道铺粉段扭矩。B44/B10/B15 的新增结果均由各自原始输入实际计算，不复制 B17 标签；尚未针对这三台设备重新标定或验证识别精度，不能将接入成功等同于跨设备性能已验证。
- M130 使用已归档视觉双输出权重，并按训练约定执行粉床背景颜色标准化。案例来自“11月20日-高功率翘曲／牙冠”真实图像序列；没有扭矩和环境采样，因此相关展示通道隐藏。每个播放分段是铺粉后图像至熔化后图像的时间窗口，不代表完整打印层耗时。设备照片使用提供的 `CRPBFM130.jpg`。
- 首层或尚无先前正常参照的层只给识别结果；数据到达、形成有效参照后才出现溯源。缺少数据不伪造贡献，也不填充随机小值。
- 模型输出顺序、原始权重来源和哈希在 `inference_models/registry.json`；各案例阈值、输入图像来源、参照及分卷校验在 `analysis_packages/`。展示图像与实际标准化模型输入分别保存。

### 后续采集数据的模型接口

已绑定模型的五台设备可通过 `POST /api/slm/analysis/devices/{deviceId}/layers` 提交新任务的逐层输入；OpenAPI 页面 `/docs` 可查看字段和试调用。这是采集端适配接口，当前页面播放列表仍使用仓库随附案例；新任务进入设备时间轴需要由采集端接入任务发布流程，接口不会将新任务悄悄混进旧案例。

使用 multipart：`before` 为铺粉后图像；BLT 同时提供 `after` 熔化后图像，M130 提供同尺寸 `mask`（非零为零件区）。`metadata` 为 JSON 字符串：

```json
{
  "task_id": "new-build-001", "task_name": "新成形任务",
  "layer": 1, "total_layers": 1000, "time": "2026-10-21T12:00:00+08:00",
  "roi": [260, 160, 2344, 1488],
  "torque_time": [0, 1, 2], "scraper": [2.1, 2.3, 2.2], "platform": [-12.1, -12.2, -12.0]
}
```

上述扭矩数值仅说明请求结构，不是随附案例数据。BLT 应传完整铺粉段的实际采样，时间严格递增，两通道等长，ROI 必须在原图内；M130 不传 ROI/扭矩字段。设备型号、输入模态、ROI 与训练预处理必须匹配，不承诺任意格式、任意模态的数据都适用。模型为 CPU 执行，不触发硬件指令。

新任务按设备和任务 ID 隔离保存至 `backend/data/live_analysis/`（忽略 Git），真实处理后保留标准化输入、输出、输入及模型哈希。`GET /api/slm/analysis/devices/{deviceId}/tasks/{taskId}/layers/{layer}` 直接读取已保存结果，不调用模型。相同输入重复提交返回已有结果，同层不同输入拒绝覆盖；层号与采集时间须递增。正常参照只从该任务已处理的较早层选择。新任务没有自己的封存结果时，推理失败返回 503，不能借用旧案例播放结果。

维护者重建模型和封存包（需要原始研究数据，普通部署不执行）：

```bash
python scripts/export_inference_models.py --chapters /path/to/章节代码
python scripts/build_analysis_packages.py --case b44-20250321-09-20 --raw /path/to/7103_factory_dataset_v1
python scripts/build_analysis_packages.py --case m130 --chapters /path/to/章节代码
```

BLT 另三个 case ID 为 `blt-s430-20240828`、`b10-20250509-07-47`、`b15-20250107-20-02`。重建输入会真实执行模型；各输入分卷低于 GitHub 单文件上限。
