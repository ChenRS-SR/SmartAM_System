"""
振动传感器模块 (WTVB02-485)
============================
支持COM口连接，提供振动速度、角度、位移、频率、温度等数据采集
"""

import time
import json
import threading
import numpy as np
from datetime import datetime
from typing import Optional, Dict, List, Callable, Tuple
from dataclasses import dataclass, field


@dataclass
class VibrationData:
    """振动数据结构"""
    timestamp: float
    # 速度 (mm/s)
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    # 角度 (°)
    ax: float = 0.0
    ay: float = 0.0
    az: float = 0.0
    # 温度 (°C)
    temperature: float = 0.0
    # 位移 (μm)
    sx: float = 0.0
    sy: float = 0.0
    sz: float = 0.0
    # 频率 (Hz)
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    # 加速度 (m/s²) - 部分设备支持
    acx: float = 0.0
    acy: float = 0.0
    acz: float = 0.0
    # 综合振动强度
    magnitude: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'vx': self.vx, 'vy': self.vy, 'vz': self.vz,
            'ax': self.ax, 'ay': self.ay, 'az': self.az,
            'temperature': self.temperature,
            'sx': self.sx, 'sy': self.sy, 'sz': self.sz,
            'fx': self.fx, 'fy': self.fy, 'fz': self.fz,
            'acx': self.acx, 'acy': self.acy, 'acz': self.acz,
            'magnitude': self.magnitude
        }


class VibrationSensor:
    """WTVB02-485 振动传感器驱动"""
    
    # 寄存器地址映射
    REGISTERS = {
        'vx': 58,    # 0x3A 振动速度x
        'vy': 59,    # 0x3B 振动速度y
        'vz': 60,    # 0x3C 振动速度z
        'ax': 61,    # 0x3D 振动角度x
        'ay': 62,    # 0x3E 振动角度y
        'az': 63,    # 0x3F 振动角度z
        'temperature': 64,  # 0x40 温度
        'sx': 65,    # 0x41 振动位移x
        'sy': 66,    # 0x42 振动位移y
        'sz': 67,    # 0x43 振动位移z
        'fx': 68,    # 0x44 振动频率x
        'fy': 69,    # 0x45 振动频率y
        'fz': 70,    # 0x46 振动频率z
    }
    
    def __init__(self, com_port: str = "COM5", baudrate: int = 9600, 
                 address: int = 0x50, timeout: float = 1.0):
        self.com_port = com_port
        self.baudrate = baudrate
        self.address = address
        self.timeout = timeout
        
        self.device = None
        self.is_connected = False
        self.last_error = ""
        
        # 数据采集线程
        self._采集线程 = None
        self._停止标志 = threading.Event()
        self._数据队列: List[VibrationData] = []
        self._队列锁 = threading.Lock()
        self._最大队列长度 = 1000
        
        # 回调函数
        self._回调列表: List[Callable[[VibrationData], None]] = []
        
        # 历史数据用于统计
        self._历史数据: List[VibrationData] = []
        self._历史数据锁 = threading.Lock()
        self._最大历史长度 = 5000
        
    def connect(self) -> bool:
        """连接振动传感器"""
        try:
            # 尝试导入设备模型
            try:
                import sys
                sys.path.insert(0, r'D:\FDM_Monitor_Diagnosis\SLM数据采集')
                import device_model
            except ImportError:
                self.last_error = "无法导入device_model模块"
                print(f"[VibrationSensor] {self.last_error}")
                return False
            
            # 创建设备实例
            self.device = device_model.DeviceModel(
                deviceName="WTVB02-485",
                port=self.com_port,
                baudrate=self.baudrate,
                address=self.address
            )
            
            # 打开设备
            if self.device.openDevice():
                self.device.startLoopRead()
                self.is_connected = True
                self.last_error = ""
                print(f"[VibrationSensor] 成功连接到 {self.com_port}")
                return True
            else:
                self.last_error = f"无法打开设备 {self.com_port}"
                print(f"[VibrationSensor] {self.last_error}")
                return False
                
        except Exception as e:
            self.last_error = f"连接失败: {str(e)}"
            print(f"[VibrationSensor] {self.last_error}")
            return False
    
    def disconnect(self):
        """断开传感器连接"""
        self._停止标志.set()
        
        if self._采集线程 and self._采集线程.is_alive():
            self._采集线程.join(timeout=2.0)
        
        if self.device:
            try:
                self.device.stopLoopRead()
                self.device.closeDevice()
            except:
                pass
            self.device = None
        
        self.is_connected = False
        print("[VibrationSensor] 已断开连接")
    
    def read_data(self) -> Optional[VibrationData]:
        """读取一次传感器数据"""
        if not self.is_connected or not self.device:
            return None
        
        try:
            data = VibrationData(timestamp=time.time())
            
            # 读取速度数据
            data.vx = self._safe_read('vx', 0.0)
            data.vy = self._safe_read('vy', 0.0)
            data.vz = self._safe_read('vz', 0.0)
            
            # 读取角度数据
            data.ax = self._safe_read('ax', 0.0)
            data.ay = self._safe_read('ay', 0.0)
            data.az = self._safe_read('az', 0.0)
            
            # 读取温度
            data.temperature = self._safe_read('temperature', 0.0)
            
            # 读取位移数据
            data.sx = self._safe_read('sx', 0.0)
            data.sy = self._safe_read('sy', 0.0)
            data.sz = self._safe_read('sz', 0.0)
            
            # 读取频率数据
            data.fx = self._safe_read('fx', 0.0)
            data.fy = self._safe_read('fy', 0.0)
            data.fz = self._safe_read('fz', 0.0)
            
            # 计算综合振动强度 (使用速度数据)
            data.magnitude = np.sqrt(data.vx**2 + data.vy**2 + data.vz**2) / np.sqrt(3)
            
            return data
            
        except Exception as e:
            self.last_error = f"读取数据失败: {str(e)}"
            return None
    
    def _safe_read(self, key: str, default: float) -> float:
        """安全读取寄存器数据"""
        try:
            if key in self.REGISTERS:
                reg = self.REGISTERS[key]
                value = self.device.get(str(reg))
                return float(value) if value is not None else default
            return default
        except:
            return default
    
    def start_continuous_read(self, interval: float = 0.05):
        """开始连续数据采集"""
        if self._采集线程 and self._采集线程.is_alive():
            return
        
        self._停止标志.clear()
        self._采集线程 = threading.Thread(target=self._采集循环, args=(interval,))
        self._采集线程.daemon = True
        self._采集线程.start()
        print(f"[VibrationSensor] 开始连续采集，间隔 {interval}s")
    
    def _采集循环(self, interval: float):
        """数据采集循环"""
        while not self._停止标志.is_set():
            data = self.read_data()
            if data:
                # 添加到队列
                with self._队列锁:
                    self._数据队列.append(data)
                    if len(self._数据队列) > self._最大队列长度:
                        self._数据队列.pop(0)
                
                # 添加到历史数据
                with self._历史数据锁:
                    self._历史数据.append(data)
                    if len(self._历史数据) > self._最大历史长度:
                        self._历史数据.pop(0)
                
                # 触发回调
                for callback in self._回调列表:
                    try:
                        callback(data)
                    except Exception as e:
                        print(f"[VibrationSensor] 回调错误: {e}")
            
            self._停止标志.wait(interval)
    
    def get_latest_data(self) -> Optional[VibrationData]:
        """获取最新数据"""
        with self._队列锁:
            if self._数据队列:
                return self._数据队列[-1]
            return None
    
    def get_data_batch(self, count: int = 100) -> List[VibrationData]:
        """获取一批数据"""
        with self._队列锁:
            return self._数据队列[-count:].copy()
    
    def get_history_data(self, duration: float = 10.0) -> List[VibrationData]:
        """获取指定时间范围内的历史数据"""
        current_time = time.time()
        with self._历史数据锁:
            return [d for d in self._历史数据 if current_time - d.timestamp <= duration]
    
    def register_callback(self, callback: Callable[[VibrationData], None]):
        """注册数据回调"""
        if callback not in self._回调列表:
            self._回调列表.append(callback)
    
    def unregister_callback(self, callback: Callable[[VibrationData], None]):
        """取消注册回调"""
        if callback in self._回调列表:
            self._回调列表.remove(callback)
    
    def calculate_statistics(self, duration: float = 5.0) -> Dict:
        """计算指定时间内的统计信息"""
        data = self.get_history_data(duration)
        if not data:
            return {}
        
        stats = {}
        fields = ['vx', 'vy', 'vz', 'ax', 'ay', 'az', 'temperature', 
                  'sx', 'sy', 'sz', 'fx', 'fy', 'fz', 'magnitude']
        
        for field in fields:
            values = [getattr(d, field) for d in data]
            arr = np.array(values)
            stats[field] = {
                'mean': float(np.mean(arr)),
                'std': float(np.std(arr)),
                'max': float(np.max(arr)),
                'min': float(np.min(arr)),
                'rms': float(np.sqrt(np.mean(arr**2)))
            }
        
        return stats


class MockVibrationSensor:
    """模拟振动传感器（用于调试）"""
    
    def __init__(self, com_port: str = "COM5", baudrate: int = 9600, 
                 address: int = 0x50, timeout: float = 1.0):
        self.com_port = com_port
        self.baudrate = baudrate
        self.address = address
        self.timeout = timeout
        self.is_connected = False
        self.last_error = ""
        
        self._采集线程 = None
        self._停止标志 = threading.Event()
        self._数据队列: List[VibrationData] = []
        self._队列锁 = threading.Lock()
        self._回调列表: List[Callable[[VibrationData], None]] = []
        self._历史数据: List[VibrationData] = []
        self._历史数据锁 = threading.Lock()
        self._最大历史长度 = 5000
        
        # 模拟参数
        self._基线振动 = 0.02  # 基线振动幅度
        self._峰值振动 = 0.15  # 峰值振动幅度
        self._触发频率 = 0.1  # 触发频率 (10秒一次)
        self._触发持续时间 = 3.0  # 触发持续时间
        
    def connect(self) -> bool:
        """模拟连接"""
        self.is_connected = True
        self.last_error = ""
        print(f"[MockVibrationSensor] 模拟连接成功 {self.com_port}")
        return True
    
    def disconnect(self):
        """断开连接"""
        self._停止标志.set()
        if self._采集线程 and self._采集线程.is_alive():
            self._采集线程.join(timeout=2.0)
        self.is_connected = False
        print("[MockVibrationSensor] 已断开连接")
    
    def read_data(self) -> VibrationData:
        """生成模拟数据"""
        t = time.time()
        
        # 模拟周期性的振动触发（模拟扑粉动作）
        cycle = (t % 10) / 10  # 10秒一个周期
        
        if 0.2 < cycle < 0.5:  # 第一次振动
            intensity = self._峰值振动 * np.sin((cycle - 0.2) / 0.3 * np.pi)
        elif 0.6 < cycle < 0.9:  # 第二次振动
            intensity = self._峰值振动 * 0.7 * np.sin((cycle - 0.6) / 0.3 * np.pi)
        else:
            intensity = self._基线振动
        
        # 添加噪声
        noise = np.random.normal(0, 0.005, 3)
        
        data = VibrationData(
            timestamp=t,
            vx=intensity * 0.8 + noise[0],
            vy=intensity * 0.6 + noise[1],
            vz=intensity * 0.9 + noise[2],
            ax=intensity * 2 + np.random.normal(0, 0.5),
            ay=intensity * 1.5 + np.random.normal(0, 0.5),
            az=intensity * 2.5 + np.random.normal(0, 0.5),
            temperature=25.0 + np.random.normal(0, 1.0),
            sx=intensity * 10 + np.random.normal(0, 1),
            sy=intensity * 8 + np.random.normal(0, 1),
            sz=intensity * 12 + np.random.normal(0, 1),
            fx=50 + intensity * 100 + np.random.normal(0, 5),
            fy=50 + intensity * 80 + np.random.normal(0, 5),
            fz=50 + intensity * 120 + np.random.normal(0, 5),
            magnitude=intensity
        )
        
        return data
    
    def start_continuous_read(self, interval: float = 0.05):
        """开始连续数据采集"""
        if self._采集线程 and self._采集线程.is_alive():
            return
        
        self._停止标志.clear()
        self._采集线程 = threading.Thread(target=self._采集循环, args=(interval,))
        self._采集线程.daemon = True
        self._采集线程.start()
    
    def _采集循环(self, interval: float):
        """数据采集循环"""
        while not self._停止标志.is_set():
            data = self.read_data()
            
            with self._队列锁:
                self._数据队列.append(data)
                if len(self._数据队列) > 1000:
                    self._数据队列.pop(0)
            
            with self._历史数据锁:
                self._历史数据.append(data)
                if len(self._历史数据) > self._最大历史长度:
                    self._历史数据.pop(0)
            
            for callback in self._回调列表:
                try:
                    callback(data)
                except:
                    pass
            
            self._停止标志.wait(interval)
    
    def get_latest_data(self) -> Optional[VibrationData]:
        """获取最新数据"""
        with self._队列锁:
            if self._数据队列:
                return self._数据队列[-1]
            return None
    
    def get_data_batch(self, count: int = 100) -> List[VibrationData]:
        """获取一批数据"""
        with self._队列锁:
            return self._数据队列[-count:].copy()
    
    def get_history_data(self, duration: float = 10.0) -> List[VibrationData]:
        """获取历史数据"""
        current_time = time.time()
        with self._历史数据锁:
            return [d for d in self._历史数据 if current_time - d.timestamp <= duration]
    
    def register_callback(self, callback: Callable[[VibrationData], None]):
        """注册回调"""
        if callback not in self._回调列表:
            self._回调列表.append(callback)
    
    def unregister_callback(self, callback: Callable[[VibrationData], None]):
        """取消注册回调"""
        if callback in self._回调列表:
            self._回调列表.remove(callback)
    
    def calculate_statistics(self, duration: float = 5.0) -> Dict:
        """计算统计信息"""
        data = self.get_history_data(duration)
        if not data:
            return {}
        
        stats = {}
        fields = ['vx', 'vy', 'vz', 'ax', 'ay', 'az', 'temperature',
                  'sx', 'sy', 'sz', 'fx', 'fy', 'fz', 'magnitude']
        
        for field in fields:
            values = [getattr(d, field) for d in data]
            arr = np.array(values)
            stats[field] = {
                'mean': float(np.mean(arr)),
                'std': float(np.std(arr)),
                'max': float(np.max(arr)),
                'min': float(np.min(arr)),
                'rms': float(np.sqrt(np.mean(arr**2)))
            }
        
        return stats
