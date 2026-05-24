# 更新日志 (Changelog)

所有重要的变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- **SLS (选择性激光烧结) 设备支持**
  - Fotric 628CH 红外热成像仪驱动 (HTTP REST API)
  - WTVB02-485 三轴振动传感器驱动 (Modbus RTU)
  - ROBOIDE 舵机控制器 (串口通信)
  - VibrationOptimizer: 7种振动检测算法
    - composite (综合优化)
    - velocity_based (速度优先)
    - displacement_based (位移优先)
    - frequency_based (频率优先)
    - rms (均方根值)
    - peak (峰值检测)
    - energy (能量计算)
  - 铺粉动作自动检测与触发
  - SLS前端界面 (Dashboard/Analysis/Control)
  
- **SLM (选择性激光熔化) 设备支持**
  - 双通道工业相机采集 (CH1/CH2)
  - 振动触发图像采集
  - 视频诊断与回放功能
  - 实时健康状态监测
  - ROI配置与闭环调控集成
  
- **多工艺架构升级**
  - 统一的设备类型管理
  - 工艺切换面板
  - 模块化核心驱动架构 (fdm/slm/sls)

### Fixed
- 修复 Z 偏移计算逻辑
- 修复前端状态显示不同步问题
- 修复 DAQ 单例模式问题
- 修复 SLS API 路由和状态获取问题

### Changed
- 优化参数管理器逻辑
- 重构闭环控制算法
- 重构架构支持多设备类型延迟初始化

## [0.1.0] - 2026-03-03

### Added
- 初始版本发布
- FastAPI 后端框架
- Vue 3 前端界面
- IDS 相机采集支持
- Fotric 红外相机支持
- 旁轴摄像头支持
- OctoPrint 打印机集成
- CSV 数据记录
- 实时视频流 (MJPEG)
- PacNet AI 缺陷预测集成
- 9组标准塔采集模式支持
- 时空同步缓冲机制（静默区/稳定区）
- M114 坐标实时获取
- WebSocket 实时数据推送

---

## 版本说明

- **MAJOR**: 不兼容的 API 修改
- **MINOR**: 向下兼容的功能新增
- **PATCH**: 向下兼容的问题修复
