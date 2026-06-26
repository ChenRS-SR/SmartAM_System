"""
SLM表格故障诊断
================

递归读取设备导出的CSV文件，基于固定规则模型输出SLM界面可用的健康状态码。
该模块不绑定具体设备号或目录层级，新增数据放入数据根目录后可重新扫描或使用watch模式触发识别。
"""

from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def status_priority(status_code: int) -> int:
    """健康最低，单类故障居中，多系统故障最高。"""

    if status_code == 0:
        return 0
    if status_code == 90:
        return 2
    return 1
CSV_ENCODINGS = ("utf-8-sig", "utf-16", "gb18030")


@dataclass
class FaultEvidence:
    """单条故障证据，来源可以是文件名、报警日志或表格内容。"""

    source: str
    text: str
    file: str


@dataclass
class DiagnosisResult:
    """诊断结果，字段名与SLM健康状态接口保持一致。"""

    device_id: str
    case_dir: str
    status_code: int
    status_label: str
    status_labels: List[str]
    categories: List[str]
    confidence: float
    evidence: List[FaultEvidence] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    feature_summary: Dict[str, Dict[str, float]] = field(default_factory=dict)
    diagnosed_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> Dict:
        return {
            "device_id": self.device_id,
            "case_dir": self.case_dir,
            "status_code": self.status_code,
            "status_label": self.status_label,
            "status_labels": self.status_labels,
            "categories": self.categories,
            "confidence": self.confidence,
            "evidence": [item.__dict__ for item in self.evidence],
            "source_files": self.source_files,
            "feature_summary": self.feature_summary,
            "diagnosed_at": self.diagnosed_at,
        }


class FaultRuleModel:
    """固定规则模型：使用关键词证据映射到SLM状态码。"""

    def __init__(self, config: Dict):
        self.config = config
        self.status_codes = {int(key): value for key, value in config["status_codes"].items()}
        self.rules = config["rules"]
        self.multi_fault_status_code = int(config.get("multi_fault_status_code", 90))

    @classmethod
    def load(cls, model_path: Path) -> "FaultRuleModel":
        with model_path.open("r", encoding="utf-8") as file_obj:
            return cls(json.load(file_obj))

    def classify(self, texts: Sequence[str]) -> Tuple[int, str, List[str], List[str], float]:
        joined_text = "\n".join(text for text in texts if text).lower()
        matched: Dict[str, Dict] = {}

        for rule in self.rules:
            keyword_hits = [
                keyword for keyword in rule["keywords"]
                if keyword.lower() in joined_text
            ]
            if keyword_hits:
                matched[rule["category"]] = {
                    "status_code": int(rule["status_code"]),
                    "label": rule["label"],
                    "hits": keyword_hits,
                }

        if not matched:
            status_code = 0
            label = self.status_codes[0]
            return status_code, label, [label], [], 1.0

        categories = list(matched.keys())
        has_explicit_compound = "复合故障" in joined_text or "多系统" in joined_text
        if len(categories) > 1 or has_explicit_compound:
            status_code = self.multi_fault_status_code
            label = self.status_codes[status_code]
        else:
            only_category = categories[0]
            status_code = matched[only_category]["status_code"]
            label = matched[only_category]["label"]

        status_labels = [label]
        if status_code == self.multi_fault_status_code:
            status_labels.append(
                "包含故障:" + "、".join(matched[category]["label"] for category in categories)
            )
        for category in categories:
            hits = "、".join(matched[category]["hits"][:4])
            status_labels.append(f"{matched[category]['label']}证据:{hits}")

        # 命中文本越多置信度越高，规则模型最高不超过0.95，避免被误读为概率模型。
        hit_count = sum(len(value["hits"]) for value in matched.values())
        confidence = min(0.95, 0.55 + 0.08 * hit_count + 0.07 * len(categories))
        return status_code, label, status_labels, categories, round(confidence, 3)


def iter_csv_files(data_root: Path) -> Iterable[Path]:
    """递归遍历CSV文件，目录新增数据后无需改代码。"""

    yield from sorted(data_root.rglob("*.csv"))


def group_case_files(csv_files: Iterable[Path]) -> Dict[Path, List[Path]]:
    groups: Dict[Path, List[Path]] = {}
    for csv_file in csv_files:
        groups.setdefault(csv_file.parent, []).append(csv_file)
    return groups


def extract_device_id(path: Path) -> str:
    for part in path.parts:
        match = re.search(r"B\d+", part, flags=re.IGNORECASE)
        if match:
            return match.group(0).upper()
    return "UNKNOWN"


def read_csv_rows(csv_path: Path, max_rows: Optional[int] = None) -> Tuple[List[str], List[List[str]]]:
    last_error: Optional[UnicodeError] = None
    for encoding in CSV_ENCODINGS:
        try:
            with csv_path.open("r", encoding=encoding, newline="") as file_obj:
                reader = csv.reader(file_obj)
                header = next(reader, [])
                rows: List[List[str]] = []
                for row_index, row in enumerate(reader):
                    if max_rows is not None and row_index >= max_rows:
                        break
                    rows.append(row)
                return header, rows
        except UnicodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return [], []


def normalize_cell(value: str) -> str:
    return value.strip().strip("\ufeff").strip()


def extract_fault_from_filename(csv_path: Path) -> Optional[FaultEvidence]:
    stem = csv_path.stem
    if "故障" not in stem:
        return None
    readable = stem.replace("_", " ").replace("$", "、")
    return FaultEvidence(source="filename", text=readable, file=str(csv_path))


def extract_alarm_log_evidence(csv_path: Path) -> List[FaultEvidence]:
    if "报警日志" not in csv_path.name:
        return []

    header, rows = read_csv_rows(csv_path)
    normalized_header = [normalize_cell(item) for item in header]
    content_indexes = [
        index for index, name in enumerate(normalized_header)
        if "报警内容" in name or "报警" == name
    ]

    evidence: List[FaultEvidence] = []
    for row in rows:
        cells = [normalize_cell(cell) for cell in row]
        for index in content_indexes:
            if index < len(cells) and cells[index]:
                evidence.append(FaultEvidence(source="alarm_log", text=cells[index], file=str(csv_path)))
    return evidence


def summarize_fault_features(csv_path: Path) -> Dict[str, Dict[str, float]]:
    """提取故障窗口中的关键数值列，供后续人工复核和模型迭代。"""

    if "故障" not in csv_path.name or csv_path.stat().st_size == 0:
        return {}

    header, rows = read_csv_rows(csv_path)
    normalized_header = [normalize_cell(item) for item in header]
    focus_words = ("扭矩", "压力", "氧含量", "风机转速", "流量", "滤芯阻力", "温度")
    focus_indexes = [
        index for index, name in enumerate(normalized_header)
        if any(word in name for word in focus_words)
    ]

    stats: Dict[str, Dict[str, float]] = {}
    for index in focus_indexes:
        name = normalized_header[index]
        values: List[float] = []
        for row in rows:
            if index >= len(row):
                continue
            cell = normalize_cell(row[index])
            if not cell:
                continue
            try:
                values.append(float(cell))
            except ValueError:
                continue
        if values:
            stats[name] = {
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "mean": round(sum(values) / len(values), 4),
            }
    return stats


def diagnose_case(case_dir: Path, files: Sequence[Path], model: FaultRuleModel) -> DiagnosisResult:
    evidence: List[FaultEvidence] = []
    feature_summary: Dict[str, Dict[str, float]] = {}

    for csv_file in sorted(files):
        filename_evidence = extract_fault_from_filename(csv_file)
        if filename_evidence is not None:
            evidence.append(filename_evidence)

        if "报警日志" in csv_file.name and csv_file.stat().st_size > 0:
            evidence.extend(extract_alarm_log_evidence(csv_file))

        for key, value in summarize_fault_features(csv_file).items():
            feature_summary[f"{csv_file.name}:{key}"] = value

    texts = [item.text for item in evidence]
    status_code, label, status_labels, categories, confidence = model.classify(texts)
    return DiagnosisResult(
        device_id=extract_device_id(case_dir),
        case_dir=str(case_dir),
        status_code=status_code,
        status_label=label,
        status_labels=status_labels,
        categories=categories,
        confidence=confidence,
        evidence=evidence[:20],
        source_files=[str(item) for item in sorted(files)],
        feature_summary=feature_summary,
    )


def summarize_by_device(results: Sequence[DiagnosisResult]) -> Dict[str, Dict]:
    """每台设备取最严重且最近的状态，供界面直接消费。"""

    latest: Dict[str, DiagnosisResult] = {}
    for result in results:
        current = latest.get(result.device_id)
        if current is None:
            latest[result.device_id] = result
            continue
        result_rank = status_priority(result.status_code)
        current_rank = status_priority(current.status_code)
        if result_rank > current_rank or (result_rank == current_rank and result.case_dir > current.case_dir):
            latest[result.device_id] = result

    return {device_id: result.to_dict() for device_id, result in sorted(latest.items())}


def diagnose_dataset(data_root: Path, model_path: Path) -> Dict:
    model = FaultRuleModel.load(model_path)
    csv_files = list(iter_csv_files(data_root))
    case_groups = group_case_files(csv_files)
    results = [diagnose_case(case_dir, files, model) for case_dir, files in sorted(case_groups.items())]

    status_counts: Dict[str, int] = {}
    for result in results:
        key = str(result.status_code)
        status_counts[key] = status_counts.get(key, 0) + 1

    fault_type_counts: Dict[str, int] = {}
    for result in results:
        for category in result.categories:
            fault_type_counts[category] = fault_type_counts.get(category, 0) + 1

    return {
        "data_root": str(data_root),
        "model_path": str(model_path),
        "status_code_map": {str(key): value for key, value in sorted(model.status_codes.items())},
        "diagnosed_at": datetime.now().isoformat(timespec="seconds"),
        "total_csv_files": len(csv_files),
        "total_cases": len(results),
        "device_count": len({result.device_id for result in results if result.device_id != "UNKNOWN"}),
        "status_counts": dict(sorted(status_counts.items(), key=lambda item: int(item[0]))),
        "fault_type_counts": dict(sorted(fault_type_counts.items())),
        "device_latest_status": summarize_by_device(results),
        "cases": [result.to_dict() for result in results],
    }


def diagnose_until_stopped(
    data_root: Path,
    model_path: Path,
    output_path: Path,
    interval_seconds: int = 30,
) -> None:
    """轮询目录变化；新增CSV后重新诊断并覆盖输出JSON。"""

    last_signature: Optional[Tuple[int, int]] = None
    while True:
        csv_files = list(iter_csv_files(data_root))
        signature = (len(csv_files), int(max((path.stat().st_mtime for path in csv_files), default=0)))
        if signature != last_signature:
            report = diagnose_dataset(data_root, model_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            last_signature = signature
            print(f"[SLM表格诊断] 已更新: {output_path}")
        time.sleep(interval_seconds)
