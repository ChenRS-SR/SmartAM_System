"""
模型推理 API
============
提供 AI 推理相关的接口：
- 获取最新预测结果
- 控制推理参数
- 查看推理统计
"""

import sys
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

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


class PredictionResult(BaseModel):
    """预测结果模型"""
    available: bool
    flow_rate_label: str
    flow_rate_conf: float
    feed_rate_label: str
    feed_rate_conf: float
    z_offset_label: str
    z_offset_conf: float
    hot_end_label: str
    hot_end_conf: float
    inference_time_ms: float


class InferenceConfig(BaseModel):
    """推理配置模型"""
    inference_interval: float  # 秒
    device: str  # cuda/cpu


@router.get("/prediction", response_model=PredictionResult)
async def get_latest_prediction():
    """获取最新预测结果"""
    daq = _get_daq()
    
    if not daq or not daq._latest_data:
        raise HTTPException(status_code=503, detail="数据不可用")
    
    pred = daq._latest_data.prediction
    
    return PredictionResult(
        available=pred.available,
        flow_rate_label=pred.flow_rate_label,
        flow_rate_conf=pred.flow_rate_conf,
        feed_rate_label=pred.feed_rate_label,
        feed_rate_conf=pred.feed_rate_conf,
        z_offset_label=pred.z_offset_label,
        z_offset_conf=pred.z_offset_conf,
        hot_end_label=pred.hot_end_label,
        hot_end_conf=pred.hot_end_conf,
        inference_time_ms=pred.inference_time_ms
    )


@router.get("/status")
async def get_inference_status():
    """获取推理引擎状态"""
    daq = _get_daq()
    
    if not daq or not hasattr(daq, 'pacnet') or not daq.pacnet:
        return {
            "loaded": False,
            "message": "推理引擎未加载"
        }
    
    return {
        "loaded": daq.pacnet.is_loaded,
        "device": str(daq.pacnet.device),
        "inference_interval": daq.pacnet.inference_interval,
        "model_path": daq.pacnet.model_path,
        "latest_inference_time_ms": daq.pacnet._latest_result.inference_time_ms if daq.pacnet._latest_result else None
    }


@router.post("/config")
async def update_inference_config(config: InferenceConfig):
    """更新推理配置"""
    daq = _get_daq()
    
    if not daq or not daq.pacnet:
        raise HTTPException(status_code=503, detail="推理引擎不可用")
    
    daq.pacnet.set_inference_interval(config.inference_interval)
    
    return {
        "message": "配置已更新",
        "inference_interval": config.inference_interval
    }


@router.get("/history")
async def get_prediction_history(limit: int = 100):
    """获取预测历史（用于分析）"""
    daq = _get_daq()
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 不可用")
    
    # TODO: 实现历史记录查询
    return {
        "message": "功能开发中",
        "limit": limit
    }
