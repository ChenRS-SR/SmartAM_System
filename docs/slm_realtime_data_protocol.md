# SLM实时数据接入协议与示例

本文档用于外部采集端接入 SmartAM SLM 二级界面。外部采集端可以和 SmartAM 不在同一台设备上，只要能通过网络访问 SmartAM 后端端口，就可以按约定发送结构化 JSON。系统会完成以下工作：

- 实时参数栏按 1 秒节拍读取并显示最近事件。
- `采集时间` 使用外部事件中的 `event_time`，后台不会用服务器时间替代。
- 未接入真实数据时，真实硬件模式显示固定闭集参数，值为 `--`。
- `media.ch1` 携带当前图像或视频 URL 时，前端 CH1 主摄通道同步更新；没有图片时可直接缺省。
- 后端模型对事件进行在线诊断，并把结果显示在“SLM设备健康状态”卡片内部。

## 部署与端口

SmartAM 后端运行在监控服务器上，数据采集端只需要访问后端 HTTP 端口。采集端不要求使用 SmartAM 的 Python 环境，也不要求和后端在同一台机器。

典型拓扑：

```text
SLM设备/采集工控机
  -> HTTP POST
  -> http://<SmartAM后端服务器IP>:8000/api/slm/realtime/data
  -> SmartAM后端
  -> SmartAM前端页面读取并显示
```

后端环境名只对 SmartAM 服务器本机启动有效。本项目当前测试环境是 `pytorch_env`；如果部署到其他服务器，可以使用任意等价 Python 环境，只要依赖安装完整即可。若一键启动脚本中使用了其他环境名，以脚本和现场服务器环境为准；采集端不关心这个环境名。

服务器本机调试时可只监听本机：

```bash
cd <SmartAM_System项目目录>/backend
conda run -n pytorch_env python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

需要让另一台设备传数据时，后端必须监听局域网地址。推荐监听所有网卡：

```bash
cd <SmartAM_System项目目录>/backend
conda run -n pytorch_env python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

然后采集端使用：

```text
http://<SmartAM后端服务器IP>:8000/api
```

例如 SmartAM 后端服务器 IP 为 `192.168.1.20`：

```text
http://192.168.1.20:8000/api
```

部署检查：

- SmartAM 后端服务器防火墙需要放行 `8000` 端口。
- 采集端先访问 `GET http://<SmartAM后端服务器IP>:8000/api/slm/realtime/schema`，能返回 JSON 即表示端口连通。
- 如果现场使用反向代理或 HTTPS，只需要把接口基础路径替换为代理后的地址，例如 `https://smartam.example.com/api`。

正式界面由 SmartAM 后端 `8000` 端口统一提供。启动脚本会先构建前端页面，再由 FastAPI 服务页面和 API：

```text
http://<SmartAM后端服务器IP>:8000/slm/dashboard
```

`5173` 仅作为前端开发调试端口使用，不作为现场局域网正式入口。需要单独调试前端时可运行：

```bash
cd <SmartAM_System项目目录>/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

采集端不需要访问前端开发端口；它只需要向后端 API 端口发送数据。

本文后续命令中的接口基础路径记作：

```text
<SMARTAM_API_BASE>
```

本机调试时 `<SMARTAM_API_BASE>` 通常是 `http://127.0.0.1:8000/api`；跨设备接入时通常是 `http://<SmartAM后端服务器IP>:8000/api`。

## 接口总览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/slm/realtime/schema` | 读取参数闭集、状态码映射和模型路径 |
| POST | `/slm/realtime/data` | 推送单台设备的一次实时事件 |
| GET | `/slm/realtime/data/{device_id}` | 读取单台设备最近一次实时事件和诊断结果 |
| DELETE | `/slm/realtime/data/{device_id}` | 清空单台设备实时缓存，便于调试 |

## 最小打通流程

项目内已放好可运行示例：

- 带报警故障样例：[slm_realtime_fault_sample.json](examples/slm_realtime_fault_sample.json)
- 无报警缺字段样例：[slm_realtime_minimal_sample.json](examples/slm_realtime_minimal_sample.json)
- Python 客户端：[slm_realtime_client.py](examples/slm_realtime_client.py)

运行带报警故障样例：

```bash
cd <SmartAM_System项目目录>
python docs/examples/slm_realtime_client.py \
  --base-url <SMARTAM_API_BASE> \
  --keep
```

预期输出类似：

```text
[schema] success=True parameters=20
[post] status=3 刮刀扭矩/位置故障 frontend=1 confidence=98.0% layer=alarm_rule
[latest] hasData=True eventTime=2026-06-27 10:15:30 ch1=True
```

运行无报警、缺少大部分参数和 CH1 图像的样例：

```bash
python docs/examples/slm_realtime_client.py \
  --base-url <SMARTAM_API_BASE> \
  --sample docs/examples/slm_realtime_minimal_sample.json \
  --expect-status-label 健康
```

预期输出类似：

```text
[schema] success=True parameters=20
[post] status=0 健康 frontend=0 confidence=91.5% layer=statistical
[latest] hasData=True eventTime=2026-06-27 10:20:00 ch1=False
```

加 `--keep` 会保留后台最近事件，便于打开前端页面查看参数、诊断结果和 CH1 图像。调试结束后清空：

```bash
curl -X DELETE <SMARTAM_API_BASE>/slm/realtime/data/slm-b8
```

不加 `--keep` 时，示例脚本会自动清空该事件。

## 查询参数闭集

```bash
curl <SMARTAM_API_BASE>/slm/realtime/schema
```

返回核心字段：

```json
{
  "success": true,
  "protocolVersion": "2026-06-27",
  "parameterSchema": [
    { "id": "current_layer", "name": "当前层", "unit": "层" }
  ],
  "numericParameterIds": ["current_layer", "sequence"],
  "modelPath": "backend/models/slm_fault_diagnosis.joblib"
}
```

实时参数栏固定显示以下参数；未送入字段显示 `--`。

| id | 名称 | 单位 |
| --- | --- | --- |
| current_layer | 当前层 | 层 |
| sequence | 数据序号 |  |
| record_status | 状态参数 |  |
| data_time | 采集时间 |  |
| scraper_torque | 刮刀扭矩 | % |
| oxygen | 成形室氧含量 | % |
| ambient_oxygen | 环境氧含量 | % |
| chamber_temperature | 成形室温度 | ℃ |
| gas_flow | 循环气体流量 | m3/h |
| fan_speed | 风机转速 | % |
| medium_filter_resistance | 中效滤芯阻力 | mBar |
| high_filter_resistance | 高效滤芯阻力 | mBar |
| gas_pressure | 气源压力 | Bar |
| compressed_air_pressure | 压缩空气压力 | Bar |
| servo_temperature_x | X轴伺服温度 | ℃ |
| servo_temperature_y | Y轴伺服温度 | ℃ |
| galvo_temperature_x | X轴振镜温度 | ℃ |
| galvo_temperature_y | Y轴振镜温度 | ℃ |
| output_current_x | X轴输出电流 | mA |
| output_current_y | Y轴输出电流 | mA |

## 推送事件

`device_id` 可传 `slm-b8` 或 `B8`，后台统一归一化为 `slm-b8`。`event_time` 必须由采集端填写，建议格式为 `YYYY-MM-DD HH:mm:ss` 或 ISO8601 字符串。

```bash
curl -X POST <SMARTAM_API_BASE>/slm/realtime/data \
  -H "Content-Type: application/json" \
  --data @docs/examples/slm_realtime_fault_sample.json
```

样例 JSON：

```json
{
  "device_id": "slm-b8",
  "event_time": "2026-06-27 10:15:30",
  "sequence": 338361,
  "parameters": {
    "current_layer": 1978,
    "sequence": 338361,
    "scraper_torque": 0.12,
    "oxygen": 0.006,
    "fan_speed": 46.2,
    "servo_temperature_x": 52.7,
    "output_current_y": -11
  },
  "alarms": [
    {
      "time": "2026-06-27 10:15:30",
      "code": "SCRAPER_TORQUE",
      "message": "故障暂停，刮刀扭矩故障"
    }
  ],
  "media": {
    "ch1": {
      "media_type": "image",
      "mime_type": "image/png",
      "image_base64": "..."
    }
  }
}
```

`parameters` 也支持数组形式：

```json
[
  { "id": "oxygen", "value": 0.006 },
  { "id": "fan_speed", "value": 46.2 }
]
```

## 字段缺省规则

`alarms` 表示设备或上位机能读到的报警/故障文本。如果设备侧暂时读不到报警日志，不要伪造报警内容；直接省略 `alarms` 或传空数组 `[]`。后台会把报警文本特征视为“无报警”，诊断走统计模型层，整条实时显示链路仍正常运行。

| 字段 | 是否必填 | 缺省处理 |
| --- | --- | --- |
| `device_id` | 必填 | 缺失或空字符串返回 400 |
| `event_time` | 必填 | 缺失返回 400；后台不会用服务器时间替代采集时间 |
| `sequence` | 可选 | 缺失时仅不显示事件序号的原始值 |
| `parameters` | 可选，可只传部分闭集参数 | 缺失参数在前端固定闭集里显示 `--`；模型只使用已收到的数值，其余按训练流程的缺失值策略处理 |
| `alarms` | 可选 | 缺失、空字符串或空数组均按无报警处理；若传入，必须是字符串数组或对象数组 |
| `media.ch1` | 可选 | 缺失时本次事件没有图片或视频，返回的 `media` 可为空；参数、报警和诊断仍照常处理 |

无报警、缺少大部分参数的最小事件：

```json
{
  "device_id": "slm-b8",
  "event_time": "2026-06-27 10:20:00",
  "sequence": 990001,
  "parameters": {
    "current_layer": 120,
    "sequence": 990001,
    "oxygen": 0.012,
    "gas_flow": 438.5,
    "fan_speed": 47.1
  }
}
```

这种输入会返回完整的 `sample.parameters` 闭集；未送入的 `scraper_torque`、温度、压力、电流等值为 `--`，`diagnosis.modelLayer` 为 `statistical`，`media.ch1` 不存在。

## CH1图像或视频

图像和视频不是必填项。采集端没有相机、暂时没有图片，或只想先打通参数链路时，可以完全不传 `media` 字段：

```json
{
  "device_id": "slm-b8",
  "event_time": "2026-06-27 10:20:00",
  "parameters": {
    "oxygen": 0.012,
    "fan_speed": 47.1
  }
}
```

这种情况下后端返回的 `sample.media` 为空对象，前端不会把图片作为必需数据。

图片 data URL：

```json
{
  "media": {
    "ch1": {
      "media_type": "image",
      "data_url": "data:image/jpeg;base64,..."
    }
  }
}
```

图片 base64：

```json
{
  "media": {
    "ch1": {
      "media_type": "image",
      "mime_type": "image/png",
      "image_base64": "..."
    }
  }
}
```

视频 URL：

```json
{
  "media": {
    "ch1": {
      "media_type": "video",
      "url": "http://<视频服务器IP>:9000/live/ch1.mp4"
    }
  }
}
```

前端会根据 `media_type` 选择 `img` 或 `video` 渲染。外部如果只提供当前帧，建议每秒随参数事件更新一次图片；如果提供视频 URL，后续事件继续更新参数和诊断即可。视频 URL 必须是前端浏览器能访问到的地址，不一定和 SmartAM 后端同端口。

## 响应字段

`POST /slm/realtime/data` 返回：

```json
{
  "success": true,
  "sample": {
    "hasData": true,
    "deviceId": "slm-b8",
    "eventTime": "2026-06-27 10:15:30",
    "receivedAt": "2026-06-27T00:00:00",
    "parameters": [
      { "id": "current_layer", "name": "当前层", "value": "1978", "unit": "层" }
    ],
    "media": {
      "ch1": {
        "media_type": "image",
        "data_url": "data:image/png;base64,...",
        "url": "",
        "event_time": "2026-06-27 10:15:30"
      }
    },
    "diagnosis": {
      "statusCode": 3,
      "statusLabel": "刮刀扭矩/位置故障",
      "frontendStatusCode": 1,
      "frontendStatusLabel": "铺粉/刮刀系统异常",
      "confidence": 0.98,
      "confidenceText": "98.0%",
      "modelLayer": "alarm_rule"
    },
    "health": {
      "status": "powder_fault",
      "status_code": 1,
      "status_labels": ["刮刀扭矩/位置故障", "98.0%"]
    }
  }
}
```

关键字段含义：

| 字段 | 含义 |
| --- | --- |
| `sample.parameters` | 前端实时参数栏使用的闭集显示参数 |
| `sample.media.ch1` | CH1通道当前图片或视频；缺省时该字段不存在 |
| `diagnosis.statusCode` | 7103原始故障模式状态码 |
| `diagnosis.frontendStatusCode` | 前端健康控件使用的0-4状态码 |
| `diagnosis.confidence` | 模型置信度，0-1 |
| `diagnosis.modelLayer` | `alarm_rule` 表示报警语义规则层，`statistical` 表示统计模型层 |
| `health` | 前端“SLM设备健康状态”控件直接使用的状态 |

## 读取最近事件

```bash
curl <SMARTAM_API_BASE>/slm/realtime/data/slm-b8
```

若没有实时数据：

```json
{
  "success": true,
  "sample": {
    "hasData": false,
    "deviceId": "slm-b8",
    "parameters": [],
    "diagnosis": {
      "statusLabel": "等待实时数据",
      "confidenceText": "--"
    }
  }
}
```

前端真实硬件模式收到这个状态时，参数栏显示 `--`。

## 诊断频率

参数和 CH1 图像可以按 1 秒刷新。诊断服务内部设置了最小运行间隔：

- 有新增报警消息时立即诊断。
- 没有新增报警时，未到最小间隔会复用最近诊断结论。

这样在线诊断不会阻塞高频监测显示。

## 前端联调

1. 打开 SmartAM 前端地址，例如 `http://<SmartAM后端服务器IP>:8000/slm/dashboard`。
2. 选择 `SLM`。
3. 进入 `打印状态监测`，选择 `铂力特 S310 B8`。
4. 真实硬件模式下先清空缓存，此时实时参数应为 `--`：

```bash
curl -X DELETE <SMARTAM_API_BASE>/slm/realtime/data/slm-b8
```

5. 运行样例：

```bash
python docs/examples/slm_realtime_client.py \
  --base-url <SMARTAM_API_BASE> \
  --keep
```

6. 页面应在 1 秒左右显示：

- 采集时间来自样例 `event_time`。
- `氧含量`、`刮刀扭矩` 等参数刷新。
- CH1 主摄显示样例图片。
- 健康卡片内实时诊断显示 `刮刀扭矩/位置故障`，置信度 `98.0%`。

## 模拟模式

前端采集设置中启用“使用模拟数据”时，不读取实时接口；页面使用当前设备的 7103 基线参数，并按 1 秒节拍叠加小幅波动。模拟模式下采集时间使用浏览器当前真实时间，便于演示实时读取效果。
