# 闭环控制与SLM设备健康状态集成

## 功能说明

将闭环调控系统的诊断结果同步到SLM设备健康状态，实现：
- 诊断激光功率异常 → 返回状态码 2
- 诊断正常 → 返回状态码 0

## 状态码定义

| 状态码 | 含义 | 说明 |
|--------|------|------|
| -1 | 未开机 | 设备未启动 |
| 0 | 健康 | 所有系统正常 |
| 1 | 刮刀磨损 | 铺粉系统异常 |
| 2 | 激光功率异常 | 激光系统异常 |
| 3 | 保护气体异常 | 气体系统异常 |
| 4 | 复合故障 | 多系统异常 |

## 快速使用

### 方式1：自动桥接（推荐）

```python
from core.closed_loop_controller import ClosedLoopController, create_default_config
from core.slm.slm_acquisition import get_slm_acquisition
from core.slm.closed_loop_integration import setup_closed_loop_to_slm_health_bridge

# 1. 创建实例
slm_acquisition = get_slm_acquisition(use_mock=True)
config = create_default_config()
controller = ClosedLoopController(config)

# 2. 建立桥接（自动同步诊断结果到健康状态）
integration = setup_closed_loop_to_slm_health_bridge(controller, slm_acquisition)

# 3. 处理预测结果（自动更新健康状态）
from core.closed_loop_controller import ParameterType, ParameterState

predictions = {
    ParameterType.HOTEND_TEMP: (ParameterState.LOW, 0.8),  # 激光异常
}
controller.process_prediction(predictions)
# 健康状态会自动更新为：状态码 2（激光功率异常）
```

### 方式2：直接更新

```python
from core.slm.closed_loop_integration import update_slm_health_from_diagnosis

# 直接根据诊断结果更新SLM健康状态
update_slm_health_from_diagnosis(
    slm_acquisition,
    is_laser_fault=True,    # 激光异常
    is_powder_fault=False,  # 铺粉正常
    is_gas_fault=False,     # 气体正常
    confidence=0.85         # 置信度
)
# 健康状态会更新为：状态码 2（激光功率异常）
```

### 方式3：API接口

前端可以通过API获取当前健康状态：

```javascript
// 获取健康状态
fetch('/slm/health/status')
  .then(res => res.json())
  .then(data => {
    console.log('状态码:', data.health.status_code);
    console.log('状态:', data.health.status);
    console.log('标签:', data.health.status_labels);
  });
```

## 闭环控制器诊断逻辑

目前闭环系统主要诊断激光相关参数：

```python
# 在 closed_loop_controller.py 中

# 激光相关参数（目前只诊断这些）
laser_related_params = [
    ParameterType.HOTEND_TEMP,  # 热端温度与激光功率相关
]

# 诊断逻辑
for param in laser_related_params:
    if param in predictions:
        state, confidence = predictions[param]
        if state != ParameterState.NORMAL and confidence >= threshold:
            # 激光异常 -> 状态码 2
            status_code = 2
```

## 扩展诊断参数

如果需要诊断更多参数，可以修改 `closed_loop_controller.py`：

```python
# 在 _update_diagnosis_status 方法中

laser_related_params = [
    ParameterType.HOTEND_TEMP,
    # 添加更多激光相关参数
    ParameterType.LASER_POWER,  # 如果有这个参数
]

# 或者添加其他类型的诊断
powder_related_params = [
    ParameterType.FLOW_RATE,
    ParameterType.FEED_RATE,
]
```

## 运行示例

```bash
cd SmartAM_System/backend

# 运行集成示例
python examples/closed_loop_health_integration_example.py
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `core/closed_loop_controller.py` | 闭环控制器（已添加诊断状态功能） |
| `core/slm/closed_loop_integration.py` | 集成模块（新建） |
| `examples/closed_loop_health_integration_example.py` | 使用示例 |

## 注意事项

1. 目前闭环系统只诊断激光相关参数，其他参数（铺粉、气体）需要通过视频诊断引擎或其他方式诊断
2. 状态码 2 表示激光功率异常，包括功率过低（LOW）和过高（HIGH）两种情况
3. 诊断结果会实时同步到前端，通过 WebSocket 或 API 获取
