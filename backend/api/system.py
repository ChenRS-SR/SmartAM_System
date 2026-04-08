"""
系统配置 API
============
提供系统配置的获取和保存
"""

import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

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


class OctoPrintConfig(BaseModel):
    """OctoPrint 配置"""
    host: str = "localhost:5000"
    api_key: str = ""


class CameraConfig(BaseModel):
    """相机配置"""
    ids_enabled: bool = True
    ids_device_id: int = 0
    side_url: str = ""
    resolution: str = "1920x1080"


class ThermalConfig(BaseModel):
    """热成像配置"""
    enabled: bool = True
    port: str = "COM3"
    baudrate: int = 921600
    emissivity: float = 0.95


class ModelConfig(BaseModel):
    """模型配置"""
    path: str = "weights/model_full.pt"
    scaler_path: str = "weights/scaler.pkl"
    use_gpu: bool = True
    frequency: int = 5


class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    octoprint: Dict[str, Any]
    camera: Dict[str, Any]
    thermal: Dict[str, Any]
    model: Dict[str, Any]


# 内存中的配置缓存（实际项目中应该持久化到文件）
_config_cache = {
    "octoprint": {"host": "localhost:5000", "api_key": "UGjrS2T5n_48GF0YsWADx1EoTILjwn7ZkeWUfgGvW2Q"},
    "camera": {"ids_enabled": True, "ids_device_id": 0, "side_url": "", "resolution": "1920x1080"},
    "thermal": {"enabled": True, "port": "COM3", "baudrate": 921600, "emissivity": 0.95},
    "model": {"path": "weights/model_full.pt", "scaler_path": "weights/scaler.pkl", "use_gpu": True, "frequency": 5}
}


def _init_config_from_env():
    """从环境变量初始化配置"""
    try:
        from config import get_octo_config
        octo = get_octo_config()
        # 提取 host 从 URL
        url = octo.url
        host = url.replace("http://", "").replace("https://", "")
        _config_cache["octoprint"] = {
            "host": host,
            "api_key": octo.api_key
        }
        print(f"[System API] 从环境变量加载 OctoPrint 配置: {host}")
        print(f"[System API] API Key: {octo.api_key[:20]}...")
    except Exception as e:
        print(f"[System API] 从环境变量加载配置失败: {e}")
        # 如果 pydantic-settings 加载失败，直接读取 .env 文件
        try:
            import os
            env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('OCTOPRINT_API_KEY='):
                            api_key = line.split('=', 1)[1].strip()
                            _config_cache["octoprint"]["api_key"] = api_key
                            print(f"[System API] 从 .env 文件读取 API Key: {api_key[:20]}...")
                        elif line.startswith('OCTOPRINT_URL='):
                            url = line.split('=', 1)[1].strip()
                            host = url.replace("http://", "").replace("https://", "")
                            _config_cache["octoprint"]["host"] = host
        except Exception as e2:
            print(f"[System API] 从 .env 文件读取也失败: {e2}")


# 初始化时加载环境变量配置
_init_config_from_env()


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config():
    """获取系统配置"""
    return SystemConfigResponse(
        octoprint=_config_cache["octoprint"],
        camera=_config_cache["camera"],
        thermal=_config_cache["thermal"],
        model=_config_cache["model"]
    )


@router.post("/config/octoprint")
async def save_octoprint_config(config: OctoPrintConfig):
    """保存 OctoPrint 配置"""
    _config_cache["octoprint"] = config.dict()
    
    # 同时更新 DAQ 配置
    try:
        daq = _get_daq()
        if daq:
            # 构建完整 URL
            url = config.host
            if not url.startswith("http"):
                url = f"http://{url}"
            daq.config.octoprint_url = url
            daq.config.octoprint_api_key = config.api_key
            print(f"[System API] 已更新 DAQ OctoPrint 配置: {url}")
    except Exception as e:
        print(f"[System API] 更新 DAQ 配置失败: {e}")
    
    return {"message": "OctoPrint 配置已保存", "config": config.dict()}


@router.post("/config/camera")
async def save_camera_config(config: CameraConfig):
    """保存相机配置"""
    _config_cache["camera"] = config.dict()
    return {"message": "相机配置已保存", "config": config.dict()}


@router.post("/config/thermal")
async def save_thermal_config(config: ThermalConfig):
    """保存热成像配置"""
    _config_cache["thermal"] = config.dict()
    return {"message": "热成像配置已保存", "config": config.dict()}


@router.post("/config/model")
async def save_model_config(config: ModelConfig):
    """保存模型配置"""
    _config_cache["model"] = config.dict()
    return {"message": "模型配置已保存", "config": config.dict()}


@router.post("/model/reload")
async def reload_model():
    """重新加载模型"""
    # TODO: 实现模型重新加载
    return {"message": "模型重新加载功能待实现"}


@router.get("/test")
async def test_system_connection():
    """测试系统连接"""
    return {"status": "ok", "message": "系统连接正常"}
