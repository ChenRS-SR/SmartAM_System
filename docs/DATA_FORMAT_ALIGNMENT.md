# SmartAM_System 数据格式对齐文档

本文档说明新采集系统与 VB02_ids_websocket.py 遗留系统的数据格式对齐情况。

## CSV 格式对比

### 遗留系统 (VB02_ids_websocket.py)
- **文件名**: `print_message.csv`
- **列数**: 22列

### 新系统 (SmartAM_System)
- **文件名**: `print_message.csv` ✓
- **列数**: 22列 ✓
- **注意**: 阈值已更新 (flow_rate: [90,110], feed_rate: [80,120], z_offset: [-0.05, 0.15], hotend: [200, 230])

## CSV 列定义

| 索引 | 列名 | 说明 | 数据来源 |
|------|------|------|----------|
| 0 | `image_path` | IDS相机图像相对路径 | IDS相机采集 |
| 1 | `computer_image_path` | 旁轴相机图像相对路径 | 旁轴相机采集 |
| 2 | `timestamp` | 时间戳 | 系统生成 |
| 3 | `current_x` | 当前X坐标 | M114Coordinator |
| 4 | `current_y` | 当前Y坐标 | M114Coordinator |
| 5 | `current_z` | 当前Z坐标 | M114Coordinator |
| 6 | `flow_rate` | 流量倍率(%) | 前端配置/API |
| 7 | `feed_rate` | 进给倍率(%) | 前端配置/API |
| 8 | `z_offset` | Z偏移(mm) | 前端配置/API |
| 9 | `target_hotend` | 目标热端温度(°C) | 前端配置/API |
| 10 | `hot_end` | 实际热端温度(°C) | OctoPrint API |
| 11 | `bed` | 热床温度(°C) | OctoPrint API |
| 12 | `img_num` | 图像编号 | 自动递增 |
| 13 | `flow_rate_class` | 流量分类(0/1/2) | 自动计算 |
| 14 | `feed_rate_class` | 进给分类(0/1/2) | 自动计算 |
| 15 | `z_offset_class` | Z偏移分类(0/1/2) | 自动计算 |
| 16 | `hotend_class` | 温度分类(0/1/2) | 自动计算 |
| 17 | `fotric_temp_min` | 红外最低温度(°C) | Fotric相机 |
| 18 | `fotric_temp_max` | 红外最高温度(°C) | Fotric相机 |
| 19 | `fotric_temp_avg` | 红外平均温度(°C) | Fotric相机 |
| 20 | `fotric_image_path` | 红外伪彩色图像路径 | Fotric相机 |
| 21 | `fotric_data_path` | 红外温度矩阵路径(.npz) | Fotric相机 |

## 参数分类阈值

```python
PARAM_THRESHOLDS = {
    "flow_rate": [90, 110],     # <90: 0(Low), 90-110: 1(Normal), >110: 2(High)
    "feed_rate": [80, 120],     # <80: 0(Low), 80-120: 1(Normal), >120: 2(High)
    "z_offset": [-0.05, 0.15],  # <-0.05: 0(Low), -0.05~0.15: 1(Normal), >0.15: 2(High)
    "hotend": [200, 230]        # <200: 0(Low), 200-230: 1(Normal), >230: 2(High)
}
```

## Z偏移计算说明

新系统区分了**初始Z补偿**和**Z调节偏移**：

### 初始Z补偿 (initial_z_offset)
- **默认值**: -2.55mm
- **作用**: 打印机调平后的基准Z补偿
- **发送时机**: 只在打印开始前发送一次
- **G-code**: `M290 Z{initial_z_offset}`

### Z调节偏移 (z_offset)
- **默认值**: 0.0mm
- **作用**: 打印过程中的动态调节值
- **范围**: -0.5~0.5mm
- **显示**: 界面上显示的Z偏移是相对于初始补偿的调节值

### 实际发送的M290值
```
实际Z值 = initial_z_offset + z_offset

例如:
- 初始补偿: -2.55mm
- 调节偏移: +0.1mm
- 实际发送: M290 Z-2.45
```

### 回正参数
点击"回正参数"按钮时：
- flow_rate = 100%
- feed_rate = 100%
- z_offset = 0.0mm (保持initial_z_offset不变)
- target_hotend = 200°C

## 文件夹结构

```
task_YYYYMMDD_HHMMSS/           # 任务目录
├── images/                     # 图像目录
│   ├── IDS_Camera/             # IDS相机图像
│   │   ├── 000000.jpg
│   │   ├── 000001.jpg
│   │   └── ...
│   ├── Computer_Camera/        # 旁轴相机图像
│   │   ├── 000000.jpg
│   │   └── ...
│   ├── Fotric_Camera/          # 红外伪彩色图像
│   │   ├── 000000.jpg
│   │   └── ...
│   └── Fotric_Data/            # 红外温度矩阵
│       ├── 000000.npz
│       └── ...
├── print_message.csv           # 主数据文件 (22列)
└── task_config.json            # 任务配置信息
```

## API 配置

### 前端配置界面
- **流量比例**: 20-200%, 默认 100%
- **进给比例**: 20-200%, 默认 100%
- **Z调节偏移**: -0.5~0.5mm, 默认 0.0 (相对于初始补偿)
- **初始Z补偿**: -5~5mm, 默认 -2.55mm (打印机调平基准)
- **目标热端温度**: 150-260°C, 默认 200°C

### 采集模式

#### 1. 固定参数模式
- 手动设置参数，采集过程中保持不变

#### 2. 随机参数模式
- 从预设选项中随机生成参数组合
- flow_rate/feed_rate: 从RATE_OPTIONS中选择 [20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200]
- z_offset: 从Z_OFF_OPTIONS中选择 [-0.32,-0.28,-0.24,-0.20,-0.16,-0.08,-0.04,0,0.04,0.08,0.16,0.20,0.24,0.28,0.32]
- hotend: 150-250°C，每隔5度
- 可配置时间间隔（默认120秒）

#### 3. 9组标准塔模式
| 塔编号 | 热端温度 | Z补偿 | 描述 |
|--------|----------|-------|------|
| Tower 1 | 185°C | -0.15mm | 低温+压头，高风险易堵头 |
| Tower 2 | 185°C | 0.00mm | 低温，层间结合差 |
| Tower 3 | 185°C | +0.25mm | 低温+远离，易脱落 |
| Tower 4 | 215°C | -0.15mm | 正常温+压头，表面波浪纹 |
| Tower 5 | 215°C | 0.00mm | **黄金样本（标准态）** |
| Tower 6 | 215°C | +0.25mm | 正常温+远离，层间缝隙 |
| Tower 7 | 245°C | -0.15mm | 高温+压头，严重溢料 |
| Tower 8 | 245°C | 0.00mm | 高温，拉丝多 |
| Tower 9 | 245°C | +0.25mm | 高温+远离，结构松散 |

每塔内部按高度区间变化速度和流量：
| 高度区间(mm) | 速度(F) | 流量(E) | 描述 |
|--------------|---------|---------|------|
| 0-10 | 50% | 75% | 慢速缺料 |
| 10-20 | 50% | 100% | 慢速正常 |
| 20-30 | 50% | 125% | 慢速过挤 |
| 30-40 | 100% | 75% | 正常速缺料 |
| 40-50 | 100% | 100% | **完全标准态** |
| 50-60 | 100% | 125% | 正常速过挤 |
| 60-70 | 160% | 75% | 高速缺料 |
| 70-80 | 160% | 100% | 高速正常 |
| 80-90 | 160% | 125% | 高速过挤 |

### 时空同步缓冲

#### 静默区策略
1. **参数变化后静默**: 默认1.0mm高度范围内不采集
2. **稳定采集区**: 静默区后9.0mm高度范围正常采集(2Hz)
3. **过渡区**: 0.5mm高度范围准备进入下一段

#### 稳定判断
- 参数变化后，等待Z轴变化默认0.6mm再开始采集
- 确保物理状态（喷嘴压力、温度）稳定

### API 端点

#### 配置采集
```
POST /api/acquisition/config
Content-Type: application/json

{
  "save_directory": "./data",
  "capture_fps": 2,
  "enable_ids": true,
  "enable_side_camera": true,
  "enable_fotric": true,
  "enable_vibration": false,
  "octoprint_url": "http://127.0.0.1:5000",
  "octoprint_api_key": "...",
  "flow_rate": 100,
  "feed_rate": 100,
  "z_offset": 0.0,
  "target_hotend": 200,
  "initial_z_offset": -2.55,
  "param_mode": "tower",
  "random_interval_sec": 120,
  "current_tower": 5,
  "stability_z_diff_mm": 0.6,
  "silent_height_mm": 1.0
}
```

#### 动态更新参数 (采集中)
```
POST /api/acquisition/params
Content-Type: application/json

{
  "flow_rate": 100,
  "feed_rate": 100,
  "z_offset": 0.0,
  "target_hotend": 200
}
```

**注意**: `z_offset` 是相对于 `initial_z_offset` 的调节值。实际发送的 M290 Z值 = initial_z_offset + z_offset

## 与遗留系统对比

| 功能 | 遗留系统 | 新系统 |
|------|----------|--------|
| GUI | tkinter | Vue3 + Element Plus |
| 后端 | Flask | FastAPI |
| 坐标来源 | OctoPrint WebSocket | M114Coordinator |
| 参数设置 | 120秒定时改变 | 前端配置/API |
| 数据格式 | 22列CSV | 22列CSV ✓ |
| 图像格式 | JPG | JPG ✓ |
| 热像数据 | NPZ | NPZ ✓ |

## 测试检查清单

### 基础功能
- [ ] CSV文件包含22列
- [ ] 图像保存到正确子目录
- [ ] Fotric数据保存为NPZ格式
- [ ] 参数分类计算正确 (flow_rate:[90,110], feed_rate:[80,120], z_offset:[-0.05,0.15], hotend:[200,230])
- [ ] M114坐标获取正常
- [ ] OctoPrint温度获取正常
- [ ] 前端参数设置生效

### Z偏移功能
- [ ] 初始Z补偿配置正确 (默认-2.55mm)
- [ ] Z偏移计算正确 (actual = initial + adjustment)
- [ ] 回正参数按钮工作正常
- [ ] 参数颜色显示正确 (Low/Normal/High)

### 采集模式
- [ ] 固定参数模式工作正常
- [ ] 随机参数模式工作正常 (间隔可调)
- [ ] 9组标准塔模式工作正常
- [ ] 每塔9个高度区间参数正确

### 时空同步缓冲
- [ ] 参数变化后静默区不采集
- [ ] 稳定区正常采集 (2Hz)
- [ ] Z高度差稳定判断正确 (默认0.6mm)

## 注意事项

1. **坐标来源**: 新系统使用 M114Coordinator 获取实时坐标，比 OctoPrint WebSocket 更精确
2. **参数设置**: 新系统支持3种参数生成模式：固定、随机、9组标准塔
3. **分类计算**: flow_rate_class, feed_rate_class 基于设定的参数值，hotend_class 基于实际温度
4. **Z偏移处理**: 
   - 界面上显示的Z偏移是相对于初始补偿的调节值
   - 实际发送的M290 = initial_z_offset + z_offset
   - 初始补偿只在打印开始前发送一次
5. **阈值更新**: 
   - flow_rate: [90, 110]
   - feed_rate: [80, 120]
   - z_offset: [-0.05, 0.15]
   - hotend: [200, 230]
6. **时空同步缓冲**:
   - 参数变化后进入静默区（默认1.0mm），不采集数据
   - 静默区后是稳定采集区（9.0mm），以2Hz频率采集
   - 参数变化后需等待Z轴变化0.6mm才认为稳定
7. **9组标准塔**:
   - 每组塔有固定的温度和Z补偿
   - 每组内部按高度区间（0-90mm）变化速度和流量
   - 采集前会提示确认当前塔参数
