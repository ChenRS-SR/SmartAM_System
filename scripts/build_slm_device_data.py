#!/usr/bin/env python3
"""
根据 7103 诊断报告生成前端设备群监测数据。

生成结果放在项目根目录的 slm_device_data/，每个设备卡片都有独立目录，
包含设备信息 JSON、thumbnail 图片、真实数据预览 CSV 和原始数据路径清单。
"""

from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = PROJECT_ROOT / "diagnosis" / "slm_fault_report.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "slm_device_data"
DEVICE_ROOT_NAME = "SLM"
THUMBNAIL_ASSET = PROJECT_ROOT / "scripts" / "assets" / "slm_thumbnail.jpg"
SUPPORTED_THUMBNAIL_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}

CSV_ENCODINGS = ("utf-8-sig", "utf-16", "gb18030")

STATUS_CODE_MAP_0_4 = {
    0: "健康",
    1: "铺粉/刮刀系统异常",
    2: "激光器/水冷机异常",
    3: "气氛循环系统异常",
    4: "复合故障",
}

CATEGORY_TO_FRONTEND_CODE = {
    "powder_spreading_abnormal": 1,
    "scraper_torque_position_fault": 1,
    "servo_drive_fault": 1,
    "powder_axis_fault": 1,
    "powder_storage_fault": 1,
    "laser_chiller_fault": 2,
    "oxygen_abnormal": 3,
    "fan_fault": 3,
    "air_pressure_fault": 3,
    "filter_fault": 3,
    "valve_switch_fault": 3,
    "ash_bucket_fault": 3,
    "scan_emergency_fault": 4,
    "parameter_config_fault": 4,
}

STATUS_STYLE = {
    0: {"color": "#22c55e", "health": "healthy", "text": "健康运行"},
    1: {"color": "#f97316", "health": "fault", "text": "铺粉/刮刀异常"},
    2: {"color": "#ef4444", "health": "fault", "text": "激光系统异常"},
    3: {"color": "#0ea5e9", "health": "fault", "text": "气氛循环异常"},
    4: {"color": "#dc2626", "health": "fault", "text": "复合故障"},
}

# 目前7103中绝大多数设备按铂力特设备显示；B17暂作为唯一华科设备占位。
# 后续接真实设备数据库时，只需要把这里的归属/标签字段替换成数据库转换结果。
DEVICE_OWNER_OVERRIDES = {
    "B17": "华科",
}

PARAMETER_FIELDS = (
    ("current_layer", "层数", "当前层"),
    ("sequence", "序号", "数据序号"),
    ("scraper_torque", "刮刀扭矩", "刮刀扭矩"),
    ("compressed_air_pressure", "压缩空气压力", "压缩空气压力"),
    ("gas_pressure", "气源压力", "气源压力"),
    ("oxygen", "成形室氧含量", "成形室氧含量"),
    ("ambient_oxygen", "环境氧含量", "环境氧含量"),
    ("fan_speed", "风机转速", "风机转速"),
    ("chamber_temperature", "成形室温度", "成形室温度"),
    ("gas_flow", "循环气体实时流量", "循环气体流量"),
    ("medium_filter_resistance", "中效滤芯阻力", "中效滤芯阻力"),
    ("high_filter_resistance", "高效滤芯阻力", "高效滤芯阻力"),
    ("servo_temperature_x", "伺服温度[X轴]", "X轴伺服温度"),
    ("servo_temperature_y", "伺服温度[Y轴]", "Y轴伺服温度"),
    ("galvo_temperature_x", "振镜温度[X轴]", "X轴振镜温度"),
    ("galvo_temperature_y", "振镜温度[Y轴]", "Y轴振镜温度"),
    ("output_current_x", "输出电流[X轴]", "X轴输出电流"),
    ("output_current_y", "输出电流[Y轴]", "Y轴输出电流"),
)


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_folder_name(name: str) -> str:
    """设备目录按设备名命名，仅替换文件系统不允许的分隔符。"""

    return re.sub(r"[\\/:\0]+", "-", name).strip() or "未命名设备"


def resolve_project_path(raw_path: str | Path) -> Path:
    """文件数据库保存相对路径，读取时统一按项目根目录解析。"""

    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def project_relative_text(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except (ValueError, OSError):
        return str(path)


def device_sort_key(device_id: str) -> Tuple[int, str]:
    match = re.search(r"\d+", device_id)
    return (int(match.group(0)) if match else 9999, device_id)


def case_time_key(case_dir: str) -> Tuple[str, str]:
    """从目录名中提取时间戳；提取不到时用完整路径保证排序稳定。"""

    patterns = re.findall(r"(20\d{6}[-_]?\d{0,6}|20\d{2}-\d{2}-\d{2})", case_dir)
    return (max(patterns) if patterns else "", case_dir)


def select_latest_status_by_device(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """设备群页面展示“当前感”状态，因此每台设备取最近一次诊断样本。"""

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for case in report.get("cases", []):
        device_id = case.get("device_id")
        if device_id and device_id != "UNKNOWN":
            grouped[device_id].append(case)

    if not grouped:
        return report.get("device_latest_status", {})

    return {
        device_id: max(cases, key=lambda item: case_time_key(item.get("case_dir", "")))
        for device_id, cases in grouped.items()
    }


def normalize_frontend_status(categories: Iterable[str], raw_status_code: int) -> int:
    """把诊断模型细分状态归并到当前前端支持的 0-4 状态码。"""

    if raw_status_code == 0:
        return 0

    mapped_codes = {
        CATEGORY_TO_FRONTEND_CODE.get(category, 4)
        for category in categories
    }
    mapped_codes.discard(0)
    if not mapped_codes:
        return 4
    if len(mapped_codes) == 1:
        return mapped_codes.pop()
    return 4


def health_status_name(status_code: int) -> str:
    return {
        -1: "power_off",
        0: "healthy",
        1: "powder_fault",
        2: "laser_fault",
        3: "gas_fault",
        4: "compound_fault",
    }.get(status_code, "compound_fault")


def build_health_data(status_code: int, status_labels: List[str], categories: List[str]) -> Dict[str, Any]:
    """按前端健康控件字段组织子系统状态。"""

    health = {
        "status": health_status_name(status_code),
        "status_code": status_code,
        "status_labels": status_labels,
        "laser_system": {"status": "healthy", "message": "健康"},
        "powder_system": {"status": "healthy", "message": "健康"},
        "gas_system": {"status": "healthy", "message": "健康"},
    }

    if status_code == 0:
        return health

    if status_code in (1, 4) or any(CATEGORY_TO_FRONTEND_CODE.get(item) == 1 for item in categories):
        health["powder_system"] = {"status": "fault", "message": "铺粉/刮刀系统异常"}
    if status_code in (2, 4) or any(CATEGORY_TO_FRONTEND_CODE.get(item) == 2 for item in categories):
        health["laser_system"] = {"status": "fault", "message": "激光器/水冷机异常"}
    if status_code in (3, 4) or any(CATEGORY_TO_FRONTEND_CODE.get(item) == 3 for item in categories):
        health["gas_system"] = {"status": "fault", "message": "气氛循环系统异常"}

    if status_code == 4:
        for key in ("laser_system", "powder_system", "gas_system"):
            if health[key]["status"] != "fault":
                health[key] = {"status": "fault", "message": "需检查"}

    return health


def split_name_unit(header: str) -> Tuple[str, str]:
    name = header.strip()
    unit = ""
    match = re.search(r"[(（]([^()（）]*)[)）]", name)
    if match:
        unit = match.group(1).strip()
        name = re.sub(r"[(（][^()（）]*[)）]", "", name).strip()
    return name, unit


def format_value(value: Any) -> str:
    raw = str(value).strip()
    if raw == "":
        return "--"
    try:
        number = float(raw)
    except ValueError:
        return raw
    if number.is_integer():
        return str(int(number))
    return f"{number:.3f}".rstrip("0").rstrip(".")


def open_csv(path: Path):
    last_error: Optional[UnicodeError] = None
    for encoding in CSV_ENCODINGS:
        try:
            file_obj = path.open("r", encoding=encoding, newline="")
            file_obj.read(1)
            file_obj.seek(0)
            return file_obj
        except UnicodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    return path.open("r", encoding="utf-8", newline="")


def read_last_data_row(csv_path: Path) -> Tuple[List[str], Dict[str, str]]:
    with open_csv(csv_path) as file_obj:
        reader = csv.DictReader(file_obj)
        headers = reader.fieldnames or []
        last_row: Dict[str, str] = {}
        for row in reader:
            if any(str(value).strip() for value in row.values()):
                last_row = {str(key): str(value) for key, value in row.items() if key is not None}
        return headers, last_row


def is_numeric_data_csv(csv_path: Path) -> bool:
    name = csv_path.name
    if any(skip in name for skip in ("设备信息", "报警日志", "打印日志")):
        return False
    try:
        headers, row = read_last_data_row(csv_path)
    except Exception:
        return False
    joined = "".join(headers)
    return bool(row) and any(word in joined for word in ("层数", "时间", "刮刀", "压力", "氧含量", "温度", "风机"))


def pick_representative_csv(status: Dict[str, Any]) -> Optional[Path]:
    source_files = [resolve_project_path(item) for item in status.get("source_files", [])]
    for csv_path in source_files:
        if csv_path.exists() and is_numeric_data_csv(csv_path):
            return csv_path

    case_dir = resolve_project_path(status.get("case_dir", ""))
    if case_dir.exists():
        for csv_path in sorted(case_dir.rglob("*.csv")):
            if is_numeric_data_csv(csv_path):
                return csv_path

        device_tag = status.get("device_id", "")
        for parent in [case_dir, *case_dir.parents]:
            if device_tag and device_tag in parent.name:
                for csv_path in sorted(parent.rglob("*.csv")):
                    if is_numeric_data_csv(csv_path):
                        return csv_path
                break
    return None


def build_parameters(csv_path: Optional[Path]) -> Tuple[List[Dict[str, str]], Optional[str], Optional[str]]:
    if csv_path is None:
        return [], None, None

    headers, row = read_last_data_row(csv_path)
    parameters: List[Dict[str, str]] = []
    used_headers: set[str] = set()

    for param_id, keyword, display_name in PARAMETER_FIELDS:
        header = next((item for item in headers if keyword.lower() in item.lower()), None)
        if not header or header in used_headers:
            continue
        used_headers.add(header)
        _, unit = split_name_unit(header)
        parameters.append(
            {
                "id": param_id,
                "name": display_name,
                "value": format_value(row.get(header, "")),
                "unit": unit,
            }
        )
        if len(parameters) >= 8:
            break

    data_time = row.get("时间") or row.get("采集时间")
    return parameters, data_time, project_relative_text(csv_path)


def write_preview_csv(source: Optional[Path], target: Path, max_rows: int = 120) -> None:
    if source is None:
        target.write_text("", encoding="utf-8")
        return

    with open_csv(source) as file_obj:
        reader = csv.reader(file_obj)
        rows = []
        for index, row in enumerate(reader):
            rows.append(row)
            if index >= max_rows:
                break

    with target.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.writer(file_obj, lineterminator="\n")
        writer.writerows(rows)


def parse_device_info(status: Dict[str, Any]) -> Dict[str, str]:
    info_file = next(
        (
            resolve_project_path(item)
            for item in status.get("source_files", [])
            if "设备信息" in Path(item).name and resolve_project_path(item).exists()
        ),
        None,
    )
    info: Dict[str, str] = {}
    if info_file is None:
        return info

    with open_csv(info_file) as file_obj:
        for line in file_obj:
            text = line.strip().strip(",")
            if ":" in text:
                key, value = text.split(":", 1)
                info[key.strip()] = value.strip()
    return info


def copy_thumbnail_asset(device_dir: Path) -> str:
    """每台设备目录只认 thumbnail.*，扩展名用于区分图片格式。"""

    if not THUMBNAIL_ASSET.exists():
        raise FileNotFoundError(f"缺少设备缩略图资产: {THUMBNAIL_ASSET}")
    suffix = THUMBNAIL_ASSET.suffix.lower()
    if suffix not in SUPPORTED_THUMBNAIL_SUFFIXES:
        raise ValueError(f"不支持的缩略图格式: {THUMBNAIL_ASSET.name}")
    thumbnail_name = f"thumbnail{suffix}"
    shutil.copy2(THUMBNAIL_ASSET, device_dir / thumbnail_name)
    return thumbnail_name


def build_device_record(device_tag: str, status: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    raw_status_code = int(status.get("status_code", -1))
    categories = list(status.get("categories", []))
    frontend_status_code = normalize_frontend_status(categories, raw_status_code)
    frontend_label = STATUS_CODE_MAP_0_4[frontend_status_code]
    style = STATUS_STYLE[frontend_status_code]
    info = parse_device_info(status)
    model = info.get("设备名称") or ("S400" if "S400" in status.get("case_dir", "") else "S310")
    serial = info.get("序列号") or device_tag
    device_id = f"slm-{device_tag.lower()}"
    owner = DEVICE_OWNER_OVERRIDES.get(device_tag, "铂力特")
    display_name = f"华科SLM {device_tag}" if owner == "华科" else f"铂力特 {model} {device_tag}"
    database_tag = f"{owner}-{model}-{device_tag}"
    device_folder = safe_folder_name(display_name)
    device_dir = output_dir / DEVICE_ROOT_NAME / device_folder
    device_dir.mkdir(parents=True, exist_ok=True)

    representative_csv = pick_representative_csv(status)
    parameters, data_time, representative_csv_path = build_parameters(representative_csv)
    if not parameters:
        parameters = [{"id": "diagnosis_status", "name": "诊断状态码", "value": str(frontend_status_code), "unit": ""}]

    status_labels = [frontend_label]
    for label in status.get("status_labels", [])[:4]:
        if label not in status_labels:
            status_labels.append(label)
    health_data = build_health_data(frontend_status_code, status_labels, categories)

    thumbnail_name = copy_thumbnail_asset(device_dir)

    preview_path = device_dir / "real_data" / "preview.csv"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    write_preview_csv(representative_csv, preview_path)

    source_manifest = {
        "source_case_dir": status.get("case_dir"),
        "source_files": status.get("source_files", []),
        "representative_csv": representative_csv_path,
        "preview_csv": str(preview_path.relative_to(DEFAULT_OUTPUT)),
    }
    write_json(device_dir / "real_data" / "source_manifest.json", source_manifest)

    device_record = {
        "id": device_id,
        "tag": device_tag,
        "dataTag": f"7103-{device_tag}",
        "databaseTag": database_tag,
        "owner": owner,
        "name": display_name,
        "model": f"铂力特 {model}",
        "serial": serial,
        "location": "7103 现场数据设备群",
        "online": True,
        "health": style["health"],
        "statusText": style["text"],
        "thumbnail": f"/slm_device_data/{DEVICE_ROOT_NAME}/{quote(device_folder)}/{thumbnail_name}",
        "dataDirectory": f"slm_device_data/{DEVICE_ROOT_NAME}/{device_folder}",
        "parameters": parameters,
        "updatedAt": data_time or status.get("diagnosed_at"),
        "healthData": health_data,
        "diagnosis": {
            "source": "7103最近样本",
            "rawStatusCode": raw_status_code,
            "rawStatusLabel": status.get("status_label"),
            "frontendStatusCode": frontend_status_code,
            "frontendStatusLabel": frontend_label,
            "categories": categories,
            "confidence": status.get("confidence"),
            "evidence": status.get("evidence", [])[:5],
        },
        "realData": source_manifest,
    }
    write_json(device_dir / "device.json", device_record)
    return device_record


def main() -> int:
    report = read_json(DEFAULT_REPORT)
    output_dir = DEFAULT_OUTPUT
    if output_dir.exists():
        shutil.rmtree(output_dir)
    (output_dir / DEVICE_ROOT_NAME).mkdir(parents=True, exist_ok=True)

    device_latest_status = select_latest_status_by_device(report)
    devices = []
    for device_tag in sorted(device_latest_status, key=device_sort_key):
        devices.append(build_device_record(device_tag, device_latest_status[device_tag], output_dir))

    manifest = {
        "version": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sourceRoot": report.get("data_root"),
        "diagnosisReport": project_relative_text(DEFAULT_REPORT),
        "diagnosisPolicy": "每台设备取 7103 中最近一次诊断样本，并归并到前端 0-4 状态码。",
        "statusCodeMap": {str(key): value for key, value in STATUS_CODE_MAP_0_4.items()},
        "categoryToFrontendCode": CATEGORY_TO_FRONTEND_CODE,
        "deviceCount": len(devices),
        "devices": devices,
    }
    write_json(output_dir / "manifest.json", manifest)
    print(f"[SLM设备群数据] 已生成 {len(devices)} 台设备: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
