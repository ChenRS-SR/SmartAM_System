"""SLM 工艺综合评分 —— 体能量密度 (VED) 计算。

体能量密度 VED = fill_power / (fill_speed × scan_spacing × layer_thickness)
单位 J/mm³，用于判断粉末是否被正确熔化：
  - VED 过低 → 未熔合 / 层间结合差
  - VED 过高 → 过熔 / 气孔 / 飞溅

原样移植自 Desktop/slm/slm_metrics.py（无 GUI 依赖）。
"""

from typing import Optional, Tuple


def compute_energy_density(
    fill_power: float,
    fill_speed: float,
    scan_spacing: float,
    layer_thickness: float,
) -> Optional[float]:
    """计算体能量密度 (J/mm³)。任一输入为 None / 0 / 负数或分母 <= 0 时返回 None。"""
    if not all((fill_power, fill_speed, scan_spacing, layer_thickness)):
        return None
    denom = fill_speed * scan_spacing * layer_thickness
    if denom <= 0:
        return None
    return fill_power / denom


def score_energy_density(
    ved: Optional[float],
    window_min: float,
    window_max: float,
) -> Tuple[str, str]:
    """根据体能量密度给出评分状态和一句话建议。

    返回 (status, suggestion)：
      status: "low" | "ok" | "high" | "unknown"
    """
    if ved is None:
        return "unknown", "参数不完整，无法计算体能量密度"

    if ved < window_min:
        return "low", "体能量密度偏低，建议提高功率或降低速度，避免未熔合缺陷"
    if ved > window_max:
        return "high", "体能量密度偏高，建议降低功率或提高速度，避免过熔/气孔"
    return "ok", "体能量密度在工艺窗口内，无需调整"
