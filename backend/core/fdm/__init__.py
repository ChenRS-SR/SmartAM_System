"""
FDM (Fused Deposition Modeling) 模块
=====================================
熔融沉积成型工艺监控模块

包含设备驱动:
- IDS相机 (ids_camera.py) - 随轴工业相机
- 旁轴相机 (side_camera.py) - USB摄像头
- Fotric热像仪 (fotric_driver.py) - 红外温度监测
- 参数管理器 (parameter_manager.py) - 打印参数管理

主采集类:
- DataAcquisition (data_acquisition.py) - FDM数据采集系统

注意:
- M114协调器 (coordinator.py) 已废弃，改用 DisplayLayerProgress 插件获取 Z 高度
"""

from .data_acquisition import (
    DataAcquisition,
    AcquisitionConfig,
    AcquisitionState,
    FrameData,
    get_acquisition,
    get_daq_system,
    reset_acquisition
)
from .ids_camera import IDSCamera, get_ids_camera, reset_ids_camera
from .side_camera import SideCamera, get_side_camera, reset_side_camera
from .fotric_driver import FotricEnhancedDevice, Fotric628CHEnhanced as Fotric628CHDevice
from .coordinator import M114Coordinator, get_coordinator, reset_coordinator
from .parameter_manager import (
    ParameterManager,
    ParameterSet,
    ParameterMode,
    STANDARD_TOWERS,
    HEIGHT_SEGMENTS
)

__all__ = [
    # 主采集类
    'DataAcquisition',
    'AcquisitionConfig',
    'AcquisitionState',
    'FrameData',
    'get_acquisition',
    'get_daq_system',
    'reset_acquisition',
    
    # 相机
    'IDSCamera',
    'get_ids_camera',
    'reset_ids_camera',
    'SideCamera',
    'get_side_camera',
    'reset_side_camera',
    
    # 热像仪
    'FotricEnhancedDevice',
    'Fotric628CHDevice',
    
    # 协调器 (已废弃：使用 DisplayLayerProgress 插件获取 Z 高度)
    'M114Coordinator',
    'get_coordinator',
    'reset_coordinator',
    
    # 参数管理
    'ParameterManager',
    'ParameterSet',
    'ParameterMode',
    'STANDARD_TOWERS',
    'HEIGHT_SEGMENTS',
]

__version__ = "1.0.0"
