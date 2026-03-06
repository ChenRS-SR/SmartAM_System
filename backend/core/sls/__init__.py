"""
SLS (选择性激光烧结) 采集模块

核心功能：
- 振动传感器监测刮刀运动
- 扑粉检测状态机
- 双摄像头触发采集
- 红外热像仪数据采集
"""

from .sls_acquisition import SLSAcquisition, get_sls_acquisition
from .powder_detector import PowderDetector, MotionState
from .vibration_sensor import VibrationSensor

__all__ = [
    'SLSAcquisition',
    'get_sls_acquisition', 
    'PowderDetector',
    'MotionState',
    'VibrationSensor',
]
