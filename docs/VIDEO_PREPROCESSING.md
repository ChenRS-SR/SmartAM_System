# SLM 视频预处理与双模式播放指南

## 概述

为了解决实时畸变矫正导致的GPU过载和播放卡顿问题，系统现在支持**视频预处理**功能：

1. **预处理模式**（推荐）：提前完成畸变矫正和视角调整，播放时零实时计算
2. **实时模式**：保留原有的实时矫正功能，适合调试和标定

## 快速开始

### 1. 预处理视频

```bash
# 进入项目目录
cd SmartAM_System

# 预处理 normal 场景（使用默认标定）
python scripts/preprocess_videos.py normal --fps 10

# 预处理其他场景
python scripts/preprocess_videos.py scene_underpower --fps 10
python scripts/preprocess_videos.py scene_overpower --fps 10

# 强制重新处理
python scripts/preprocess_videos.py normal --force
```

### 2. 启动后端

```bash
cd backend
python -m uvicorn main:app --reload
```

### 3. 前端选择模式

1. 打开调控面板
2. 点击"设置"按钮
3. 选择播放模式：
   - **预处理模式**：流畅播放，无GPU负载
   - **实时模式**：可调参数，适合调试

## 文件结构

```
SmartAM_System/
├── scripts/
│   └── preprocess_videos.py      # 预处理脚本
├── backend/
│   └── core/
│       └── slm/
│           ├── dual_mode_player.py      # 双模式播放器
│           ├── simple_video_player.py   # 简化播放器
│           └── video_preprocessor.py    # 预处理器
├── frontend/
│   └── src/
│       └── components/
│           └── slm/
│               ├── DualModeSettings.vue     # 双模式设置
│               └── RegulationControl.vue    # 调控面板
└── simulation_record/
    ├── normal/                      # 原始视频
    ├── normal_processed/            # 预处理后视频
    │   ├── CH1_processed.mp4
    │   ├── CH2_processed.mp4
    │   └── CH3_processed.mp4
    ├── scene_underpower/
    └── scene_overpower/
```

## API 接口

### 预处理视频
```http
POST /api/slm/video_file_mode/preprocess
Content-Type: application/json

{
  "folder": "normal",
  "fps": 10,
  "force": false
}
```

### 获取预处理状态
```http
GET /api/slm/video_file_mode/preprocess/status?folder=normal
```

### 设置双模式播放器
```http
POST /api/slm/video_file_mode/dual_mode/setup
Content-Type: application/json

{
  "mode": "preprocessed",  // 或 "realtime"
  "folder": "normal",
  "fps": 10,
  "enable_correction": false
}
```

### 播放控制
```http
POST /api/slm/video_file_mode/dual_mode/play
POST /api/slm/video_file_mode/dual_mode/pause
POST /api/slm/video_file_mode/dual_mode/stop
```

## 性能对比

| 模式 | GPU负载 | CPU负载 | 流畅度 | 适用场景 |
|------|---------|---------|--------|----------|
| 预处理 | 低 | 低 | ⭐⭐⭐⭐⭐ | 正式演示 |
| 实时 | 高 | 中 | ⭐⭐⭐ | 调试/标定 |

## 故障排除

### 预处理失败
1. 检查视频文件是否存在
2. 检查标定文件 `calibration_points.json` 是否存在
3. 查看预处理日志

### 播放卡顿
1. 确认已使用预处理模式
2. 降低播放帧率（如从30fps降到10fps）
3. 检查系统资源占用

### 视频不同步
- Normal场景视频已预处理对齐，无需运行时同步
- 其他场景请确保使用相同时间基准的视频

## 技术细节

### 预处理流程
1. 读取原始视频
2. 应用畸变矫正（透视变换）
3. 调整分辨率（默认640x480）
4. 重新编码保存

### 双模式播放器
- **预处理模式**：直接读取处理后的视频，无计算
- **实时模式**：每帧实时应用 `cv2.warpPerspective`

## 更新日志

- **2024-03-11**: 初始版本，支持预处理模式和实时模式
