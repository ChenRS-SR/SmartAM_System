"""
核心逻辑模块
============
包含：模型推理、串口通信、调控算法

模块结构:
- fdm/ - FDM (熔融沉积成型) 工艺模块
- slm/ - SLM (选择性激光熔化) 工艺模块
- sls/ - SLS (选择性激光烧结) 工艺模块
- common/ - 通用模块 (推理、控制、模拟等)
"""

# FDM模块导出
from .fdm import (
    DataAcquisition,
    AcquisitionConfig,
    AcquisitionState,
    FrameData,
    get_acquisition,
    get_daq_system,
    reset_acquisition,
    IDSCamera,
    get_ids_camera,
    reset_ids_camera,
    SideCamera,
    get_side_camera,
    reset_side_camera,
    FotricEnhancedDevice,
    Fotric628CHDevice,
    M114Coordinator,
    get_coordinator,
    reset_coordinator,
    ParameterManager,
    ParameterSet,
    ParameterMode,
    STANDARD_TOWERS,
    HEIGHT_SEGMENTS,
)

__all__ = [
    # FDM主采集
    'DataAcquisition',
    'AcquisitionConfig',
    'AcquisitionState',
    'FrameData',
    'get_acquisition',
    'get_daq_system',
    'reset_acquisition',
    
    # FDM相机
    'IDSCamera',
    'get_ids_camera',
    'reset_ids_camera',
    'SideCamera',
    'get_side_camera',
    'reset_side_camera',
    
    # FDM热像仪
    'FotricEnhancedDevice',
    'Fotric628CHDevice',
    
    # FDM协调器
    'M114Coordinator',
    'get_coordinator',
    'reset_coordinator',
    
    # FDM参数管理
    'ParameterManager',
    'ParameterSet',
    'ParameterMode',
    'STANDARD_TOWERS',
    'HEIGHT_SEGMENTS',
]
