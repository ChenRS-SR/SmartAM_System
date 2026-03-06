"""
SLS控制API
"""

from fastapi import APIRouter
from pydantic import BaseModel

from core.sls import get_sls_acquisition

router = APIRouter()


class LayerRequest(BaseModel):
    layer: int


class ThresholdRequest(BaseModel):
    threshold: float


@router.post("/layer")
async def set_layer(request: LayerRequest):
    """设置当前层数"""
    try:
        sls = get_sls_acquisition()
        sls.set_layer(request.layer)
        return {"success": True, "layer": request.layer}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/threshold")
async def set_threshold(request: ThresholdRequest):
    """设置振动阈值"""
    try:
        sls = get_sls_acquisition()
        if sls.powder_detector:
            sls.powder_detector.config['motion_threshold'] = request.threshold
            return {"success": True, "threshold": request.threshold}
        return {"success": False, "error": "扑粉检测器未初始化"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/reset")
async def reset_state():
    """重置状态机"""
    try:
        sls = get_sls_acquisition()
        if sls.powder_detector:
            sls.powder_detector.reset_state()
            return {"success": True, "message": "状态机已重置"}
        return {"success": False, "error": "扑粉检测器未初始化"}
    except Exception as e:
        return {"success": False, "error": str(e)}
