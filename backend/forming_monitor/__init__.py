"""成形监测（增材制造异常识别系统 v1.0）后端模块。

集成到 SmartAM：把本包复制到 SmartAM_System/backend/forming_monitor/，在 backend/api/__init__.py 中
    from forming_monitor import router as forming_router
    router.include_router(forming_router)          # 得到 /api/slm/forming/*
详见 ../../集成说明.md。
"""
from .router import router  # noqa: F401
