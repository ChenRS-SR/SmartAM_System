"""SLM 闭环调控（参数监控 + 闭环反馈）后端模块。

把 Desktop/slm 桌面程序（「SLM 闭环调控系统 - 参数显示界面」）的界面与功能下沉为 Web 接口：
浏览器无法读取本地文件，因此这里以 FastAPI 提供：
  - read.json / feedback.json / request.json 文件通信（试验台事件、检测反馈、主动请求）
  - 试验台 HTTP API 代理（GET /api/slc/parts、POST /api/slc/fill-params、POST /api/powder/amount）
  - 体能量密度（VED）评分

挂载方式（backend/api/__init__.py）：
    from slm_control import router as slm_control_router
    router.include_router(slm_control_router)     # 得到 /api/slm/control/*
"""
from .router import router  # noqa: F401
