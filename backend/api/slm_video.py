"""
SLM 视频播放 API
===============
提供统一的视频播放控制接口
"""

import asyncio
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse, JSONResponse

from core.slm import get_player_manager

router = APIRouter(prefix="/slm/video", tags=["SLM Video"])

# 预导入播放器模块
_player_manager = None

def _get_manager():
    """获取播放器管理器（延迟导入）"""
    global _player_manager
    if _player_manager is None:
        _player_manager = get_player_manager()
    return _player_manager


@router.post("/setup/preprocessed")
async def setup_preprocessed(
    folder: str = "normal",
    fps: int = 10
):
    """设置预处理模式播放器"""
    try:
        manager = _get_manager()
        success = manager.setup_preprocessed(folder, fps)
        
        if success:
            return {
                "success": True,
                "message": f"已设置预处理模式: {folder}",
                "folder": folder,
                "fps": fps
            }
        else:
            return {
                "success": False,
                "message": "设置失败，请检查视频文件是否存在"
            }
    except Exception as e:
        print(f"[VideoAPI] 设置预处理模式失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}


@router.post("/setup/realtime")
async def setup_realtime(
    video_files: dict,
    fps: int = 10,
    enable_correction: bool = False
):
    """设置实时处理模式播放器"""
    try:
        manager = _get_manager()
        success = manager.setup_realtime(video_files, fps, enable_correction)
        
        if success:
            return {
                "success": True,
                "message": "已设置实时模式",
                "fps": fps
            }
        else:
            return {
                "success": False,
                "message": "设置失败"
            }
    except Exception as e:
        print(f"[VideoAPI] 设置实时模式失败: {e}")
        return {"success": False, "message": str(e)}


@router.post("/play")
async def play():
    """开始播放"""
    try:
        manager = _get_manager()
        success = manager.play()
        
        if success:
            return {"success": True, "message": "开始播放"}
        else:
            return {"success": False, "message": "播放失败，播放器未初始化"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/pause")
async def pause():
    """暂停播放"""
    try:
        manager = _get_manager()
        success = manager.pause()
        
        if success:
            return {"success": True, "message": "已暂停"}
        else:
            return {"success": False, "message": "暂停失败"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/stop")
async def stop():
    """停止播放"""
    try:
        manager = _get_manager()
        success = manager.stop()
        
        if success:
            return {"success": True, "message": "已停止"}
        else:
            return {"success": False, "message": "停止失败"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/status")
async def get_status():
    """获取播放器状态"""
    try:
        manager = _get_manager()
        status = manager.get_status()
        return {"success": True, **status}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/stream/{channel}")
async def video_stream(channel: str, quality: int = 85):
    """
    视频流 (MJPEG)
    channel: CH1, CH2 或 CH3
    """
    if channel not in ['CH1', 'CH2', 'CH3']:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid channel. Use CH1, CH2 or CH3."}
        )
    
    return StreamingResponse(
        video_stream_generator(channel, quality),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


async def video_stream_generator(channel: str, quality: int = 85):
    """视频流生成器"""
    print(f"[VideoStream] {channel} 视频流启动")
    frame_count = 0
    
    manager = _get_manager()
    
    while True:
        try:
            # 获取帧
            jpeg = manager.get_frame_jpeg(channel, quality)
            
            if jpeg:
                frame_count += 1
                if frame_count <= 3:
                    print(f"[VideoStream] {channel} 发送第{frame_count}帧，{len(jpeg)} bytes")
                
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n"
                    b"\r\n" + jpeg + b"\r\n"
                )
                
                # 控制帧率
                status = manager.get_status()
                fps = status.get('fps', 10)
                await asyncio.sleep(1.0 / fps)
            else:
                # 如果没有帧，等待一下再试
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"[VideoStream] {channel} 错误: {e}")
            await asyncio.sleep(0.5)
