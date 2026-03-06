"""
SLS采集API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.sls import get_sls_acquisition

router = APIRouter()


class StartRequest(BaseModel):
    layer: int = 0


class StartResponse(BaseModel):
    success: bool
    message: str
    recording_dir: Optional[str] = None


class StatusResponse(BaseModel):
    is_running: bool
    current_layer: int
    recording_dir: Optional[str]
    stats: dict
    powder_detector: Optional[dict]
    vibration: dict


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


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """获取采集状态"""
    try:
        sls = get_sls_acquisition()
        status = sls.get_status()
        return StatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
