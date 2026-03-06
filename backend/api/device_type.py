"""
设备类型管理 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.device_manager import get_device_manager

router = APIRouter(prefix="/device-type", tags=["设备类型"])


class DeviceTypeRequest(BaseModel):
    device_type: str  # 'fdm', 'sls', 'slm'


class DeviceTypeResponse(BaseModel):
    success: bool
    message: str
    current_type: Optional[str] = None
    status: Optional[dict] = None


@router.post("/select", response_model=DeviceTypeResponse)
async def select_device_type(request: DeviceTypeRequest):
    """
    选择设备类型并初始化对应驱动
    
    - fdm: 熔融沉积成型（IDS相机、Fotric、OctoPrint）
    - sls: 选择性激光烧结（振动传感器、双摄像头、Fotric）
    - slm: 选择性激光熔化（待实现）
    """
    import traceback
    
    try:
        manager = get_device_manager()
        success = manager.set_device_type(request.device_type)
        
        if success:
            return DeviceTypeResponse(
                success=True,
                message=f"已切换到 {request.device_type.upper()} 模式",
                current_type=request.device_type,
                status=manager.get_status()
            )
        else:
            return DeviceTypeResponse(
                success=False,
                message=f"切换到 {request.device_type} 失败，请检查设备连接",
                current_type=manager.current_type.value
            )
    except Exception as e:
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        logging.error(f"[DeviceType API] 选择设备类型失败: {error_detail}")
        # 返回 200 但标记为失败，避免前端显示网络错误
        return DeviceTypeResponse(
            success=False,
            message=f"设备初始化失败: {str(e)}",
            current_type="none"
        )


@router.get("/current", response_model=DeviceTypeResponse)
async def get_current_device_type():
    """获取当前设备类型和状态"""
    try:
        manager = get_device_manager()
        return DeviceTypeResponse(
            success=True,
            message="获取成功",
            current_type=manager.current_type.value,
            status=manager.get_status()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_current_device():
    """停止当前设备"""
    try:
        manager = get_device_manager()
        manager.stop_current_device()
        return {
            "success": True,
            "message": "设备已停止",
            "current_type": manager.current_type.value
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
