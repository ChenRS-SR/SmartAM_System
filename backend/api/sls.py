"""
SLS设备API路由
==============
提供SLS设备的数据采集、状态查询和视频流接口
基于新的SLS采集模块（Fotric HTTP API + Vibration Modbus）
"""

import asyncio
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, List
import json
import time
import io

# 导入SLS采集模块
try:
    from core.sls import get_sls_acquisition, SLSAcquisition
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.sls import get_sls_acquisition, SLSAcquisition

router = APIRouter(prefix="/sls", tags=["SLS"])

# 全局采集实例
_acquisition_instance: Optional[SLSAcquisition] = None


def get_acquisition() -> Optional[SLSAcquisition]:
    """获取SLS采集实例"""
    global _acquisition_instance
    
    if _acquisition_instance is None:
        try:
            _acquisition_instance = get_sls_acquisition(simulation_mode=False)
        except Exception as e:
            print(f"[SLS API] 创建采集实例失败: {e}")
            return None
    
    return _acquisition_instance


def reset_acquisition():
    """重置采集实例"""
    global _acquisition_instance
    
    if _acquisition_instance:
        _acquisition_instance.cleanup()
        _acquisition_instance = None


def get_default_status() -> dict:
    """获取默认状态（设备未启动时）"""
    return {
        "is_running": False,
        "health": {
            "status": "power_off",
            "status_code": -1,
            "status_labels": [],
            "laser_system": {"status": "unknown", "message": "未检测"},
            "powder_system": {"status": "unknown", "message": "未检测"},
            "temp_system": {"status": "unknown", "message": "未检测"}
        },
        "sensor_status": {
            "thermal": {"enabled": True, "connected": False, "type": "fotric", "ip": None},
            "vibration": {"enabled": True, "connected": False, "com_port": None},
            "servo": {"enabled": True, "connected": False, "com_port": None}
        },
        "servo_status": {
            "angle": 90,
            "is_moving": False
        },
        "thermal_data": {
            "temp_min": 0,
            "temp_max": 0,
            "temp_avg": 0,
            "temp_center": 0
        },
        "vibration_data": {
            "velocity": {"x": 0, "y": 0, "z": 0},
            "displacement": {"x": 0, "y": 0, "z": 0},
            "frequency": {"x": 0, "y": 0, "z": 0},
            "magnitude": 0,
            "triggered": False
        }
    }


@router.get("/status")
async def get_sls_status():
    """获取SLS采集系统状态"""
    acquisition = get_acquisition()
    
    if acquisition is None or not acquisition.is_running:
        return get_default_status()
    
    # 获取设备状态
    device_status = acquisition.get_device_status()
    current_data = acquisition.get_current_data()
    
    return {
        "is_running": acquisition.is_running,
        "health": {
            "status": "healthy" if acquisition.health_status == 0 else "fault",
            "status_code": acquisition.health_status,
            "status_labels": get_health_labels(acquisition.health_status),
            "laser_system": {"status": "normal", "message": "正常运行"},
            "powder_system": {
                "status": "flowing" if current_data.get('system', {}).get('powder_flowing') else "idle",
                "message": "铺粉中" if current_data.get('system', {}).get('powder_flowing') else "待机"
            },
            "temp_system": {
                "status": "normal" if current_data.get('thermal', {}).get('temp_max', 0) < 400 else "warning",
                "message": f"最高温 {current_data.get('thermal', {}).get('temp_max', 0):.1f}°C"
            }
        },
        "sensor_status": {
            "thermal": {
                "enabled": True,
                "connected": device_status.get('fotric', {}).get('connected', False),
                "type": "fotric",
                "ip": device_status.get('fotric', {}).get('ip')
            },
            "vibration": {
                "enabled": True,
                "connected": device_status.get('vibration', {}).get('connected', False),
                "com_port": device_status.get('vibration', {}).get('port'),
                "algorithm": device_status.get('vibration', {}).get('algorithm', 'composite'),
                "threshold": device_status.get('vibration', {}).get('threshold', 0.1)
            },
            "servo": {
                "enabled": True,
                "connected": device_status.get('servo', {}).get('connected', False),
                "com_port": device_status.get('servo', {}).get('port')
            }
        },
        "servo_status": current_data.get('servo', {}),
        "thermal_data": current_data.get('thermal', {}),
        "vibration_data": current_data.get('vibration', {})
    }


def get_health_labels(status_code: int) -> List[str]:
    """获取健康状态标签"""
    labels = []
    if status_code == 0:
        labels.append("正常运行")
    if status_code == 1 or status_code == 4:
        labels.append("铺粉故障")
    if status_code == 2 or status_code == 4:
        labels.append("激光故障")
    if status_code == 3 or status_code == 4:
        labels.append("温度异常")
    return labels


@router.post("/start")
@router.get("/start")
async def start_acquisition(
    fotric_ip: str = "192.168.1.100",
    vibration_com: str = "COM5",
    servo_com: str = "COM6",
    vibration_threshold: float = 0.1,
    vibration_algorithm: str = "composite",
    use_mock: bool = False
):
    """启动SLS数据采集"""
    global _acquisition_instance
    
    try:
        # 如果已有实例，先清理
        if _acquisition_instance:
            _acquisition_instance.cleanup()
            _acquisition_instance = None
        
        # 创建新实例
        _acquisition_instance = get_sls_acquisition(
            fotric_ip=fotric_ip,
            vibration_port=vibration_com,
            servo_port=servo_com,
            simulation_mode=use_mock,
            force_new=True
        )
        
        # 初始化设备
        success = _acquisition_instance.initialize_devices()
        if not success:
            return {
                "success": False,
                "message": "部分设备初始化失败，请检查设备连接",
                "device_status": _acquisition_instance.get_device_status()
            }
        
        # 设置振动参数
        _acquisition_instance.set_vibration_threshold(vibration_threshold)
        _acquisition_instance.set_vibration_algorithm(vibration_algorithm)
        
        # 启动采集
        if _acquisition_instance.start_acquisition():
            return {
                "success": True,
                "message": "SLS采集已启动",
                "config": {
                    "fotric_ip": fotric_ip,
                    "vibration_com": vibration_com,
                    "servo_com": servo_com,
                    "vibration_threshold": vibration_threshold,
                    "vibration_algorithm": vibration_algorithm,
                    "use_mock": use_mock
                },
                "device_status": _acquisition_instance.get_device_status()
            }
        else:
            return {
                "success": False,
                "message": "启动采集失败，没有可用设备"
            }
            
    except Exception as e:
        print(f"[SLS API] 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"启动失败: {str(e)}"}


@router.post("/stop")
@router.get("/stop")
async def stop_acquisition():
    """停止SLS数据采集"""
    try:
        reset_acquisition()
        return {"success": True, "message": "SLS采集已停止"}
    except Exception as e:
        return {"success": False, "message": f"停止失败: {str(e)}"}


@router.post("/vibration/threshold")
async def set_vibration_threshold(threshold: float):
    """设置振动触发阈值"""
    try:
        acquisition = get_acquisition()
        if acquisition:
            acquisition.set_vibration_threshold(threshold)
        return {
            "success": True,
            "message": f"振动阈值已设置为 {threshold}",
            "threshold": threshold
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/vibration/algorithm")
async def set_vibration_algorithm(algorithm: str):
    """设置振动检测算法"""
    valid_algorithms = ["composite", "velocity_based", "displacement_based", 
                       "frequency_based", "rms", "peak", "energy"]
    
    if algorithm not in valid_algorithms:
        return {
            "success": False,
            "message": f"无效算法: {algorithm}",
            "valid_algorithms": valid_algorithms
        }
    
    try:
        acquisition = get_acquisition()
        if acquisition:
            success = acquisition.set_vibration_algorithm(algorithm)
            if success:
                return {
                    "success": True,
                    "message": f"振动算法已设置为 {algorithm}",
                    "algorithm": algorithm
                }
            else:
                return {"success": False, "message": "设置算法失败"}
        else:
            return {"success": False, "message": "采集实例不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/vibration/sensitivity")
async def set_vibration_sensitivity(level: int):
    """设置振动灵敏度 (1-5)"""
    try:
        acquisition = get_acquisition()
        if acquisition:
            acquisition.set_vibration_sensitivity(level)
        return {
            "success": True,
            "message": f"振动灵敏度已设置为 {level}",
            "level": level
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/vibration/calibrate")
async def calibrate_vibration(duration: float = 5.0):
    """校准振动传感器"""
    try:
        acquisition = get_acquisition()
        if acquisition:
            success = acquisition.calibrate_vibration(duration)
            if success:
                return {
                    "success": True,
                    "message": f"振动传感器校准完成 ({duration}s)"
                }
            else:
                return {"success": False, "message": "校准失败"}
        else:
            return {"success": False, "message": "采集实例不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/vibration/reset_peak")
async def reset_vibration_peak():
    """重置振动峰值"""
    try:
        acquisition = get_acquisition()
        if acquisition:
            acquisition.reset_vibration_peak()
        return {"success": True, "message": "振动峰值已重置"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/vibration/statistics")
async def get_vibration_statistics():
    """获取振动统计信息"""
    try:
        acquisition = get_acquisition()
        if acquisition:
            stats = acquisition.get_vibration_statistics()
            return {"success": True, "statistics": stats}
        else:
            return {"success": False, "message": "采集实例不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/vibration/waveform")
async def get_vibration_waveform(limit: int = 100):
    """获取振动波形数据"""
    try:
        acquisition = get_acquisition()
        if acquisition:
            waveform = acquisition.get_waveform_data(limit)
            return {"success": True, "waveform": waveform}
        else:
            return {"success": False, "message": "采集实例不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/servo/move")
async def move_servo(angle: int = 90, speed: int = 50):
    """控制舵机移动到指定角度"""
    try:
        acquisition = get_acquisition()
        if acquisition is None:
            return {"success": False, "message": "采集实例不存在"}
        
        if acquisition.servo and acquisition.device_status.get('servo'):
            success = acquisition.servo.set_angle(angle, speed)
            return {
                "success": success,
                "message": f"舵机移动到 {angle}°" if success else "舵机控制失败",
                "angle": angle,
                "speed": speed
            }
        else:
            return {"success": False, "message": "舵机未连接"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.post("/servo/sweep")
async def sweep_servo(
    start_angle: int = 0,
    end_angle: int = 180,
    step: int = 10,
    delay: float = 0.5
):
    """控制舵机扫描"""
    try:
        acquisition = get_acquisition()
        if acquisition is None:
            return {"success": False, "message": "采集实例不存在"}
        
        if acquisition.servo and acquisition.device_status.get('servo'):
            # 在后台执行扫描
            import threading
            def do_sweep():
                acquisition.servo.sweep(start_angle, end_angle, step, delay)
            
            thread = threading.Thread(target=do_sweep, daemon=True)
            thread.start()
            
            return {
                "success": True,
                "message": f"舵机扫描已启动 ({start_angle}°-{end_angle}°)",
                "start_angle": start_angle,
                "end_angle": end_angle,
                "step": step
            }
        else:
            return {"success": False, "message": "舵机未连接"}
    except Exception as e:
        return {"success": False, "message": str(e)}


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


@router.get("/data/current")
async def get_current_data():
    """获取当前数据"""
    try:
        acquisition = get_acquisition()
        if acquisition:
            return {"success": True, "data": acquisition.get_current_data()}
        else:
            return {"success": False, "message": "采集实例不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/data/history")
async def get_data_history(count: int = 100):
    """获取历史数据"""
    try:
        acquisition = get_acquisition()
        if acquisition:
            return {"success": True, "history": acquisition.get_data_history(count)}
        else:
            return {"success": False, "message": "采集实例不存在"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ========== 视频流 ==========

def generate_frame_stream(get_frame_func):
    """生成视频流"""
    while True:
        try:
            frame = get_frame_func()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.1)
        except Exception as e:
            print(f"[SLS Stream] 错误: {e}")
            time.sleep(0.5)


@router.get("/stream/thermal")
async def stream_thermal():
    """红外热像视频流"""
    def get_frame():
        acquisition = get_acquisition()
        if acquisition:
            return acquisition.get_thermal_frame()
        return None
    
    return StreamingResponse(
        generate_frame_stream(get_frame),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )


# ========== WebSocket ==========

@router.websocket("/ws/data")
async def sls_data_websocket(websocket: WebSocket):
    """WebSocket实时数据推送"""
    await websocket.accept()
    
    acquisition = get_acquisition()
    
    # 数据推送任务
    async def data_pusher():
        while True:
            try:
                if acquisition and acquisition.is_running:
                    data = acquisition.get_current_data()
                    await websocket.send_json({
                        "type": "data",
                        "timestamp": time.time(),
                        "data": data
                    })
                else:
                    await websocket.send_json({
                        "type": "status",
                        "is_running": False,
                        "message": "采集未运行"
                    })
                await asyncio.sleep(0.1)  # 10Hz
            except Exception as e:
                print(f"[SLS WebSocket] 推送错误: {e}")
                break
    
    # 启动推送任务
    pusher_task = asyncio.create_task(data_pusher())
    
    try:
        while True:
            # 接收前端命令
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                data = json.loads(message)
                
                cmd_type = data.get('type')
                
                if cmd_type == 'servo_move':
                    angle = data.get('angle', 90)
                    speed = data.get('speed', 50)
                    if acquisition and acquisition.servo:
                        acquisition.servo.set_angle(angle, speed)
                
                elif cmd_type == 'servo_sweep':
                    start = data.get('start', 0)
                    end = data.get('end', 180)
                    step = data.get('step', 10)
                    if acquisition and acquisition.servo:
                        import threading
                        threading.Thread(
                            target=acquisition.servo.sweep,
                            args=(start, end, step, 0.5),
                            daemon=True
                        ).start()
                
                elif cmd_type == 'set_threshold':
                    threshold = data.get('threshold', 0.1)
                    if acquisition:
                        acquisition.set_vibration_threshold(threshold)
                
                elif cmd_type == 'set_algorithm':
                    algorithm = data.get('algorithm', 'composite')
                    if acquisition:
                        acquisition.set_vibration_algorithm(algorithm)
                
                elif cmd_type == 'calibrate':
                    duration = data.get('duration', 5.0)
                    if acquisition:
                        acquisition.calibrate_vibration(duration)
                
                elif cmd_type == 'reset_peak':
                    if acquisition:
                        acquisition.reset_vibration_peak()
                        
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"[SLS WebSocket] 处理消息错误: {e}")
                
    except WebSocketDisconnect:
        print("[SLS WebSocket] 客户端断开连接")
    except Exception as e:
        print(f"[SLS WebSocket] 错误: {e}")
    finally:
        pusher_task.cancel()
        try:
            await pusher_task
        except asyncio.CancelledError:
            pass
