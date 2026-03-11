# 视频文件模拟模式修复总结

## 问题描述
SLM Dashboard 的视频文件模拟模式无法正常工作，CH1/CH2/CH3 视频容器显示"未连接"。

## 根本原因分析

### 1. 静态文件服务 404 错误
**原因**: Windows 下 `__file__` 路径解析不正确  
**修复**: 使用 `os.path.abspath(__file__)` 确保路径正确

### 2. 视频文件配置未正确应用
**原因**: `_apply_global_video_file_config()` 只在 `initialize()` 中调用，但 `initialize()` 只在 `start()` 中调用，而实例创建时（`__init__`）没有应用全局配置  
**修复**: 在 `SLMAcquisition.__init__()` 末尾添加 `self._apply_global_video_file_config()`

### 3. 实例重置问题
**原因**: `get_acquisition()` 默认 `check_mode=True`，导致只读操作（如获取状态）触发 `use_mock` 模式检查，不匹配时重置实例  
**修复**: 
- 将 `get_acquisition()` 的默认 `check_mode` 改为 `False`
- 这防止了状态查询等只读操作意外重置实例

### 4. 视频流通道限制
**原因**: `/stream/camera/{channel}` 只接受 CH1 和 CH2，但视频文件模式有 CH3  
**修复**: 将验证改为接受 `['CH1', 'CH2', 'CH3']`

## 修改的文件

### backend/main.py
- 改进项目根目录计算逻辑
- 添加静态文件挂载调试输出

### backend/core/slm/slm_acquisition.py
- 在 `__init__` 中添加全局视频文件配置应用
```python
# 在 __init__ 末尾
self._apply_global_video_file_config()
```

### backend/api/slm.py
- 修改 `get_acquisition()` 默认参数：`check_mode=True` → `check_mode=False`
- 修改 `camera_stream()` 通道验证：`['CH1', 'CH2']` → `['CH1', 'CH2', 'CH3']`

## 测试验证

### 1. 静态文件服务
```
/public/test.html: 200 OK
/video-test: 200 OK
```

### 2. 视频文件模式配置
```
POST /api/slm/video_file_mode/setup: success
GET /api/slm/video_file_mode/config: enabled=true
```

### 3. 采集启动
```
POST /api/slm/start?use_mock=true: success
GET /api/slm/status: is_running=true, fps=~8
```

### 4. 视频流
```
GET /api/slm/stream/camera/CH1: JPEG stream OK
GET /api/slm/stream/camera/CH2: JPEG stream OK
GET /api/slm/stream/camera/CH3: JPEG stream OK
```

## 使用说明

1. 确保视频文件存在于 `simulation_record/` 目录
2. 访问前端设置页面配置视频文件路径
3. 或使用 API 直接配置：
```bash
curl -X POST http://localhost:8000/api/slm/video_file_mode/setup \
  -H "Content-Type: application/json" \
  -d '{"video_files":{"CH1":"path/to/ch1.mp4",...},"enable_correction":false}'
```
4. 启动采集：`POST /api/slm/start?use_mock=true`
5. 打开 Dashboard 查看视频流
