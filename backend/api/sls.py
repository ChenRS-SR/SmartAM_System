"""
SLS API路由 - 选择性激光烧结
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.sls import get_sls_acquisition

router = APIRouter(prefix="/sls", tags=["SLS采集"])


class StartRequest(BaseModel):
    layer: int = 0


class StartResponse(BaseModel):
    success: bool
    message: str
    recording_dir: Optional[str] = None


# ========== 采集控制 ==========

@router.post("/start", response_model=StartResponse)
async def start_acquisition(request: StartRequest):
    """开始SLS采集"""
    try:
        sls = get_sls_acquisition()
        success = sls.start_acquisition(layer=request.layer)
        
        if success:
            return StartResponse(
                success=True,
                message=f"采集已启动，从第{request.layer}层开始",
                recording_dir=sls.recording_dir
            )
        else:
            return StartResponse(
                success=False,
                message="采集启动失败"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_acquisition():
    """停止SLS采集"""
    try:
        sls = get_sls_acquisition()
        sls.stop_acquisition()
        return {"success": True, "message": "采集已停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """获取采集状态"""
    try:
        sls = get_sls_acquisition()
        status = sls.get_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 振动传感器 ==========

@router.get("/vibration")
async def get_vibration_status():
    """获取振动传感器状态"""
    try:
        sls = get_sls_acquisition()
        return {
            'connected': sls.vibration_sensor.connected if sls.vibration_sensor else False,
            'magnitude': sls.vibration_sensor.vibration_magnitude if sls.vibration_sensor else 0,
            'data': sls.vibration_sensor.get_current_data().__dict__ if sls.vibration_sensor else None
        }
    except Exception as e:
        return {'error': str(e)}


# ========== 扑粉检测 ==========

@router.get("/powder")
async def get_powder_status():
    """获取扑粉检测状态"""
    try:
        sls = get_sls_acquisition()
        if sls.powder_detector:
            return sls.powder_detector.get_status()
        return {'error': '扑粉检测器未初始化'}
    except Exception as e:
        return {'error': str(e)}


# ========== 设备状态 ==========

@router.get("/devices")
async def get_device_status():
    """获取所有设备状态"""
    try:
        sls = get_sls_acquisition()
        
        devices = {
            'vibration': {
                'connected': sls.vibration_sensor.connected if sls.vibration_sensor else False,
                'magnitude': sls.vibration_sensor.vibration_magnitude if sls.vibration_sensor else 0
            },
            'main_camera': {
                'connected': sls.main_camera.isOpened() if sls.main_camera else False
            },
            'secondary_camera': {
                'connected': sls.secondary_camera.isOpened() if sls.secondary_camera else False
            },
            'thermal': {
                'connected': sls.thermal_camera is not None
            }
        }
        
        return devices
    except Exception as e:
        return {'error': str(e)}


# ========== 控制 ==========

@router.post("/control/layer")
async def set_layer(layer: int):
    """设置当前层数"""
    try:
        sls = get_sls_acquisition()
        sls.set_layer(layer)
        return {"success": True, "layer": layer}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/control/threshold")
async def set_threshold(threshold: float):
    """设置振动阈值"""
    try:
        sls = get_sls_acquisition()
        if sls.powder_detector:
            sls.powder_detector.config['motion_threshold'] = threshold
            return {"success": True, "threshold": threshold}
        return {"success": False, "error": "扑粉检测器未初始化"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/control/reset")
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
