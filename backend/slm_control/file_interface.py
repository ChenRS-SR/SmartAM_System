"""SLM 闭环调控 - 文件通信接口（read.json / feedback.json / request.json）。

通信协议：
  read.json     试验台写入事件 → 上位机读取
  feedback.json 上位机写入反馈 → 试验台读取并执行
  request.json  上位机主动请求 → 试验台检查并响应

原样移植自 Desktop/slm/slm_file_interface.py 与 slm_request_protocol.py。
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from .config import COMM_DIR, READ_FILE, FEEDBACK_FILE, REQUEST_FILE
from .models import TestbenchEvent, DetectionFeedback

logger = logging.getLogger(__name__)


def _path(default_name: str, filepath: Optional[Path] = None) -> Path:
    return Path(filepath) if filepath else COMM_DIR / default_name


# ============================================================
# read.json（试验台 → 上位机）
# ============================================================

def read_event(filepath: Optional[Path] = None) -> Optional[TestbenchEvent]:
    """从 read.json 读取试验台事件。返回 TestbenchEvent 或 None。"""
    path = _path(READ_FILE, filepath)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return TestbenchEvent.from_dict(data)
    except FileNotFoundError:
        logger.debug(f"{path} 不存在")
        return None
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"解析 {path} 失败: {e}")
        return None


# ============================================================
# feedback.json（上位机 → 试验台）
# ============================================================

def write_feedback(
    feedback: DetectionFeedback,
    filepath: Optional[Path] = None,
) -> bool:
    """将检测反馈写入 feedback.json（原子写入）。"""
    path = _path(FEEDBACK_FILE, filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = feedback.to_dict()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
        logger.info(
            f"反馈已写入 {path}: action={feedback.action}, "
            f"defects={feedback.defect_count}, "
            f"powder_multiplier={feedback.powder_multiplier}, "
            f"compensation={feedback.compensation}"
        )
        return True
    except OSError as e:
        logger.error(f"写入 {path} 失败: {e}")
        return False


def read_feedback(filepath: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """读取 feedback.json 当前内容。返回 JSON dict 或 None。"""
    path = _path(FEEDBACK_FILE, filepath)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# ============================================================
# request.json（上位机 → 试验台，主动请求）
# ============================================================

def write_request(action: str, **extra) -> bool:
    """向试验台写入一个请求。action: "ping" | "request_status" | "request_sync"。"""
    path = _path(REQUEST_FILE)
    data = {
        "action": action,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "request_id": int(datetime.now().timestamp() * 1000) % 100000,
        **extra,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
        logger.info(f"请求已发送: action={action}, id={data['request_id']}")
        return True
    except OSError as e:
        logger.error(f"写入请求失败: {e}")
        return False


def request_status() -> bool:
    """PC 端主动请求试验台当前状态。"""
    return write_request("request_status")


def request_parameter_sync() -> bool:
    """PC 端主动请求试验台重新发送参数同步。"""
    return write_request("request_sync")


def ping_testbench() -> bool:
    """轻量 ping——确认试验台通信链路正常。"""
    return write_request("ping")
