# 更新日志 (Changelog)

所有重要的变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 9组标准塔采集模式支持
- 时空同步缓冲机制（静默区/稳定区）
- M114 坐标实时获取
- WebSocket 实时数据推送
- PacNet AI 缺陷预测集成

### Fixed
- 修复 Z 偏移计算逻辑
- 修复前端状态显示不同步问题
- 修复 DAQ 单例模式问题

### Changed
- 优化参数管理器逻辑
- 重构闭环控制算法

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

---

## 版本说明

- **MAJOR**: 不兼容的 API 修改
- **MINOR**: 向下兼容的功能新增
- **PATCH**: 向下兼容的问题修复
