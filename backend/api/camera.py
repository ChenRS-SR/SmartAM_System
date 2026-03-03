"""
相机控制 API
============
提供相机相关的接口：
- 获取相机状态
- 拍照
- 切换视频源
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


class CameraStatus(BaseModel):
    """相机状态模型"""
    ids_available: bool
    ids_frame_count: int
    side_available: bool
    side_frame_count: int
    thermal_available: bool


class CameraSnapshotResponse(BaseModel):
    """拍照响应"""
    success: bool
    message: str
    file_path: Optional[str] = None


@router.get("/status", response_model=CameraStatus)
async def get_camera_status():
    """获取相机状态"""
    from main import daq
    
    if daq:
        status = daq.get_camera_status()
        # 检查 thermal 状态
        thermal_available = False
        if hasattr(daq, '_fotric_device') and daq._fotric_device:
            thermal_available = getattr(daq._fotric_device, 'is_connected', False)
        
        return CameraStatus(
            ids_available=status["ids"]["available"],
            ids_frame_count=status["ids"]["frame_count"],
            side_available=status["side"]["available"],
            side_frame_count=status["side"]["frame_count"],
            thermal_available=thermal_available
        )
    
    return CameraStatus(
        ids_available=False,
        ids_frame_count=0,
        side_available=False,
        side_frame_count=0,
        thermal_available=False
    )


@router.post("/snapshot/ids", response_model=CameraSnapshotResponse)
async def snapshot_ids():
    """IDS 相机拍照"""
    from main import daq
    import cv2
    import os
    from datetime import datetime
    
    if not daq or not daq._ids_camera:
        raise HTTPException(status_code=503, detail="IDS 相机不可用")
    
    frame = daq._get_ids_frame()
    if frame is None:
        raise HTTPException(status_code=500, detail="无法获取图像")
    
    # 保存图片到 snapshots 目录
    save_dir = "./snapshots"
    os.makedirs(save_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ids_snapshot_{timestamp}.jpg"
    filepath = os.path.join(save_dir, filename)
    
    # 保存图片
    success = cv2.imwrite(filepath, frame)
    if not success:
        raise HTTPException(status_code=500, detail="保存图片失败")
    
    return CameraSnapshotResponse(
        success=True,
        message="拍照成功",
        file_path=filepath
    )


@router.post("/snapshot/side", response_model=CameraSnapshotResponse)
async def snapshot_side():
    """旁轴摄像头拍照"""
    from main import daq
    import cv2
    import os
    from datetime import datetime
    
    if not daq or not daq._side_camera:
        raise HTTPException(status_code=503, detail="旁轴摄像头不可用")
    
    # 获取旁轴相机帧
    frame = None
    if hasattr(daq._side_camera, 'get_frame'):
        frame = daq._side_camera.get_frame()
    else:
        ret, frame = daq._side_camera.read()
    if frame is None:
        raise HTTPException(status_code=500, detail="无法获取图像")
    
    # 保存图片到 snapshots 目录
    save_dir = "./snapshots"
    os.makedirs(save_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"side_snapshot_{timestamp}.jpg"
    filepath = os.path.join(save_dir, filename)
    
    # 保存图片
    success = cv2.imwrite(filepath, frame)
    if not success:
        raise HTTPException(status_code=500, detail="保存图片失败")
    
    return CameraSnapshotResponse(
        success=True,
        message="拍照成功",
        file_path=filepath
    )


@router.get("/streams")
async def list_streams():
    """列出可用视频流"""
    return {
        "streams": [
            {"id": "combined", "name": "组合画面", "url": "/video_feed"},
            {"id": "ids", "name": "IDS 相机（随轴）", "url": "/video_feed/ids"},
            {"id": "side", "name": "旁轴摄像头", "url": "/video_feed/side"}
        ]
    }
