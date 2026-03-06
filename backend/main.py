"""
SmartAM_System - 后端入口 (FastAPI)
========================================
核心功能：
1. 提供 RESTful API 接口
2. WebSocket 实时数据推送（使用 DAQ 系统数据）
3. 视频流服务 (MJPEG Stream - IDS + 旁轴 + 红外组合画面)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import json
import asyncio
import time
from datetime import datetime
import cv2
import numpy as np
import threading
from typing import Optional
import signal
import sys

# 导入 DAQ 系统
try:
    from core.data_acquisition import get_daq_system, FrameData
    DAQ_AVAILABLE = True
    print("[Main] DAQ 系统导入成功")
except ImportError as e:
    DAQ_AVAILABLE = False
    print(f"[Main] DAQ 系统导入失败: {e}")

# 全局 DAQ 系统实例
daq = None


def signal_handler(signum, frame):
    """信号处理函数 - 确保服务关闭时停止 M114 轮询"""
    global daq
    print(f"\n[Main] 接收到信号 {signum}，正在优雅关闭...")
    if daq:
        try:
            daq.stop()
            print("[Main] DAQ 已停止")
        except Exception as e:
            print(f"[Main] 停止 DAQ 时出错: {e}")
    sys.exit(0)

# 注册信号处理程序
signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # 终止信号


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 设备选择后延迟初始化"""
    
    print("[Main] SmartAM 后端服务启动")
    print("[Main] 等待前端选择设备类型...")
    
    yield
    
    # 关闭时清理
    from core.device_manager import get_device_manager
    device_manager = get_device_manager()
    if device_manager.current_type.value != "none":
        print(f"[Main] 正在关闭 {device_manager.current_type.value} 设备...")
        device_manager.stop_current_device()
    print("[Main] 服务已关闭")


app = FastAPI(
    title="SmartAM System API",
    description="智能制造增材制造监控系统",
    version="1.0.0",
    lifespan=lifespan
)

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== API 路由注册 ==========
from api import router as api_router
app.include_router(api_router, prefix="/api")

# 注册健康检查路由（根路径）
from api.health import router as health_router
app.include_router(health_router)


# ========== 基础路由 ==========

@app.get("/")
async def root():
    """系统状态检查"""
    status = {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "service": "SmartAM_System Backend",
        "daq_available": DAQ_AVAILABLE and daq is not None
    }
    
    if daq:
        status["camera"] = daq.get_camera_status()
    
    return status


@app.get("/api/status")
async def get_system_status():
    """获取系统运行状态"""
    if daq:
        return {
            "printer": daq.get_printer_status(),
            "thermal": daq.get_thermal_status(),
            "camera": daq.get_camera_status(),
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "printer": {"connected": False},
            "thermal": {"available": False},
            "camera": {"ids": {"available": False}, "side": {"available": False}},
            "timestamp": datetime.now().isoformat()
        }


# ========== 视频流服务 ==========

def get_status_color(label: str) -> tuple:
    """根据状态标签返回颜色 (B, G, R)"""
    if label == "Low":
        return (0, 255, 255)  # 黄色
    elif label == "High":
        return (0, 0, 255)    # 红色
    else:  # Normal
        return (0, 255, 0)    # 绿色


def create_combined_frame(
    ids_frame: Optional[np.ndarray], 
    side_frame: Optional[np.ndarray],
    thermal_data: Optional[dict] = None,
    prediction: Optional[dict] = None,
    printer_data: Optional[dict] = None
) -> np.ndarray:
    """
    创建组合画面
    
    布局：
    ┌─────────────┬─────────────┐
    │  IDS相机    │  旁轴相机   │
    │  (随轴)     │  (罗技USB)  │
    ├─────────────┴─────────────┤
    │      红外热像图           │
    └───────────────────────────┘
    """
    # 创建 1080x1920 的画布
    canvas = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    # 区域尺寸
    top_height = 540
    full_width = 1920
    
    # 1. IDS 相机（左上，随轴）
    if ids_frame is not None:
        ids_resized = cv2.resize(ids_frame, (960, top_height))
        canvas[0:top_height, 0:960] = ids_resized
        cv2.putText(canvas, "IDS Camera (On-Axis)", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    else:
        cv2.putText(canvas, "IDS Camera - No Signal", (300, 270),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # 2. 旁轴摄像头（右上，罗技 USB）
    if side_frame is not None:
        side_resized = cv2.resize(side_frame, (960, top_height))
        canvas[0:top_height, 960:1920] = side_resized
        cv2.putText(canvas, "Side Camera (Logitech)", (970, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    else:
        cv2.putText(canvas, "Side Camera - No Signal", (1260, 270),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # 3. 红外热像图（底部）
    thermal_x_offset = 50  # 热像图左侧留空用于显示预测结果
    if thermal_data and thermal_data.get("available"):
        # 从 thermal_data 获取温度矩阵（已经由调用方提供）
        thermal_matrix = thermal_data.get("matrix")
        if thermal_matrix is not None:
            temp_min = thermal_data.get("min", 0)
            temp_max = thermal_data.get("max", 100)
            
            if temp_max > temp_min:
                normalized = ((thermal_matrix - temp_min) / (temp_max - temp_min) * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(thermal_matrix, dtype=np.uint8)
            
            colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
            thermal_resized = cv2.resize(colored, (1100, 480))  # 缩小一点，留出边距
            
            # 放在底部偏左
            canvas[top_height+30:top_height+510, thermal_x_offset:thermal_x_offset+1100] = thermal_resized
            
            # 显示温度信息
            info_text = f"Thermal: {temp_min:.1f}~{temp_max:.1f}C | Melt Pool: {thermal_data.get('melt_pool', 0):.1f}C"
            cv2.putText(canvas, info_text, (thermal_x_offset + 10, top_height + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        else:
            cv2.putText(canvas, "Thermal Camera - No Data", (400, 810),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    else:
        cv2.putText(canvas, "Thermal Camera - No Signal", (400, 810),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # 4. 右侧显示 PacNet 预测结果
    if prediction and prediction.get("available"):
        x_start = 1200
        y_start = 600
        line_height = 50
        
        # 标题
        cv2.putText(canvas, "PacNet Prediction", (x_start, y_start),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        # 各参数预测结果
        tasks = [
            ("Flow Rate", prediction.get("flow_rate", {})),
            ("Feed Rate", prediction.get("feed_rate", {})),
            ("Z Offset", prediction.get("z_offset", {})),
            ("Hotend", prediction.get("hot_end", {}))
        ]
        
        for i, (task_name, task_data) in enumerate(tasks):
            y_pos = y_start + 60 + i * line_height
            label = task_data.get("label", "Normal")
            conf = task_data.get("confidence", 0)
            color = get_status_color(label)
            
            text = f"{task_name:10s}: {label:6s} ({conf:.0%})"
            cv2.putText(canvas, text, (x_start, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    else:
        # 显示等待推理
        cv2.putText(canvas, "PacNet: Waiting...", (1200, 600),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (128, 128, 128), 2)
    
    # 5. 底部状态栏
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_text = f"SmartAM System - {current_time}"
    
    # 添加打印机状态
    if printer_data:
        status_text += f" | X:{printer_data.get('x', 0):.1f} Y:{printer_data.get('y', 0):.1f} Z:{printer_data.get('z', 0):.1f}"
        status_text += f" | T:{printer_data.get('nozzle_temp', 0):.1f}C"
    
    cv2.putText(canvas, status_text, (10, 1070),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return canvas


async def video_stream_generator():
    """
    视频流生成器 - 多相机组合画面
    支持无硬件模式（显示模拟画面）
    """
    frame_count = 0
    
    while True:
        try:
            # 尝试从 DAQ 获取数据（如果可用）
            ids_frame = None
            side_frame = None
            thermal_status = None
            prediction_dict = None
            printer_dict = None
            
            if daq:
                # 检查是否处于模拟模式
                is_simulation = getattr(daq, '_simulation_mode_active', False)
                
                # 获取 IDS 帧（真实或模拟）
                if hasattr(daq, '_ids_camera') and daq._ids_camera:
                    try:
                        ids_frame = daq._get_ids_frame()
                    except:
                        pass
                elif is_simulation and hasattr(daq, '_simulation_generator') and daq._simulation_generator:
                    # 模拟模式：从模拟生成器获取
                    try:
                        ids_frame = daq._simulation_generator.generate_ids_frame()
                    except:
                        pass
                
                # 获取旁轴相机帧（真实或模拟）
                if hasattr(daq, '_side_camera') and daq._side_camera:
                    try:
                        ret, side_frame = daq._side_camera.read()
                        if not ret:
                            side_frame = None
                    except:
                        pass
                elif is_simulation and hasattr(daq, '_simulation_generator') and daq._simulation_generator:
                    try:
                        side_frame = daq._simulation_generator.generate_side_frame()
                    except:
                        pass
                
                # 获取热像数据（真实或模拟）
                if hasattr(daq, '_fotric_device') and daq._fotric_device:
                    try:
                        if daq._fotric_device.is_connected:
                            thermal_data = daq._fotric_device.get_thermal_data()
                            if thermal_data is not None:
                                thermal_status = {
                                    "available": True,
                                    "matrix": thermal_data,
                                    "min": float(np.min(thermal_data)),
                                    "max": float(np.max(thermal_data)),
                                    "melt_pool": float(np.max(thermal_data))
                                }
                    except:
                        pass
                elif is_simulation and hasattr(daq, '_simulation_generator') and daq._simulation_generator:
                    try:
                        thermal_data = daq._simulation_generator.generate_thermal_data()
                        thermal_status = {
                            "available": True,
                            "matrix": thermal_data,
                            "min": float(np.min(thermal_data)),
                            "max": float(np.max(thermal_data)),
                            "melt_pool": float(np.max(thermal_data))
                        }
                    except:
                        pass
                
                # 获取打印机状态（真实或模拟）
                if hasattr(daq, '_current_position'):
                    pos = daq._current_position
                    printer_dict = {
                        "x": pos.get("X", 0),
                        "y": pos.get("Y", 0),
                        "z": pos.get("Z", 0),
                        "nozzle_temp": 0,
                        "state": "Unknown"
                    }
                    # 模拟模式下显示特殊状态
                    if is_simulation:
                        printer_dict["state"] = "Simulation"
            
            # 创建组合画面
            combined = create_combined_frame(
                ids_frame, side_frame, thermal_status, 
                prediction_dict, printer_dict
            )
            
            # 编码为 JPEG
            ret, buffer = cv2.imencode('.jpg', combined, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                )
                frame_count += 1
            
            await asyncio.sleep(0.033)  # ~30 FPS
            
        except Exception as e:
            print(f"[VideoStream] 错误: {e}")
            await asyncio.sleep(0.1)


@app.get("/video_feed")
async def video_feed():
    """
    MJPEG 视频流接口 - 多相机组合画面
    前端使用: <img src="http://localhost:8000/video_feed">
    
    画面布局：
    - 左上：IDS 相机（随轴，跟随打印头）
    - 右上：旁轴摄像头（罗技 USB，整体视角）
    - 底部：红外热像图（熔池温度分布）
    """
    return StreamingResponse(
        video_stream_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# 单独的视频流接口（可选）
@app.get("/video_feed/ids")
async def video_feed_ids():
    """IDS 相机单独视频流（支持模拟模式）"""
    async def ids_generator():
        while True:
            frame = None
            if daq:
                is_simulation = getattr(daq, '_simulation_mode_active', False)
                if daq._ids_camera:
                    try:
                        frame = daq._get_ids_frame()
                    except:
                        pass
                elif is_simulation and daq._simulation_generator:
                    try:
                        frame = daq._simulation_generator.generate_ids_frame()
                    except:
                        pass
            
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
            await asyncio.sleep(0.033)
    
    return StreamingResponse(ids_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/video_feed/side")
async def video_feed_side():
    """旁轴摄像头单独视频流（支持模拟模式）"""
    async def side_generator():
        while True:
            frame = None
            if daq:
                is_simulation = getattr(daq, '_simulation_mode_active', False)
                if daq._side_camera:
                    try:
                        frame = daq._side_camera.get_frame() if hasattr(daq._side_camera, 'get_frame') else daq._side_camera.read()[1]
                    except:
                        pass
                elif is_simulation and daq._simulation_generator:
                    try:
                        frame = daq._simulation_generator.generate_side_frame()
                    except:
                        pass
            
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
            await asyncio.sleep(0.033)
    
    return StreamingResponse(side_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


# ========== WebSocket 实时数据 ==========

@app.websocket("/ws/sensor_data")
async def sensor_websocket(websocket: WebSocket):
    """
    WebSocket 实时传感器数据推送
    推送频率: 100ms (10Hz)
    """
    await websocket.accept()
    
    # 用于接收 DAQ 数据的回调
    latest_data: Optional[FrameData] = None
    
    def on_new_data(packet: FrameData):
        nonlocal latest_data
        latest_data = packet
    
    # 注册回调
    if daq:
        daq.register_callback(on_new_data)
    
    try:
        last_frame_number = -1
        last_status_update = 0
        
        while True:
            current_time = time.time()
            
            # 更新帧号缓存
            if daq and latest_data and latest_data.frame_number != last_frame_number:
                last_frame_number = latest_data.frame_number
            
            # 每秒发送一次完整状态（不管是否有新帧）
            if daq and (current_time - last_status_update) >= 1.0:
                last_status_update = current_time
                
                # 【调试】确认进入发送分支
                print(f"[WebSocket-DEBUG] 准备发送数据, daq={daq is not None}, state={daq.get_status().get('state', 'unknown') if daq else 'N/A'}")
                
                try:
                    # 获取打印机状态（包含打印任务状态）
                    printer_status = daq.get_printer_status()
                    
                    # 获取采集状态（包含四个参数值）
                    acq_status = daq.get_status()
                    
                    # 获取当前Z高度（多源获取）
                    current_z = 0.0
                    
                    # 方法1：从 latest_data 获取（采集循环中更新的位置）
                    if latest_data and latest_data.current_z > 0:
                        current_z = latest_data.current_z
                    
                    # 方法2：从 DAQ 的 _current_position 获取（M114更新的位置）
                    if hasattr(daq, '_current_position') and daq._current_position.get('Z', 0) > 0:
                        # 优先使用更新的值
                        m114_z = daq._current_position.get('Z', 0)
                        if m114_z > 0:
                            current_z = m114_z
                    
                    # 调试输出（包含数据来源）
                    temp_debug = printer_status.get('hotend_actual', 0)
                    frame_z = latest_data.current_z if latest_data else 0
                    m114_z = daq._current_position.get('Z', 0) if hasattr(daq, '_current_position') else 0
                    # 【调试】每次都输出，确认数据流
                    print(f"[WebSocket-DEBUG] current_z={current_z:.2f}, frame_z={frame_z:.2f}, m114_z={m114_z:.2f}, state={acq_status.get('state', 'idle')}")
                    # 简化输出，只在Z>0时显示
                    if current_z > 0 and int(current_time) % 5 == 0:  # 每5秒显示一次
                        print(f"[WebSocket] Z={current_z:.2f}mm, T={temp_debug:.1f}°C, "
                              f"State={acq_status.get('state', 'unknown')}, "
                              f"FR={acq_data.get('flow_rate', 0)}, V={acq_data.get('feed_rate', 0)}")
                    
                    # 确保 acquisition 中的 current_z 和 current_params 正确
                    acq_data = acq_status.get("current_params", {})
                    
                    # 构造发送数据
                    data = {
                        "timestamp": datetime.now().isoformat(),
                        "frame_id": latest_data.frame_number if latest_data else 0,
                        "printer": {
                            "connected": printer_status.get("connected", False),
                            "state": printer_status.get("state", "Unknown"),
                            "temperature": {
                                "nozzle": printer_status.get("hotend_actual", 0),
                                "bed": printer_status.get("bed_actual", 0),
                                "nozzle_target": printer_status.get("hotend_target", 0),
                                "bed_target": printer_status.get("bed_target", 0)
                            },
                            "position": {
                                "x": latest_data.current_x if latest_data else 0,
                                "y": latest_data.current_y if latest_data else 0,
                                "z": current_z
                            },
                            "progress": printer_status.get("progress", 0),
                            "filename": printer_status.get("filename", ""),
                            "print_time": printer_status.get("print_time", 0),
                            "print_time_left": printer_status.get("print_time_left", 0)
                        },
                        "acquisition": {
                            "state": acq_status.get("state", "idle"),
                            "frame_count": acq_status.get("frame_count", 0),
                            "duration": acq_status.get("duration", 0),
                            "fps": acq_status.get("fps", 0),
                            "save_directory": acq_status.get("save_directory", ""),
                            "current_params": {
                                "flow_rate": acq_data.get("flow_rate", 0),
                                "feed_rate": acq_data.get("feed_rate", 0),
                                "z_offset": acq_data.get("z_offset", 0),
                                "target_hotend": acq_data.get("target_hotend", 0)
                            },
                            "current_z": current_z,
                            "param_mode": acq_status.get("param_mode", "fixed"),
                            "current_segment": acq_status.get("current_segment")
                        },
                        "thermal": {
                            "available": latest_data.fotric_data is not None if latest_data else False,
                            "min": latest_data.fotric_temp_min if latest_data else 0,
                            "max": latest_data.fotric_temp_max if latest_data else 0,
                            "avg": latest_data.fotric_temp_avg if latest_data else 0,
                            "melt_pool": latest_data.fotric_temp_max if latest_data else 0
                        },
                        "camera": {
                            "ids_available": latest_data.ids_image is not None if latest_data else False,
                            "ids_frame_count": latest_data.frame_number if latest_data else 0,
                            "side_available": latest_data.side_image is not None if latest_data else False,
                            "side_frame_count": latest_data.frame_number if latest_data else 0
                        },
                        "prediction": {
                            "available": latest_data is not None,
                            "flow_rate": {
                                "class": latest_data.flow_rate_class if latest_data else 1,
                                "label": ["Low", "Normal", "High"][latest_data.flow_rate_class if latest_data else 1],
                                "confidence": 0.8
                            },
                            "feed_rate": {
                                "class": latest_data.feed_rate_class if latest_data else 1,
                                "label": ["Low", "Normal", "High"][latest_data.feed_rate_class if latest_data else 1],
                                "confidence": 0.8
                            },
                            "z_offset": {
                                "class": latest_data.z_offset_class if latest_data else 1,
                                "label": ["Low", "Normal", "High"][latest_data.z_offset_class if latest_data else 1],
                                "confidence": 0.8
                            },
                            "hot_end": {
                                "class": latest_data.hotend_class if latest_data else 1,
                                "label": ["Low", "Normal", "High"][latest_data.hotend_class if latest_data else 1],
                                "confidence": 0.8
                            },
                            "inference_time_ms": 50
                        }
                    }
                    
                    await websocket.send_text(json.dumps(data))
                except Exception as e:
                    print(f"[WebSocket] 发送状态失败: {e}")
                    # 发送心跳保持连接
                    await websocket.send_text(json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "heartbeat": True
                    }))
            
            await asyncio.sleep(0.1)  # 100ms 间隔
            
    except Exception as e:
        print(f"[WebSocket] 连接断开: {e}")
    finally:
        if daq:
            daq.unregister_callback(on_new_data)
        # 安全关闭 WebSocket（避免重复关闭）
        try:
            await websocket.close()
        except RuntimeError:
            # 连接已关闭，忽略错误
            pass


# ========== 主入口 ==========

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
