"""
SLM设备API路由
==============
提供SLM设备的数据采集、状态查询和视频流接口
"""

import asyncio
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, List
import json
import time

from core.slm import get_slm_acquisition, reset_slm_acquisition, SLMAcquisition

router = APIRouter(prefix="/slm", tags=["SLM"])

# 获取SLM采集实例（使用slm_acquisition模块的单例）
def get_acquisition(create_if_none: bool = True, use_mock: bool = False, check_mode: bool = False) -> Optional[SLMAcquisition]:
    """获取SLM采集实例
    
    Args:
        create_if_none: 如果实例不存在，是否创建新实例
        use_mock: 是否使用模拟模式（仅在创建新实例时有效）
        check_mode: 是否检查use_mock模式匹配（默认False，避免只读操作触发重置）
    """
    acquisition = get_slm_acquisition(use_mock=use_mock, check_mode=check_mode)
    if acquisition is None and not create_if_none:
        return None
    return acquisition

def get_acquisition_status_safe() -> dict:
    """安全地获取采集状态（即使实例不存在）"""
    acquisition = get_acquisition(create_if_none=False)
    if acquisition is None:
        return {
            "is_running": False,
            "health": {
                "status": "power_off",
                "status_code": -1,
                "status_labels": [],
                "laser_system": {"status": "unknown", "message": "未检测"},
                "powder_system": {"status": "unknown", "message": "未检测"},
                "gas_system": {"status": "unknown", "message": "未检测"}
            },
            "sensor_status": {
                "camera_ch1": {"enabled": True, "connected": False},
                "camera_ch2": {"enabled": True, "connected": False},
                "thermal": {"enabled": True, "connected": False},
                "vibration": {"enabled": True, "connected": False, "com_port": ""}
            },
            "frame_number": 0,
            "statistics": {"fps": 0, "total_frames": 0, "duration": 0}
        }
    return acquisition.get_status()


@router.get("/status")
async def get_slm_status():
    """获取SLM采集系统状态"""
    return get_acquisition_status_safe()


@router.post("/start")
@router.get("/start")  # 也支持GET，方便浏览器测试
async def start_acquisition(
    camera_ch1_index: int = 2,
    camera_ch2_index: int = 3,
    vibration_com: str = "COM5",
    use_mock: bool = False
):
    """启动SLM数据采集"""
    print(f"[API] 收到启动请求: CH1={camera_ch1_index}, CH2={camera_ch2_index}, COM={vibration_com}, mock={use_mock}")
    
    # 获取当前实例
    acquisition = get_acquisition(create_if_none=False)
    
    # 如果实例已存在且正在运行，先停止
    if acquisition and acquisition.is_running:
        print("[API] 采集已在运行中，拒绝启动")
        return {"success": False, "message": "采集已在运行中"}
    
    # 如果实例存在但已停止，重置实例
    if acquisition:
        print("[API] 清理已停止的旧实例...")
        reset_slm_acquisition()
        # 等待资源完全释放
        import time
        time.sleep(1.0)
    
    # 创建新实例（支持切换模拟/真实模式）
    print("[API] 创建新采集实例...")
    acquisition = get_slm_acquisition(use_mock=use_mock)
    
    # 初始化
    print("[API] 初始化传感器...")
    success = acquisition.initialize(
        camera_ch1_index=camera_ch1_index,
        camera_ch2_index=camera_ch2_index,
        vibration_com=vibration_com,
        use_mock=use_mock
    )
    
    if not success:
        print("[API] 初始化失败")
        reset_slm_acquisition()
        return {"success": False, "message": "初始化失败，请检查硬件连接"}
    
    # 启动
    print("[API] 启动采集...")
    acquisition.start()
    
    print("[API] 采集启动成功")
    return {
        "success": True,
        "message": "采集已启动",
        "config": {
            "camera_ch1_index": camera_ch1_index,
            "camera_ch2_index": camera_ch2_index,
            "vibration_com": vibration_com,
            "use_mock": use_mock
        }
    }


@router.post("/stop")
@router.get("/stop")  # 也支持GET，方便浏览器测试
async def stop_acquisition():
    """停止SLM数据采集并释放资源"""
    acquisition = get_acquisition(create_if_none=False)
    if acquisition:
        try:
            acquisition.stop()
            print("[API] 采集已停止，资源已释放")
        except Exception as e:
            print(f"[API] 停止采集时出错: {e}")
        finally:
            # 清理全局实例，下次会重新创建
            reset_slm_acquisition()
    return {"success": True, "message": "采集已停止"}


@router.post("/sensor/{sensor_name}/enable")
async def set_sensor_enabled(sensor_name: str, enabled: bool = True):
    """设置传感器启用状态"""
    acquisition = get_acquisition()
    
    valid_sensors = ['camera_ch1', 'camera_ch2', 'vibration', 'thermal']
    if sensor_name not in valid_sensors:
        return {"success": False, "message": f"无效的传感器名称: {sensor_name}"}
    
    acquisition.set_sensor_enabled(sensor_name, enabled)
    
    return {
        "success": True,
        "message": f"{sensor_name} 已{'启用' if enabled else '禁用'}",
        "sensor": sensor_name,
        "enabled": enabled
    }


@router.post("/vibration/com_port")
async def set_vibration_com_port(port: str):
    """设置振动传感器COM口"""
    acquisition = get_acquisition()
    acquisition.set_com_port(port)
    return {
        "success": True,
        "message": f"COM口已设置为 {port}",
        "port": port
    }


@router.get("/com_ports")
async def get_available_com_ports():
    """获取可用COM口列表"""
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        port_list = [
            {
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid
            }
            for port in ports
        ]
        return {"success": True, "ports": port_list}
    except Exception as e:
        return {"success": False, "message": str(e), "ports": []}


@router.get("/cameras")
async def get_available_cameras():
    """获取可用摄像头列表 - 独立检测，不需要初始化"""
    try:
        from core.slm.camera_manager import CameraManager
        # 创建临时实例仅用于检测
        temp_manager = CameraManager(ch1_index=0, ch2_index=1)
        cameras = temp_manager.find_available_cameras()
        return {"success": True, "cameras": cameras}
    except Exception as e:
        print(f"[API] 摄像头检测错误: {e}")
        return {"success": False, "message": str(e), "cameras": []}


@router.post("/health/status")
async def update_health_status(
    status_code: int = 0,
    labels: Optional[List[str]] = None
):
    """更新设备健康状态（供模型调用或前端刷新）"""
    acquisition = get_acquisition()
    acquisition.update_health_status(status_code, labels or [])
    
    return {
        "success": True,
        "status_code": status_code,
        "labels": labels or [],
        "health": acquisition._health_state.to_dict()
    }


@router.get("/health/status")
async def get_health_status():
    """获取当前设备健康状态"""
    acquisition = get_acquisition(create_if_none=False)
    if acquisition is None:
        return {
            "success": True,
            "health": {
                "status": "power_off",
                "status_code": -1,
                "status_labels": [],
                "laser_system": {"status": "unknown", "message": "未检测"},
                "powder_system": {"status": "unknown", "message": "未检测"},
                "gas_system": {"status": "unknown", "message": "未检测"}
            },
            "is_running": False
        }
    return {
        "success": True,
        "health": acquisition._health_state.to_dict(),
        "is_running": acquisition.is_running
    }


# ========== 视频录制与诊断 ==========

@router.post("/capture/setup")
async def setup_image_capture(save_dir: str = "F:/SmartAM_recordings"):
    """设置图像采集器"""
    try:
        acquisition = get_acquisition()
        success = acquisition.setup_image_capture(save_dir)
        return {
            "success": success,
            "save_directory": str(acquisition._image_capture.save_dir) if acquisition._image_capture else save_dir
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/capture/enable")
async def enable_image_capture(enabled: bool = True):
    """启用/禁用图像采集（随采集自动启动）"""
    try:
        acquisition = get_acquisition()
        result = acquisition.set_image_capture_enabled(enabled)
        return {
            "success": result.get('success', True),
            "message": result.get('message', ''),
            "enabled": enabled,
            "is_running": acquisition.is_running
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/capture/start")
async def start_image_capture():
    """开始图像采集（手动控制）"""
    try:
        acquisition = get_acquisition()
        result = acquisition.start_image_capture()
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/capture/stop")
async def stop_image_capture():
    """停止图像采集"""
    try:
        acquisition = get_acquisition()
        result = acquisition.stop_image_capture()
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/capture/threshold")
async def set_capture_threshold(threshold: float = 0.1):
    """设置振动触发阈值"""
    try:
        acquisition = get_acquisition()
        acquisition.set_capture_threshold(threshold)
        return {
            "success": True,
            "threshold": threshold
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/capture/directory")
async def set_capture_save_directory(save_dir: str):
    """设置图像保存目录"""
    try:
        acquisition = get_acquisition()
        result = acquisition.set_capture_save_directory(save_dir)
        return result
    except Exception as e:
        return {"success": False, "message": str(e), "path": ""}


@router.get("/capture/status")
async def get_image_capture_status():
    """获取图像采集器状态"""
    try:
        acquisition = get_acquisition()
        status = acquisition.get_image_capture_status()
        return {"success": True, **status}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/capture/correction_info")
async def get_correction_info():
    """获取畸变矫正信息"""
    try:
        import sys
        from pathlib import Path
        # 添加backend到路径
        backend_path = str(Path(__file__).parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from core.slm.distortion_corrector import get_distortion_corrector
        corrector = get_distortion_corrector()
        info = corrector.get_calibration_info()
        
        return {"success": True, **info}
    except Exception as e:
        print(f"[API] 获取矫正信息失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}


@router.post("/capture/correction/enable")
async def set_correction_enabled(enabled: bool = True):
    """设置畸变矫正启用状态"""
    try:
        acquisition = get_acquisition()
        if acquisition._image_capture:
            acquisition._image_capture.set_correction_enabled(enabled)
            return {"success": True, "enabled": enabled}
        else:
            return {"success": False, "message": "图像采集器未初始化"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ========== 视频文件模拟 API ==========

from fastapi import Body
from typing import Dict

@router.post("/video_file_mode/setup")
async def setup_video_file_mode(
    video_files: Dict[str, str] = Body(...),
    enable_correction: bool = Body(True)
):
    """设置视频文件模拟模式
    
    Args:
        video_files: 视频文件路径字典，如 {'CH1': 'path/to/ch1.mp4', ...}
        enable_correction: 是否启用畸变矫正
    """
    try:
        print(f"[API] 设置视频文件模式: {video_files}, 矫正: {enable_correction}")
        
        if not video_files:
            return {"success": False, "message": "至少需要提供一个视频文件路径"}
        
        acquisition = get_acquisition()
        
        # 设置视频文件模式
        success = acquisition.set_video_file_mode(video_files, enable_correction)
        
        return {
            "success": success,
            "video_files": video_files,
            "correction_enabled": enable_correction
        }
    except Exception as e:
        print(f"[API] 设置视频文件模式失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}


@router.get("/video_file_mode/config")
async def get_video_file_mode_config():
    """获取视频文件模拟模式配置"""
    try:
        acquisition = get_acquisition()
        config = acquisition.get_video_file_mode_config()
        return {"success": True, **config}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/video_file_mode/disable")
async def disable_video_file_mode():
    """禁用视频文件模拟模式"""
    try:
        acquisition = get_acquisition()
        acquisition.disable_video_file_mode()
        return {"success": True, "message": "视频文件模式已禁用"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/video_file_mode/fps")
async def set_video_file_fps(fps: int = 30):
    """设置视频文件播放帧率
    
    Args:
        fps: 播放帧率 (1-60)，默认 30
    """
    try:
        acquisition = get_acquisition(create_if_none=False)
        if acquisition is None:
            return {"success": False, "message": "采集实例不存在，请先配置视频文件"}
        
        success = acquisition.set_video_file_fps(fps)
        if success:
            return {"success": True, "fps": fps, "message": f"播放帧率已设置为 {fps} FPS"}
        else:
            return {"success": False, "message": "设置失败，当前不是视频文件模式或采集未启动"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/video_file_mode/scan")
async def scan_video_files(folder: str = "normal"):
    """自动扫描 simulation_record 文件夹中的视频文件
    
    Args:
        folder: 子文件夹名称，默认为 "normal"
    """
    try:
        from pathlib import Path
        
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        
        # 默认扫描 normal 文件夹
        if folder:
            simulation_dir = project_root / "simulation_record" / folder
        else:
            simulation_dir = project_root / "simulation_record"
        
        print(f"[API] 扫描视频文件目录: {simulation_dir}")
        
        if not simulation_dir.exists():
            return {
                "success": False,
                "message": f"目录不存在: {simulation_dir}",
                "videos": {}
            }
        
        # 扫描视频文件
        videos = {}
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        
        for ext in video_extensions:
            for video_file in simulation_dir.glob(f"*{ext}"):
                filename = video_file.name
                # 匹配 CH1, CH2, CH3
                for ch in ['CH1', 'CH2', 'CH3']:
                    if filename.startswith(ch + "_") or filename.startswith(ch.lower() + "_") or filename.startswith(f"ch{ch[-1]}_"):
                        videos[ch] = {
                            "path": str(video_file),
                            "filename": filename
                        }
                        print(f"[API] 找到 {ch} 视频: {filename}")
                        break
        
        return {
            "success": True,
            "videos": videos,
            "directory": str(simulation_dir),
            "folder": folder
        }
    except Exception as e:
        print(f"[API] 扫描视频文件失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}


# ========== 双模式视频播放 API ==========

@router.post("/video_file_mode/preprocess")
async def preprocess_videos(
    folder: str = Body("normal"),
    fps: int = Body(10),
    force: bool = Body(False)
):
    """预处理视频文件
    
    提前应用畸变矫正和视角调整，生成优化后的视频
    后续播放时使用预处理视频，无需实时计算
    
    Args:
        folder: 场景文件夹名称 (normal, scene_underpower, scene_overpower)
        fps: 输出帧率
        force: 是否强制重新处理
    """
    try:
        from pathlib import Path
        import subprocess
        import sys
        
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "preprocess_videos.py"
        
        if not script_path.exists():
            return {
                "success": False,
                "message": f"预处理脚本不存在: {script_path}"
            }
        
        # 运行预处理脚本
        cmd = [
            sys.executable,
            str(script_path),
            folder,
            "--fps", str(fps)
        ]
        
        if force:
            cmd.append("--force")
        
        print(f"[API] 执行预处理: {' '.join(cmd)}")
        
        # 异步执行
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return {
                "success": True,
                "message": f"视频预处理完成",
                "folder": folder,
                "fps": fps,
                "output": stdout.decode('utf-8', errors='ignore')
            }
        else:
            return {
                "success": False,
                "message": f"预处理失败: {stderr.decode('utf-8', errors='ignore')}",
                "folder": folder
            }
            
    except Exception as e:
        print(f"[API] 预处理视频失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}


@router.get("/video_file_mode/preprocess/status")
async def get_preprocess_status(folder: str = "normal"):
    """获取预处理状态"""
    try:
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        processed_dir = project_root / "simulation_record" / f"{folder}_processed"
        original_dir = project_root / "simulation_record" / folder
        
        # 检查预处理文件夹
        is_processed = processed_dir.exists()
        
        # 检查各通道视频
        channels = {}
        for ch in ['CH1', 'CH2', 'CH3']:
            processed_file = processed_dir / f"{ch}_processed.mp4"
            original_files = list(original_dir.glob(f"{ch}*.mp4")) + list(original_dir.glob(f"{ch.lower()}*.mp4"))
            
            channels[ch] = {
                "processed": processed_file.exists(),
                "processed_path": str(processed_file) if processed_file.exists() else None,
                "original_exists": len(original_files) > 0,
                "original_path": str(original_files[0]) if original_files else None
            }
        
        return {
            "success": True,
            "folder": folder,
            "is_processed": is_processed,
            "processed_dir": str(processed_dir),
            "channels": channels,
            "recommendation": "preprocessed" if all(c["processed"] for c in channels.values() if c["original_exists"]) else "realtime"
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/video_file_mode/dual_mode/setup")
async def setup_dual_mode_player(
    mode: str = Body("preprocessed"),  # "preprocessed" 或 "realtime"
    folder: str = Body("normal"),
    fps: int = Body(10),
    enable_correction: bool = Body(False),
    video_files: Optional[Dict[str, str]] = Body(None)
):
    """设置双模式视频播放器
    
    模式1 - preprocessed (推荐):
        - 使用 preprocess_videos.py 生成的视频
        - 流畅播放，零实时计算
        - 适合正式演示
    
    模式2 - realtime:
        - 实时畸变矫正和视角调整
        - 可调参数，适合调试和标定
    
    Args:
        mode: 播放模式 ("preprocessed" 或 "realtime")
        folder: 场景文件夹（preprocessed模式使用）
        fps: 播放帧率
        enable_correction: 实时模式是否启用矫正
        video_files: 视频文件路径（realtime模式使用）
    """
    try:
        import sys
        from pathlib import Path
        backend_path = str(Path(__file__).parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from core.slm.dual_mode_player import init_player, get_player
        
        if mode == "preprocessed":
            # 预处理模式
            player = init_player('preprocessed', scene_name=folder, fps=fps)
        else:
            # 实时模式
            if not video_files:
                # 自动扫描
                scan_result = await scan_video_files(folder)
                video_files = {
                    ch: info["path"] 
                    for ch, info in scan_result.get("videos", {}).items()
                }
            
            player = init_player(
                'realtime',
                video_files=video_files,
                fps=fps,
                enable_correction=enable_correction
            )
        
        return {
            "success": True,
            "mode": mode,
            "folder": folder,
            "fps": fps,
            "channels": list(player.video_files.keys()) if player else []
        }
        
    except Exception as e:
        print(f"[API] 设置双模式播放器失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}


@router.get("/video_file_mode/dual_mode/status")
async def get_dual_mode_status():
    """获取双模式播放器状态"""
    try:
        import sys
        from pathlib import Path
        backend_path = str(Path(__file__).parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from core.slm.dual_mode_player import get_player
        
        player = get_player()
        
        if player is None:
            return {
                "success": True,
                "initialized": False,
                "message": "播放器未初始化"
            }
        
        return {
            "success": True,
            "initialized": True,
            "mode": player.config.mode,
            "fps": player.config.fps,
            "is_playing": player.is_playing,
            "channels": list(player.video_files.keys()),
            "enable_correction": player.config.enable_correction if player.config.mode == 'realtime' else None
        }
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/video_file_mode/dual_mode/play")
async def dual_mode_play():
    """开始播放"""
    try:
        import sys
        from pathlib import Path
        backend_path = str(Path(__file__).parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from core.slm.dual_mode_player import get_player
        
        player = get_player()
        if player is None:
            return {"success": False, "message": "播放器未初始化"}
        
        player.play()
        return {"success": True, "message": "开始播放"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/video_file_mode/dual_mode/pause")
async def dual_mode_pause():
    """暂停播放"""
    try:
        import sys
        from pathlib import Path
        backend_path = str(Path(__file__).parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from core.slm.dual_mode_player import get_player
        
        player = get_player()
        if player is None:
            return {"success": False, "message": "播放器未初始化"}
        
        player.pause()
        return {"success": True, "message": "已暂停"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/video_file_mode/dual_mode/stop")
async def dual_mode_stop():
    """停止播放"""
    try:
        import sys
        from pathlib import Path
        backend_path = str(Path(__file__).parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from core.slm.dual_mode_player import stop_player
        
        stop_player()
        return {"success": True, "message": "已停止"}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/capture/correction/set_path")
async def set_calibration_path(path: str = Body(..., embed=True)):
    """设置标定文件路径"""
    try:
        import sys
        from pathlib import Path
        # 添加backend到路径
        backend_path = str(Path(__file__).parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from core.slm.distortion_corrector import reset_corrector, get_distortion_corrector, DistortionCorrector
        
        # 验证路径是否存在
        path_obj = Path(path)
        if not path_obj.exists():
            return {"success": False, "message": f"文件不存在: {path}"}
        
        # 重置并创建新的矫正器（使用指定路径）
        reset_corrector()
        # 创建全局实例，使用指定路径
        import core.slm.distortion_corrector as dc
        dc._corrector_instance = DistortionCorrector(calibration_file=path)
        
        corrector = get_distortion_corrector()
        info = corrector.get_calibration_info()
        
        return {
            "success": True,
            "message": "标定文件路径已设置",
            **info
        }
    except Exception as e:
        print(f"[API] 设置标定文件路径失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}


@router.post("/capture/correction/reload")
async def reload_calibration():
    """重新加载标定数据"""
    try:
        import sys
        from pathlib import Path
        # 添加backend到路径
        backend_path = str(Path(__file__).parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        from core.slm.distortion_corrector import reset_corrector, get_distortion_corrector
        
        # 重置并重新加载矫正器
        reset_corrector()
        corrector = get_distortion_corrector()
        
        info = corrector.get_calibration_info()
        
        return {
            "success": True,
            "message": "标定数据已重新加载",
            **info
        }
    except Exception as e:
        print(f"[API] 重新加载标定数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}


# ========== 视频诊断 API ==========

@router.post("/diagnosis/setup")
async def setup_diagnosis_engine(model_path: str = None, frame_count: int = 50):
    """设置视频诊断引擎"""
    try:
        acquisition = get_acquisition()
        success = acquisition.setup_diagnosis_engine(model_path, frame_count)
        status = acquisition.get_diagnosis_status()
        return {
            "success": success,
            "has_model": status.get('has_model', False),
            "model_path": model_path
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/diagnosis/start")
async def start_video_diagnosis(
    ch1_video: str = None,
    ch2_video: str = None,
    ch3_video: str = None,
    mode: str = "simulation"
):
    """开始视频诊断
    
    Args:
        ch1_video: CH1视频文件路径
        ch2_video: CH2视频文件路径
        ch3_video: CH3视频文件路径
        mode: 'realtime' 或 'simulation'
    """
    try:
        acquisition = get_acquisition()
        
        video_files = {}
        if ch1_video:
            video_files['CH1'] = ch1_video
        if ch2_video:
            video_files['CH2'] = ch2_video
        if ch3_video:
            video_files['CH3'] = ch3_video
        
        if not video_files:
            return {"success": False, "message": "请至少选择一个视频文件"}
        
        success = acquisition.start_video_diagnosis(video_files, mode)
        return {
            "success": success,
            "mode": mode,
            "videos": video_files
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/diagnosis/status")
async def get_diagnosis_status():
    """获取诊断状态"""
    try:
        acquisition = get_acquisition()
        status = acquisition.get_diagnosis_status()
        return {"success": True, **status}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/diagnosis/health")
async def get_diagnosis_health():
    """获取诊断相关的健康状态（用于前端显示诊断结果）"""
    try:
        acquisition = get_acquisition()
        # 获取最新的健康状态
        packet = acquisition.get_latest_packet()
        if packet:
            return {
                "success": True,
                "health": packet.health,
                "is_diagnosis_result": True
            }
        return {
            "success": True,
            "health": acquisition._health_state.to_dict(),
            "is_diagnosis_result": False
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


# ========== WebSocket 实时数据 ==========

@router.websocket("/ws/data")
async def slm_data_websocket(websocket: WebSocket):
    """
    WebSocket实时数据推送
    推送频率: 10Hz (100ms)
    """
    await websocket.accept()
    acquisition = get_acquisition()
    
    # 注册回调
    async def send_data(data):
        try:
            # 移除大体积的二进制数据，只发送元数据
            if 'camera_ch1' in data and data['camera_ch1']:
                data['camera_ch1'].pop('jpeg_data', None)
            if 'camera_ch2' in data and data['camera_ch2']:
                data['camera_ch2'].pop('jpeg_data', None)
            if 'thermal_image' in data:
                data.pop('thermal_image')
            
            await websocket.send_json(data)
        except:
            pass
    
    acquisition.register_ws_callback(send_data)
    
    try:
        while True:
            # 接收前端消息（如传感器开关命令）
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                data = json.loads(message)
                
                # 处理命令
                if data.get('type') == 'set_sensor':
                    sensor = data.get('sensor')
                    enabled = data.get('enabled', True)
                    acquisition.set_sensor_enabled(sensor, enabled)
                    
                elif data.get('type') == 'set_com_port':
                    port = data.get('port', 'COM5')
                    acquisition.set_com_port(port)
                    
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"[WebSocket] 消息处理错误: {e}")
            
    except WebSocketDisconnect:
        print("[WebSocket] 客户端断开连接")
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
    finally:
        acquisition.unregister_ws_callback(send_data)
        try:
            await websocket.close()
        except:
            pass


# ========== 视频流接口 ==========

# 预先导入播放器模块（避免循环导入）
_video_player_imported = False
_dual_mode_player = None
_simple_video_player = None

def _ensure_video_players_imported():
    """确保视频播放器模块已导入"""
    global _video_player_imported, _dual_mode_player, _simple_video_player
    
    if not _video_player_imported:
        import sys
        from pathlib import Path
        backend_path = str(Path(__file__).parent.parent)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        
        try:
            from core.slm.dual_mode_player import get_player
            _dual_mode_player = get_player
        except ImportError:
            _dual_mode_player = None
        
        try:
            from core.slm.simple_video_player import get_video_player
            _simple_video_player = get_video_player
        except ImportError:
            _simple_video_player = None
        
        _video_player_imported = True


async def video_stream_generator(channel: str, quality: int = 85):
    """视频流生成器 - 使用采集系统的视频文件模式"""
    print(f"[VideoStream] {channel} 视频流生成器启动")
    frame_count = 0
    
    while True:
        try:
            jpeg = None
            fps = 10
            
            # 使用采集系统的 camera_manager（支持视频文件模式）
            acquisition = get_acquisition(create_if_none=False, check_mode=False)
            
            if acquisition is None or acquisition.camera_manager is None:
                await asyncio.sleep(0.5)
                continue
            
            jpeg = acquisition.camera_manager.get_frame_jpeg(channel, quality)
            
            # 发送帧
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
                await asyncio.sleep(1.0 / fps)
            else:
                await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"[VideoStream] {channel} 错误: {e}")
            await asyncio.sleep(0.1)


@router.get("/stream/camera/{channel}")
async def camera_stream(channel: str, quality: int = 85):
    """
    摄像头视频流 (MJPEG)
    channel: CH1, CH2 或 CH3
    """
    if channel not in ['CH1', 'CH2', 'CH3']:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid channel. Use 'CH1' or 'CH2'."}
        )
    
    return StreamingResponse(
        video_stream_generator(channel, quality),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


async def thermal_stream_generator(quality: int = 85):
    """热像视频流生成器（支持视频文件模式的CH3）"""
    while True:
        try:
            # 每次循环获取当前实例（可能为None）
            acquisition = get_acquisition(create_if_none=False)
            
            if acquisition is None:
                await asyncio.sleep(0.5)
                continue
            
            jpeg_bytes = None
            
            # 1. 如果是视频文件模式且有CH3视频，从VideoFileCameraManager获取
            if (hasattr(acquisition, 'camera_manager') and 
                acquisition.camera_manager is not None and
                hasattr(acquisition.camera_manager, 'get_frame_jpeg')):
                try:
                    jpeg_bytes = acquisition.camera_manager.get_frame_jpeg('CH3', quality)
                except:
                    pass
            
            # 2. 如果没有获取到帧，尝试从热像仪获取
            if jpeg_bytes is None and acquisition.thermal_camera:
                try:
                    thermal_image = acquisition.thermal_camera.generate_thermal_image(640, 480)
                    if thermal_image is not None:
                        import cv2
                        ret, jpeg = cv2.imencode('.jpg', thermal_image, [cv2.IMWRITE_JPEG_QUALITY, quality])
                        if ret:
                            jpeg_bytes = jpeg.tobytes()
                except:
                    pass
            
            # 3. 返回帧（如果有）
            if jpeg_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg_bytes)).encode() + b"\r\n"
                    b"\r\n" + jpeg_bytes + b"\r\n"
                )
            else:
                await asyncio.sleep(0.1)
                continue
            
            await asyncio.sleep(0.033)  # ~30 FPS
            
        except Exception as e:
            print(f"[ThermalStream] 错误: {e}")
            await asyncio.sleep(0.1)


@router.get("/stream/thermal")
async def thermal_stream(quality: int = 85):
    """红外热像视频流 (MJPEG)"""
    return StreamingResponse(
        thermal_stream_generator(quality),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ========== 数据查询接口 ==========

@router.get("/data/latest")
async def get_latest_data():
    """获取最新一帧数据"""
    acquisition = get_acquisition()
    packet = acquisition.get_latest_packet()
    
    if packet is None:
        return {"success": False, "message": "暂无数据"}
    
    data = packet.to_dict()
    
    # 移除大体积数据
    data.pop('thermal_image', None)
    if data.get('camera_ch1'):
        data['camera_ch1'].pop('jpeg_data', None)
    if data.get('camera_ch2'):
        data['camera_ch2'].pop('jpeg_data', None)
    
    return {"success": True, "data": data}


@router.get("/vibration/waveform")
async def get_vibration_waveform(duration: float = 10.0):
    """获取振动波形数据"""
    acquisition = get_acquisition()
    
    if acquisition.vibration_sensor:
        data = acquisition.vibration_sensor.get_history_data(duration)
        
        if not data:
            return {"success": False, "message": "暂无振动数据"}
        
        return {
            "success": True,
            "waveform": {
                'timestamps': [d.timestamp for d in data],
                'vx': [d.vx for d in data],
                'vy': [d.vy for d in data],
                'vz': [d.vz for d in data],
                'magnitude': [d.magnitude for d in data]
            },
            "sample_count": len(data)
        }
    
    return {"success": False, "message": "振动传感器未初始化"}


@router.get("/vibration/statistics")
async def get_vibration_statistics(duration: float = 5.0):
    """获取振动统计数据"""
    acquisition = get_acquisition()
    
    if acquisition.vibration_sensor:
        stats = acquisition.vibration_sensor.calculate_statistics(duration)
        return {
            "success": True,
            "statistics": stats,
            "duration": duration
        }
    
    return {"success": False, "message": "振动传感器未初始化"}


@router.get("/thermal/statistics")
async def get_thermal_statistics():
    """获取热像统计数据"""
    acquisition = get_acquisition()
    
    if acquisition.thermal_camera:
        data = acquisition.thermal_camera.get_latest_data()
        if data:
            return {
                "success": True,
                "statistics": {
                    "temp_min": data.temp_min,
                    "temp_max": data.temp_max,
                    "temp_avg": data.temp_avg,
                    "temp_center": data.temp_center,
                    "fps": data.fps
                }
            }
        return {"success": False, "message": "暂无热像数据"}
    
    return {"success": False, "message": "热像仪未初始化"}
