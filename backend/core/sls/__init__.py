"""
SLS (Selective Laser Sintering) 设备控制模块
=============================================
集成Fotric热成像仪、振动传感器和舵机控制器

设备清单:
- Fotric 628CH: 红外热成像仪 (HTTP API)
- WTVB02-485: 三轴振动传感器 (Modbus RTU)
- ROBOIDE Servo: 舵机控制器 (Serial)

使用示例:
    from backend.core.sls import get_sls_acquisition
    
    # 获取采集实例
    sls = get_sls_acquisition(simulation_mode=True)
    
    # 初始化设备
    sls.initialize_devices()
    
    # 开始采集
    sls.start_acquisition()
    
    # 获取数据
    data = sls.get_current_data()
"""

from .fotric_device import FotricEnhancedDevice, MockFotricDevice
from .vibration_sensor import VibrationSensor, MockVibrationSensor, VibrationData
from .vibration_optimizer import VibrationOptimizer, OptimizerConfig
from .servo_controller import ServoController, MockServoController
from .sls_acquisition import (
    SLSAcquisition,
    SLSDataPacket,
    get_sls_acquisition
)

__all__ = [
    # Fotric热成像仪
    'FotricEnhancedDevice',
    'MockFotricDevice',
    
    # 振动传感器
    'VibrationSensor',
    'MockVibrationSensor',
    'VibrationData',
    
    # 振动优化器
    'VibrationOptimizer',
    'OptimizerConfig',
    
    # 舵机控制器
    'ServoController',
    'MockServoController',
    
    # SLS采集
    'SLSAcquisition',
    'SLSDataPacket',
    'get_sls_acquisition',
]

__version__ = "1.0.0"
