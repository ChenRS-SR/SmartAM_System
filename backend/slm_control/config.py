"""SLM 闭环调控 - 配置文件。全部可用环境变量覆盖。"""
from __future__ import annotations

import os
from pathlib import Path

PKG = Path(__file__).resolve().parent


def _p(env: str, default) -> Path:
    return Path(os.environ.get(env, str(default))).expanduser()


# ============ 文件通信配置 ============

# 通信目录（read.json / feedback.json / request.json 所在目录）。
# 默认指向包内 sample_comm/，无试验台时仍有一份演示数据可看、可写。
COMM_DIR = _p("SLM_COMM_DIR", PKG / "sample_comm")

READ_FILE = "read.json"        # 试验台 → 上位机：事件通知
FEEDBACK_FILE = "feedback.json"  # 上位机 → 试验台：参数调整 / 停止指令
REQUEST_FILE = "request.json"   # 上位机 → 试验台：主动请求
SAMPLE_PARTS_FILE = "parts.json"  # 试验台离线时回退的样例零件列表

POLL_INTERVAL = 0.5  # 桌面端轮询 read.json 的间隔（Web 端按 ~1s 轮询）

# ============ HTTP API 配置 ============

API_BASE_URL = os.environ.get("SLM_API_BASE_URL", "http://100.84.216.36:18081")
API_TIMEOUT_MS = int(os.environ.get("SLM_API_TIMEOUT_MS", "5000"))

# ============ 参数安全范围 ============

SAFE_RANGES = {
    "fill_power": {
        "min": 50,          # W
        "max": 500,         # W
        "default": 200,     # W
        "unit": "W",
        "description": "填充功率",
    },
    "fill_speed": {
        "min": 100,         # mm/s
        "max": 5000,        # mm/s
        "default": 1000,    # mm/s
        "unit": "mm/s",
        "description": "填充速度",
    },
    "scan_spacing": {
        "min": 0.02,        # mm
        "max": 0.2,         # mm
        "default": 0.1,     # mm
        "unit": "mm",
        "description": "扫描间距",
    },
    "powder_feed_rate": {
        "min": 0.5,         # g/min
        "max": 20.0,        # g/min
        "default": 5.0,     # g/min
        "unit": "g/min",
        "description": "送粉速率",
    },
}

# ============ 综合评分（体能量密度） ============

ENERGY_DENSITY_WINDOW = {
    "min": 50.0,
    "max": 120.0,
}

# 闭环调控允许自动调整的参数
AUTO_ADJUSTABLE_PARAMS = [
    "fill_power",
    "fill_speed",
    "scan_spacing",
    "powder_feed_rate",
]
