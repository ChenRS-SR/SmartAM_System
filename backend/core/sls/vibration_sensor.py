"""
SLS振动传感器模块（基于SLS项目实现）
====================================
WTVB02-485振动传感器控制模块
基于Modbus RTU协议
支持三轴振动速度/位移/频率读取
"""

import time
import threading
import random
import math
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from .device_model import DeviceModel


@dataclass
class VibrationData:
    """振动数据结构"""
    vx: float  # X轴振动速度 (mm/s)
    vy: float  # Y轴振动速度 (mm/s)
    vz: float  # Z轴振动速度 (mm/s)
    dx: float  # X轴振动位移 (μm)
    dy: float  # Y轴振动位移 (μm)
    dz: float  # Z轴振动位移 (μm)
    fx: float  # X轴振动频率 (Hz)
    fy: float  # Y轴振动频率 (Hz)
    fz: float  # Z轴振动频率 (Hz)
    temperature: float  # 温度 (°C)
    magnitude: float  # 综合振动幅度
    timestamp: float


class VibrationSensor(DeviceModel):
    """振动传感器控制类（基于SLS项目）"""
    
    # Modbus寄存器地址
    REG_VELOCITY_X = 0x3A  # 58 - 振动速度X
    REG_VELOCITY_Y = 0x3B  # 59 - 振动速度Y
    REG_VELOCITY_Z = 0x3C  # 60 - 振动速度Z
    REG_DISPLACEMENT_X = 0x3D  # 61 - 振动位移X
    REG_DISPLACEMENT_Y = 0x3E  # 62 - 振动位移Y
    REG_DISPLACEMENT_Z = 0x3F  # 63 - 振动位移Z
    REG_FREQUENCY_X = 0x40  # 64 - 振动频率X
    REG_FREQUENCY_Y = 0x41  # 65 - 振动频率Y
    REG_FREQUENCY_Z = 0x42  # 66 - 振动频率Z
    REG_TEMPERATURE = 0x43  # 67 - 温度
    
    def __init__(self, com_port: str = "COM5", baudrate: int = 9600, slave_id: int = 0x50):
        """
        初始化振动传感器
        
        Args:
            com_port: 串口号
            baudrate: 波特率
            slave_id: Modbus从机地址
        """
        super().__init__(
            deviceName="WTVB02-485",
            portName=com_port,
            baud=baudrate,
            ADDR=slave_id
        )
        
        self.lock = threading.Lock()
        
        # 当前数据
        self.current_data = {
            'velocity_x': 0.0,
            'velocity_y': 0.0,
            'velocity_z': 0.0,
            'displacement_x': 0.0,
            'displacement_y': 0.0,
            'displacement_z': 0.0,
            'frequency_x': 0.0,
            'frequency_y': 0.0,
            'frequency_z': 0.0,
            'temperature': 0.0
        }
        
        # 峰值数据
        self.peak_data = {
            'velocity_x': 0.0,
            'velocity_y': 0.0,
            'velocity_z': 0.0
        }
        
        # 振动触发检测
        self.last_trigger_time = 0
        self.vibration_magnitude = 0.0
        self.detection_threshold = 0.1  # 默认阈值
        
        # 波形数据缓存
        self.waveform_buffer = {
            'x': [],
            'y': [],
            'z': []
        }
        self.max_buffer_size = 500
        
        # 最近峰值重置时间
        self.last_peak_reset_time = 0
        
        print(f"ℹ️ 初始化振动传感器 (端口: {self.serialConfig.portName}, 波特率: {self.serialConfig.baud})")
    
    def process_data(self, length):
        """重写数据解析方法"""
        if self.statReg is not None:
            for i in range(int(length / 2)):
                if 2 * i + 4 >= len(self.TempBytes):
                    break
                
                value = (self.TempBytes[2 * i + 3] << 8) | self.TempBytes[2 * i + 4]
                value = float(value)
                
                reg_addr = self.statReg + i
                
                with self.lock:
                    if reg_addr in [0x3A, 0x3B, 0x3C]:  # 速度数据
                        axis = ['x', 'y', 'z'][reg_addr - 0x3A]
                        self.current_data[f'velocity_{axis}'] = abs(value) / 100.0  # 转换为实际值
                        self.peak_data[f'velocity_{axis}'] = max(
                            self.peak_data[f'velocity_{axis}'],
                            self.current_data[f'velocity_{axis}']
                        )
                    elif reg_addr in [0x3D, 0x3E, 0x3F]:  # 位移数据
                        axis = ['x', 'y', 'z'][reg_addr - 0x3D]
                        self.current_data[f'displacement_{axis}'] = abs(value) / 100.0
                    elif reg_addr in [0x40, 0x41, 0x42]:  # 频率数据
                        axis = ['x', 'y', 'z'][reg_addr - 0x40]
                        self.current_data[f'frequency_{axis}'] = abs(value) / 100.0
                    elif reg_addr == 0x43:  # 温度数据
                        self.current_data['temperature'] = value / 100.0
                
                self.set(str(self.statReg), value)
                self.statReg += 1
            
            self.TempBytes.clear()
    
    def connect(self) -> bool:
        """连接设备"""
        try:
            if not self.isOpen:
                result = self.openDevice()
                if result and self.isOpen:
                    print(f"✅ 成功连接到振动传感器 {self.serialConfig.portName}")
                    return True
                else:
                    print(f"❌ 无法连接到振动传感器 {self.serialConfig.portName}")
                    return False
            return self.isOpen
        except Exception as e:
            print(f"❌ 振动传感器连接异常: {str(e)}")
            self.isOpen = False
            return False
    
    def disconnect(self):
        """断开连接"""
        self.stop_monitoring()
        if self.isOpen:
            self.closeDevice()
            print("ℹ️ 已断开与振动传感器的连接")
    
    def start_monitoring(self) -> bool:
        """开始监测振动数据"""
        if self.connect():
            self.startLoopRead()
            print("✅ 开始振动监测")
            return True
        return False
    
    def stop_monitoring(self):
        """停止监测振动数据"""
        try:
            if self.loop:
                self.stopLoopRead()
                time.sleep(0.2)
                print("ℹ️ 停止振动监测")
        except Exception as e:
            print(f"⚠️ 停止监测时出现警告: {str(e)}")
    
    def read_data(self) -> Optional[VibrationData]:
        """读取振动数据"""
        if not self.isOpen:
            return None
        
        with self.lock:
            vx = self.current_data['velocity_x']
            vy = self.current_data['velocity_y']
            vz = self.current_data['velocity_z']
            dx = self.current_data['displacement_x']
            dy = self.current_data['displacement_y']
            dz = self.current_data['displacement_z']
            fx = self.current_data['frequency_x']
            fy = self.current_data['frequency_y']
            fz = self.current_data['frequency_z']
            temp = self.current_data['temperature']
        
        magnitude = math.sqrt(vx**2 + vy**2 + vz**2)
        
        data = VibrationData(
            vx=vx, vy=vy, vz=vz,
            dx=dx, dy=dy, dz=dz,
            fx=fx, fy=fy, fz=fz,
            temperature=temp,
            magnitude=magnitude,
            timestamp=time.time()
        )
        
        # 更新波形缓冲区
        self.waveform_buffer['x'].append(vx)
        self.waveform_buffer['y'].append(vy)
        self.waveform_buffer['z'].append(vz)
        
        for key in self.waveform_buffer:
            if len(self.waveform_buffer[key]) > self.max_buffer_size:
                self.waveform_buffer[key] = self.waveform_buffer[key][-self.max_buffer_size:]
        
        return data
    
    def get_velocity_data(self) -> Tuple[float, float, float]:
        """获取振动速度数据"""
        return (
            self.current_data['velocity_x'],
            self.current_data['velocity_y'],
            self.current_data['velocity_z']
        )
    
    def get_peak_velocity(self) -> Tuple[float, float, float]:
        """获取峰值振动速度"""
        return (
            self.peak_data['velocity_x'],
            self.peak_data['velocity_y'],
            self.peak_data['velocity_z']
        )
    
    def reset_peak_values(self):
        """重置峰值数据"""
        with self.lock:
            for key in self.peak_data:
                self.peak_data[key] = 0.0
            self.last_peak_reset_time = time.time()
            print(f"✅ 振动峰值已重置")
    
    def check_vibration_trigger(self, threshold: float = None) -> Tuple[bool, float]:
        """检查振动信号是否超过阈值"""
        if threshold is None:
            threshold = self.detection_threshold
        
        try:
            data = self.read_data()
            if data is None:
                return False, 0.0
            
            self.vibration_magnitude = data.magnitude
            
            # 更新峰值
            current_time = time.time()
            if current_time - self.last_peak_reset_time >= 10.0:
                self.peak_data['velocity_x'] = max(self.peak_data['velocity_x'], data.vx)
                self.peak_data['velocity_y'] = max(self.peak_data['velocity_y'], data.vy)
                self.peak_data['velocity_z'] = max(self.peak_data['velocity_z'], data.vz)
            
            triggered = self.vibration_magnitude > threshold
            return triggered, self.vibration_magnitude
            
        except Exception as e:
            print(f"❌ 振动触发检查失败: {e}")
            return False, 0.0
    
    def get_waveform_data(self, limit: int = 100) -> Dict:
        """获取波形数据"""
        return {
            'x': self.waveform_buffer['x'][-limit:] if len(self.waveform_buffer['x']) > limit else self.waveform_buffer['x'],
            'y': self.waveform_buffer['y'][-limit:] if len(self.waveform_buffer['y']) > limit else self.waveform_buffer['y'],
            'z': self.waveform_buffer['z'][-limit:] if len(self.waveform_buffer['z']) > limit else self.waveform_buffer['z'],
            'sample_count': len(self.waveform_buffer['x'])
        }
    
    def get_status(self) -> Dict:
        """获取传感器状态"""
        return {
            'com_port': self.serialConfig.portName,
            'baudrate': self.serialConfig.baud,
            'is_connected': self.isOpen,
            'current_data': self.current_data.copy(),
            'peak_data': self.peak_data.copy(),
            'vibration_magnitude': self.vibration_magnitude
        }


class MockVibrationSensor(VibrationSensor):
    """模拟振动传感器（用于测试）"""
    
    def __init__(self, com_port: str = "COM5", baudrate: int = 9600, slave_id: int = 0x50):
        super().__init__(com_port, baudrate, slave_id)
        self._simulation_active = False
        self._base_vibration = 0.05
    
    def connect(self) -> bool:
        """模拟连接"""
        print(f"[MockVibration] 模拟连接到 {self.serialConfig.portName}")
        self.isOpen = True
        return True
    
    def disconnect(self):
        """模拟断开"""
        print("[MockVibration] 模拟断开")
        self.isOpen = False
    
    def read_data(self) -> Optional[VibrationData]:
        """生成模拟数据"""
        import random
        
        # 生成随机振动数据
        vx = self._base_vibration + random.gauss(0, 0.02)
        vy = self._base_vibration + random.gauss(0, 0.02)
        vz = self._base_vibration + random.gauss(0, 0.02)
        
        dx = vx * 10 + random.gauss(0, 0.5)
        dy = vy * 10 + random.gauss(0, 0.5)
        dz = vz * 10 + random.gauss(0, 0.5)
        
        fx = 50 + random.gauss(0, 5)
        fy = 50 + random.gauss(0, 5)
        fz = 50 + random.gauss(0, 5)
        
        magnitude = math.sqrt(vx**2 + vy**2 + vz**2)
        
        data = VibrationData(
            vx=max(0, vx),
            vy=max(0, vy),
            vz=max(0, vz),
            dx=max(0, dx),
            dy=max(0, dy),
            dz=max(0, dz),
            fx=max(0, fx),
            fy=max(0, fy),
            fz=max(0, fz),
            temperature=25.0 + random.gauss(0, 1),
            magnitude=magnitude,
            timestamp=time.time()
        )
        
        # 更新当前数据
        with self.lock:
            self.current_data['velocity_x'] = data.vx
            self.current_data['velocity_y'] = data.vy
            self.current_data['velocity_z'] = data.vz
            self.current_data['displacement_x'] = data.dx
            self.current_data['displacement_y'] = data.dy
            self.current_data['displacement_z'] = data.dz
            self.current_data['frequency_x'] = data.fx
            self.current_data['frequency_y'] = data.fy
            self.current_data['frequency_z'] = data.fz
            self.current_data['temperature'] = data.temperature
        
        # 更新波形缓冲区
        self.waveform_buffer['x'].append(vx)
        self.waveform_buffer['y'].append(vy)
        self.waveform_buffer['z'].append(vz)
        
        for key in self.waveform_buffer:
            if len(self.waveform_buffer[key]) > self.max_buffer_size:
                self.waveform_buffer[key] = self.waveform_buffer[key][-self.max_buffer_size:]
        
        return data
    
    def start_monitoring(self) -> bool:
        """模拟开始监测"""
        print("[MockVibration] 模拟开始监测")
        self.isOpen = True
        return True
    
    def stop_monitoring(self):
        """模拟停止监测"""
        print("[MockVibration] 模拟停止监测")


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("振动传感器测试")
    print("=" * 60)
    
    # 使用模拟传感器测试
    sensor = MockVibrationSensor()
    
    if sensor.connect():
        print("\n读取10次数据:")
        for i in range(10):
            data = sensor.read_data()
            if data:
                print(f"  读取 {i+1}: X={data.vx:.4f}, Y={data.vy:.4f}, Z={data.vz:.4f}, "
                      f"幅度={data.magnitude:.4f}")
            time.sleep(0.1)
        
        print(f"\n波形数据点数: {sensor.get_waveform_data()['sample_count']}")
        
        # 测试触发检测
        triggered, magnitude = sensor.check_vibration_trigger(threshold=0.1)
        print(f"\n振动触发检测: 触发={triggered}, 幅度={magnitude:.4f}")
        
        sensor.disconnect()
