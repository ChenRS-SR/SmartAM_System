"""
SLM数据采集主模块
================
整合摄像头、振动传感器、红外热像仪的数据采集
提供统一的接口和WebSocket数据推送
"""

import time
import json
import threading
import asyncio
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import numpy as np

from .vibration_sensor import VibrationSensor, MockVibrationSensor, VibrationData
from .thermal_camera import ThermalCamera, MockThermalCamera, ThermalData
from .camera_manager import CameraManager, MockCameraManager, CameraFrame


class SLMHealthStatus(Enum):
    """SLM设备健康状态"""
    POWER_OFF = "power_off"           # 未开机
    HEALTHY = "healthy"               # 健康
    LASER_FAULT = "laser_fault"       # 激光系统异常
    POWDER_FAULT = "powder_fault"     # 铺粉系统异常
    GAS_FAULT = "gas_fault"           # 保护气体异常
    COMPOUND_FAULT = "compound_fault" # 复合故障


@dataclass
class SLMHealthState:
    """SLM健康状态数据"""
    status: SLMHealthStatus = SLMHealthStatus.POWER_OFF
    status_code: int = 0  # 0:健康, 1:刮刀磨损, 2:刮刀磨损(重复?), 3:激光功率异常, 4:保护气体异常
    status_labels: List[str] = field(default_factory=list)
    
    # 子系统状态
    laser_system: Dict = field(default_factory=lambda: {'status': 'unknown', 'message': '未检测'})
    powder_system: Dict = field(default_factory=lambda: {'status': 'unknown', 'message': '未检测'})
    gas_system: Dict = field(default_factory=lambda: {'status': 'unknown', 'message': '未检测'})
    
    def to_dict(self) -> Dict:
        return {
            'status': self.status.value,
            'status_code': self.status_code,
            'status_labels': self.status_labels,
            'laser_system': self.laser_system,
            'powder_system': self.powder_system,
            'gas_system': self.gas_system
        }


@dataclass
class SLMDataPacket:
    """SLM数据包"""
    timestamp: float
    frame_number: int
    
    # 传感器连接状态
    sensor_status: Dict = field(default_factory=dict)
    
    # 摄像头数据
    camera_ch1: Optional[Dict] = None  # JPEG图像的base64或URL
    camera_ch2: Optional[Dict] = None
    
    # 红外热像数据
    thermal: Optional[Dict] = None
    thermal_image: Optional[bytes] = None  # JPEG图像
    
    # 振动数据
    vibration: Optional[Dict] = None
    vibration_waveform: Dict = field(default_factory=dict)  # XYZ波形数据
    
    # 统计数据
    statistics: Dict = field(default_factory=dict)
    
    # 健康状态
    health: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'frame_number': self.frame_number,
            'sensor_status': self.sensor_status,
            'camera_ch1': self.camera_ch1,
            'camera_ch2': self.camera_ch2,
            'thermal': self.thermal,
            'vibration': self.vibration,
            'vibration_waveform': self.vibration_waveform,
            'statistics': self.statistics,
            'health': self.health
        }


class SLMAcquisition:
    """SLM数据采集主类"""
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        
        # 传感器实例
        self.camera_manager: Optional[Any] = None
        self.vibration_sensor: Optional[Any] = None
        self.thermal_camera: Optional[Any] = None
        
        # 配置
        self.camera_ch1_index = 2
        self.camera_ch2_index = 3
        self.vibration_com_port = "COM5"
        self.vibration_baudrate = 9600
        
        # 状态
        self.is_running = False
        self.frame_number = 0
        
        # 传感器启用状态
        self.camera_ch1_enabled = True
        self.camera_ch2_enabled = True
        self.vibration_enabled = True
        self.thermal_enabled = True
        
        # 数据缓存
        self._latest_packet: Optional[SLMDataPacket] = None
        self._数据锁 = threading.Lock()
        
        # 波形数据缓存 (用于实时波形显示)
        self._vibration_buffer_x: List[float] = []
        self._vibration_buffer_y: List[float] = []
        self._vibration_buffer_z: List[float] = []
        self._波形锁 = threading.Lock()
        self._最大波形点数 = 500
        
        # 采集线程
        self._采集线程: Optional[threading.Thread] = None
        self._停止标志 = threading.Event()
        
        # WebSocket回调
        self._ws_callbacks: List[Callable[[Dict], None]] = []
        
        # 健康状态
        self._health_state = SLMHealthState()
        
        # 统计信息
        self._statistics = {
            'start_time': None,
            'total_frames': 0,
            'fps': 0.0,
            'last_fps_time': 0,
            'frame_count': 0
        }
    
    def initialize(self, camera_ch1_index: int = 2, camera_ch2_index: int = 3,
                   vibration_com: str = "COM5", use_mock: bool = None) -> bool:
        """初始化所有传感器"""
        if use_mock is not None:
            self.use_mock = use_mock
        
        self.camera_ch1_index = camera_ch1_index
        self.camera_ch2_index = camera_ch2_index
        self.vibration_com_port = vibration_com
        
        print(f"[SLMAcquisition] 初始化传感器 (模拟模式: {self.use_mock})...")
        
        # 创建传感器实例
        if self.use_mock:
            self.camera_manager = MockCameraManager(
                ch1_index=camera_ch1_index,
                ch2_index=camera_ch2_index
            )
            self.vibration_sensor = MockVibrationSensor(com_port=vibration_com)
            self.thermal_camera = MockThermalCamera()
        else:
            self.camera_manager = CameraManager(
                ch1_index=camera_ch1_index,
                ch2_index=camera_ch2_index
            )
            self.vibration_sensor = VibrationSensor(com_port=vibration_com)
            self.thermal_camera = ThermalCamera()
        
        # 连接传感器
        success = True
        
        if self.camera_ch1_enabled or self.camera_ch2_enabled:
            if not self.camera_manager.connect():
                print("[SLMAcquisition] 摄像头连接失败，将使用模拟数据")
                # 如果真实连接失败，切换到模拟
                if not self.use_mock:
                    self.camera_manager = MockCameraManager(
                        ch1_index=camera_ch1_index,
                        ch2_index=camera_ch2_index
                    )
                    self.camera_manager.connect()
        
        if self.vibration_enabled:
            if not self.vibration_sensor.connect():
                print("[SLMAcquisition] 振动传感器连接失败，将使用模拟数据")
                if not self.use_mock:
                    self.vibration_sensor = MockVibrationSensor(com_port=vibration_com)
                    self.vibration_sensor.connect()
        
        if self.thermal_enabled:
            if not self.thermal_camera.connect():
                print("[SLMAcquisition] 红外热像仪连接失败，将使用模拟数据")
                if not self.use_mock:
                    self.thermal_camera = MockThermalCamera()
                    self.thermal_camera.connect()
        
        print("[SLMAcquisition] 初始化完成")
        return True
    
    def start(self):
        """开始数据采集"""
        if self.is_running:
            return
        
        print("[SLMAcquisition] 开始数据采集")
        
        # 启动传感器采集
        if self.camera_manager:
            self.camera_manager.start_continuous_capture()
        if self.vibration_sensor:
            self.vibration_sensor.start_continuous_read(interval=0.05)
        if self.thermal_camera:
            self.thermal_camera.start_continuous_read(interval=0.1)
        
        # 启动主采集线程
        self._停止标志.clear()
        self._采集线程 = threading.Thread(target=self._采集循环)
        self._采集线程.daemon = True
        self._采集线程.start()
        
        self.is_running = True
        self._statistics['start_time'] = time.time()
        self._statistics['last_fps_time'] = time.time()
        
        # 更新健康状态为开机/健康
        self._health_state.status = SLMHealthStatus.HEALTHY
        print("[SLMAcquisition] 健康状态已更新为: HEALTHY")
    
    def stop(self):
        """停止数据采集"""
        print("[SLMAcquisition] 停止数据采集")
        self._停止标志.set()
        
        if self._采集线程 and self._采集线程.is_alive():
            self._采集线程.join(timeout=2.0)
        
        # 停止传感器
        if self.camera_manager:
            self.camera_manager.disconnect()
        if self.vibration_sensor:
            self.vibration_sensor.disconnect()
        if self.thermal_camera:
            self.thermal_camera.disconnect()
        
        # 重置健康状态为未开机
        self._health_state.status = SLMHealthStatus.POWER_OFF
        print("[SLMAcquisition] 健康状态已重置为: POWER_OFF")
        
        self.is_running = False
    
    def _采集循环(self):
        """主采集循环"""
        while not self._停止标志.is_set():
            try:
                packet = self._采集一帧()
                
                with self._数据锁:
                    self._latest_packet = packet
                    self.frame_number += 1
                
                # 更新统计
                self._更新统计()
                
                # 触发WebSocket回调
                self._触发回调(packet.to_dict())
                
                # 控制帧率 (10 FPS)
                self._停止标志.wait(0.1)
                
            except Exception as e:
                print(f"[SLMAcquisition] 采集错误: {e}")
                self._停止标志.wait(0.1)
    
    def _采集一帧(self) -> SLMDataPacket:
        """采集一帧数据"""
        packet = SLMDataPacket(
            timestamp=time.time(),
            frame_number=self.frame_number
        )
        
        # 1. 传感器状态
        packet.sensor_status = self._获取传感器状态()
        
        # 2. 摄像头数据
        if self.camera_manager:
            if self.camera_ch1_enabled:
                jpeg = self.camera_manager.get_frame_jpeg('CH1')
                if jpeg:
                    packet.camera_ch1 = {
                        'available': True,
                        'timestamp': time.time(),
                        'size': len(jpeg)
                    }
                    # 存储JPEG数据供流服务使用
                    packet.camera_ch1['jpeg_data'] = jpeg
            
            if self.camera_ch2_enabled:
                jpeg = self.camera_manager.get_frame_jpeg('CH2')
                if jpeg:
                    packet.camera_ch2 = {
                        'available': True,
                        'timestamp': time.time(),
                        'size': len(jpeg)
                    }
                    packet.camera_ch2['jpeg_data'] = jpeg
        
        # 3. 红外热像数据
        if self.thermal_camera and self.thermal_enabled:
            thermal_data = self.thermal_camera.get_latest_data()
            if thermal_data:
                packet.thermal = thermal_data.to_dict()
                # 生成热图
                thermal_image = self.thermal_camera.generate_thermal_image(640, 480)
                if thermal_image is not None:
                    import cv2
                    ret, jpeg = cv2.imencode('.jpg', thermal_image, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ret:
                        packet.thermal_image = jpeg.tobytes()
        
        # 4. 振动数据
        if self.vibration_sensor and self.vibration_enabled:
            vib_data = self.vibration_sensor.get_latest_data()
            if vib_data:
                packet.vibration = vib_data.to_dict()
                
                # 更新波形缓冲区
                with self._波形锁:
                    self._vibration_buffer_x.append(vib_data.vx)
                    self._vibration_buffer_y.append(vib_data.vy)
                    self._vibration_buffer_z.append(vib_data.vz)
                    
                    # 限制长度
                    if len(self._vibration_buffer_x) > self._最大波形点数:
                        self._vibration_buffer_x.pop(0)
                        self._vibration_buffer_y.pop(0)
                        self._vibration_buffer_z.pop(0)
                
                # 添加波形数据到包
                with self._波形锁:
                    packet.vibration_waveform = {
                        'x': self._vibration_buffer_x.copy(),
                        'y': self._vibration_buffer_y.copy(),
                        'z': self._vibration_buffer_z.copy(),
                        'sample_count': len(self._vibration_buffer_x)
                    }
        
        # 5. 统计数据
        if self.vibration_sensor and self.vibration_enabled:
            packet.statistics['vibration'] = self.vibration_sensor.calculate_statistics(duration=5.0)
        
        # 6. 健康状态
        packet.health = self._health_state.to_dict()
        
        return packet
    
    def _获取传感器状态(self) -> Dict:
        """获取所有传感器的状态"""
        status = {
            'camera_ch1': {
                'enabled': self.camera_ch1_enabled,
                'connected': False
            },
            'camera_ch2': {
                'enabled': self.camera_ch2_enabled,
                'connected': False
            },
            'vibration': {
                'enabled': self.vibration_enabled,
                'connected': False,
                'com_port': self.vibration_com_port
            },
            'thermal': {
                'enabled': self.thermal_enabled,
                'connected': False
            }
        }
        
        if self.camera_manager:
            cam_status = self.camera_manager.get_status()
            status['camera_ch1']['connected'] = cam_status['CH1']['connected']
            status['camera_ch2']['connected'] = cam_status['CH2']['connected']
        
        if self.vibration_sensor:
            status['vibration']['connected'] = self.vibration_sensor.is_connected
        
        if self.thermal_camera:
            status['thermal']['connected'] = self.thermal_camera.is_connected
        
        return status
    
    def _更新统计(self):
        """更新统计信息"""
        self._statistics['frame_count'] += 1
        self._statistics['total_frames'] = self.frame_number
        
        current_time = time.time()
        elapsed = current_time - self._statistics['last_fps_time']
        
        if elapsed >= 1.0:
            self._statistics['fps'] = self._statistics['frame_count'] / elapsed
            self._statistics['frame_count'] = 0
            self._statistics['last_fps_time'] = current_time
    
    def _触发回调(self, data: Dict):
        """触发WebSocket回调"""
        for callback in self._ws_callbacks:
            try:
                # 如果回调是异步函数，使用asyncio运行
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                print(f"[SLMAcquisition] 回调错误: {e}")
    
    def get_latest_packet(self) -> Optional[SLMDataPacket]:
        """获取最新数据包"""
        with self._数据锁:
            return self._latest_packet
    
    def get_status(self) -> Dict:
        """获取采集状态"""
        return {
            'is_running': self.is_running,
            'frame_number': self.frame_number,
            'fps': self._statistics['fps'],
            'duration': time.time() - self._statistics['start_time'] if self._statistics['start_time'] else 0,
            'sensor_status': self._获取传感器状态()
        }
    
    def set_sensor_enabled(self, sensor: str, enabled: bool):
        """设置传感器启用状态"""
        if sensor == 'camera_ch1':
            self.camera_ch1_enabled = enabled
        elif sensor == 'camera_ch2':
            self.camera_ch2_enabled = enabled
        elif sensor == 'vibration':
            self.vibration_enabled = enabled
        elif sensor == 'thermal':
            self.thermal_enabled = enabled
        
        # 更新摄像头管理器
        if self.camera_manager:
            if sensor == 'camera_ch1':
                self.camera_manager.set_camera_enabled('CH1', enabled)
            elif sensor == 'camera_ch2':
                self.camera_manager.set_camera_enabled('CH2', enabled)
    
    def set_com_port(self, port: str):
        """设置振动传感器COM口"""
        self.vibration_com_port = port
        if self.vibration_sensor:
            # 需要重新初始化
            was_running = self.is_running
            if was_running:
                self.stop()
            
            self.vibration_sensor.com_port = port
            
            if was_running:
                self.start()
    
    def update_health_status(self, status_code: int, labels: List[str] = None):
        """更新设备健康状态（由模型调用）"""
        self._health_state.status_code = status_code
        self._health_state.status_labels = labels or []
        
        # 解析状态码
        # 0: 健康
        # 1: 刮刀磨损
        # 2: 刮刀磨损 (重复)
        # 3: 激光功率异常
        # 4: 保护气体异常
        
        faults = []
        
        # 激光系统状态
        if status_code == 3:
            self._health_state.laser_system = {
                'status': 'fault',
                'message': '激光功率衰减或波动'
            }
            faults.append('laser')
        else:
            self._health_state.laser_system = {
                'status': 'healthy',
                'message': '健康'
            }
        
        # 铺粉系统状态
        if status_code in [1, 2]:
            self._health_state.powder_system = {
                'status': 'fault',
                'message': '刮刀磨损'
            }
            faults.append('powder')
        else:
            self._health_state.powder_system = {
                'status': 'healthy',
                'message': '健康'
            }
        
        # 保护气体状态
        if status_code == 4:
            self._health_state.gas_system = {
                'status': 'fault',
                'message': '舱内气体异常'
            }
            faults.append('gas')
        else:
            self._health_state.gas_system = {
                'status': 'healthy',
                'message': '健康'
            }
        
        # 确定总体状态
        if len(faults) == 0:
            self._health_state.status = SLMHealthStatus.HEALTHY
        elif len(faults) > 1:
            self._health_state.status = SLMHealthStatus.COMPOUND_FAULT
        elif 'laser' in faults:
            self._health_state.status = SLMHealthStatus.LASER_FAULT
        elif 'powder' in faults:
            self._health_state.status = SLMHealthStatus.POWDER_FAULT
        elif 'gas' in faults:
            self._health_state.status = SLMHealthStatus.GAS_FAULT
    
    def register_ws_callback(self, callback: Callable[[Dict], None]):
        """注册WebSocket回调"""
        if callback not in self._ws_callbacks:
            self._ws_callbacks.append(callback)
    
    def unregister_ws_callback(self, callback: Callable[[Dict], None]):
        """取消注册WebSocket回调"""
        if callback in self._ws_callbacks:
            self._ws_callbacks.remove(callback)


# 全局实例
_slm_acquisition_instance: Optional[SLMAcquisition] = None


def get_slm_acquisition(use_mock: bool = False) -> SLMAcquisition:
    """获取SLM采集实例（单例）"""
    global _slm_acquisition_instance
    if _slm_acquisition_instance is None:
        _slm_acquisition_instance = SLMAcquisition(use_mock=use_mock)
    return _slm_acquisition_instance
