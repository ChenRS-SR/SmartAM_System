"""SLM 闭环调控 - 数据结构（read.json 事件与 feedback.json 反馈）。

原样移植自 Desktop/slm/slm_file_interface.py 中的 dataclass 定义。
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class TestbenchEvent:
    """试验台发来的事件。

    事件类型：
      - pre_print / parameter_sync  : 打印前参数同步（携带初始工艺参数）
      - pre_scan  / powder_completed : 铺粉完成
      - post_scan / scan_completed   : 激光扫描完成
    """
    trigger: str          # "pre_print" | "pre_scan" | "post_scan"
    event: str            # "parameter_sync" | "powder_completed" | "scan_completed"
    layer: int            # 当前层号（parameter_sync 时为 0）
    device_id: str        # 设备 ID
    job_name: str         # 任务名
    timestamp: str        # 触发时间
    source: str           # 来源
    parameters: Dict[str, float] = field(default_factory=dict)  # 工艺参数（parameter_sync 事件携带）

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TestbenchEvent":
        return cls(
            trigger=d.get("trigger", ""),
            event=d.get("event", ""),
            layer=d.get("layer", 0),
            device_id=d.get("device_id", ""),
            job_name=d.get("job_name", ""),
            timestamp=d.get("timestamp", ""),
            source=d.get("source", ""),
            parameters=d.get("parameters", {}),
        )

    @property
    def is_parameter_sync(self) -> bool:
        return self.trigger == "pre_print" and self.event == "parameter_sync"

    @property
    def is_powder_completed(self) -> bool:
        return self.trigger == "pre_scan" and self.event == "powder_completed"

    @property
    def is_scan_completed(self) -> bool:
        return self.trigger == "post_scan" and self.event == "scan_completed"


@dataclass
class DefectInfo:
    """单个缺陷信息"""
    defect_id: int
    class_key: str         # 缺陷类型: "scraper_damage", "powder_insufficient", "warpage"
    class_name: str        # 中文名: "刮刀破损", "铺粉不足", "翘曲"
    confidence: float      # 置信度 0~1
    area_mm2: float = 0.0
    center_galvo_mm: List[float] = field(default_factory=lambda: [0.0, 0.0])
    bbox_xywh: List[float] = field(default_factory=lambda: [0, 0, 0, 0])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.defect_id,
            "class_key": self.class_key,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "can_send": True,
            "status": "sendable",
            "reason": "ok",
            "manual_override": False,
            "manual_confirmed": False,
            "confirm_mode": "",
            "original_status": "",
            "original_reason": "",
            "area_mm2": self.area_mm2,
            "bbox_uv": {
                "lt": [0, 0], "rt": [0, 0], "rb": [0, 0], "lb": [0, 0]
            },
            "bbox_xywh": self.bbox_xywh,
            "center_uv": [0.0, 0.0],
            "center_galvo_mm": self.center_galvo_mm,
            "corners_galvo_mm": {
                "lt": [0.0, 0.0], "rt": [0.0, 0.0],
                "rb": [0.0, 0.0], "lb": [0.0, 0.0]
            },
            "corner_status": {
                "lt": {"can_send": True, "status": "sendable", "reason": "ok"},
                "rt": {"can_send": True, "status": "sendable", "reason": "ok"},
                "rb": {"can_send": True, "status": "sendable", "reason": "ok"},
                "lb": {"can_send": True, "status": "sendable", "reason": "ok"},
            }
        }


@dataclass
class CompensationParams:
    """激光工艺参数补偿值（feedback.json 中 compensation 字段的内容）。"""
    fill_power: Optional[float] = None        # 调整后的填充功率 (W)
    fill_speed: Optional[float] = None        # 调整后的填充速度 (mm/s)
    scan_spacing: Optional[float] = None      # 调整后的扫描间距 (mm)

    def to_dict(self) -> Optional[Dict[str, Any]]:
        result = {}
        if self.fill_power is not None:
            result["fill_power"] = self.fill_power
        if self.fill_speed is not None:
            result["fill_speed"] = self.fill_speed
        if self.scan_spacing is not None:
            result["scan_spacing"] = self.scan_spacing
        return result if result else None


@dataclass
class DetectionFeedback:
    """检测反馈（写入 feedback.json 的完整结构）。"""
    command_id: int
    layer: int
    job_name: str
    device_id: str
    detection_time: str

    # 缺陷检测结果
    powder_insufficient: bool = False
    warpage: bool = False
    blade_damage: bool = False
    confidence: Dict[str, float] = field(default_factory=lambda: {
        "powder_insufficient": 0.0,
        "warpage": 0.0,
        "blade_damage": 0.0,
    })

    # 决策动作
    action: str = "continue"
    recommended_action: str = "continue"
    blade_damage_alarm: bool = False
    stop_print: bool = False

    # 参数调整
    powder_multiplier: float = 1.0
    recommended_powder_multiplier: float = 1.0
    compensation: Optional[Dict] = None

    # 信息
    message: str = ""
    defect_count: int = 0
    defect_summary: str = ""
    coordinate_dry_run: bool = False
    defect_coordinate_unit: str = "mm"
    defect_coordinate_space: str = "galvo"

    # 缺陷列表
    defects: List[DefectInfo] = field(default_factory=list)

    def add_defect(self, defect: DefectInfo) -> None:
        self.defects.append(defect)
        self._update_summary()

    def set_action_stop(self, message: str = "") -> None:
        self.action = "stop"
        self.recommended_action = "stop"
        self.stop_print = True
        if message:
            self.message = message

    def set_action_continue(
        self,
        powder_multiplier: float = 1.0,
        compensation: Optional[CompensationParams] = None,
        message: str = "",
    ) -> None:
        self.action = "continue"
        self.recommended_action = "adjust_continue"
        self.stop_print = False
        self.blade_damage_alarm = False
        self.powder_multiplier = powder_multiplier
        self.recommended_powder_multiplier = powder_multiplier
        if compensation is not None:
            self.compensation = compensation.to_dict()
        if message:
            self.message = message

    def _update_summary(self) -> None:
        powder = sum(1 for d in self.defects if d.class_key == "powder_insufficient")
        warp = sum(1 for d in self.defects if d.class_key == "warpage")
        scraper = sum(1 for d in self.defects if d.class_key == "scraper_damage")

        self.powder_insufficient = powder > 0
        self.warpage = warp > 0
        self.blade_damage = scraper > 0
        self.defect_count = len(self.defects)
        self.defect_summary = f"powder_lack={powder}, warping_exposure={warp}, scraper_damage={scraper}"

        if powder > 0:
            self.confidence["powder_insufficient"] = max(
                d.confidence for d in self.defects if d.class_key == "powder_insufficient"
            )
        if warp > 0:
            self.confidence["warpage"] = max(
                d.confidence for d in self.defects if d.class_key == "warpage"
            )
        if scraper > 0:
            self.confidence["blade_damage"] = max(
                d.confidence for d in self.defects if d.class_key == "scraper_damage"
            )

        if scraper > 0:
            self.blade_damage_alarm = True
            if self.action != "stop":
                self.set_action_stop(
                    self.message or f"第{self.layer}层检测到刮刀破损报警，建议停止打印"
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "data": {
                "type": "detection_feedback",
                "trigger": "post_detection",
                "layer": self.layer,
                "job_name": self.job_name,
                "device_id": self.device_id,
                "result_time": self.detection_time,

                "powder_insufficient": self.powder_insufficient,
                "warpage": self.warpage,
                "blade_damage": self.blade_damage,
                "confidence": self.confidence,

                "action": self.action,
                "recommended_action": self.recommended_action,
                "blade_damage_alarm": self.blade_damage_alarm,
                "stop_print": self.stop_print,
                "powder_multiplier": self.powder_multiplier,
                "recommended_powder_multiplier": self.recommended_powder_multiplier,
                "compensation": self.compensation,

                "message": self.message,
                "defect_count": self.defect_count,
                "defect_summary": self.defect_summary,
                "coordinate_dry_run": self.coordinate_dry_run,
                "defect_coordinate_unit": self.defect_coordinate_unit,
                "defect_coordinate_space": self.defect_coordinate_space,

                "defects": [d.to_dict() for d in self.defects],
            }
        }
