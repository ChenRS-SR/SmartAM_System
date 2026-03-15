"""
SLS数据采集模块
===============
集成Fotric热成像仪、振动传感器和舵机控制器
参考SLS项目实现，使用HTTP-based Fotric设备和Modbus振动传感器
"""

import asyncio
import threading
import time
import numpy as np
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import cv2

from .fotric_device import FotricEnhancedDevice, MockFotricDevice
from .vibration_sensor import VibrationSensor, MockVibrationSensor
from .vibration_optimizer import VibrationOptimizer
from .servo_controller import ServoController, MockServoController


@dataclass
class SLSDataPacket:
    """SLS数据包"""
    timestamp: float
    
    # 热成像数据
    thermal_temp_min: float = 0.0
    thermal_temp_max: float = 0.0
    thermal_temp_avg: float = 0.0
    thermal_temp_center: float = 0.0
    thermal_image: Optional[np.ndarray] = None
    thermal_jpeg: Optional[bytes] = None
    
    # 振动数据
    vibration_vx: float = 0.0
    vibration_vy: float = 0.0
    vibration_vz: float = 0.0
    vibration_dx: float = 0.0
    vibration_dy: float = 0.0
    vibration_dz: float = 0.0
    vibration_fx: float = 0.0
    vibration_fy: float = 0.0
    vibration_fz: float = 0.0
    vibration_magnitude: float = 0.0
    vibration_triggered: bool = False
    
    # 舵机状态
    servo_angle: int = 90
    servo_is_moving: bool = False
    
    # 系统状态
    health_status: int = 0  # 0=healthy, 1=powder, 2=laser, 3=temp, 4=compound
    powder_flowing: bool = False
    
    def to_dict(self) -> Dict:
        """转换为字典（用于JSON序列化）"""
        return {
            'timestamp': self.timestamp,
            'thermal': {
                'temp_min': round(self.thermal_temp_min, 2),
                'temp_max': round(self.thermal_temp_max, 2),
                'temp_avg': round(self.thermal_temp_avg, 2),
                'temp_center': round(self.thermal_temp_center, 2),
                'has_image': self.thermal_image is not None or self.thermal_jpeg is not None
            },
            'vibration': {
                'velocity': {
                    'x': round(self.vibration_vx, 4),
                    'y': round(self.vibration_vy, 4),
                    'z': round(self.vibration_vz, 4)
                },
                'displacement': {
                    'x': round(self.vibration_dx, 2),
                    'y': round(self.vibration_dy, 2),
                    'z': round(self.vibration_dz, 2)
                },
                'frequency': {
                    'x': round(self.vibration_fx, 2),
                    'y': round(self.vibration_fy, 2),
                    'z': round(self.vibration_fz, 2)
                },
                'magnitude': round(self.vibration_magnitude, 4),
                'triggered': self.vibration_triggered
            },
            'servo': {
                'angle': self.servo_angle,
                'is_moving': self.servo_is_moving
            },
            'system': {
                'health_status': self.health_status,
                'powder_flowing': self.powder_flowing
            }
        }


class SLSAcquisition:
    """SLS数据采集主类"""
    
    def __init__(self, 
                 fotric_ip: str = "192.168.1.100",
                 vibration_port: str = "COM5",
                 servo_port: str = "COM6",
                 simulation_mode: bool = False):
        """
        初始化SLS数据采集
        
        Args:
            fotric_ip: Fotric热成像仪IP地址
            vibration_port: 振动传感器串口
            servo_port: 舵机控制器串口
            simulation_mode: 模拟模式
        """
        self.simulation_mode = simulation_mode
        
        # 设备实例
        self.fotric: Optional[FotricEnhancedDevice] = None
        self.vibration_sensor: Optional[VibrationSensor] = None
        self.vibration_optimizer: Optional[VibrationOptimizer] = None
        self.servo: Optional[ServoController] = None
        
        # 设备配置
        self.fotric_ip = fotric_ip
        self.vibration_port = vibration_port
        self.servo_port = servo_port
        
        # 采集状态
        self.is_running = False
        self.acquisition_thread: Optional[threading.Thread] = None
        self.loop = asyncio.new_event_loop()
        
        # 数据存储
        self.current_data = SLSDataPacket(timestamp=time.time())
        self.data_history: deque = deque(maxlen=1000)
        self.thermal_frame_buffer: deque = deque(maxlen=30)
        
        # 回调函数
        self.data_callbacks: List[Callable] = []
        
        # 振动触发阈值
        self.vibration_threshold = 0.1
        self.vibration_algorithm = "composite"
        self.vibration_sensitivity = 3
        
        # 铺粉检测参数
        self.powder_detection_threshold = 0.15
        self.powder_detection_cooldown = 2.0
        self.last_powder_time = 0
        self.powder_flowing = False
        
        # 状态
        self.health_status = 0  # 0=healthy
        self.device_status = {
            'fotric': False,
            'vibration': False,
            'servo': False
        }
        
        print("=" * 60)
        print("SLS数据采集模块初始化")
        print(f"  模拟模式: {simulation_mode}")
        print(f"  Fotric IP: {fotric_ip}")
        print(f"  振动传感器端口: {vibration_port}")
        print(f"  舵机端口: {servo_port}")
        print("=" * 60)
    
    def initialize_devices(self) -> bool:
        """初始化所有设备"""
        success = True
        
        # 初始化Fotric热成像仪
        try:
            if self.simulation_mode:
                self.fotric = MockFotricDevice(self.fotric_ip)
            else:
                self.fotric = FotricEnhancedDevice(self.fotric_ip)
            
            if self.fotric.connect():
                print("✅ Fotric热成像仪连接成功")
                self.device_status['fotric'] = True
            else:
                print("❌ Fotric热成像仪连接失败")
                success = False
        except Exception as e:
            print(f"❌ Fotric初始化错误: {e}")
            success = False
        
        # 初始化振动传感器
        try:
            if self.simulation_mode:
                self.vibration_sensor = MockVibrationSensor(self.vibration_port)
            else:
                self.vibration_sensor = VibrationSensor(self.vibration_port)
            
            if self.vibration_sensor.connect():
                print("✅ 振动传感器连接成功")
                self.device_status['vibration'] = True
                
                # 创建优化器
                self.vibration_optimizer = VibrationOptimizer(self.vibration_sensor)
                self.vibration_optimizer.set_algorithm(self.vibration_algorithm)
                self.vibration_optimizer.set_sensitivity(self.vibration_sensitivity)
                
                # 自动校准
                if self.vibration_optimizer.config.auto_calibrate:
                    self.vibration_optimizer.calibrate(duration=3.0)
            else:
                print("❌ 振动传感器连接失败")
                success = False
        except Exception as e:
            print(f"❌ 振动传感器初始化错误: {e}")
            success = False
        
        # 初始化舵机
        try:
            if self.simulation_mode:
                self.servo = MockServoController(self.servo_port)
            else:
                self.servo = ServoController(self.servo_port)
            
            if self.servo.connect():
                print("✅ 舵机控制器连接成功")
                self.device_status['servo'] = True
            else:
                print("❌ 舵机控制器连接失败")
                success = False
        except Exception as e:
            print(f"❌ 舵机初始化错误: {e}")
            success = False
        
        return success
    
    def start_acquisition(self) -> bool:
        """开始数据采集"""
        if self.is_running:
            print("⚠️ 采集已在运行中")
            return True
        
        if not any(self.device_status.values()):
            print("❌ 没有可用设备，无法启动采集")
            return False
        
        self.is_running = True
        self.acquisition_thread = threading.Thread(
            target=self._acquisition_loop,
            daemon=True
        )
        self.acquisition_thread.start()
        print("✅ SLS数据采集已启动")
        return True
    
    def stop_acquisition(self):
        """停止数据采集"""
        self.is_running = False
        if self.acquisition_thread and self.acquisition_thread.is_alive():
            self.acquisition_thread.join(timeout=2.0)
        print("ℹ️ SLS数据采集已停止")
    
    def _acquisition_loop(self):
        """采集循环"""
        while self.is_running:
            try:
                packet = SLSDataPacket(timestamp=time.time())
                
                # 采集热成像数据
                if self.fotric and self.device_status['fotric']:
                    try:
                        thermal_data = self.fotric.get_thermal_array()
                        if thermal_data is not None:
                            packet.thermal_temp_min = float(np.min(thermal_data))
                            packet.thermal_temp_max = float(np.max(thermal_data))
                            packet.thermal_temp_avg = float(np.mean(thermal_data))
                            
                            # 中心点温度
                            h, w = thermal_data.shape
                            packet.thermal_temp_center = float(thermal_data[h//2, w//2])
                            packet.thermal_image = thermal_data
                            
                            # 生成JPEG
                            jpeg = self.fotric.generate_jpeg(thermal_data)
                            if jpeg:
                                packet.thermal_jpeg = jpeg
                                self.thermal_frame_buffer.append(jpeg)
                    except Exception as e:
                        print(f"⚠️ 热成像采集错误: {e}")
                
                # 采集振动数据
                if self.vibration_sensor and self.device_status['vibration']:
                    try:
                        vib_data = self.vibration_sensor.read_data()
                        if vib_data:
                            packet.vibration_vx = vib_data.vx
                            packet.vibration_vy = vib_data.vy
                            packet.vibration_vz = vib_data.vz
                            packet.vibration_dx = vib_data.dx
                            packet.vibration_dy = vib_data.dy
                            packet.vibration_dz = vib_data.dz
                            packet.vibration_fx = vib_data.fx
                            packet.vibration_fy = vib_data.fy
                            packet.vibration_fz = vib_data.fz
                            packet.vibration_magnitude = vib_data.magnitude
                    except Exception as e:
                        print(f"⚠️ 振动采集错误: {e}")
                
                # 使用优化器检查振动触发
                if self.vibration_optimizer and self.device_status['vibration']:
                    try:
                        triggered, magnitude = self.vibration_optimizer.check_vibration_trigger(
                            self.vibration_threshold
                        )
                        packet.vibration_triggered = triggered
                        packet.vibration_magnitude = magnitude
                    except Exception as e:
                        print(f"⚠️ 振动优化器错误: {e}")
                
                # 获取舵机状态
                if self.servo and self.device_status['servo']:
                    try:
                        packet.servo_angle = self.servo.current_angle
                        packet.servo_is_moving = self.servo.is_moving
                    except Exception as e:
                        print(f"⚠️ 舵机状态错误: {e}")
                
                # 铺粉检测
                packet.powder_flowing = self._detect_powder_flow(packet)
                
                # 更新健康状态
                packet.health_status = self._calculate_health_status(packet)
                
                # 更新当前数据和历史
                self.current_data = packet
                self.data_history.append(packet)
                
                # 触发回调
                for callback in self.data_callbacks:
                    try:
                        callback(packet)
                    except Exception as e:
                        print(f"⚠️ 回调错误: {e}")
                
                time.sleep(0.05)  # 20Hz采集
                
            except Exception as e:
                print(f"❌ 采集循环错误: {e}")
                time.sleep(0.1)
    
    def _detect_powder_flow(self, packet: SLSDataPacket) -> bool:
        """检测铺粉动作"""
        current_time = time.time()
        
        # 基于振动检测
        if packet.vibration_triggered and packet.vibration_magnitude > self.powder_detection_threshold:
            if current_time - self.last_powder_time > self.powder_detection_cooldown:
                self.last_powder_time = current_time
                self.powder_flowing = True
                return True
        
        # 冷却期后重置
        if current_time - self.last_powder_time > self.powder_detection_cooldown:
            self.powder_flowing = False
        
        return self.powder_flowing
    
    def _calculate_health_status(self, packet: SLSDataPacket) -> int:
        """计算健康状态
        
        Returns:
            0: 健康
            1: 铺粉故障
            2: 激光故障
            3: 温度故障
            4: 复合故障
        """
        status = 0
        
        # 检查温度异常
        if packet.thermal_temp_max > 400:  # 温度超过400°C
            status = 3
        
        # 检查振动异常（持续高振动）
        if packet.vibration_magnitude > 0.5:
            if status == 0:
                status = 1  # 铺粉相关
            else:
                status = 4  # 复合故障
        
        self.health_status = status
        return status
    
    def get_current_data(self) -> Dict:
        """获取当前数据"""
        return self.current_data.to_dict()
    
    def get_data_history(self, count: int = 100) -> List[Dict]:
        """获取历史数据"""
        history = list(self.data_history)[-count:]
        return [d.to_dict() for d in history]
    
    def get_thermal_frame(self) -> Optional[bytes]:
        """获取最新热成像帧"""
        if self.current_data.thermal_jpeg:
            return self.current_data.thermal_jpeg
        if self.thermal_frame_buffer:
            return self.thermal_frame_buffer[-1]
        return None
    
    def get_waveform_data(self, limit: int = 100) -> Dict:
        """获取振动波形数据"""
        if self.vibration_sensor:
            return self.vibration_sensor.get_waveform_data(limit)
        return {'x': [], 'y': [], 'z': [], 'sample_count': 0}
    
    def get_vibration_statistics(self) -> Dict:
        """获取振动统计信息"""
        if self.vibration_optimizer:
            return self.vibration_optimizer.get_statistics()
        return {}
    
    def set_vibration_threshold(self, threshold: float):
        """设置振动触发阈值"""
        self.vibration_threshold = threshold
        print(f"✅ 振动阈值设置为: {threshold}")
    
    def set_vibration_algorithm(self, algorithm: str) -> bool:
        """设置振动检测算法"""
        if self.vibration_optimizer:
            result = self.vibration_optimizer.set_algorithm(algorithm)
            if result:
                self.vibration_algorithm = algorithm
            return result
        return False
    
    def set_vibration_sensitivity(self, level: int):
        """设置振动灵敏度"""
        if self.vibration_optimizer:
            self.vibration_optimizer.set_sensitivity(level)
            self.vibration_sensitivity = level
    
    def calibrate_vibration(self, duration: float = 5.0) -> bool:
        """校准振动传感器"""
        if self.vibration_optimizer:
            return self.vibration_optimizer.calibrate(duration)
        return False
    
    def reset_vibration_peak(self):
        """重置振动峰值"""
        if self.vibration_sensor:
            self.vibration_sensor.reset_peak_values()
    
    def add_data_callback(self, callback: Callable):
        """添加数据回调"""
        if callback not in self.data_callbacks:
            self.data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable):
        """移除数据回调"""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    def get_device_status(self) -> Dict:
        """获取设备状态"""
        return {
            'fotric': {
                'connected': self.device_status['fotric'],
                'ip': self.fotric_ip if self.fotric else None
            },
            'vibration': {
                'connected': self.device_status['vibration'],
                'port': self.vibration_port if self.vibration_sensor else None,
                'algorithm': self.vibration_algorithm,
                'threshold': self.vibration_threshold,
                'sensitivity': self.vibration_sensitivity
            },
            'servo': {
                'connected': self.device_status['servo'],
                'port': self.servo_port if self.servo else None
            },
            'health_status': self.health_status
        }
    
    def cleanup(self):
        """清理资源"""
        print("\n正在清理SLS资源...")
        self.stop_acquisition()
        
        if self.fotric:
            self.fotric.disconnect()
        if self.vibration_sensor:
            self.vibration_sensor.disconnect()
        if self.servo:
            self.servo.disconnect()
        
        print("✅ SLS资源清理完成")


# 全局实例
_sls_acquisition: Optional[SLSAcquisition] = None


def get_sls_acquisition(
    fotric_ip: str = "192.168.1.100",
    vibration_port: str = "COM5",
    servo_port: str = "COM6",
    simulation_mode: bool = False,
    force_new: bool = False
) -> SLSAcquisition:
    """获取SLS采集实例（单例模式）"""
    global _sls_acquisition
    
    if _sls_acquisition is None or force_new:
        _sls_acquisition = SLSAcquisition(
            fotric_ip=fotric_ip,
            vibration_port=vibration_port,
            servo_port=servo_port,
            simulation_mode=simulation_mode
        )
    
    return _sls_acquisition


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("SLS数据采集测试")
    print("=" * 60)
    
    # 创建采集实例（模拟模式）
    acquisition = SLSAcquisition(simulation_mode=True)
    
    # 初始化设备
    if acquisition.initialize_devices():
        print("\n✅ 设备初始化成功")
        
        # 添加数据回调
        def on_data(packet: SLSDataPacket):
            print(f"\r数据: T={packet.thermal_temp_avg:.1f}°C, "
                  f"V=({packet.vibration_vx:.3f}, {packet.vibration_vy:.3f}, {packet.vibration_vz:.3f}), "
                  f"M={packet.vibration_magnitude:.3f}, "
                  f"Servo={packet.servo_angle}°", end='', flush=True)
        
        acquisition.add_data_callback(on_data)
        
        # 开始采集
        if acquisition.start_acquisition():
            print("\n\n采集运行中，按Ctrl+C停止...")
            try:
                time.sleep(10)
            except KeyboardInterrupt:
                print("\n\n停止采集...")
        
        # 显示统计
        stats = acquisition.get_vibration_statistics()
        print(f"\n振动统计: {stats}")
    else:
        print("\n❌ 设备初始化失败")
    
    acquisition.cleanup()
