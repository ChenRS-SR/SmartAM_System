"""
SLM 核心模块
============
提供SLM设备的数据采集、视频播放和调控功能

导出:
- SLMAcquisition: 主采集类
- VideoPlayerManager: 统一视频播放器管理器
- get_slm_acquisition: 获取采集实例
- reset_slm_acquisition: 重置采集实例
"""

from .slm_acquisition import SLMAcquisition, get_slm_acquisition, reset_slm_acquisition
from .video_player_manager import get_player_manager, reset_player_manager

__all__ = [
    'SLMAcquisition',
    'get_slm_acquisition',
    'reset_slm_acquisition',
    'get_player_manager',
    'reset_player_manager',
]
