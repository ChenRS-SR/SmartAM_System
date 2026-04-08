"""
设备管理 API
============
提供手动连接/断开设备的功能
"""

import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

router = APIRouter()


def _get_daq():
    """获取 DAQ 实例（从设备管理器动态获取）"""
    try:
        from core.device_manager import get_device_manager
        manager = get_device_manager()
        # 如果当前是 FDM 模式，返回 FDM acquisition
        if manager.current_type.value == "fdm":
            return manager.fdm_acquisition
    except Exception as e:
        print(f"[API] 获取 DAQ 失败: {e}")
    return None


class DeviceConnectRequest(BaseModel):
    """设备连接请求"""
    device_type: str  # ids, side_camera, fotric, vibration, m114


class DeviceStatusResponse(BaseModel):
    """设备状态响应"""
    ids: bool
    side_camera: bool
    fotric: bool
    vibration: bool
    m114: bool


@router.get("/status")
async def get_device_status():
    """获取所有设备的连接状态"""
    daq = _get_daq()
    
    if not daq:
        return {
            "available": False,
            "message": "DAQ 系统未初始化",
            "devices": {}
        }
    
    status = daq.get_device_status()
    
    return {
        "available": True,
        "message": "设备状态查询成功",
        "devices": status
    }


@router.post("/connect")
async def connect_device(req: DeviceConnectRequest):
    """手动连接指定设备"""
    daq = _get_daq()
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    valid_devices = ['ids', 'side_camera', 'fotric', 'vibration', 'm114']
    
    if req.device_type not in valid_devices:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的设备类型: {req.device_type}. 有效类型: {', '.join(valid_devices)}"
        )
    
    success = daq.connect_device(req.device_type)
    
    if success:
        return {
            "message": f"设备 {req.device_type} 连接成功",
            "device": req.device_type,
            "connected": True
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"设备 {req.device_type} 连接失败，请检查硬件连接"
        )


@router.post("/connect-all")
async def connect_all_devices():
    """连接所有可用设备"""
    daq = _get_daq()
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    results = daq.initialize_devices()
    
    connected_count = sum(1 for v in results.values() if v)
    
    return {
        "message": f"设备连接完成，成功 {connected_count}/{len(results)} 个",
        "results": results
    }


@router.post("/disconnect-all")
async def disconnect_all_devices():
    """断开所有设备连接"""
    daq = _get_daq()
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    results = daq.disconnect_all_devices()
    
    disconnected_count = sum(1 for v in results.values() if v)
    
    return {
        "message": f"设备断开完成，成功 {disconnected_count}/{len(results)} 个",
        "results": results
    }


@router.post("/start-acquisition")
async def start_data_acquisition():
    """启动数据采集"""
    daq = _get_daq()
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    # 检查是否有设备连接
    status = daq.get_device_status()
    if not any(status.values()):
        raise HTTPException(
            status_code=400, 
            detail="没有可用的设备，请先连接设备"
        )
    
    success = daq.start()
    
    if success:
        return {
            "message": "数据采集已启动",
            "status": "running"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="数据采集启动失败"
        )


@router.post("/stop-acquisition")
async def stop_data_acquisition():
    """停止数据采集"""
    daq = _get_daq()
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    success = daq.stop()
    
    return {
        "message": "数据采集已停止" if success else "数据采集未在运行",
        "status": "stopped" if success else "idle"
    }
