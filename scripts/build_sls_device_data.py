#!/usr/bin/env python3
"""
根据已生成的 SLM 文件数据库，复制出同构 SLS 模拟设备群数据。

SLS 当前没有独立现场数据，因此这里保留与 SLM 相同的模拟案例结构，
只替换设备命名、文件根目录和缩略图；后续替换视频或真实 CSV 时不需要改前端。
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote

from build_slm_device_data import (
    STATUS_CODE_MAP_0_4,
    SUPPORTED_THUMBNAIL_SUFFIXES,
    project_relative_text,
    safe_folder_name,
    write_json,
    write_preview_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SLM_MANIFEST = PROJECT_ROOT / "slm_device_data" / "manifest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "sls_device_data"
DEVICE_ROOT_NAME = "SLS"
THUMBNAIL_ASSET = PROJECT_ROOT / "scripts" / "assets" / "sls_thumbnail.jpg"
DEVICE_COUNT = 10


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def resolve_project_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else PROJECT_ROOT / path


def copy_sls_thumbnail(device_dir: Path) -> str:
    """SLS 与 SLM 一样只认 thumbnail.*，当前资产为 JPEG。"""

    if not THUMBNAIL_ASSET.exists():
        raise FileNotFoundError(f"缺少SLS设备缩略图资产: {THUMBNAIL_ASSET}")
    suffix = THUMBNAIL_ASSET.suffix.lower()
    if suffix not in SUPPORTED_THUMBNAIL_SUFFIXES:
        raise ValueError(f"不支持的SLS缩略图格式: {THUMBNAIL_ASSET.name}")
    thumbnail_name = f"thumbnail{suffix}"
    shutil.copy2(THUMBNAIL_ASSET, device_dir / thumbnail_name)
    return thumbnail_name


def build_sls_record(index: int, source_device: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    tag = f"S{index:02d}"
    display_name = f"华中数控SLS {tag}"
    device_folder = safe_folder_name(display_name)
    device_dir = output_dir / DEVICE_ROOT_NAME / device_folder
    device_dir.mkdir(parents=True, exist_ok=True)

    source_manifest = dict(source_device.get("realData") or {})
    representative_csv = source_manifest.get("representative_csv") or ""
    representative_path = resolve_project_path(representative_csv) if representative_csv else None
    preview_path = device_dir / "real_data" / "preview.csv"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    write_preview_csv(representative_path if representative_path and representative_path.exists() else None, preview_path)

    sls_manifest = {
        "source_case_dir": source_manifest.get("source_case_dir", ""),
        "source_files": source_manifest.get("source_files", []),
        "representative_csv": representative_csv,
        "preview_csv": f"{DEVICE_ROOT_NAME}/{device_folder}/real_data/preview.csv",
        "copiedFrom": source_device.get("id", ""),
    }
    write_json(device_dir / "real_data" / "source_manifest.json", sls_manifest)

    thumbnail_name = copy_sls_thumbnail(device_dir)
    device_record = {
        **source_device,
        "id": f"sls-{tag.lower()}",
        "tag": tag,
        "dataTag": f"SLS-{tag}",
        "databaseTag": f"华中数控-SLS-{tag}",
        "owner": "华中数控",
        "name": display_name,
        "model": "华中数控 SLS",
        "serial": tag,
        "location": "SLS 模拟设备群",
        "thumbnail": f"/sls_device_data/{DEVICE_ROOT_NAME}/{quote(device_folder)}/{thumbnail_name}",
        "dataDirectory": f"sls_device_data/{DEVICE_ROOT_NAME}/{device_folder}",
        "diagnosis": {
            **(source_device.get("diagnosis") or {}),
            "source": "SLM同构模拟案例",
            "copiedFromDevice": source_device.get("id", ""),
        },
        "realData": sls_manifest,
    }
    write_json(device_dir / "device.json", device_record)
    return device_record


def main() -> int:
    slm_manifest = read_json(SLM_MANIFEST)
    source_devices: List[Dict[str, Any]] = list(slm_manifest.get("devices", []))[:DEVICE_COUNT]
    if len(source_devices) < DEVICE_COUNT:
        raise ValueError(f"SLM源设备不足 {DEVICE_COUNT} 台，无法生成完整SLS设备群")

    if DEFAULT_OUTPUT.exists():
        shutil.rmtree(DEFAULT_OUTPUT)
    (DEFAULT_OUTPUT / DEVICE_ROOT_NAME).mkdir(parents=True, exist_ok=True)

    devices = [
        build_sls_record(index, source_device, DEFAULT_OUTPUT)
        for index, source_device in enumerate(source_devices)
    ]
    manifest = {
        "version": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sourceRoot": slm_manifest.get("sourceRoot", ""),
        "sourceMirror": project_relative_text(SLM_MANIFEST),
        "diagnosisReport": slm_manifest.get("diagnosisReport", ""),
        "diagnosisPolicy": "SLS暂使用SLM同构模拟案例；设备名替换为华中数控SLS S00-S09。",
        "statusCodeMap": {str(key): value for key, value in STATUS_CODE_MAP_0_4.items()},
        "categoryToFrontendCode": slm_manifest.get("categoryToFrontendCode", {}),
        "parameterSchema": slm_manifest.get("parameterSchema", []),
        "deviceCount": len(devices),
        "devices": devices,
    }
    write_json(DEFAULT_OUTPUT / "manifest.json", manifest)
    print(f"[SLS设备群数据] 已生成 {len(devices)} 台设备: {DEFAULT_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
