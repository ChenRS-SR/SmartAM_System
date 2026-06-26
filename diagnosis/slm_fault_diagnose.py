#!/usr/bin/env python3
"""
SLM表格故障识别命令行入口
========================

示例：
python SmartAM_System/diagnosis/slm_fault_diagnose.py --data-root 7103 --output SmartAM_System/diagnosis/slm_fault_report.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSIS_ROOT = Path(__file__).resolve().parent

# 按文件路径加载诊断模块，避免触发core.slm包初始化时加载实时采集依赖。
DIAGNOSIS_MODULE_PATH = DIAGNOSIS_ROOT / "fault_table_diagnosis.py"
spec = importlib.util.spec_from_file_location("slm_fault_table_diagnosis", DIAGNOSIS_MODULE_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"无法加载诊断模块: {DIAGNOSIS_MODULE_PATH}")
diagnosis_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = diagnosis_module
spec.loader.exec_module(diagnosis_module)

diagnose_dataset = diagnosis_module.diagnose_dataset
diagnose_until_stopped = diagnosis_module.diagnose_until_stopped


DEFAULT_MODEL = DIAGNOSIS_ROOT / "slm_fault_rules.json"


def resolve_project_path(raw_path: str) -> Path:
    """命令行相对路径默认按项目根目录解析，方便跨设备复制 7103 数据。"""

    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def project_relative_text(value: str) -> str:
    try:
        path = Path(value)
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        return path.relative_to(PROJECT_ROOT).as_posix()
    except (ValueError, OSError):
        return value


def make_report_paths_relative(report: dict) -> dict:
    """报告内只保存项目相对路径，避免把本机绝对路径写入文件级数据库。"""

    for key in ("data_root", "model_path"):
        if isinstance(report.get(key), str):
            report[key] = project_relative_text(report[key])

    for status in report.get("device_latest_status", {}).values():
        normalize_status_paths(status)
    for status in report.get("cases", []):
        normalize_status_paths(status)
    return report


def normalize_status_paths(status: dict) -> None:
    if isinstance(status.get("case_dir"), str):
        status["case_dir"] = project_relative_text(status["case_dir"])
    if isinstance(status.get("source_files"), list):
        status["source_files"] = [
            project_relative_text(item) if isinstance(item, str) else item
            for item in status["source_files"]
        ]
    for evidence in status.get("evidence", []):
        if isinstance(evidence, dict) and isinstance(evidence.get("file"), str):
            evidence["file"] = project_relative_text(evidence["file"])


def post_latest_status(report: dict, api_url: str, device_id: str | None = None) -> None:
    latest_status = report["device_latest_status"]
    if device_id:
        if device_id not in latest_status:
            raise ValueError(f"报告中未找到设备: {device_id}")
        selected = latest_status[device_id]
    else:
        fault_devices = [
            item for item in latest_status.values()
            if int(item.get("status_code", -1)) > 0
        ]
        selected = fault_devices[0] if fault_devices else next(iter(latest_status.values()))

    query = urlencode(
        {
            "status_code": int(selected["status_code"]),
            "labels": selected["status_labels"],
        },
        doseq=True,
    )
    separator = "&" if "?" in api_url else "?"
    request = Request(f"{api_url}{separator}{query}", data=b"", method="POST")
    with urlopen(request, timeout=5) as response:
        body = response.read().decode("utf-8")
    print(f"[SLM表格诊断] 已推送状态到 {api_url}: {body}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="递归读取SLM CSV数据并输出故障状态码")
    parser.add_argument("--data-root", required=True, help="CSV数据根目录，例如 7103")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="规则模型JSON路径")
    parser.add_argument("--output", required=True, help="诊断报告JSON输出路径")
    parser.add_argument("--watch", action="store_true", help="持续监控目录，有新增CSV时自动重新输出")
    parser.add_argument("--interval", type=int, default=30, help="watch模式轮询间隔，单位秒")
    parser.add_argument("--api-url", help="可选：推送到SLM后端，例如 http://127.0.0.1:8000/slm/health/status")
    parser.add_argument("--device-id", help="可选：推送指定设备的最新状态，例如 B40")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    data_root = resolve_project_path(args.data_root).resolve()
    model_path = resolve_project_path(args.model).resolve()
    output_path = resolve_project_path(args.output).resolve()

    if args.watch:
        diagnose_until_stopped(data_root, model_path, output_path, args.interval)
        return 0

    report = make_report_paths_relative(diagnose_dataset(data_root, model_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SLM表格诊断] 报告已输出: {output_path}")
    print(
        "[SLM表格诊断] 汇总: "
        f"CSV={report['total_csv_files']}, 批次={report['total_cases']}, "
        f"设备={report['device_count']}, 状态分布={report['status_counts']}"
    )

    if args.api_url:
        post_latest_status(report, args.api_url, args.device_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
