"""数据源接口。实时接入时（例如由 SmartAM 的采集模块写入新层）实现同名方法即可替换离线回放。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LayerInputs:
    """识别与溯源所需的单层输入。"""
    layer: int
    before: Path                 # 铺粉后图像
    after: Path                  # 烧结后图像
    torque_times: list           # 铺粉段扭矩窗口的时间戳（精确到秒）
    scraper: list                # 刮刀扭矩 %
    platform: list               # 加工平台扭矩 %
    extra: dict = field(default_factory=dict)


class DataSource:
    """一台设备的数据源。task_id 为成形任务编号，layer 为层号。"""

    def tasks(self) -> list[dict]:
        """[{id, name, startTime, layers, height, parts, layerThickness}]"""
        raise NotImplementedError

    def layers(self, task_id: str) -> list[int]:
        """该任务中数据完整（铺粉后/烧结后图像成对、扭矩对齐）的层号，升序。"""
        raise NotImplementedError

    def inputs(self, task_id: str, layer: int) -> LayerInputs:
        raise NotImplementedError

    def frame(self, task_id: str, layer: int) -> dict:
        """数据接入页的单层数据：图像信息、铺粉与烧结段扭矩曲线、设备状态参数、采集通道。"""
        raise NotImplementedError

    def record(self, task_id: str, layer: int) -> dict:
        """逐层接入记录的一行。"""
        raise NotImplementedError

    def image_path(self, task_id: str, layer: int, kind: str) -> Path:
        """kind: before / after。只在服务端使用，不返回给前端。"""
        raise NotImplementedError

    def layer_time(self, task_id: str, layer: int) -> str:
        raise NotImplementedError

    def alarms(self, task_id: str, until: str | None = None, n: int = 5) -> list[dict]:
        """设备报警（最新在前）：[{time, text}]"""
        return []
