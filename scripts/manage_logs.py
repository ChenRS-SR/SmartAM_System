#!/usr/bin/env python3
"""
SmartAM日志存储管理脚本
======================
用于启动前清理日志、查看当前日志占用。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from utils.log_storage import cleanup_log_storage, get_log_dir  # noqa: E402


def format_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}GB"


def collect_status(log_dir: Path) -> dict:
    files = []
    if log_dir.exists():
        for path in sorted(log_dir.iterdir()):
            if path.is_file() and (path.suffix in {".log", ".out", ".err"} or ".log." in path.name):
                files.append({
                    "path": str(path),
                    "size": path.stat().st_size,
                })
    return {
        "log_dir": str(log_dir),
        "total_size": sum(item["size"] for item in files),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="SmartAM日志存储管理")
    parser.add_argument("--clean", action="store_true", help="按限额清理和轮转日志")
    parser.add_argument("--status", action="store_true", help="显示日志目录占用")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出")
    args = parser.parse_args()

    log_dir = get_log_dir(PROJECT_ROOT)
    result = cleanup_log_storage(log_dir) if args.clean else collect_status(log_dir)
    status = collect_status(log_dir)

    output = {
        "clean_result": result if args.clean else None,
        "status": status,
    }
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    if args.clean:
        removed = result.get("removed", [])
        print(f"[日志清理] 目录: {result['log_dir']}")
        print(f"[日志清理] 当前总量: {format_size(result['total_size'])}")
        print(f"[日志清理] 已删除: {len(removed)} 个旧日志")
    if args.status or not args.clean:
        print(f"[日志状态] 目录: {status['log_dir']}")
        print(f"[日志状态] 当前总量: {format_size(status['total_size'])}")
        for item in status["files"]:
            print(f"  {format_size(item['size']):>8}  {item['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
