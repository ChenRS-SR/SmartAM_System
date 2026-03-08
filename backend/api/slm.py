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

from core.slm import get_slm_acquisition, SLMAcquisition

router = APIRouter(prefix="/slm", tags=["SLM"])

# 全局SLM采集实例
_slm_instance: Optional[SLMAcquisition] = None

# 获取SLM采集实例
def get_acquisition() -> SLMAcquisition:
    global _slm_instance
    if _slm_instance is None:
        _slm_instance = SLMAcquisition(use_mock=False)
    return _slm_instance


@router.get("/status")
async def get_slm_status():
    """获取SLM采集系统状态"""
    acquisition = get_acquisition()
    return acquisition.get_status()


@router.post("/start")
@router.get("/start")  # 也支持GET，方便浏览器测试
async def start_acquisition(
    camera_ch1_index: int = 2,
    camera_ch2_index: int = 3,
    vibration_com: str = "COM5",
    use_mock: bool = False
):
    """启动SLM数据采集"""
    global _slm_instance
    
    print(f"[API] 收到启动请求: CH1={camera_ch1_index}, CH2={camera_ch2_index}, COM={vibration_com}, mock={use_mock}")
    
    # 如果实例已存在且正在运行，先停止
    if _slm_instance and _slm_instance.is_running:
        print("[API] 采集已在运行中，拒绝启动")
        return {"success": False, "message": "采集已在运行中"}
    
    # 如果实例存在但已停止，先清理
    if _slm_instance:
        print("[API] 清理已停止的旧实例...")
        try:
            _slm_instance.stop()
        except:
            pass
        _slm_instance = None
        # 等待资源完全释放
        import time
        time.sleep(1.0)
    
    # 创建新实例（支持切换模拟/真实模式）
    print("[API] 创建新采集实例...")
    _slm_instance = SLMAcquisition(use_mock=use_mock)
    
    # 初始化
    print("[API] 初始化传感器...")
    success = _slm_instance.initialize(
        camera_ch1_index=camera_ch1_index,
        camera_ch2_index=camera_ch2_index,
        vibration_com=vibration_com,
        use_mock=use_mock
    )
    
    if not success:
        print("[API] 初始化失败")
        _slm_instance = None
        return {"success": False, "message": "初始化失败，请检查硬件连接"}
    
    # 启动
    print("[API] 启动采集...")
    _slm_instance.start()
    
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
    global _slm_instance
    if _slm_instance:
        try:
            _slm_instance.stop()
            print("[API] 采集已停止，资源已释放")
        except Exception as e:
            print(f"[API] 停止采集时出错: {e}")
        finally:
            # 清理全局实例，下次会重新创建
            _slm_instance = None
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
    """更新设备健康状态（供模型调用）"""
    acquisition = get_acquisition()
    acquisition.update_health_status(status_code, labels or [])
    
    return {
        "success": True,
        "status_code": status_code,
        "labels": labels or [],
        "health": acquisition._health_state.to_dict()
    }


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

async def video_stream_generator(channel: str, quality: int = 85):
    """视频流生成器"""
    acquisition = get_acquisition()
    
    while True:
        try:
            if acquisition.camera_manager:
                jpeg = acquisition.camera_manager.get_frame_jpeg(channel, quality)
                if jpeg:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n"
                        b"\r\n" + jpeg + b"\r\n"
                    )
            
            await asyncio.sleep(0.033)  # ~30 FPS
            
        except Exception as e:
            print(f"[VideoStream] 错误: {e}")
            await asyncio.sleep(0.1)


@router.get("/stream/camera/{channel}")
async def camera_stream(channel: str, quality: int = 85):
    """
    摄像头视频流 (MJPEG)
    channel: CH1 或 CH2
    """
    if channel not in ['CH1', 'CH2']:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid channel. Use 'CH1' or 'CH2'."}
        )
    
    return StreamingResponse(
        video_stream_generator(channel, quality),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


async def thermal_stream_generator(quality: int = 85):
    """热像视频流生成器"""
    acquisition = get_acquisition()
    
    while True:
        try:
            if acquisition.thermal_camera:
                thermal_image = acquisition.thermal_camera.generate_thermal_image(640, 480)
                if thermal_image is not None:
                    import cv2
                    ret, jpeg = cv2.imencode('.jpg', thermal_image, [cv2.IMWRITE_JPEG_QUALITY, quality])
                    if ret:
                        jpeg_bytes = jpeg.tobytes()
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: " + str(len(jpeg_bytes)).encode() + b"\r\n"
                            b"\r\n" + jpeg_bytes + b"\r\n"
                        )
            
            await asyncio.sleep(0.1)  # 10 FPS for thermal
            
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
