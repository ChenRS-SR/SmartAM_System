"""
SLM实时参数接入与故障诊断服务。

该模块只保存外部实时数据接口送入的最新事件；7103静态数据只用于模拟模式和模型训练，
真实硬件模式没有事件输入时由前端显示固定闭集参数的缺省值。
"""

from __future__ import annotations

import math
import time
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "slm_fault_diagnosis.joblib"

PARAMETER_SCHEMA = [
    {"id": "current_layer", "name": "当前层", "unit": "层"},
    {"id": "sequence", "name": "数据序号", "unit": ""},
    {"id": "record_status", "name": "状态参数", "unit": ""},
    {"id": "data_time", "name": "采集时间", "unit": ""},
    {"id": "scraper_torque", "name": "刮刀扭矩", "unit": "%"},
    {"id": "oxygen", "name": "成形室氧含量", "unit": "%"},
    {"id": "ambient_oxygen", "name": "环境氧含量", "unit": "%"},
    {"id": "chamber_temperature", "name": "成形室温度", "unit": "℃"},
    {"id": "gas_flow", "name": "循环气体流量", "unit": "m3/h"},
    {"id": "fan_speed", "name": "风机转速", "unit": "%"},
    {"id": "medium_filter_resistance", "name": "中效滤芯阻力", "unit": "mBar"},
    {"id": "high_filter_resistance", "name": "高效滤芯阻力", "unit": "mBar"},
    {"id": "gas_pressure", "name": "气源压力", "unit": "Bar"},
    {"id": "compressed_air_pressure", "name": "压缩空气压力", "unit": "Bar"},
    {"id": "servo_temperature_x", "name": "X轴伺服温度", "unit": "℃"},
    {"id": "servo_temperature_y", "name": "Y轴伺服温度", "unit": "℃"},
    {"id": "galvo_temperature_x", "name": "X轴振镜温度", "unit": "℃"},
    {"id": "galvo_temperature_y", "name": "Y轴振镜温度", "unit": "℃"},
    {"id": "output_current_x", "name": "X轴输出电流", "unit": "mA"},
    {"id": "output_current_y", "name": "Y轴输出电流", "unit": "mA"},
]

NUMERIC_PARAMETER_IDS = [
    item["id"]
    for item in PARAMETER_SCHEMA
    if item["id"] not in {"record_status", "data_time"}
]

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

FRONTEND_STATUS_LABELS = {
    -1: "等待实时数据",
    0: "系统健康",
    1: "铺粉/刮刀系统异常",
    2: "激光器/水冷机异常",
    3: "气氛循环系统异常",
    4: "复合故障",
}


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_device_id(device_id: str) -> str:
    text = str(device_id).strip()
    if text.lower().startswith("slm-"):
        return text.lower()
    return f"slm-{text.lower()}"


def format_value(value: Any) -> str:
    if value is None:
        return "--"
    raw = str(value).strip()
    if raw == "":
        return "--"
    try:
        number = float(raw)
    except ValueError:
        return raw
    if not math.isfinite(number):
        return "--"
    if number.is_integer():
        return str(int(number))
    return f"{number:.3f}".rstrip("0").rstrip(".")


def parse_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalize_parameters(raw_parameters: Any) -> Dict[str, Any]:
    if raw_parameters is None:
        return {}
    if isinstance(raw_parameters, dict):
        return dict(raw_parameters)
    if not isinstance(raw_parameters, list):
        raise ValueError("parameters必须是对象或参数数组")

    parameters: Dict[str, Any] = {}
    for item in raw_parameters:
        if not isinstance(item, dict):
            raise ValueError("参数数组中的每项必须是对象")
        key = item.get("id") or item.get("name")
        if not key:
            raise ValueError("参数项必须包含id或name")
        parameters[str(key)] = item.get("value")
    return parameters


def normalize_alarms(raw_alarms: Any) -> List[Dict[str, str]]:
    if raw_alarms in (None, ""):
        return []
    if not isinstance(raw_alarms, list):
        raise ValueError("alarms必须是数组")

    alarms: List[Dict[str, str]] = []
    for item in raw_alarms:
        if isinstance(item, str):
            alarms.append({"message": item})
            continue
        if isinstance(item, dict):
            message = str(item.get("message") or item.get("text") or "").strip()
            if message:
                alarms.append(
                    {
                        "time": str(item.get("time") or ""),
                        "code": str(item.get("code") or ""),
                        "message": message,
                    }
                )
            continue
        raise ValueError("alarms数组只支持字符串或对象")
    return alarms


def normalize_media(raw_media: Any, payload: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    media_source = raw_media if isinstance(raw_media, dict) else {}
    ch1_source = media_source.get("ch1") or media_source.get("CH1") or {}
    if not isinstance(ch1_source, dict):
        raise ValueError("media.ch1必须是对象")

    data_url = str(ch1_source.get("data_url") or payload.get("ch1_image") or "").strip()
    url = str(ch1_source.get("url") or ch1_source.get("video_url") or payload.get("ch1_video_url") or "").strip()
    image_base64 = str(ch1_source.get("image_base64") or payload.get("ch1_image_base64") or "").strip()
    mime_type = str(ch1_source.get("mime_type") or "image/jpeg").strip()
    media_type = str(ch1_source.get("media_type") or ch1_source.get("type") or "").strip().lower()

    if image_base64 and not data_url:
        data_url = f"data:{mime_type};base64,{image_base64}"
    if not media_type:
        if data_url.startswith("data:video/") or re_video_url(url):
            media_type = "video"
        elif data_url or url:
            media_type = "image"

    media: Dict[str, Dict[str, str]] = {}
    if data_url or url:
        media["ch1"] = {
            "media_type": media_type or "image",
            "data_url": data_url,
            "url": url,
            "event_time": str(payload.get("event_time") or ""),
        }
    return media


def re_video_url(url: str) -> bool:
    lower_url = url.lower().split("?", 1)[0]
    return lower_url.endswith((".mp4", ".webm", ".ogg", ".mov"))


def parameters_to_display(
    values: Dict[str, Any],
    event_time: str,
    status_text: str,
) -> List[Dict[str, str]]:
    display: List[Dict[str, str]] = []
    for schema in PARAMETER_SCHEMA:
        param_id = schema["id"]
        if param_id == "data_time":
            value = event_time
        elif param_id == "record_status":
            value = status_text
        else:
            value = values.get(param_id, values.get(schema["name"]))
        display.append(
            {
                "id": param_id,
                "name": schema["name"],
                "value": format_value(value),
                "unit": schema["unit"],
            }
        )
    return display


def build_health_data(frontend_status_code: int, labels: Iterable[str]) -> Dict[str, Any]:
    status_labels = [label for label in labels if label]
    if not status_labels:
        status_labels = [FRONTEND_STATUS_LABELS.get(frontend_status_code, "未知状态")]

    health = {
        "status": {
            -1: "power_off",
            0: "healthy",
            1: "powder_fault",
            2: "laser_fault",
            3: "gas_fault",
            4: "compound_fault",
        }.get(frontend_status_code, "compound_fault"),
        "status_code": frontend_status_code,
        "status_labels": status_labels,
        "laser_system": {"status": "healthy", "message": "健康"},
        "powder_system": {"status": "healthy", "message": "健康"},
        "gas_system": {"status": "healthy", "message": "健康"},
    }

    if frontend_status_code == -1:
        health["laser_system"] = {"status": "unknown", "message": "等待实时数据"}
        health["powder_system"] = {"status": "unknown", "message": "等待实时数据"}
        health["gas_system"] = {"status": "unknown", "message": "等待实时数据"}
    elif frontend_status_code in (1, 4):
        health["powder_system"] = {"status": "fault", "message": "铺粉/刮刀系统异常"}
    if frontend_status_code in (2, 4):
        health["laser_system"] = {"status": "fault", "message": "激光器/水冷机异常"}
    if frontend_status_code in (3, 4):
        health["gas_system"] = {"status": "fault", "message": "气氛循环系统异常"}
    return health


class SLMFaultDiagnosisRuntime:
    """加载训练好的7103故障识别模型，供实时数据事件调用。"""

    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH):
        self.model_path = model_path
        self._artifact: Optional[Dict[str, Any]] = None
        self._model_mtime: Optional[float] = None

    def load(self) -> Dict[str, Any]:
        if not self.model_path.exists():
            raise FileNotFoundError(f"SLM故障诊断模型不存在: {self.model_path}")
        model_mtime = self.model_path.stat().st_mtime
        if self._artifact is None or self._model_mtime != model_mtime:
            self._artifact = joblib.load(self.model_path)
            self._model_mtime = model_mtime
        return self._artifact

    def _rule_predict(self, text: str, rules_config: Dict[str, Any]) -> Optional[int]:
        joined_text = text.lower()
        matched: Dict[str, Dict[str, Any]] = {}
        for rule in rules_config.get("rules", []):
            keyword_hits = [
                keyword for keyword in rule.get("keywords", [])
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

    def predict(
        self,
        parameters: Dict[str, Any],
        alarms: List[Dict[str, str]],
        event_time: str,
    ) -> Dict[str, Any]:
        artifact = self.load()
        numeric_features = artifact["numeric_features"]
        text = "\n".join(alarm["message"] for alarm in alarms if alarm.get("message")).strip()
        if not text:
            text = "无报警"

        row = {"text": text}
        for feature_id in numeric_features:
            row[feature_id] = parse_number(parameters.get(feature_id))
        frame = pd.DataFrame([row], columns=["text", *numeric_features])
        pipeline = artifact["pipeline"]
        rule_code = self._rule_predict(text, artifact.get("rules_config", {}))
        raw_code = int(rule_code if rule_code is not None else pipeline.predict(frame)[0])
        confidence = 0.0
        if rule_code is not None:
            confidence = 0.98
        elif hasattr(pipeline, "predict_proba"):
            probabilities = pipeline.predict_proba(frame)[0]
            confidence = float(max(probabilities))

        status_label = STATUS_CODE_MAP.get(raw_code, f"未知状态{raw_code}")
        frontend_code = RAW_TO_FRONTEND_STATUS.get(raw_code, 4)
        return {
            "enabled": True,
            "modelVersion": artifact.get("model_version", "unknown"),
            "statusCode": raw_code,
            "statusLabel": status_label,
            "frontendStatusCode": frontend_code,
            "frontendStatusLabel": FRONTEND_STATUS_LABELS.get(frontend_code, "未知状态"),
            "confidence": round(confidence, 4),
            "confidenceText": f"{confidence * 100:.1f}%",
            "faultModes": [] if raw_code == 0 else [status_label],
            "eventTime": event_time,
            "modelLayer": "alarm_rule" if rule_code is not None else "statistical",
            "input": {
                "alarmCount": len(alarms),
                "parameterCount": len([value for value in parameters.values() if value not in (None, "")]),
            },
            "evidence": alarms[:5],
        }


class SLMRealtimeDataStore:
    """线程内最新实时数据缓存；后续外部系统按接口持续写入即可。"""

    def __init__(self, diagnosis_runtime: Optional[SLMFaultDiagnosisRuntime] = None):
        self._diagnosis_runtime = diagnosis_runtime or SLMFaultDiagnosisRuntime()
        self._latest: Dict[str, Dict[str, Any]] = {}
        self._last_diagnosis_at: Dict[str, float] = {}
        self._lock = RLock()
        self.diagnosis_min_interval_seconds = 1.0

    def submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        device_id = normalize_device_id(str(payload.get("device_id") or ""))
        if device_id == "slm-":
            raise ValueError("device_id不能为空")

        event_time = str(payload.get("event_time") or "").strip()
        if not event_time:
            raise ValueError("event_time不能为空，采集时间必须由真实事件提供")

        parameters = normalize_parameters(payload.get("parameters"))
        alarms = normalize_alarms(payload.get("alarms"))
        media = normalize_media(payload.get("media"), payload)
        now_seconds = time.time()
        with self._lock:
            previous = self._latest.get(device_id)
            last_diagnosis_at = self._last_diagnosis_at.get(device_id, 0.0)

        # 诊断不跟随高频图像/参数逐帧运行；有新报警时立即诊断，否则按最小间隔复用上次结论。
        should_diagnose = (
            previous is None
            or bool(alarms)
            or now_seconds - last_diagnosis_at >= self.diagnosis_min_interval_seconds
        )
        if should_diagnose:
            diagnosis = self._diagnosis_runtime.predict(parameters, alarms, event_time)
            diagnosis_runtime_at = now_text()
        elif previous and previous.get("diagnosis"):
            diagnosis = previous["diagnosis"]
            diagnosis_runtime_at = previous.get("diagnosisUpdatedAt", "")
        else:
            diagnosis = self._diagnosis_runtime.predict(parameters, alarms, event_time)
            diagnosis_runtime_at = now_text()
        health = build_health_data(
            int(diagnosis["frontendStatusCode"]),
            [diagnosis["statusLabel"], diagnosis["confidenceText"]],
        )
        display_parameters = parameters_to_display(parameters, event_time, diagnosis["statusLabel"])
        sample = {
            "hasData": True,
            "deviceId": device_id,
            "eventTime": event_time,
            "receivedAt": now_text(),
            "sequence": payload.get("sequence"),
            "parameters": display_parameters,
            "rawParameters": parameters,
            "alarms": alarms,
            "media": media,
            "diagnosis": diagnosis,
            "diagnosisUpdatedAt": diagnosis_runtime_at,
            "health": health,
        }
        with self._lock:
            self._latest[device_id] = sample
            if should_diagnose:
                self._last_diagnosis_at[device_id] = now_seconds
        return sample

    def latest(self, device_id: str) -> Dict[str, Any]:
        normalized_id = normalize_device_id(device_id)
        with self._lock:
            sample = self._latest.get(normalized_id)
        if sample is None:
            return {
                "hasData": False,
                "deviceId": normalized_id,
                "eventTime": "",
                "receivedAt": "",
                "parameters": [],
                "alarms": [],
                "media": {},
                "diagnosis": {
                    "enabled": True,
                    "modelVersion": "",
                    "statusCode": -1,
                    "statusLabel": "等待实时数据",
                    "frontendStatusCode": -1,
                    "frontendStatusLabel": "等待实时数据",
                    "confidence": None,
                    "confidenceText": "--",
                    "faultModes": [],
                    "eventTime": "",
                    "input": {"alarmCount": 0, "parameterCount": 0},
                    "evidence": [],
                },
                "health": build_health_data(-1, ["等待实时数据"]),
            }
        return sample

    def clear(self, device_id: str) -> None:
        normalized_id = normalize_device_id(device_id)
        with self._lock:
            self._latest.pop(normalized_id, None)
            self._last_diagnosis_at.pop(normalized_id, None)

    def schema(self) -> Dict[str, Any]:
        return {
            "protocolVersion": "2026-06-27",
            "parameterSchema": PARAMETER_SCHEMA,
            "numericParameterIds": NUMERIC_PARAMETER_IDS,
            "statusCodeMap": STATUS_CODE_MAP,
            "frontendStatusMap": FRONTEND_STATUS_LABELS,
            "modelPath": str(self._diagnosis_runtime.model_path.relative_to(PROJECT_ROOT)),
        }


_slm_realtime_store = SLMRealtimeDataStore()


def get_slm_realtime_store() -> SLMRealtimeDataStore:
    return _slm_realtime_store
