"""
振动传感器驱动 (WTVB02-485)
用于SLS系统的刮刀运动检测
"""

import serial
import threading
import time
import logging
from typing import Optional, Callable, Dict
from dataclasses import dataclass


@dataclass
class VibrationData:
    """振动数据结构"""
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    velocity_z: float = 0.0
    displacement_x: float = 0.0
    displacement_y: float = 0.0
    displacement_z: float = 0.0
    frequency_x: float = 0.0
    frequency_y: float = 0.0
    frequency_z: float = 0.0
    temperature: float = 0.0
    timestamp: float = 0.0


class VibrationSensor:
    """
    WTVB02-485 振动传感器驱动
    
    功能：
    1. 串口通信读取振动数据
    2. 计算综合振动强度
    3. 检测振动触发
    """
    
    def __init__(self, port: str = "COM3", baudrate: int = 9600, address: int = 1):
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        
        # 当前数据
        self.current_data = VibrationData()
        self._data_lock = threading.Lock()
        
        # 综合振动强度
        self.vibration_magnitude = 0.0
        
        # 读取线程
        self._read_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 回调函数列表
        self._callbacks: list[Callable] = []
        
        # 模拟模式（用于调试）
        self.simulation_mode = False
        self._simulation_thread: Optional[threading.Thread] = None
        
        logging.info(f"[VibrationSensor] 初始化 (端口: {port}, 波特率: {baudrate})")
    
    def connect(self) -> bool:
        """连接振动传感器"""
        try:
            # 尝试打开串口
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1.0
            )
            
            # 串口打开成功
            self.connected = True
            self._running = True
            self.simulation_mode = False
            
            # 启动真实读取线程
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()
            
            logging.info(f"[VibrationSensor] 连接成功: {self.port}")
            return True
            
        except Exception as e:
            logging.warning(f"[VibrationSensor] 串口连接失败: {e}")
            # 启用模拟模式
            self.simulation_mode = True
            self.connected = True  # 模拟模式下也算连接
            self._running = True
            
            # 启动模拟线程（而不是真实读取线程）
            self._start_simulation()
            
            logging.info("[VibrationSensor] 已切换到模拟模式")
            return True
    
    def disconnect(self):
        """断开连接"""
        self._running = False
        
        # 等待真实读取线程结束
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=2.0)
        
        # 等待模拟线程结束
        if self._simulation_thread and self._simulation_thread.is_alive():
            self._simulation_thread.join(timeout=2.0)
        
        # 关闭串口
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except Exception as e:
                logging.debug(f"[VibrationSensor] 关闭串口异常: {e}")
        
        self.connected = False
        logging.info("[VibrationSensor] 已断开")
    
    def _read_loop(self):
        """数据读取循环"""
        # 模拟模式下不执行真实读取
        if self.simulation_mode:
            logging.info("[VibrationSensor] 模拟模式，跳过真实读取循环")
            return
            
        while self._running:
            try:
                if self.serial and self.serial.is_open:
                    try:
                        # 读取寄存器数据 (简化版Modbus RTU)
                        data = self._read_registers(0x3A, 10)
                        if data:
                            self._parse_data(data)
                    except Exception as e:
                        logging.debug(f"[VibrationSensor] 读取异常: {e}")
                
                time.sleep(0.05)  # 20Hz读取频率
                
            except Exception as e:
                logging.error(f"[VibrationSensor] 读取循环错误: {e}")
                time.sleep(0.1)
    
    def _read_registers(self, start_addr: int, count: int) -> Optional[bytes]:
        """读取Modbus寄存器 (简化实现)"""
        if not self.serial:
            return None
        
        # 构建Modbus RTU请求帧
        # [地址] [功能码03] [起始地址高] [起始地址低] [寄存器数高] [寄存器数低] [CRC低] [CRC高]
        request = bytes([
            self.address,
            0x03,
            (start_addr >> 8) & 0xFF,
            start_addr & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF
        ])
        
        # 计算CRC16 (简化，实际需要完整CRC计算)
        crc = self._calculate_crc(request)
        request += bytes([crc & 0xFF, (crc >> 8) & 0xFF])
        
        self.serial.write(request)
        response = self.serial.read(5 + count * 2)  # 响应长度
        
        return response if len(response) >= 5 else None
    
    def _calculate_crc(self, data: bytes) -> int:
        """计算Modbus CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def _parse_data(self, response: bytes):
        """解析传感器数据"""
        if len(response) < 5:
            return
        
        try:
            data_len = response[2]
            data_bytes = response[3:3+data_len]
            
            with self._data_lock:
                # 解析各个寄存器 (根据WTVB02-485协议)
                # 0x3A-0x3C: 速度X/Y/Z
                self.current_data.velocity_x = self._parse_register(data_bytes, 0)
                self.current_data.velocity_y = self._parse_register(data_bytes, 2)
                self.current_data.velocity_z = self._parse_register(data_bytes, 4)
                
                # 0x3D-0x3F: 位移X/Y/Z
                self.current_data.displacement_x = self._parse_register(data_bytes, 6)
                self.current_data.displacement_y = self._parse_register(data_bytes, 8)
                self.current_data.displacement_z = self._parse_register(data_bytes, 10)
                
                # 0x40-0x42: 频率X/Y/Z
                self.current_data.frequency_x = self._parse_register(data_bytes, 12)
                self.current_data.frequency_y = self._parse_register(data_bytes, 14)
                self.current_data.frequency_z = self._parse_register(data_bytes, 16)
                
                # 0x43: 温度
                self.current_data.temperature = self._parse_register(data_bytes, 18) / 100.0
                
                self.current_data.timestamp = time.time()
            
            # 计算综合振动强度
            self._calculate_magnitude()
            
            # 通知回调
            self._notify_callbacks()
            
        except Exception as e:
            logging.error(f"[VibrationSensor] 数据解析错误: {e}")
    
    def _parse_register(self, data: bytes, offset: int) -> float:
        """解析单个寄存器值"""
        if offset + 2 > len(data):
            return 0.0
        value = (data[offset] << 8) | data[offset + 1]
        # 处理有符号数
        if value > 32767:
            value -= 65536
        return float(value)
    
    def _calculate_magnitude(self):
        """计算综合振动强度"""
        with self._data_lock:
            # 使用速度分量的RMS作为综合强度
            vx = self.current_data.velocity_x
            vy = self.current_data.velocity_y
            vz = self.current_data.velocity_z
            
            # 归一化并计算综合强度
            self.vibration_magnitude = (vx**2 + vy**2 + vz**2) ** 0.5 / 1000.0
    
    def get_current_data(self) -> VibrationData:
        """获取当前振动数据"""
        with self._data_lock:
            return VibrationData(
                velocity_x=self.current_data.velocity_x,
                velocity_y=self.current_data.velocity_y,
                velocity_z=self.current_data.velocity_z,
                displacement_x=self.current_data.displacement_x,
                displacement_y=self.current_data.displacement_y,
                displacement_z=self.current_data.displacement_z,
                frequency_x=self.current_data.frequency_x,
                frequency_y=self.current_data.frequency_y,
                frequency_z=self.current_data.frequency_z,
                temperature=self.current_data.temperature,
                timestamp=self.current_data.timestamp
            )
    
    def check_vibration_trigger(self, threshold: float = 0.05) -> tuple[bool, float]:
        """
        检查是否触发振动
        
        Returns:
            (是否触发, 振动强度)
        """
        magnitude = self.vibration_magnitude
        is_triggered = magnitude > threshold
        return is_triggered, magnitude
    
    def add_callback(self, callback: Callable):
        """添加数据更新回调"""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self):
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                callback(self.current_data)
            except Exception as e:
                logging.error(f"[VibrationSensor] 回调错误: {e}")
    
    def _start_simulation(self):
        """启动模拟数据生成"""
        self._simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._simulation_thread.start()
    
    def _simulation_loop(self):
        """模拟数据生成循环"""
        import math
        t = 0
        while self._running:
            # 生成模拟振动数据
            with self._data_lock:
                self.current_data.velocity_x = abs(math.sin(t) * 100)
                self.current_data.velocity_y = abs(math.cos(t) * 80)
                self.current_data.velocity_z = abs(math.sin(t * 0.5) * 50)
                self.current_data.temperature = 25.0 + math.sin(t * 0.1) * 5
                self.current_data.timestamp = time.time()
            
            self._calculate_magnitude()
            self._notify_callbacks()
            
            t += 0.1
            time.sleep(0.05)  # 20Hz
