#!/usr/bin/env python3
"""
训练SLM实时故障识别模型。

输入为 diagnosis/slm_fault_report.json。报告中的 status_code 作为监督标签；
模型输入只使用报警证据文本、故障文件名和可解析的实时参数，避免把 status_label
直接作为特征造成标签泄漏。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = PROJECT_ROOT / "diagnosis" / "slm_fault_report.json"
DEFAULT_RULES = PROJECT_ROOT / "diagnosis" / "slm_fault_rules.json"
DEFAULT_MODEL = PROJECT_ROOT / "backend" / "models" / "slm_fault_diagnosis.joblib"
DEFAULT_JSON_REPORT = PROJECT_ROOT / "backend" / "models" / "slm_fault_diagnosis_report.json"
DEFAULT_MD_REPORT = PROJECT_ROOT / "docs" / "slm_fault_model_report.md"
CSV_ENCODINGS = ("utf-8-sig", "utf-16", "gb18030")

STATUS_CODE_MAP = {
    0: "健康",
    1: "成形室氧含量异常",
    2: "铺粉检测缺粉/重铺异常",
    3: "刮刀扭矩/位置故障",
    4: "刮刀/平台伺服故障",
    5: "落粉轴故障",
    6: "灰桶/收粉/卸灰故障",
    7: "预涂料/储粉粉位故障",
    8: "风机转速/变速故障",
    9: "气源/压缩空气/蝶阀压力故障",
    10: "过滤器/滤芯/反吹故障",
    11: "蝶阀开关状态故障",
    12: "激光器/水冷机故障",
    13: "扫描/急停/安全回路故障",
    14: "工艺参数/配置异常",
    90: "多系统复合故障",
}

RAW_TO_FRONTEND_STATUS = {
    0: 0,
    1: 3,
    2: 1,
    3: 1,
    4: 1,
    5: 1,
    6: 3,
    7: 1,
    8: 3,
    9: 3,
    10: 3,
    11: 3,
    12: 2,
    13: 4,
    14: 4,
    90: 4,
}

PARAMETER_KEYWORDS = {
    "current_layer": ("层数", "当前层"),
    "sequence": ("序号", "数据序号"),
    "scraper_torque": ("刮刀扭矩",),
    "oxygen": ("成形室氧含量",),
    "ambient_oxygen": ("环境氧含量",),
    "chamber_temperature": ("成形室温度",),
    "gas_flow": ("循环气体实时流量",),
    "fan_speed": ("风机转速",),
    "medium_filter_resistance": ("中效滤芯阻力",),
    "high_filter_resistance": ("高效滤芯阻力",),
    "gas_pressure": ("过滤器气源压力", "气源压力"),
    "compressed_air_pressure": ("压缩空气压力",),
    "servo_temperature_x": ("伺服温度[X轴]", "0#伺服温度[X轴]"),
    "servo_temperature_y": ("伺服温度[Y轴]", "0#伺服温度[Y轴]"),
    "galvo_temperature_x": ("振镜温度[X轴]", "0#振镜温度[X轴]"),
    "galvo_temperature_y": ("振镜温度[Y轴]", "0#振镜温度[Y轴]"),
    "output_current_x": ("输出电流[X轴]", "0#输出电流[X轴]"),
    "output_current_y": ("输出电流[Y轴]", "0#输出电流[Y轴]"),
}


def resolve_project_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else PROJECT_ROOT / path


def project_relative_text(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except (ValueError, OSError):
        return str(path)


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


def split_name_unit(header: str) -> str:
    return re.sub(r"[(（][^()（）]*[)）]", "", header.strip()).strip()


def find_header(headers: List[str], keywords: Tuple[str, ...]) -> Optional[str]:
    for keyword in keywords:
        exact_header = next(
            (item for item in headers if split_name_unit(item).lower() == keyword.lower()),
            None,
        )
        if exact_header:
            return exact_header
    for keyword in keywords:
        matched = next((item for item in headers if keyword.lower() in item.lower()), None)
        if matched:
            return matched
    return None


def parse_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(str(value).strip())
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def csv_parameter_score(csv_path: Path) -> int:
    if csv_path.stat().st_size == 0 or any(skip in csv_path.name for skip in ("设备信息", "报警日志", "打印日志")):
        return 0
    try:
        headers, row = read_last_data_row(csv_path)
    except Exception:
        return 0
    if not row:
        return 0
    return sum(1 for keywords in PARAMETER_KEYWORDS.values() if find_header(headers, keywords))


def case_time_key(path_text: str) -> Tuple[str, str]:
    patterns = re.findall(r"(20\d{6}[-_]?\d{0,6}|20\d{2}-\d{2}-\d{2})", path_text)
    return (max(patterns) if patterns else "", path_text)


def collect_case_csvs(case: Dict[str, Any]) -> List[Path]:
    candidates: List[Path] = []

    def append(path: Path) -> None:
        if path.suffix.lower() == ".csv" and path.exists() and path not in candidates:
            candidates.append(path)

    for source_file in case.get("source_files", []):
        append(resolve_project_path(source_file))
    case_dir = resolve_project_path(case.get("case_dir", ""))
    if case_dir.exists():
        for csv_path in sorted(case_dir.rglob("*.csv")):
            append(csv_path)

    scored = [
        (csv_parameter_score(csv_path), case_time_key(str(csv_path)), csv_path)
        for csv_path in candidates
    ]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [csv_path for _, _, csv_path in scored]


def extract_numeric_features(case: Dict[str, Any]) -> Dict[str, Optional[float]]:
    features = {feature_id: None for feature_id in PARAMETER_KEYWORDS}
    for csv_path in collect_case_csvs(case):
        headers, row = read_last_data_row(csv_path)
        for feature_id, keywords in PARAMETER_KEYWORDS.items():
            if features[feature_id] is not None:
                continue
            header = find_header(headers, keywords)
            if header:
                features[feature_id] = parse_number(row.get(header))
        if all(value is not None for value in features.values()):
            break
    return features


def case_text(case: Dict[str, Any]) -> str:
    evidence_texts = [
        str(item.get("text", "")).strip()
        for item in case.get("evidence", [])
        if isinstance(item, dict) and str(item.get("text", "")).strip()
    ]
    fault_file_names = [
        Path(path_text).stem.replace("_", " ").replace("$", "、")
        for path_text in case.get("source_files", [])
        if "故障" in Path(path_text).name
    ]
    text = "\n".join([*evidence_texts, *fault_file_names]).strip()
    return text or "无报警"


def rule_predict(text: str, rules_config: Dict[str, Any]) -> Optional[int]:
    joined_text = text.lower()
    matched: Dict[str, Dict[str, Any]] = {}
    for rule in rules_config["rules"]:
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
        return None
    if len(matched) > 1 or "复合故障" in joined_text or "多系统" in joined_text:
        return int(rules_config.get("multi_fault_status_code", 90))
    return int(next(iter(matched.values()))["status_code"])


def build_dataset(report: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.Series]:
    rows: List[Dict[str, Any]] = []
    labels: List[int] = []
    for case in report.get("cases", []):
        row = {"text": case_text(case), **extract_numeric_features(case)}
        rows.append(row)
        labels.append(int(case["status_code"]))
    return pd.DataFrame(rows, columns=["text", *PARAMETER_KEYWORDS.keys()]), pd.Series(labels, name="status_code")


def map_frontend(code: int) -> int:
    return RAW_TO_FRONTEND_STATUS.get(int(code), 4)


def build_model(numeric_features: List[str]) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "text",
                TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1),
                "text",
            ),
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            ),
        ]
    )
    classifier = LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        solver="lbfgs",
        random_state=42,
    )
    return Pipeline(steps=[("features", preprocessor), ("classifier", classifier)])


def hybrid_predict(model: Pipeline, rules_config: Dict[str, Any], x: pd.DataFrame) -> List[int]:
    ml_predictions = model.predict(x)
    predictions: List[int] = []
    for index, row in x.reset_index(drop=True).iterrows():
        rule_code = rule_predict(str(row["text"]), rules_config)
        predictions.append(int(rule_code if rule_code is not None else ml_predictions[index]))
    return predictions


def evaluate_model(model: Pipeline, rules_config: Dict[str, Any], x_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
    predictions = pd.Series(hybrid_predict(model, rules_config, x_test), index=y_test.index)
    raw_accuracy = accuracy_score(y_test, predictions)
    fault_mask = y_test != 0
    fault_mode_accuracy = accuracy_score(y_test[fault_mask], predictions[fault_mask])
    frontend_truth = y_test.map(map_frontend)
    frontend_predictions = predictions.map(map_frontend)
    frontend_accuracy = accuracy_score(frontend_truth, frontend_predictions)
    labels = sorted(set(y_test.tolist()) | set(predictions.tolist()))
    return {
        "test_sample_count": int(len(y_test)),
        "raw_accuracy": round(float(raw_accuracy), 4),
        "fault_mode_accuracy": round(float(fault_mode_accuracy), 4),
        "frontend_status_accuracy": round(float(frontend_accuracy), 4),
        "classification_report": classification_report(
            y_test,
            predictions,
            labels=labels,
            target_names=[STATUS_CODE_MAP.get(int(label), str(label)) for label in labels],
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=labels).tolist(),
        "confusion_matrix_labels": labels,
    }


def write_markdown_report(path: Path, payload: Dict[str, Any]) -> None:
    metrics = payload["metrics"]
    status_counts = payload["status_counts"]
    lines = [
        "# SLM 7103故障识别模型报告",
        "",
        f"- 训练时间：{payload['trained_at']}",
        f"- 数据来源：`{payload['source_report']}`",
        f"- 样本数：{payload['sample_count']} 条",
        f"- 训练/测试划分：{payload['train_sample_count']} / {metrics['test_sample_count']}，按原始状态码分层抽样",
        f"- 模型文件：`{payload['model_path']}`",
        "",
        "## 识别率结论",
        "",
        f"- 原始故障模式测试准确率：{metrics['raw_accuracy'] * 100:.2f}%",
        f"- 故障样本模式识别率：{metrics['fault_mode_accuracy'] * 100:.2f}%",
        f"- 前端0-4健康状态归并准确率：{metrics['frontend_status_accuracy'] * 100:.2f}%",
        "",
        "该模型在留出测试集上对7103当前出现过的故障模式识别率超过95%。",
        "模型采用两级结构：第一层为7103故障报警语义规则层，第二层为字符TF-IDF与闭集参数共同驱动的多分类统计模型。",
        "训练和验证输入只包含报警证据文本、故障文件名和可解析的闭集实时参数；没有把`status_label`或`status_labels`作为特征输入。",
        "",
        "## 状态分布",
        "",
        "| 状态码 | 状态名称 | 样本数 |",
        "| --- | --- | ---: |",
    ]
    for code_text, count in sorted(status_counts.items(), key=lambda item: int(item[0])):
        lines.append(f"| {code_text} | {STATUS_CODE_MAP.get(int(code_text), '')} | {count} |")

    lines.extend(
        [
            "",
            "## 后台接入方式",
            "",
            "模型由 `backend/core/slm_realtime.py` 在收到 `/api/slm/realtime/data` 事件时加载并执行。",
            "外部真实数据送入后，后台返回原始故障模式、0-4前端健康状态、置信度和参与诊断的报警/参数数量。",
            "实时服务对诊断设置最小运行间隔；无新增报警时可复用最近诊断结论，使每秒参数/CH1图像刷新不会被模型重复计算阻塞。",
            "",
            "## 限制说明",
            "",
            "7103样本中部分设备只有报警日志或0字节样本表，因此实时接入时建议至少提供报警消息；若只提供数值参数，模型仍可运行，但可分故障类型会受传入字段完整度影响。",
            "规则层命中时置信度为报警语义强命中的工程置信度；统计层命中时置信度来自多分类逻辑回归概率输出，均作为当前输入与训练集中故障模式相似程度的工程指标使用。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def train(
    report_path: Path,
    rules_path: Path,
    model_path: Path,
    json_report_path: Path,
    md_report_path: Path,
) -> Dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rules_config = json.loads(rules_path.read_text(encoding="utf-8"))
    x, y = build_dataset(report)
    numeric_features = list(PARAMETER_KEYWORDS.keys())
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        stratify=y,
        random_state=42,
    )
    model = build_model(numeric_features)
    model.fit(x_train, y_train)
    metrics = evaluate_model(model, rules_config, x_test, y_test)
    if metrics["fault_mode_accuracy"] < 0.95:
        raise RuntimeError(f"故障模式识别率不足95%: {metrics['fault_mode_accuracy']:.4f}")

    trained_at = datetime.now().isoformat(timespec="seconds")
    payload = {
        "model_version": f"slm-fault-{trained_at}",
        "trained_at": trained_at,
        "source_report": project_relative_text(report_path),
        "rules_path": project_relative_text(rules_path),
        "model_path": project_relative_text(model_path),
        "sample_count": int(len(y)),
        "train_sample_count": int(len(y_train)),
        "status_counts": {str(code): int(count) for code, count in sorted(Counter(y).items())},
        "numeric_features": numeric_features,
        "status_code_map": STATUS_CODE_MAP,
        "raw_to_frontend_status": RAW_TO_FRONTEND_STATUS,
        "metrics": metrics,
        "model_structure": "7103报警语义规则层 + TF-IDF/闭集参数统计模型",
    }
    artifact = {
        "pipeline": model,
        "rules_config": rules_config,
        "numeric_features": numeric_features,
        "status_code_map": STATUS_CODE_MAP,
        "raw_to_frontend_status": RAW_TO_FRONTEND_STATUS,
        "model_version": payload["model_version"],
        "metrics": metrics,
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(md_report_path, payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="训练7103 SLM故障识别模型")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="slm_fault_report.json路径")
    parser.add_argument("--rules", default=str(DEFAULT_RULES), help="slm_fault_rules.json路径")
    parser.add_argument("--model-output", default=str(DEFAULT_MODEL), help="joblib模型输出路径")
    parser.add_argument("--json-report", default=str(DEFAULT_JSON_REPORT), help="训练指标JSON输出路径")
    parser.add_argument("--md-report", default=str(DEFAULT_MD_REPORT), help="Markdown报告输出路径")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = train(
        resolve_project_path(args.report),
        resolve_project_path(args.rules),
        resolve_project_path(args.model_output),
        resolve_project_path(args.json_report),
        resolve_project_path(args.md_report),
    )
    metrics = payload["metrics"]
    print(
        "[SLM故障模型] 训练完成: "
        f"样本={payload['sample_count']}, "
        f"原始准确率={metrics['raw_accuracy']:.4f}, "
        f"故障模式识别率={metrics['fault_mode_accuracy']:.4f}, "
        f"前端状态准确率={metrics['frontend_status_accuracy']:.4f}"
    )
    print(f"[SLM故障模型] 模型: {payload['model_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
