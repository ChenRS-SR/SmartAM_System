"""
数据采集 API 路由
提供采集控制接口
"""
import os
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, List

from core.data_acquisition import DataAcquisition, AcquisitionConfig, AcquisitionState, get_acquisition

router = APIRouter(tags=["acquisition"])

# 使用 core.data_acquisition 中的单例，确保与 main.py 的 WebSocket 使用同一实例
def get_acquisition_instance() -> DataAcquisition:
    """获取采集实例（单例）"""
    acq = get_acquisition()
    
    # 设置回调（只在第一次设置）
    if acq.on_state_changed is None:
        acq.on_state_changed = lambda old, new: logging.info(f"状态变化: {old.value} -> {new.value}")
    if acq.on_error is None:
        acq.on_error = lambda err: logging.error(f"采集错误: {err}")
    
    return acq


class AcquisitionSettings(BaseModel):
    """采集设置"""
    save_directory: Optional[str] = None
    capture_fps: Optional[float] = 5.0
    enable_ids: Optional[bool] = True
    enable_side_camera: Optional[bool] = True
    enable_fotric: Optional[bool] = True
    enable_vibration: Optional[bool] = False
    octoprint_url: Optional[str] = "http://127.0.0.1:5000"
    octoprint_api_key: Optional[str] = ""
    # 打印参数 (用于计算class)
    flow_rate: Optional[float] = None
    feed_rate: Optional[float] = None
    z_offset: Optional[float] = None
    target_hotend: Optional[float] = None
    # 初始Z补偿 (打印机调平后的基准值)
    initial_z_offset: Optional[float] = -2.55
    # 参数模式配置
    param_mode: Optional[str] = "fixed"  # fixed/random/tower
    random_interval_sec: Optional[float] = 120
    current_tower: Optional[int] = 1
    # 时空同步缓冲配置
    stability_z_diff_mm: Optional[float] = 0.6
    silent_height_mm: Optional[float] = 1.0


class AcquisitionResponse(BaseModel):
    """采集响应"""
    success: bool
    message: str
    data: Optional[Dict] = None


@router.post("/config", response_model=AcquisitionResponse)
async def configure_acquisition(settings: AcquisitionSettings):
    """配置采集参数"""
    try:
        acq = get_acquisition_instance()
        
        # 更新配置
        logging.info(f"[API配置] 更新采集配置: save_dir={settings.save_directory}, enable_ids={settings.enable_ids}, "
                    f"enable_side={settings.enable_side_camera}, enable_fotric={settings.enable_fotric}")
        
        if settings.save_directory:
            acq.config.save_directory = settings.save_directory
        if settings.capture_fps:
            acq.config.capture_fps = settings.capture_fps
        if settings.enable_ids is not None:
            acq.config.enable_ids = settings.enable_ids
            logging.info(f"[API配置] enable_ids 设置为 {settings.enable_ids}")
        if settings.enable_side_camera is not None:
            acq.config.enable_side_camera = settings.enable_side_camera
        if settings.enable_fotric is not None:
            acq.config.enable_fotric = settings.enable_fotric
        if settings.enable_vibration is not None:
            acq.config.enable_vibration = settings.enable_vibration
        if settings.octoprint_url:
            acq.config.octoprint_url = settings.octoprint_url
        if settings.octoprint_api_key:
            acq.config.octoprint_api_key = settings.octoprint_api_key
        if settings.initial_z_offset is not None:
            acq.config.initial_z_offset = settings.initial_z_offset
        
        # 更新参数模式配置
        if settings.param_mode:
            acq.config.param_mode = settings.param_mode
        if settings.random_interval_sec is not None:
            acq.config.random_interval_sec = settings.random_interval_sec
        if settings.current_tower is not None:
            acq.config.current_tower = settings.current_tower
        if settings.stability_z_diff_mm is not None:
            acq.config.stability_z_diff_mm = settings.stability_z_diff_mm
        if settings.silent_height_mm is not None:
            acq.config.silent_height_mm = settings.silent_height_mm
        
        # 更新打印参数 (用于计算class)
        acq.update_print_params(
            flow_rate=settings.flow_rate,
            feed_rate=settings.feed_rate,
            z_offset=settings.z_offset,
            target_hotend=settings.target_hotend
        )
        
        return AcquisitionResponse(
            success=True,
            message="配置已更新",
            data=acq.config.__dict__
        )
        
    except Exception as e:
        logging.error(f"配置采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start", response_model=AcquisitionResponse)
async def start_acquisition():
    """开始采集"""
    try:
        acq = get_acquisition_instance()
        
        # 检查保存目录
        if not os.path.exists(acq.config.save_directory):
            os.makedirs(acq.config.save_directory, exist_ok=True)
        
        success = acq.start_acquisition()
        
        if success:
            return AcquisitionResponse(
                success=True,
                message="采集已开始",
                data=acq.get_status()
            )
        else:
            return AcquisitionResponse(
                success=False,
                message="采集启动失败，可能已在采集中或无可用设备"
            )
            
    except Exception as e:
        logging.error(f"启动采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause", response_model=AcquisitionResponse)
async def pause_acquisition():
    """暂停采集"""
    try:
        acq = get_acquisition_instance()
        success = acq.pause_acquisition()
        
        if success:
            return AcquisitionResponse(
                success=True,
                message="采集已暂停",
                data=acq.get_status()
            )
        else:
            return AcquisitionResponse(
                success=False,
                message="暂停失败，当前不在采集状态"
            )
            
    except Exception as e:
        logging.error(f"暂停采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume", response_model=AcquisitionResponse)
async def resume_acquisition():
    """恢复采集"""
    try:
        acq = get_acquisition_instance()
        success = acq.resume_acquisition()
        
        if success:
            return AcquisitionResponse(
                success=True,
                message="采集已恢复",
                data=acq.get_status()
            )
        else:
            return AcquisitionResponse(
                success=False,
                message="恢复失败，当前不在暂停状态"
            )
            
    except Exception as e:
        logging.error(f"恢复采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=AcquisitionResponse)
async def stop_acquisition():
    """停止采集"""
    try:
        acq = get_acquisition_instance()
        success = acq.stop_acquisition()
        
        if success:
            return AcquisitionResponse(
                success=True,
                message="采集已停止",
                data=acq.get_status()
            )
        else:
            return AcquisitionResponse(
                success=False,
                message="停止失败，当前不在采集中"
            )
            
    except Exception as e:
        logging.error(f"停止采集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_acquisition_status():
    """获取采集状态"""
    try:
        acq = get_acquisition_instance()
        return {
            "success": True,
            "data": acq.get_status()
        }
    except Exception as e:
        logging.error(f"获取状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init", response_model=AcquisitionResponse)
async def initialize_devices():
    """初始化设备（测试用）"""
    try:
        acq = get_acquisition_instance()
        results = acq.initialize_devices()
        
        return AcquisitionResponse(
            success=True,
            message="设备初始化完成",
            data=results
        )
        
    except Exception as e:
        logging.error(f"初始化设备失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ParamUpdateRequest(BaseModel):
    """参数更新请求"""
    flow_rate: Optional[float] = None
    feed_rate: Optional[float] = None
    z_offset: Optional[float] = None
    target_hotend: Optional[float] = None


@router.post("/params", response_model=AcquisitionResponse)
async def update_params(request: ParamUpdateRequest):
    """
    更新打印参数 (采集运行中动态调整)
    同时会发送G-code到打印机
    
    注意：标准塔模式下，参数只在 Z>=5mm 时才会实际发送到打印机
    """
    try:
        acq = get_acquisition_instance()
        
        # 检查当前Z高度（塔模式下Z<5mm不允许修改）
        current_z = 0.0
        if hasattr(acq, '_current_position'):
            current_z = acq._current_position.get('Z', 0.0)
        
        # 塔模式检查：Z < 5mm 不允许修改参数
        is_tower_mode = acq.config.param_mode == "tower"
        if is_tower_mode and current_z < 5.0:
            # 只更新配置，不发送到打印机
            acq.update_print_params(
                flow_rate=request.flow_rate,
                feed_rate=request.feed_rate,
                z_offset=request.z_offset,
                target_hotend=request.target_hotend
            )
            return AcquisitionResponse(
                success=True,
                message=f"参数已缓存，将在Z>=5mm时应用 (当前Z={current_z:.2f}mm)",
                data={
                    "flow_rate": request.flow_rate,
                    "feed_rate": request.feed_rate,
                    "z_offset": request.z_offset,
                    "target_hotend": request.target_hotend,
                    "deferred": True,
                    "current_z": current_z
                }
            )
        
        # 更新采集系统的参数
        acq.update_print_params(
            flow_rate=request.flow_rate,
            feed_rate=request.feed_rate,
            z_offset=request.z_offset,
            target_hotend=request.target_hotend
        )
        
        # 发送G-code到打印机
        import requests
        octoprint_url = acq.config.octoprint_url
        api_key = acq.config.octoprint_api_key
        headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
        
        commands_sent = []
        
        if request.flow_rate is not None:
            # M221: 设置流量倍率
            gcode = f"M221 S{int(request.flow_rate)}"
            try:
                requests.post(
                    f"{octoprint_url}/api/printer/command",
                    headers=headers,
                    json={"command": gcode},
                    timeout=2
                )
                commands_sent.append(f"Flow Rate: {request.flow_rate}%")
            except Exception as e:
                logging.warning(f"发送M221失败: {e}")
        
        if request.feed_rate is not None:
            # M220: 设置速度倍率
            gcode = f"M220 S{int(request.feed_rate)}"
            try:
                requests.post(
                    f"{octoprint_url}/api/printer/command",
                    headers=headers,
                    json={"command": gcode},
                    timeout=2
                )
                commands_sent.append(f"Feed Rate: {request.feed_rate}%")
            except Exception as e:
                logging.warning(f"发送M220失败: {e}")
        
        if request.z_offset is not None:
            # 使用新的Z偏移控制逻辑（M851检查 + M290相对调整）
            if acq._m114_coord:
                target_display = request.z_offset
                current_m851 = acq._m114_coord.get_m851_z_offset(timeout=3)
                if current_m851 is not None:
                    current_display = current_m851 - (-2.55)
                    delta = target_display - current_display
                    if abs(delta) >= 0.01:
                        new_m851 = acq._m114_coord.set_z_offset_relative(delta, timeout=3, current=current_m851)
                        if new_m851:
                            commands_sent.append(f"Z Offset: {target_display:.2f}mm (M851: {current_m851:.2f}->{new_m851:.2f})")
                    else:
                        commands_sent.append(f"Z Offset: 无需调整 ({current_display:.2f}mm)")
                else:
                    commands_sent.append(f"Z Offset: 无法获取当前值，跳过")
            else:
                # 回退到旧逻辑
                initial_z = getattr(acq.config, 'initial_z_offset', 0)
                actual_z = initial_z + request.z_offset
                gcode = f"M290 Z{actual_z:.2f}"
                try:
                    requests.post(
                        f"{octoprint_url}/api/printer/command",
                        headers=headers,
                        json={"command": gcode},
                        timeout=2
                    )
                    commands_sent.append(f"Z Offset: {request.z_offset}mm (actual: {actual_z:.2f}mm)")
                except Exception as e:
                    logging.warning(f"发送M290失败: {e}")
        
        if request.target_hotend is not None:
            # M104: 设置热端温度
            gcode = f"M104 S{int(request.target_hotend)}"
            try:
                requests.post(
                    f"{octoprint_url}/api/printer/command",
                    headers=headers,
                    json={"command": gcode},
                    timeout=2
                )
                commands_sent.append(f"Hotend: {request.target_hotend}°C")
            except Exception as e:
                logging.warning(f"发送M104失败: {e}")
        
        return AcquisitionResponse(
            success=True,
            message=f"参数已更新: {', '.join(commands_sent)}" if commands_sent else "参数已更新",
            data={
                "flow_rate": request.flow_rate,
                "feed_rate": request.feed_rate,
                "z_offset": request.z_offset,
                "target_hotend": request.target_hotend,
                "current_z": current_z
            }
        )
        
    except Exception as e:
        logging.error(f"更新参数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
