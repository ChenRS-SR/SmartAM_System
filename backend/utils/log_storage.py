"""
日志存储管理
============
统一限制运行日志大小，避免长时间运行后占满磁盘。
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable


DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 5
DEFAULT_TOTAL_BYTES = 128 * 1024 * 1024
DEFAULT_LOG_LEVEL = "INFO"


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        raise ValueError(f"{name} 必须是正整数，当前值: {value}")
    if parsed <= 0:
        raise ValueError(f"{name} 必须大于0，当前值: {value}")
    return parsed


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_log_dir(project_root: Path | None = None) -> Path:
    root = project_root or get_project_root()
    return Path(os.getenv("SMARTAM_LOG_DIR", str(root / "logs"))).resolve()


def get_log_limits() -> tuple[int, int, int]:
    max_bytes = _read_int_env("SMARTAM_LOG_MAX_BYTES", DEFAULT_MAX_BYTES)
    backup_count = _read_int_env("SMARTAM_LOG_BACKUP_COUNT", DEFAULT_BACKUP_COUNT)
    total_bytes = _read_int_env("SMARTAM_LOG_TOTAL_BYTES", DEFAULT_TOTAL_BYTES)
    return max_bytes, backup_count, total_bytes


def _iter_log_files(log_dir: Path) -> Iterable[Path]:
    if not log_dir.exists():
        return []
    return (
        path for path in log_dir.iterdir()
        if path.is_file() and (path.suffix in {".log", ".out", ".err"} or ".log." in path.name)
    )


def rotate_oversized_file(path: Path, max_bytes: int, backup_count: int) -> None:
    """单个活跃日志超过限额时先轮转，防止启动后继续追加到巨型文件。"""
    if not path.exists() or path.stat().st_size <= max_bytes:
        return

    oldest = path.with_name(f"{path.name}.{backup_count}")
    if oldest.exists():
        oldest.unlink()

    for index in range(backup_count - 1, 0, -1):
        src = path.with_name(f"{path.name}.{index}")
        dst = path.with_name(f"{path.name}.{index + 1}")
        if src.exists():
            src.rename(dst)

    first_backup = path.with_name(f"{path.name}.1")
    if first_backup.exists():
        first_backup.unlink()
    path.rename(first_backup)
    path.touch()


def cleanup_log_storage(log_dir: Path | None = None) -> dict:
    """清理日志目录：先处理超大活跃日志，再按总量上限删除最旧日志。"""
    max_bytes, backup_count, total_bytes = get_log_limits()
    target_dir = log_dir or get_log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    removed: list[str] = []
    for path in list(_iter_log_files(target_dir)):
        if ".log." not in path.name and path.suffix in {".log", ".out", ".err"}:
            rotate_oversized_file(path, max_bytes, backup_count)

    files = sorted(
        [path for path in _iter_log_files(target_dir) if path.exists()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    total_size = sum(path.stat().st_size for path in files)

    for path in reversed(files):
        if total_size <= total_bytes:
            break
        size = path.stat().st_size
        path.unlink()
        total_size -= size
        removed.append(str(path))

    return {
        "log_dir": str(target_dir),
        "max_bytes": max_bytes,
        "backup_count": backup_count,
        "total_bytes": total_bytes,
        "total_size": total_size,
        "removed": removed,
    }


class _ManagedStream:
    """把 print/stdout/stderr 写入轮转文件，同时保留控制台输出。"""

    def __init__(self, original_stream, log_path: Path, max_bytes: int, backup_count: int):
        self.original_stream = original_stream
        self.handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        self._encoding = getattr(original_stream, "encoding", "utf-8") or "utf-8"

    @property
    def encoding(self) -> str:
        return self._encoding

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return bool(self.original_stream and self.original_stream.isatty())

    def write(self, text: str) -> int:
        if not text:
            return 0
        # 多路视频流和WebSocket可能并发打印，写轮转文件时使用handler锁避免切分错乱。
        self.handler.acquire()
        try:
            record = logging.LogRecord("stdout", logging.INFO, "", 0, text, None, None)
            if self.handler.shouldRollover(record):
                self.handler.doRollover()
            if self.original_stream:
                self.original_stream.write(text)
                self.original_stream.flush()
            self.handler.stream.write(text)
            self.handler.flush()
        finally:
            self.handler.release()
        return len(text)

    def flush(self) -> None:
        if self.original_stream:
            self.original_stream.flush()
        self.handler.flush()


def setup_runtime_logging(project_root: Path | None = None) -> logging.Logger:
    """配置后端运行日志：清理存储、接管print输出、配置Python日志轮转。"""
    log_dir = get_log_dir(project_root)
    cleanup_log_storage(log_dir)
    max_bytes, backup_count, _ = get_log_limits()

    stdout_log = log_dir / "slm_backend.log"
    python_log = log_dir / "smartam_runtime.log"

    sys.stdout = _ManagedStream(sys.__stdout__, stdout_log, max_bytes, backup_count)
    sys.stderr = _ManagedStream(sys.__stderr__, stdout_log, max_bytes, backup_count)

    level_name = os.getenv("SMARTAM_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        python_log,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.__stdout__)
    console_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s - %(name)s - %(message)s"))
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    logger = logging.getLogger("smartam.storage")
    logger.info(
        "日志存储限制已启用: dir=%s, single=%dMB, backups=%d, total=%dMB",
        log_dir,
        max_bytes // 1024 // 1024,
        backup_count,
        get_log_limits()[2] // 1024 // 1024,
    )
    return logger


def build_uvicorn_log_config(log_dir: Path | None = None) -> dict:
    max_bytes, backup_count, _ = get_log_limits()
    target_dir = log_dir or get_log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "uvicorn_file": {
                "formatter": "default",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(target_dir / "uvicorn.log"),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
            "access_file": {
                "formatter": "access",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(target_dir / "uvicorn_access.log"),
                "maxBytes": max_bytes,
                "backupCount": backup_count,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default", "uvicorn_file"], "level": "INFO", "propagate": False},
            "uvicorn.error": {"handlers": ["default", "uvicorn_file"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["access_file"], "level": "INFO", "propagate": False},
        },
    }
