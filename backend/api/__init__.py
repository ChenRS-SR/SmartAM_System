"""
API 路由模块
============
包含所有接口路由：
- printer: 打印机控制
- camera: 相机控制
- inference: 模型推理
- control: 调控策略
- data: 数据管理
"""

from fastapi import APIRouter

# 创建主路由
router = APIRouter()

# 导入并注册子路由
from .printer import router as printer_router
from .camera import router as camera_router
from .inference import router as inference_router
from .control import router as control_router
from .data import router as data_router
from .acquisition import router as acquisition_router
from .auth import router as auth_router
from .device import router as device_router
from .system import router as system_router
from .device_type import router as device_type_router

# SLS 路由已在此分支中禁用 (feature/onlyFDMandSLM)
SLS_AVAILABLE = False

# 导入SLM路由
try:
    from .slm import router as slm_router
    SLM_AVAILABLE = True
except ImportError as e:
    SLM_AVAILABLE = False
    print(f"[API] SLM模块导入失败: {e}")

# 导入新的SLM视频路由
try:
    from .slm_video import router as slm_video_router
    SLM_VIDEO_AVAILABLE = True
except ImportError as e:
    SLM_VIDEO_AVAILABLE = False
    print(f"[API] SLM视频模块导入失败: {e}")

# 导入SLM ROI路由
try:
    from .slm_roi import router as slm_roi_router
    SLM_ROI_AVAILABLE = True
except ImportError as e:
    SLM_ROI_AVAILABLE = False
    print(f"[API] SLM ROI模块导入失败: {e}")

router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(device_type_router, tags=["设备类型"])
router.include_router(system_router, prefix="/system", tags=["系统配置"])
router.include_router(device_router, prefix="/device", tags=["设备管理"])
router.include_router(printer_router, prefix="/printer", tags=["打印机控制"])
router.include_router(camera_router, prefix="/camera", tags=["相机控制"])
router.include_router(inference_router, prefix="/inference", tags=["模型推理"])
router.include_router(control_router, prefix="/control", tags=["调控策略"])
router.include_router(data_router, prefix="/data", tags=["数据管理"])
router.include_router(acquisition_router, prefix="/acquisition", tags=["数据采集"])

# SLS 路由已禁用
# if SLS_AVAILABLE:
#     router.include_router(sls_router)
#     print("[API] SLS路由已注册: /api/sls/*")

if SLM_AVAILABLE:
    router.include_router(slm_router)
    print("[API] SLM路由已注册: /api/slm/*")

if SLM_VIDEO_AVAILABLE:
    router.include_router(slm_video_router)
    print("[API] SLM视频路由已注册: /api/slm/video/*")

if SLM_ROI_AVAILABLE:
    router.include_router(slm_roi_router)
    print("[API] SLM ROI路由已注册: /api/slm/roi/*")

# 健康检查
@router.get("/health")
async def health_check():
    """系统健康检查"""
    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "modules": ["printer", "camera", "inference", "control", "data"]
    }
