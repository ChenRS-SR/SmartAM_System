"""SLM 闭环调控 API 路由（前缀 /slm/control）。

忠实移植 Desktop/slm/slm_gui.py 中「准备/停止」「请求更新」「发送调整参数」
「紧急停止」「恢复默认」背后的逻辑：
  - 发送：校验零件 + 4 个工艺参数（SAFE_RANGES）+ 铺粉量(>0) + 送粉倍率(0.5~2.0)
          → set_fill_params → set_powder_amount → 写 feedback.json（continue + 补偿参数）
  - 停止：写 feedback.json（stop）
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .config import SAFE_RANGES, ENERGY_DENSITY_WINDOW, AUTO_ADJUSTABLE_PARAMS, API_BASE_URL, COMM_DIR
from .file_interface import read_event, read_feedback, write_feedback, write_request
from .models import DetectionFeedback, CompensationParams
from .api_client import get_api_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slm/control", tags=["SLM闭环调控"])


class PartSelectRequest(BaseModel):
    part_id: int


class RequestRequest(BaseModel):
    action: str = "request_status"  # "ping" | "request_status" | "request_sync"


class SendRequest(BaseModel):
    part_id: int
    fill_power: float
    fill_speed: float
    scan_spacing: float
    powder_feed_rate: float = 5.0
    powder_amount: float = Field(..., gt=0, description="铺粉量，必须大于 0")
    powder_multiplier: float = 1.0
    message: str = "手动调整参数"


def _next_command_id() -> int:
    fb = read_feedback()
    if fb:
        return int(fb.get("command_id", 0)) + 1
    return 1


def _current_layer_and_job():
    event = read_event()
    return (event.layer if event else 0), (event.job_name if event else "manual")


@router.get("/config")
def get_config() -> Dict[str, Any]:
    """返回安全区间、VED 窗口、参数默认值等（供前端渲染区间条与标签）。"""
    return {
        "safe_ranges": SAFE_RANGES,
        "energy_density_window": ENERGY_DENSITY_WINDOW,
        "auto_adjustable_params": AUTO_ADJUSTABLE_PARAMS,
        "api_base_url": API_BASE_URL,
        "comm_dir": str(COMM_DIR),
        "defaults": {k: v["default"] for k, v in SAFE_RANGES.items()},
    }


@router.get("/event")
def get_event():
    """读取 read.json 的试验台事件（无则返回 null）。"""
    event = read_event()
    if event is None:
        return None
    return {
        "trigger": event.trigger,
        "event": event.event,
        "layer": event.layer,
        "device_id": event.device_id,
        "job_name": event.job_name,
        "timestamp": event.timestamp,
        "source": event.source,
        "parameters": event.parameters,
    }


@router.get("/feedback")
def get_feedback():
    """读取 feedback.json 当前内容（无则返回 null）。"""
    return read_feedback()


@router.get("/parts")
def get_parts() -> Dict[str, Any]:
    """代理试验台零件列表；离线时回退样例零件。"""
    client = get_api_client()
    parts = client.get_parts()
    return {
        "parts": parts,
        "count": len(parts),
        "offline": client.offline,
        "fallback": client.parts_fallback,
    }


@router.post("/parts/select")
def select_part(req: PartSelectRequest) -> Dict[str, Any]:
    client = get_api_client()
    if not client.get_cached_parts():
        client.get_parts()
    part = client.select_part(req.part_id)
    if part is None:
        return {"ok": False, "offline": client.offline, "message": "无效零件，请先刷新零件列表"}
    return {"ok": True, "offline": client.offline, "part": part}


@router.post("/request")
def post_request(req: RequestRequest) -> Dict[str, Any]:
    """写 request.json 主动请求试验台（对应桌面「请求更新」按钮）。"""
    action = req.action if req.action in ("ping", "request_status", "request_sync") else "request_status"
    ok = write_request(action)
    return {"ok": ok, "action": action}


@router.post("/send")
def send_adjustment(req: SendRequest) -> Dict[str, Any]:
    """发送调整参数：HTTP API + feedback.json 双写（对应桌面「发送调整参数」）。"""
    errors: list = []

    # 1. 校验零件选择
    client = get_api_client()
    if not client.get_cached_parts():
        client.get_parts()
    part = client.select_part(req.part_id)
    if part is None:
        return {"ok": False, "errors": ["零件未选择/无效"], "message": "请先选择 SLC 零件"}
    part_name = part.get("name", "?")

    # 2. 校验 4 个工艺参数（含送粉速率）
    params = {
        "fill_power": req.fill_power,
        "fill_speed": req.fill_speed,
        "scan_spacing": req.scan_spacing,
        "powder_feed_rate": req.powder_feed_rate,
    }
    for key, val in params.items():
        safe = SAFE_RANGES.get(key, {})
        vmin, vmax = safe.get("min", 0), safe.get("max", float("inf"))
        if not (vmin <= val <= vmax):
            return {
                "ok": False,
                "errors": [f"{key} 越界"],
                "message": f"{key}={val} 不在 [{vmin}, {vmax}] 范围内",
            }

    # 3. 铺粉量已由 Pydantic 校验 > 0
    # 4. 校验送粉倍率
    if not (0.5 <= req.powder_multiplier <= 2.0):
        return {"ok": False, "errors": ["送粉倍率越界"], "message": "送粉倍率应在 0.5~2.0"}

    msg = req.message or "手动调整参数"

    # 5. HTTP API：填充参数 + 铺粉量
    steps: Dict[str, bool] = {}
    if client.set_fill_params(req.part_id, req.fill_power, req.fill_speed, req.scan_spacing):
        steps["fill_params_api"] = True
    else:
        steps["fill_params_api"] = False
        errors.append("填充参数(API)")

    if client.set_powder_amount(req.powder_amount):
        steps["powder_amount_api"] = True
    else:
        steps["powder_amount_api"] = False
        errors.append("铺粉量(API)")

    # 6. 写入 feedback.json（含 API 不覆盖的送粉倍率字段）
    layer, job_name = _current_layer_and_job()
    fb = DetectionFeedback(
        command_id=_next_command_id(),
        layer=layer,
        job_name=job_name,
        device_id="camera_system",
        detection_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    fb.set_action_continue(
        powder_multiplier=req.powder_multiplier,
        compensation=CompensationParams(
            fill_power=req.fill_power,
            fill_speed=req.fill_speed,
            scan_spacing=req.scan_spacing,
        ),
        message=msg,
    )
    if write_feedback(fb):
        steps["feedback_file"] = True
    else:
        steps["feedback_file"] = False
        errors.append("feedback.json(文件)")

    return {
        "ok": not errors,
        "errors": errors,
        "steps": steps,
        "command_id": fb.command_id,
        "layer": layer,
        "job_name": job_name,
        "part_id": req.part_id,
        "part_name": part_name,
        "offline": client.offline,
    }


@router.post("/stop")
def emergency_stop() -> Dict[str, Any]:
    """紧急停止：写 stop 反馈到 feedback.json（对应桌面「紧急停止」）。"""
    layer, job_name = _current_layer_and_job()
    fb = DetectionFeedback(
        command_id=_next_command_id(),
        layer=layer,
        job_name=job_name,
        device_id="camera_system",
        detection_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    fb.set_action_stop(f"第{layer}层手动紧急停止")
    ok = write_feedback(fb)
    return {"ok": ok, "command_id": fb.command_id, "layer": layer}
