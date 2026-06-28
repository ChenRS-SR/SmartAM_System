"""
SLM/SLS 设备群文件数据库。

该模块只读取项目根目录下的 manifest.json，不生成兜底设备。
如果数据目录不存在，接口会明确报错，避免前端误以为仍在使用真实数据。
"""

from __future__ import annotations

import json
import base64
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import quote, unquote


SUPPORTED_THUMBNAIL_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".svg")
SUPPORTED_MOCK_VIDEO_SUFFIXES = (".mp4", ".webm", ".ogg", ".mov", ".m4v")
MOCK_VIDEO_CHANNELS = {
    "camera_ch1": "CH1",
    "camera_ch2": "CH2",
    "thermal": "CH3",
}
THUMBNAIL_MIME_SUFFIX = {
    "png": ".png",
    "jpg": ".jpg",
    "jpeg": ".jpg",
    "webp": ".webp",
    "svg+xml": ".svg",
    "svg": ".svg",
}


class SLMDeviceDataStore:
    """读取由脚本生成的设备群文件数据库。"""

    def __init__(
        self,
        project_root: Path | None = None,
        data_dir_name: str = "slm_device_data",
        device_root_name: str = "SLM",
        public_mount: str = "/slm_device_data",
        label: str = "SLM",
    ):
        self.project_root = project_root or Path(__file__).resolve().parents[2]
        self.data_dir_name = data_dir_name
        self.device_root_name = device_root_name
        self.public_mount = public_mount.rstrip("/")
        self.label = label
        self.data_root = self.project_root / data_dir_name
        self.device_root = self.data_root / device_root_name
        self.manifest_path = self.data_root / "manifest.json"

    def load_manifest(self) -> Dict[str, Any]:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"{self.label}设备群数据清单不存在: {self.manifest_path}")
        with self.manifest_path.open("r", encoding="utf-8") as file_obj:
            return json.load(file_obj)

    def save_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        manifest["deviceCount"] = len(manifest.get("devices", []))
        manifest["databaseUpdatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.data_root.mkdir(parents=True, exist_ok=True)
        tmp_path = self.manifest_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.manifest_path)
        return manifest

    def list_devices(self) -> List[Dict[str, Any]]:
        return [self._attach_mock_video_scan(device) for device in self.load_manifest().get("devices", [])]

    def get_device(self, device_id: str) -> Dict[str, Any]:
        for device in self.list_devices():
            if device.get("id") == device_id or device.get("tag") == device_id:
                return device
        raise KeyError(f"未找到{self.label}设备: {device_id}")

    def _safe_device_id(self, raw_id: str) -> str:
        safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw_id.strip()).strip("-").lower()
        if not safe_id:
            raise ValueError("设备ID不能为空")
        return safe_id

    def _safe_folder_name(self, raw_name: str) -> str:
        return re.sub(r"[\\/:\0]+", "-", raw_name.strip()).strip() or "未命名设备"

    def _resolve_project_path(self, raw_path: str | Path) -> Path:
        path = Path(raw_path)
        return path if path.is_absolute() else self.project_root / path

    def _device_dir(self, device: Dict[str, Any]) -> Path:
        folder_name = self._safe_folder_name(str(device.get("name") or device.get("id") or "未命名设备"))
        return self.device_root / folder_name

    def _resolve_device_dir(self, device: Dict[str, Any]) -> Path:
        data_directory = device.get("dataDirectory")
        if data_directory:
            return self._resolve_project_path(str(data_directory))
        return self._device_dir(device)

    def _normalize_online_state(self, device: Dict[str, Any]) -> None:
        if not isinstance(device.get("online"), bool):
            raise ValueError("online必须是true或false")

    def _ensure_device_layout(self, device_dir: Path) -> None:
        (device_dir / "real_data").mkdir(parents=True, exist_ok=True)
        for folder_name in ("mock_video", "mock_video_corrected"):
            for channel_folder in MOCK_VIDEO_CHANNELS.values():
                (device_dir / folder_name / channel_folder).mkdir(parents=True, exist_ok=True)

    def _public_device_path(self, device_dir: Path, filename: str) -> str:
        return f"{self.public_mount}/{self.device_root_name}/{quote(device_dir.name)}/{filename}"

    def _public_file_path(self, file_path: Path) -> str:
        relative_path = file_path.relative_to(self.data_root)
        return f"{self.public_mount}/" + "/".join(quote(part) for part in relative_path.parts)

    def _scan_channel_video(self, video_root: Path, channel_folder: str) -> Dict[str, Any]:
        channel_dir = video_root / channel_folder
        if not channel_dir.exists():
            return {
                "available": False,
                "channel": channel_folder,
                "reason": f"{channel_folder}目录不存在"
            }

        files = sorted(path for path in channel_dir.iterdir() if path.is_file())
        supported_files = [path for path in files if path.suffix.lower() in SUPPORTED_MOCK_VIDEO_SUFFIXES]
        unsupported_files = [path.name for path in files if path.suffix.lower() not in SUPPORTED_MOCK_VIDEO_SUFFIXES]

        if not supported_files:
            reason = "未发现支持格式视频" if files else "通道目录为空"
            return {
                "available": False,
                "channel": channel_folder,
                "directory": str(channel_dir),
                "reason": reason,
                "unsupportedFiles": unsupported_files
            }

        video_file = supported_files[0]
        return {
            "available": True,
            "channel": channel_folder,
            "filename": video_file.name,
            "url": self._public_file_path(video_file),
            "media_type": "video",
            "unsupportedFiles": unsupported_files
        }

    def _scan_mock_video_folder(self, device_dir: Path, folder_name: str) -> Dict[str, Any]:
        video_root = device_dir / folder_name
        if not video_root.exists():
            return {
                "folder": folder_name,
                "exists": False,
                "ready": False,
                "channels": {}
            }

        channels = {
            key: self._scan_channel_video(video_root, channel_folder)
            for key, channel_folder in MOCK_VIDEO_CHANNELS.items()
        }
        return {
            "folder": folder_name,
            "exists": True,
            "ready": any(channel.get("available") for channel in channels.values()),
            "allReady": all(channel.get("available") for channel in channels.values()),
            "channels": channels
        }

    def _attach_mock_video_scan(self, device: Dict[str, Any]) -> Dict[str, Any]:
        next_device = dict(device)
        self._normalize_online_state(next_device)
        device_dir = self._resolve_device_dir(next_device)
        raw_scan = self._scan_mock_video_folder(device_dir, "mock_video")
        corrected_scan = self._scan_mock_video_folder(device_dir, "mock_video_corrected")

        # 模拟视频只按设备目录下的通道文件夹识别，不读取固定文件名。
        next_device["mockVideo"] = {
            "supported": raw_scan["ready"],
            "dataDirectory": str(device_dir.relative_to(self.project_root)) if device_dir.exists() else str(device_dir),
            "message": "已扫描到模拟视频" if raw_scan["ready"] else "暂不支持接入",
            "sourceFolderExists": raw_scan["exists"],
            "channels": raw_scan["channels"],
            "correctedSupported": corrected_scan["ready"],
            "correctedSourceFolderExists": corrected_scan["exists"],
            "correctedChannels": corrected_scan["channels"],
            "sourceFolder": raw_scan["folder"],
            "correctedSourceFolder": corrected_scan["folder"],
        }
        return next_device

    def _find_thumbnail_file(self, device_dir: Path) -> Path | None:
        for suffix in SUPPORTED_THUMBNAIL_SUFFIXES:
            candidate = device_dir / f"thumbnail{suffix}"
            if candidate.exists():
                return candidate
        return None

    def _remove_thumbnail_files(self, device_dir: Path) -> None:
        for thumbnail_file in device_dir.glob("thumbnail.*"):
            if thumbnail_file.suffix.lower() in SUPPORTED_THUMBNAIL_SUFFIXES:
                thumbnail_file.unlink()

    def _save_thumbnail(self, device: Dict[str, Any], device_dir: Path) -> None:
        thumbnail = device.get("thumbnail", "")
        if not isinstance(thumbnail, str) or not thumbnail.startswith("data:image/"):
            return

        header, encoded = thumbnail.split(",", 1)
        mime_type = header.removeprefix("data:image/").split(";", 1)[0].lower()
        suffix = THUMBNAIL_MIME_SUFFIX.get(mime_type)
        if suffix is None:
            raise ValueError(f"不支持的缩略图格式: image/{mime_type}")

        self._remove_thumbnail_files(device_dir)
        thumbnail_name = f"thumbnail{suffix}"
        thumbnail_path = device_dir / thumbnail_name
        if suffix == ".svg":
            payload = base64.b64decode(encoded).decode("utf-8") if ";base64" in header else unquote(encoded)
            thumbnail_path.write_text(payload, encoding="utf-8")
        else:
            if ";base64" not in header:
                raise ValueError("PNG/JPEG/WEBP缩略图必须使用base64数据")
            thumbnail_path.write_bytes(base64.b64decode(encoded))
        device["thumbnail"] = self._public_device_path(device_dir, thumbnail_name)

    def _write_device_files(self, device: Dict[str, Any]) -> Dict[str, Any]:
        device.pop("mockVideo", None)
        self._normalize_online_state(device)
        device_id = self._safe_device_id(str(device.get("id", "")))
        device["id"] = device_id
        device_dir = self._device_dir(device)
        self._ensure_device_layout(device_dir)
        real_data_dir = device_dir / "real_data"

        self._save_thumbnail(device, device_dir)
        thumbnail_file = self._find_thumbnail_file(device_dir)
        if thumbnail_file is not None:
            device["thumbnail"] = self._public_device_path(device_dir, thumbnail_file.name)
        device["dataDirectory"] = f"{self.data_dir_name}/{self.device_root_name}/{device_dir.name}"
        device["databaseUpdatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")

        source_manifest = device.get("realData") or {
            "source_case_dir": "",
            "source_files": [],
            "representative_csv": "",
            "preview_csv": "",
        }
        source_manifest["preview_csv"] = f"{self.device_root_name}/{device_dir.name}/real_data/preview.csv"
        (real_data_dir / "source_manifest.json").write_text(
            json.dumps(source_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        preview_path = real_data_dir / "preview.csv"
        representative_csv = source_manifest.get("representative_csv")
        representative_path = self._resolve_project_path(representative_csv) if representative_csv else None
        if representative_path and representative_path.exists() and not preview_path.exists():
            shutil.copy2(representative_path, preview_path)
        elif not preview_path.exists():
            preview_path.write_text("", encoding="utf-8")

        (device_dir / "device.json").write_text(
            json.dumps(device, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return device

    def _migrate_thumbnail(self, device: Dict[str, Any], old_dir: Path, new_dir: Path) -> Dict[str, Any]:
        if old_dir == new_dir or not old_dir.exists():
            return device
        old_thumbnail = self._find_thumbnail_file(old_dir)
        if old_thumbnail is None:
            return device
        new_thumbnail = new_dir / old_thumbnail.name
        if not new_thumbnail.exists():
            shutil.copy2(old_thumbnail, new_thumbnail)
        device["thumbnail"] = self._public_device_path(new_dir, old_thumbnail.name)
        (new_dir / "device.json").write_text(
            json.dumps(device, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return device

    def upsert_device(self, device: Dict[str, Any]) -> Dict[str, Any]:
        manifest = self.load_manifest()
        devices = manifest.get("devices", [])
        device_id = self._safe_device_id(str(device.get("id", "")))
        old_device = next((item for item in devices if item.get("id") == device_id), {})
        old_dir = self._device_dir(old_device) if old_device else None
        next_device = {**old_device, **device, "id": device_id}
        next_device = self._write_device_files(next_device)
        new_dir = self._device_dir(next_device)
        if old_dir:
            next_device = self._migrate_thumbnail(next_device, old_dir, new_dir)
        if old_dir and old_dir != new_dir and old_dir.exists():
            shutil.rmtree(old_dir)

        replaced = False
        next_devices: List[Dict[str, Any]] = []
        for item in devices:
            if item.get("id") == device_id:
                next_devices.append(next_device)
                replaced = True
            else:
                next_devices.append(item)
        if not replaced:
            next_devices.append(next_device)

        manifest["devices"] = next_devices
        self.save_manifest(manifest)
        return next_device

    def patch_device(self, device_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_device(device_id)
        return self.upsert_device({**current, **patch, "id": current["id"]})

    def sync_devices(self, devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        manifest = self.load_manifest()
        old_devices = {device.get("id"): device for device in manifest.get("devices", [])}
        next_devices = []
        active_dirs = set()

        for device in devices:
            next_device = self._write_device_files(dict(device))
            new_dir = self._device_dir(next_device)
            old_device = old_devices.get(next_device.get("id"))
            if old_device:
                # 设备改名时沿用原缩略图，保持页面数据库和文件夹结构一致。
                next_device = self._migrate_thumbnail(next_device, self._device_dir(old_device), new_dir)
            active_dirs.add(new_dir.resolve())
            next_devices.append(next_device)

        if self.device_root.exists():
            for child in self.device_root.iterdir():
                if child.is_dir() and child.resolve() not in active_dirs:
                    shutil.rmtree(child)

        manifest["devices"] = next_devices
        return self.save_manifest(manifest)


_slm_store = SLMDeviceDataStore()
_sls_store = SLMDeviceDataStore(
    data_dir_name="sls_device_data",
    device_root_name="SLS",
    public_mount="/sls_device_data",
    label="SLS",
)


def get_slm_device_data_store() -> SLMDeviceDataStore:
    return _slm_store


def get_sls_device_data_store() -> SLMDeviceDataStore:
    return _sls_store
