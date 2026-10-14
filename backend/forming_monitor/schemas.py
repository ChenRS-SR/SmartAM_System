"""请求体定义（响应结构见 接口说明.md）。"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class AcquisitionStart(BaseModel):
    task_id: Optional[str] = Field(None, description='成形任务编号，缺省为设备当前任务')
    from_layer: Optional[int] = Field(None, description='从该层开始回放，缺省为当前层')
    interval: Optional[float] = Field(None, gt=0, description='回放间隔，秒/层')


class RecognizeRequest(BaseModel):
    device_id: str
    task_id: Optional[str] = None
    layer: Optional[int] = Field(None, description='缺省为设备当前接入层')
    threshold: float = Field(0.5, description='判定阈值（0～1）')
    modalities: list[Literal['vis', 'tq']] = Field(default_factory=lambda: ['vis', 'tq'], description='输入模态：vis 铺粉后图像，tq 扭矩')
    n_records: int = Field(5, ge=1, le=50)


class TraceRequest(BaseModel):
    device_id: str
    task_id: Optional[str] = None
    layer: Optional[int] = None
    band_px: Optional[int] = Field(None, description='零件区边缘邻域（224网格上的像素），缺省取设备配置')
    ref_mode: Literal['prev_normal', 'manual'] = Field('prev_normal', description='参照层选取：前序最近正常层 / 指定层')
    ref_layer: Optional[int] = None
    n_curve: int = Field(41, ge=5, le=200)
    n_records: int = Field(4, ge=1, le=50)
