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
    """SLM健康状态数据
    
    状态码定义（与前端保持一致）：
    -1: 未开机
     0: 健康
     1: 刮刀磨损
     2: 激光功率异常
     3: 保护气体异常
     4: 复合故障
    """
    status: SLMHealthStatus = SLMHealthStatus.POWER_OFF
    status_code: int = -1
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
    camera_ch1: Optional[Dict] = None
    camera_ch2: Optional[Dict] = None
    
    # 红外热像数据
    thermal: Optional[Dict] = None
    thermal_image: Optional[bytes] = None
    
    # 振动数据
    vibration: Optional[Dict] = None
    vibration_waveform: Dict = field(default_factory=dict)
    
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
        
        # 波形数据缓存
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
        
        # 视频录制器
        self._video_recorder: Optional[Any] = None
        self._video_recorder_enabled = False
        
        # 视频诊断引擎
        self._diagnosis_engine: Optional[Any] = None
        self._auto_diagnosis_enabled = False
        
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
        self._health_state.status_code = 0
        self._health_state.status_labels = ['系统健康']
        print("[SLMAcquisition] 健康状态已更新为: HEALTHY (状态码: 0)")
        
        # 启动视频录制（如果启用）
        if self._video_recorder_enabled and self._video_recorder:
            self._video_recorder.start_recording()
    
    def stop(self):
        """停止数据采集"""
        print("[SLMAcquisition] 停止数据采集")
        self._停止标志.set()
        
        if self._采集线程 and self._采集线程.is_alive():
            self._采集线程.join(timeout=2.0)
        
        # 停止视频录制
        if self._video_recorder:
            self._video_recorder.stop_recording()
        
        # 停止传感器
        if self.camera_manager:
            self.camera_manager.disconnect()
        if self.vibration_sensor:
            self.vibration_sensor.disconnect()
        if self.thermal_camera:
            self.thermal_camera.disconnect()
        
        # 重置健康状态为未开机
        self._health_state.status = SLMHealthStatus.POWER_OFF
        self._health_state.status_code = -1
        self._health_state.status_labels = []
        print("[SLMAcquisition] 健康状态已重置为: POWER_OFF (状态码: -1)")
        
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
            thermal_data = self.thermal_camera.get_data()
            if thermal_data:
                packet.thermal = {
                    'temp_max': thermal_data.max_temp,
                    'temp_min': thermal_data.min_temp,
                    'temp_avg': thermal_data.avg_temp,
                    'melt_pool_temp': getattr(thermal_data, 'melt_pool_temp', 0)
                }
        
        # 4. 振动数据
        if self.vibration_sensor and self.vibration_enabled:
            vib_data = self.vibration_sensor.read_data()
            if vib_data:
                packet.vibration = {
                    'x': vib_data.x,
                    'y': vib_data.y,
                    'z': vib_data.z,
                    'amplitude': vib_data.amplitude,
                    'timestamp': vib_data.timestamp
                }
                
                # 更新波形缓冲区
                with self._波形锁:
                    self._vibration_buffer_x.append(vib_data.x)
                    self._vibration_buffer_y.append(vib_data.y)
                    self._vibration_buffer_z.append(vib_data.z)
                    
                    # 限制缓冲区大小
                    if len(self._vibration_buffer_x) > self._最大波形点数:
                        self._vibration_buffer_x = self._vibration_buffer_x[-self._最大波形点数:]
                        self._vibration_buffer_y = self._vibration_buffer_y[-self._最大波形点数:]
                        self._vibration_buffer_z = self._vibration_buffer_z[-self._最大波形点数:]
                
                packet.vibration_waveform = {
                    'x': self._vibration_buffer_x[-100:] if len(self._vibration_buffer_x) > 100 else self._vibration_buffer_x,
                    'y': self._vibration_buffer_y[-100:] if len(self._vibration_buffer_y) > 100 else self._vibration_buffer_y,
                    'z': self._vibration_buffer_z[-100:] if len(self._vibration_buffer_z) > 100 else self._vibration_buffer_z,
                    'sample_count': len(self._vibration_buffer_x)
                }
        
        # 5. 统计数据
        packet.statistics = {
            'fps': self._statistics['fps'],
            'total_frames': self.frame_number,
            'duration': time.time() - self._statistics['start_time'] if self._statistics['start_time'] else 0
        }
        
        # 6. 健康状态
        packet.health = self._health_state.to_dict()
        
        return packet
    
    def _获取传感器状态(self) -> Dict:
        """获取传感器状态"""
        return {
            'camera_ch1': {
                'enabled': self.camera_ch1_enabled,
                'connected': self.camera_manager is not None and self.camera_manager.is_connected if hasattr(self.camera_manager, 'is_connected') else False
            },
            'camera_ch2': {
                'enabled': self.camera_ch2_enabled,
                'connected': self.camera_manager is not None and self.camera_manager.is_connected if hasattr(self.camera_manager, 'is_connected') else False
            },
            'thermal': {
                'enabled': self.thermal_enabled,
                'connected': self.thermal_camera is not None and self.thermal_camera.is_connected if hasattr(self.thermal_camera, 'is_connected') else False
            },
            'vibration': {
                'enabled': self.vibration_enabled,
                'connected': self.vibration_sensor is not None and self.vibration_sensor.is_connected if hasattr(self.vibration_sensor, 'is_connected') else False,
                'com_port': self.vibration_com_port
            }
        }
    
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
        
        if self.camera_manager:
            if sensor == 'camera_ch1':
                self.camera_manager.set_camera_enabled('CH1', enabled)
            elif sensor == 'camera_ch2':
                self.camera_manager.set_camera_enabled('CH2', enabled)
    
    def set_com_port(self, port: str):
        """设置振动传感器COM口"""
        self.vibration_com_port = port
        if self.vibration_sensor:
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
        
        if status_code == 0:
            self._health_state.status = SLMHealthStatus.HEALTHY
            self._health_state.laser_system = {'status': 'healthy', 'message': '健康'}
            self._health_state.powder_system = {'status': 'healthy', 'message': '健康'}
            self._health_state.gas_system = {'status': 'healthy', 'message': '健康'}
        elif status_code == 1:
            self._health_state.status = SLMHealthStatus.POWDER_FAULT
            self._health_state.laser_system = {'status': 'healthy', 'message': '健康'}
            self._health_state.powder_system = {'status': 'fault', 'message': '刮刀磨损'}
            self._health_state.gas_system = {'status': 'healthy', 'message': '健康'}
        elif status_code == 2:
            self._health_state.status = SLMHealthStatus.LASER_FAULT
            self._health_state.laser_system = {'status': 'fault', 'message': '激光功率衰减或波动'}
            self._health_state.powder_system = {'status': 'healthy', 'message': '健康'}
            self._health_state.gas_system = {'status': 'healthy', 'message': '健康'}
        elif status_code == 3:
            self._health_state.status = SLMHealthStatus.GAS_FAULT
            self._health_state.laser_system = {'status': 'healthy', 'message': '健康'}
            self._health_state.powder_system = {'status': 'healthy', 'message': '健康'}
            self._health_state.gas_system = {'status': 'fault', 'message': '舱内气体异常'}
        elif status_code == 4:
            self._health_state.status = SLMHealthStatus.COMPOUND_FAULT
            self._health_state.laser_system = {'status': 'fault', 'message': '需检查'}
            self._health_state.powder_system = {'status': 'fault', 'message': '需检查'}
            self._health_state.gas_system = {'status': 'fault', 'message': '需检查'}
        else:
            self._health_state.status = SLMHealthStatus.POWER_OFF
            self._health_state.laser_system = {'status': 'unknown', 'message': '未检测'}
            self._health_state.powder_system = {'status': 'unknown', 'message': '未检测'}
            self._health_state.gas_system = {'status': 'unknown', 'message': '未检测'}
    
    def register_ws_callback(self, callback: Callable[[Dict], None]):
        """注册WebSocket回调"""
        if callback not in self._ws_callbacks:
            self._ws_callbacks.append(callback)
    
    def unregister_ws_callback(self, callback: Callable[[Dict], None]):
        """取消注册WebSocket回调"""
        if callback in self._ws_callbacks:
            self._ws_callbacks.remove(callback)
    
    # ========== 视频录制与诊断方法 ==========
    
    def setup_video_recorder(self, save_dir: str = None) -> bool:
        """设置视频录制器"""
        try:
            from .video_recorder import VideoRecorder
            
            self._video_recorder = VideoRecorder(save_dir=save_dir or "./recordings")
            
            # 注册帧获取回调
            def get_ch1_frame():
                if self.camera_manager:
                    return self.camera_manager.get_latest_frame('CH1')
                return None
            
            def get_ch2_frame():
                if self.camera_manager:
                    return self.camera_manager.get_latest_frame('CH2')
                return None
            
            def get_ch3_frame():
                if self.thermal_camera and hasattr(self.thermal_camera, 'get_latest_frame'):
                    return self.thermal_camera.get_latest_frame()
                return None
            
            self._video_recorder.register_frame_callback('CH1', get_ch1_frame)
            self._video_recorder.register_frame_callback('CH2', get_ch2_frame)
            self._video_recorder.register_frame_callback('CH3', get_ch3_frame)
            
            print(f"[SLMAcquisition] 视频录制器已设置，保存目录: {self._video_recorder.get_save_directory()}")
            return True
        except Exception as e:
            print(f"[SLMAcquisition] 设置视频录制器失败: {e}")
            return False
    
    def set_video_recording_enabled(self, enabled: bool):
        """启用/禁用视频录制"""
        self._video_recorder_enabled = enabled
        print(f"[SLMAcquisition] 视频录制已{'启用' if enabled else '禁用'}")
        
        if self.is_running and self._video_recorder:
            if enabled:
                self._video_recorder.start_recording()
            else:
                self._video_recorder.stop_recording()
    
    def set_video_recording_interval(self, interval_seconds: int):
        """设置视频录制间隔"""
        if self._video_recorder:
            self._video_recorder.set_interval(interval_seconds)
    
    def set_video_save_directory(self, save_dir: str) -> bool:
        """设置视频保存目录"""
        if self._video_recorder:
            return self._video_recorder.set_save_directory(save_dir)
        return False
    
    def get_video_recorder_status(self) -> Dict:
        """获取视频录制器状态"""
        if self._video_recorder:
            return {
                'enabled': self._video_recorder_enabled,
                **self._video_recorder.get_status()
            }
        return {
            'enabled': False,
            'is_recording': False,
            'save_directory': '',
            'interval_seconds': 30,
            'clip_duration': 5,
            'fps': 10,
            'history_count': 0
        }
    
    def get_video_recording_history(self) -> List[Dict]:
        """获取视频录制历史"""
        if self._video_recorder:
            return self._video_recorder.get_recording_history()
        return []
    
    def setup_diagnosis_engine(self, model_path: str = None, frame_count: int = 50) -> bool:
        """设置视频诊断引擎"""
        try:
            from .video_diagnosis import get_diagnosis_engine
            
            self._diagnosis_engine = get_diagnosis_engine(model_path, frame_count)
            
            # 注册诊断结果回调
            def on_diagnosis_result(result):
                # 更新健康状态
                self.update_health_status(
                    result.status_code,
                    result.status_labels if hasattr(result, 'status_labels') else [result.status_label]
                )
                print(f"[SLMAcquisition] 诊断结果更新健康状态: {result.status_code} - {result.status_label}")
            
            self._diagnosis_engine.register_callbacks(
                result_callback=on_diagnosis_result
            )
            
            print(f"[SLMAcquisition] 诊断引擎已设置，模型: {model_path or '模拟模式'}")
            return True
        except Exception as e:
            print(f"[SLMAcquisition] 设置诊断引擎失败: {e}")
            return False
    
    def start_video_diagnosis(self, video_files: Dict[str, str], mode: str = "simulation") -> bool:
        """开始视频诊断
        
        Args:
            video_files: {'CH1': 'path/to/video1.mp4', 'CH2': '...', 'CH3': '...'}
            mode: 'realtime' 或 'simulation'
        """
        if not self._diagnosis_engine:
            print("[SLMAcquisition] 诊断引擎未初始化")
            return False
        
        from .video_diagnosis import DiagnosisMode
        
        diagnosis_mode = DiagnosisMode.REALTIME if mode == "realtime" else DiagnosisMode.SIMULATION
        
        return self._diagnosis_engine.start_diagnosis(video_files, diagnosis_mode)
    
    def get_diagnosis_status(self) -> Dict:
        """获取诊断状态"""
        if self._diagnosis_engine:
            return self._diagnosis_engine.get_status()
        return {
            'status': 'idle',
            'progress': 0,
            'has_model': False
        }


# 全局实例
_slm_acquisition_instance: Optional[SLMAcquisition] = None


def get_slm_acquisition(use_mock: bool = False) -> SLMAcquisition:
    """获取SLM采集实例（单例）"""
    global _slm_acquisition_instance
    if _slm_acquisition_instance is None:
        _slm_acquisition_instance = SLMAcquisition(use_mock=use_mock)
    return _slm_acquisition_instance
