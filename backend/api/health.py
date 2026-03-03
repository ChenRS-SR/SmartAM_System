"""
健康检查 API
============
提供服务健康状态和系统监控信息
"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import platform
import sys

router = APIRouter()


class HealthStatus(BaseModel):
    """健康状态响应模型"""
    status: str
    timestamp: str
    version: str
    uptime_seconds: float


class SystemMetrics(BaseModel):
    """系统指标响应模型"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float


class ComponentStatus(BaseModel):
    """组件状态模型"""
    name: str
    status: str  # healthy, degraded, unhealthy
    message: Optional[str] = None
    last_check: str


class DetailedHealthResponse(BaseModel):
    """详细健康检查响应"""
    status: str
    timestamp: str
    version: str
    system: SystemMetrics
    components: List[ComponentStatus]


# 启动时间
_START_TIME = datetime.now()


def _get_uptime_seconds() -> float:
    """获取运行时间（秒）"""
    return (datetime.now() - _START_TIME).total_seconds()


def _format_uptime(seconds: float) -> str:
    """格式化运行时间"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}h {minutes}m {secs}s"


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    基础健康检查端点
    
    返回服务基本状态，用于负载均衡器和监控检查
    """
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        uptime_seconds=_get_uptime_seconds()
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    详细健康检查端点
    
    返回系统资源使用情况和各组件状态
    """
    try:
        import psutil
        
        # 系统资源
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / 1024 / 1024,
            memory_total_mb=memory.total / 1024 / 1024,
            disk_percent=(disk.used / disk.total) * 100,
            disk_used_gb=disk.used / 1024 / 1024 / 1024,
            disk_total_gb=disk.total / 1024 / 1024 / 1024
        )
        
    except ImportError:
        # 如果没有 psutil，返回空数据
        system_metrics = SystemMetrics(
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_mb=0.0,
            memory_total_mb=0.0,
            disk_percent=0.0,
            disk_used_gb=0.0,
            disk_total_gb=0.0
        )
    
    # 检查各组件状态
    components = []
    
    # DAQ 状态
    try:
        from main import daq
        if daq and daq.is_running:
            components.append(ComponentStatus(
                name="DAQ",
                status="healthy",
                message="数据采集系统运行中",
                last_check=datetime.now().isoformat()
            ))
        else:
            components.append(ComponentStatus(
                name="DAQ",
                status="degraded",
                message="数据采集系统未启动",
                last_check=datetime.now().isoformat()
            ))
    except Exception as e:
        components.append(ComponentStatus(
            name="DAQ",
            status="unhealthy",
            message=str(e),
            last_check=datetime.now().isoformat()
        ))
    
    # 相机状态
    try:
        from main import daq
        camera_status = "healthy" if (daq and daq.ids_camera and daq.ids_camera.is_running) else "degraded"
        components.append(ComponentStatus(
            name="Camera",
            status=camera_status,
            message="IDS 相机运行中" if camera_status == "healthy" else "IDS 相机未连接",
            last_check=datetime.now().isoformat()
        ))
    except Exception as e:
        components.append(ComponentStatus(
            name="Camera",
            status="unhealthy",
            message=str(e),
            last_check=datetime.now().isoformat()
        ))
    
    # 模型推理状态
    try:
        from main import daq
        inference_status = "healthy" if (daq and hasattr(daq, 'inference_engine') and daq.inference_engine) else "degraded"
        components.append(ComponentStatus(
            name="Inference",
            status=inference_status,
            message="PacNet 推理引擎就绪" if inference_status == "healthy" else "推理引擎未初始化",
            last_check=datetime.now().isoformat()
        ))
    except Exception as e:
        components.append(ComponentStatus(
            name="Inference",
            status="unhealthy",
            message=str(e),
            last_check=datetime.now().isoformat()
        ))
    
    # 确定整体状态
    overall_status = "healthy"
    for comp in components:
        if comp.status == "unhealthy":
            overall_status = "unhealthy"
            break
        elif comp.status == "degraded" and overall_status == "healthy":
            overall_status = "degraded"
    
    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        system=system_metrics,
        components=components
    )


@router.get("/health/system")
async def system_info():
    """
    获取系统信息
    
    返回 Python 版本、操作系统等信息
    """
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        cuda_version = torch.version.cuda if cuda_available else None
    except ImportError:
        cuda_available = False
        cuda_version = None
    
    return {
        "platform": platform.platform(),
        "python_version": sys.version,
        "processor": platform.processor(),
        "machine": platform.machine(),
        "cuda_available": cuda_available,
        "cuda_version": cuda_version,
        "uptime": _format_uptime(_get_uptime_seconds()),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/ready")
async def readiness_check():
    """
    就绪检查（用于 Kubernetes）
    
    检查服务是否已准备好接收流量
    """
    try:
        from main import daq
        if daq and daq.is_running:
            return {"ready": True, "message": "服务已就绪"}
        else:
            return {"ready": False, "message": "DAQ 系统未启动"}
    except Exception as e:
        return {"ready": False, "message": str(e)}


@router.get("/live")
async def liveness_check():
    """
    存活检查（用于 Kubernetes）
    
    检查服务是否还在运行（不检查依赖）
    """
    return {
        "alive": True,
        "timestamp": datetime.now().isoformat(),
        "uptime": _format_uptime(_get_uptime_seconds())
    }
