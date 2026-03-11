"""
SmartAM_System - 后端入口 (FastAPI)
========================================
核心功能：
1. 提供 RESTful API 接口
2. WebSocket 实时数据推送
3. 视频流服务 (MJPEG Stream)
4. 静态文件服务（状态图片）
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
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
import os

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
    """信号处理函数"""
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
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
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


# ========== 静态文件服务 (必须在 API 路由之前) ==========
# 获取项目根目录 - 使用绝对路径确保正确
_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(_file_dir)
print(f"[Main] 项目根目录: {project_root}")
frontend_dist_path = os.path.join(project_root, "frontend", "dist")
frontend_public_path = os.path.join(project_root, "frontend", "public")

# 前端静态文件
if os.path.exists(frontend_dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")
    print(f"[Main] 前端静态文件服务已挂载: {frontend_dist_path}")
else:
    print(f"[Main] 警告: 前端静态文件目录不存在: {frontend_dist_path}")

# public目录静态文件（用于测试页面等）
if os.path.exists(frontend_public_path):
    print(f"[Main] 正在挂载 /public -> {frontend_public_path}")
    for f in os.listdir(frontend_public_path):
        print(f"[Main]   发现文件: {f}")
    app.mount("/public", StaticFiles(directory=frontend_public_path), name="public")
    print(f"[Main] Public目录服务已挂载: {frontend_public_path}")
else:
    print(f"[Main] 警告: Public目录不存在: {frontend_public_path}")

# 状态图片
state_picture_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state_picture")
if os.path.exists(state_picture_path):
    app.mount("/state_picture", StaticFiles(directory=state_picture_path), name="state_picture")
    print(f"[Main] 状态图片服务已挂载: {state_picture_path}")


# 视频测试页面
@app.get("/video-test")
async def video_test_page():
    """视频流测试页面"""
    test_page_path = os.path.join(project_root, "frontend", "public", "video-test.html")
    if os.path.exists(test_page_path):
        return FileResponse(test_page_path)
    return {"error": "视频测试页面不存在", "path": test_page_path}


# ========== API 路由注册 ==========
from api import router as api_router
app.include_router(api_router, prefix="/api")

# 注册健康检查路由（根路径）
from api.health import router as health_router
app.include_router(health_router)


# ========== 基础路由 ==========

@app.get("/")
async def root():
    """返回前端页面"""
    frontend_index = os.path.join(project_root, "frontend", "dist", "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    else:
        return {
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "service": "SmartAM_System Backend",
            "message": "Frontend not built"
        }


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
    """创建组合画面"""
    # 创建 1080x1920 的画布
    canvas = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    # 区域尺寸
    top_height = 540
    full_width = 1920
    
    # 1. IDS 相机（左上）
    if ids_frame is not None:
        ids_resized = cv2.resize(ids_frame, (960, top_height))
        canvas[0:top_height, 0:960] = ids_resized
        cv2.putText(canvas, "IDS Camera (On-Axis)", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    else:
        cv2.putText(canvas, "IDS Camera - No Signal", (300, 270),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # 2. 旁轴摄像头（右上）
    if side_frame is not None:
        side_resized = cv2.resize(side_frame, (960, top_height))
        canvas[0:top_height, 960:1920] = side_resized
        cv2.putText(canvas, "Side Camera (Logitech)", (970, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    else:
        cv2.putText(canvas, "Side Camera - No Signal", (1260, 270),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # 3. 红外热像图（底部）
    thermal_x_offset = 50
    if thermal_data and thermal_data.get("available"):
        thermal_matrix = thermal_data.get("matrix")
        if thermal_matrix is not None:
            temp_min = thermal_data.get("min", 0)
            temp_max = thermal_data.get("max", 100)
            
            if temp_max > temp_min:
                normalized = ((thermal_matrix - temp_min) / (temp_max - temp_min) * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(thermal_matrix, dtype=np.uint8)
            
            colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
            thermal_resized = cv2.resize(colored, (1100, 480))
            
            canvas[top_height+30:top_height+510, thermal_x_offset:thermal_x_offset+1100] = thermal_resized
            
            info_text = f"Thermal: {temp_min:.1f}~{temp_max:.1f}C | Melt Pool: {thermal_data.get('melt_pool', 0):.1f}C"
            cv2.putText(canvas, info_text, (thermal_x_offset + 10, top_height + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        else:
            cv2.putText(canvas, "Thermal Camera - No Data", (400, 810),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    else:
        cv2.putText(canvas, "Thermal Camera - No Signal", (400, 810),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    # 4. 右侧显示预测结果
    if prediction and prediction.get("available"):
        x_start = 1200
        y_start = 600
        
        cv2.putText(canvas, "PacNet Prediction:", (x_start, y_start),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 显示各类别的预测结果
        y_offset = y_start + 40
        for i, (key, value) in enumerate(prediction.items()):
            if key == "available":
                continue
            if isinstance(value, dict) and "label" in value:
                label = value["label"]
                confidence = value.get("confidence", 0)
                color = get_status_color(label)
                
                text = f"{key}: {label} ({confidence:.2f})"
                cv2.putText(canvas, text, (x_start, y_offset + i * 35),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # 5. 底部显示打印机状态
    if printer_data:
        bed_temp = printer_data.get("bed_temperature", 0)
        hotend_temp = printer_data.get("hotend_temperature", 0)
        progress = printer_data.get("progress", 0)
        
        status_text = f"Bed: {bed_temp:.1f}C | Hotend: {hotend_temp:.1f}C | Progress: {progress:.1f}%"
        cv2.putText(canvas, status_text, (50, 1050),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return canvas


def generate_video_stream():
    """生成视频流"""
    global daq
    
    while True:
        try:
            if daq is None:
                # 如果没有DAQ，生成测试画面
                frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                cv2.putText(frame, "DAQ System Not Initialized", (600, 540),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
                cv2.putText(frame, "Please select device type from frontend", (500, 600),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
            else:
                # 获取最新数据
                ids_frame = daq.get_latest_frame("ids")
                side_frame = daq.get_latest_frame("side")
                thermal_data = daq.get_thermal_data()
                prediction = daq.get_latest_prediction()
                printer_data = daq.get_printer_data()
                
                # 创建组合画面
                frame = create_combined_frame(
                    ids_frame, side_frame, thermal_data, prediction, printer_data
                )
            
            # 编码为JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # 控制帧率 (约 10 FPS)
            time.sleep(0.1)
            
        except Exception as e:
            print(f"[Video Stream] 错误: {e}")
            time.sleep(1)


@app.get("/video_feed")
async def video_feed():
    """视频流端点"""
    return StreamingResponse(
        generate_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ========== WebSocket 实时数据 ==========

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时数据推送"""
    global daq
    await websocket.accept()
    
    latest_data = None
    
    def on_new_data(data: FrameData):
        nonlocal latest_data
        latest_data = data
    
    # 注册回调
    if daq:
        daq.register_callback(on_new_data)
    
    try:
        while True:
            # 检查是否有新数据
            if latest_data:
                try:
                    data = {
                        "timestamp": datetime.now().isoformat(),
                        "frame_number": latest_data.frame_number if hasattr(latest_data, 'frame_number') else 0,
                        "thermal": {
                            "max": latest_data.temp_max if hasattr(latest_data, 'temp_max') else 0,
                            "min": latest_data.temp_min if hasattr(latest_data, 'temp_min') else 0,
                            "melt_pool": latest_data.melt_pool_temp if hasattr(latest_data, 'melt_pool_temp') else 0
                        } if hasattr(latest_data, 'temp_max') else None,
                        "prediction": {
                            "available": True,
                            "x_offset": {
                                "class": latest_data.x_offset_class if hasattr(latest_data, 'x_offset_class') else 1,
                                "label": ["Low", "Normal", "High"][latest_data.x_offset_class if hasattr(latest_data, 'x_offset_class') else 1],
                                "confidence": 0.8
                            },
                            "z_offset": {
                                "class": latest_data.z_offset_class if hasattr(latest_data, 'z_offset_class') else 1,
                                "label": ["Low", "Normal", "High"][latest_data.z_offset_class if hasattr(latest_data, 'z_offset_class') else 1],
                                "confidence": 0.8
                            },
                            "hot_end": {
                                "class": latest_data.hotend_class if hasattr(latest_data, 'hotend_class') else 1,
                                "label": ["Low", "Normal", "High"][latest_data.hotend_class if hasattr(latest_data, 'hotend_class') else 1],
                                "confidence": 0.8
                            },
                            "inference_time_ms": 50
                        } if hasattr(latest_data, 'x_offset_class') else {"available": False}
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
        # 安全关闭 WebSocket
        try:
            await websocket.close()
        except RuntimeError:
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
