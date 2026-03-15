# 模拟视频场景文件夹

## 文件夹结构

```
simulation_record/
├── scenes.json              # 场景配置文件
├── README.md                # 本文件
├── scene_overpower/         # 场景1: 功率过高（可恢复）
│   ├── ch1_main.mp4        # CH1 主摄像头视频
│   ├── ch2_side.mp4        # CH2 副摄像头视频
│   └── ch3_thermal.mp4     # CH3 红外热像视频
├── scene_underpower/        # 场景2: 功率过低（可恢复）
│   ├── ch1_main.mp4
│   ├── ch2_side.mp4
│   └── ch3_thermal.mp4
└── scene_underpower_critical/  # 场景3: 功率过低（不可恢复）
    ├── ch1_main.mp4
    ├── ch2_side.mp4
    └── ch3_thermal.mp4
```

## 视频文件命名规范

| 通道 | 文件名 | 说明 |
|------|--------|------|
| CH1 主摄 | `ch1_main.mp4` | 主视角摄像头 |
| CH2 副摄 | `ch2_side.mp4` | 侧视角摄像头 |
| CH3 红外 | `ch3_thermal.mp4` | 红外热像仪 |

## 场景配置说明

### scenes.json 字段说明

```json
{
  "id": "场景唯一标识",
  "name": "场景显示名称",
  "description": "场景描述",
  "folder": "视频文件夹名",
  "videos": {
    "ch1": "CH1视频文件名",
    "ch2": "CH2视频文件名",
    "ch3": "CH3视频文件名"
  },
  "timeline": {
    "totalFrames": "总帧数",
    "framesPerLayer": "每层帧数",
    "faultFrame": "故障注入帧",
    "diagnosisFrame": "诊断帧",
    "regulationFrame": "调控执行帧"
  },
  "parameters": {
    "faultPower": "故障功率值",
    "standardPower": "标准功率值",
    "abnormalType": "异常类型",
    "reason": "异常原因",
    "recoverable": "是否可恢复",
    "recoverLayers": "恢复所需层数"
  }
}
```

## 待补充信息

请在 `scenes.json` 中更新以下实际值：

1. **总帧数** (`totalFrames`): 每个视频的实际总帧数
2. **每层帧数** (`framesPerLayer`): 每层打印对应的视频帧数
3. **关键帧位置**:
   - `faultFrame`: 注入故障的帧号
   - `diagnosisFrame`: 模型诊断出异常的帧号
   - `regulationFrame`: 执行调控的帧号

## 视频录制建议

1. **三通道同步**: 确保 CH1/CH2/CH3 视频时间对齐
2. **帧率一致**: 建议 30fps，便于计算
3. **包含完整周期**: 从正常 → 故障 → 调控 → 恢复（或失败）
4. **标记关键帧**: 可在视频中添加帧号水印，方便定位
