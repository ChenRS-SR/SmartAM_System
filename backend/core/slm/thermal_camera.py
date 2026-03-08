"""
红外热像仪模块 (Optris PI450i LT)
================================
基于Connect SDK，提供温度数据采集和热图生成功能
"""

import time
import json
import threading
import numpy as np
from typing import Optional, Dict, Tuple, List, Callable
from dataclasses import dataclass


@dataclass
class ThermalData:
    """热像数据结构"""
    timestamp: float
    temperature_matrix: np.ndarray
    temp_min: float
    temp_max: float
    temp_avg: float
    temp_center: float
    width: int
    height: int
    fps: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'temp_min': float(self.temp_min),
            'temp_max': float(self.temp_max),
            'temp_avg': float(self.temp_avg),
            'temp_center': float(self.temp_center),
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'has_image': self.temperature_matrix is not None
        }


class ThermalCamera:
    """Optris PI450i LT 红外热像仪驱动"""
    
    def __init__(self, sdk_path: str = None, device_index: int = 0,
                 temperature_range: Tuple[float, float] = (-20, 100),
                 temperature_offset: float = 0.0):
        # 默认SDK路径
        self.sdk_path = sdk_path or r"D:\SLM\OPT-PIX-Connect-Rel.-3.24.3127.0\OPT PIX Connect Rel. 3.24.3127.0\SDK\Connect SDK\Lib\v120"
        self.device_index = device_index
        self.temperature_range = temperature_range
        self.temperature_offset = temperature_offset
        
        self.dll = None
        self.is_connected = False
        self.initialized = False
        self.last_error = ""
        
        # 图像参数
        self.width = 382
        self.height = 288
        self.frame_size = self.width * self.height
        
        # 帧率统计
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0.0
        
        # 数据缓存
        self._latest_data: Optional[ThermalData] = None
        self._数据锁 = threading.Lock()
        
        # 采集线程
        self._采集线程 = None
        self._停止标志 = threading.Event()
        self._回调列表: List[Callable[[ThermalData], None]] = []
        
        # 梯度补偿配置
        self.gradient_compensation = {
            'enabled': False,
            'vertical_gradient': -0.15,
            'horizontal_gradient': 0.0,
            'reference_point': 'center',
            'compensation_strength': 1.0
        }
    
    def connect(self) -> bool:
        """连接红外热像仪"""
        try:
            import os
            import ctypes
            
            # 检查SDK路径
            if not os.path.exists(self.sdk_path):
                self.last_error = f"SDK路径不存在: {self.sdk_path}"
                print(f"[ThermalCamera] {self.last_error}")
                return False
            
            # 检查DLL文件
            dll_path = os.path.join(self.sdk_path, "ImagerIPC2x64.dll")
            if not os.path.exists(dll_path):
                self.last_error = f"DLL文件不存在: {dll_path}"
                print(f"[ThermalCamera] {self.last_error}")
                return False
            
            # 加载DLL
            self.dll = ctypes.cdll.LoadLibrary(dll_path)
            
            # 定义函数原型
            self.dll.InitImagerIPC.argtypes = [ctypes.c_ushort]
            self.dll.InitImagerIPC.restype = ctypes.c_long
            
            self.dll.StartImagerIPC.argtypes = [ctypes.c_ushort]
            self.dll.StartImagerIPC.restype = ctypes.c_long
            
            self.dll.ReleaseImagerIPC.argtypes = [ctypes.c_ushort]
            self.dll.ReleaseImagerIPC.restype = ctypes.c_long
            
            self.dll.GetFrameConfig.argtypes = [
                ctypes.c_ushort, 
                ctypes.POINTER(ctypes.c_int), 
                ctypes.POINTER(ctypes.c_int), 
                ctypes.POINTER(ctypes.c_int)
            ]
            self.dll.GetFrameConfig.restype = ctypes.c_long
            
            self.dll.GetFrame.argtypes = [
                ctypes.c_ushort, 
                ctypes.c_ushort, 
                ctypes.c_void_p, 
                ctypes.c_uint, 
                ctypes.c_void_p
            ]
            self.dll.GetFrame.restype = ctypes.c_long
            
            # 初始化IPC
            result = self.dll.InitImagerIPC(self.device_index)
            if result != 0:
                self.last_error = f"IPC初始化失败，错误代码: 0x{result:08X}"
                print(f"[ThermalCamera] {self.last_error}")
                return False
            
            # 启动IPC
            start_result = self.dll.StartImagerIPC(self.device_index)
            if start_result != 0:
                self.last_error = f"启动IPC失败，错误代码: 0x{start_result:08X}"
                print(f"[ThermalCamera] {self.last_error}")
                return False
            
            # 获取图像配置
            width = ctypes.c_int()
            height = ctypes.c_int()
            depth = ctypes.c_int()
            config_result = self.dll.GetFrameConfig(
                self.device_index,
                ctypes.byref(width),
                ctypes.byref(height),
                ctypes.byref(depth)
            )
            
            if config_result == 0:
                self.width = width.value
                self.height = height.value
                self.frame_size = self.width * self.height
            
            self.is_connected = True
            self.initialized = True
            self.last_error = ""
            print(f"[ThermalCamera] 连接成功，分辨率: {self.width}x{self.height}")
            return True
            
        except Exception as e:
            self.last_error = f"连接异常: {str(e)}"
            print(f"[ThermalCamera] {self.last_error}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self._停止标志.set()
        
        if self._采集线程 and self._采集线程.is_alive():
            self._采集线程.join(timeout=2.0)
        
        if self.is_connected and self.dll:
            try:
                self.dll.ReleaseImagerIPC(self.device_index)
                print("[ThermalCamera] 已断开连接")
            except Exception as e:
                print(f"[ThermalCamera] 断开连接异常: {e}")
        
        self.is_connected = False
        self.initialized = False
        self.dll = None
    
    def get_temperature_data(self) -> Optional[np.ndarray]:
        """获取温度数据矩阵"""
        if not self.is_connected or not self.dll:
            return None
        
        try:
            import ctypes
            
            # 创建缓冲区
            buffer_size = self.frame_size * 2  # 16位数据
            image_buffer = (ctypes.c_ubyte * buffer_size)()
            metadata_buffer = (ctypes.c_ubyte * 64)()
            
            # 获取帧数据
            timeout_ms = 100
            result = self.dll.GetFrame(
                self.device_index,
                timeout_ms,
                ctypes.cast(image_buffer, ctypes.c_void_p),
                buffer_size,
                ctypes.cast(metadata_buffer, ctypes.c_void_p)
            )
            
            if result != 0:
                # 减少错误日志频率
                if not hasattr(self, '_last_error_time'):
                    self._last_error_time = 0
                if time.time() - self._last_error_time > 5.0:
                    self._last_error_time = time.time()
                    print(f"[ThermalCamera] 获取帧失败: 0x{result:08X}")
                return None
            
            # 转换为numpy数组
            temp_array = np.frombuffer(image_buffer, dtype=np.uint16)
            
            if len(temp_array) < self.frame_size:
                return None
            
            temp_array = temp_array[:self.frame_size].reshape((self.height, self.width))
            
            # 转换为摄氏度 (0.01°C单位)
            temp_celsius = temp_array.astype(np.float32) / 100.0
            
            # 应用温度偏移
            if self.temperature_offset != 0.0:
                temp_celsius += self.temperature_offset
            
            # 应用梯度补偿
            temp_celsius = self._apply_gradient_compensation(temp_celsius)
            
            # 更新帧率统计
            self._update_fps()
            
            return temp_celsius
            
        except Exception as e:
            print(f"[ThermalCamera] 获取温度数据异常: {e}")
            return None
    
    def _apply_gradient_compensation(self, temp_data: np.ndarray) -> np.ndarray:
        """应用温度梯度补偿"""
        if not self.gradient_compensation.get('enabled', False):
            return temp_data
        
        try:
            height, width = temp_data.shape
            
            # 创建坐标网格
            y_coords, x_coords = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
            
            # 确定参考点
            ref_y, ref_x = height // 2, width // 2
            
            # 计算相对距离
            dy = y_coords - ref_y
            dx = x_coords - ref_x
            
            # 计算补偿
            vertical_gradient = self.gradient_compensation.get('vertical_gradient', -0.15)
            horizontal_gradient = self.gradient_compensation.get('horizontal_gradient', 0.0)
            strength = self.gradient_compensation.get('compensation_strength', 1.0)
            
            vertical_compensation = dy * vertical_gradient * strength
            horizontal_compensation = dx * horizontal_gradient * strength
            
            compensated = temp_data - vertical_compensation - horizontal_compensation
            return compensated.astype(np.float32)
            
        except Exception as e:
            print(f"[ThermalCamera] 梯度补偿失败: {e}")
            return temp_data
    
    def _update_fps(self):
        """更新帧率统计"""
        self.frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.last_fps_time
        
        if elapsed >= 1.0:
            self.current_fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_time = current_time
    
    def read_data(self) -> Optional[ThermalData]:
        """读取热像数据"""
        temp_matrix = self.get_temperature_data()
        
        if temp_matrix is None:
            return None
        
        # 计算统计值
        temp_min = float(np.min(temp_matrix))
        temp_max = float(np.max(temp_matrix))
        temp_avg = float(np.mean(temp_matrix))
        
        # 中心温度
        center_y, center_x = temp_matrix.shape[0] // 2, temp_matrix.shape[1] // 2
        temp_center = float(temp_matrix[center_y, center_x])
        
        data = ThermalData(
            timestamp=time.time(),
            temperature_matrix=temp_matrix,
            temp_min=temp_min,
            temp_max=temp_max,
            temp_avg=temp_avg,
            temp_center=temp_center,
            width=self.width,
            height=self.height,
            fps=self.current_fps
        )
        
        with self._数据锁:
            self._latest_data = data
        
        return data
    
    def generate_thermal_image(self, display_width: int = 640, display_height: int = 480) -> Optional[np.ndarray]:
        """生成热图图像 (BGR格式)"""
        data = self.read_data()
        if data is None or data.temperature_matrix is None:
            return None
        
        try:
            import cv2
            
            temp_matrix = data.temperature_matrix
            
            # 动态调整温度范围
            actual_min = np.percentile(temp_matrix, 5)
            actual_max = np.percentile(temp_matrix, 95)
            
            if actual_max - actual_min < 1.0:
                actual_min = temp_matrix.min()
                actual_max = temp_matrix.max()
                if actual_max - actual_min < 0.5:
                    actual_min -= 0.5
                    actual_max += 0.5
            
            # 归一化到0-255
            temp_normalized = np.clip(
                (temp_matrix - actual_min) / (actual_max - actual_min) * 255,
                0, 255
            ).astype(np.uint8)
            
            # 应用伪彩色映射
            thermal_image = cv2.applyColorMap(temp_normalized, cv2.COLORMAP_JET)
            
            # 调整大小
            thermal_image = cv2.resize(thermal_image, (display_width, display_height))
            
            # 添加温度信息
            self._add_overlay(thermal_image, data, actual_min, actual_max)
            
            return thermal_image
            
        except Exception as e:
            print(f"[ThermalCamera] 生成热图失败: {e}")
            return None
    
    def _add_overlay(self, image: np.ndarray, data: ThermalData, temp_min: float, temp_max: float):
        """在热图上添加信息叠加"""
        try:
            import cv2
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            color = (255, 255, 255)
            
            # 温度信息
            info_lines = [
                f"Range: {temp_min:.1f}-{temp_max:.1f}C",
                f"Center: {data.temp_center:.1f}C",
                f"Avg: {data.temp_avg:.1f}C"
            ]
            
            # 添加半透明背景
            box_height = len(info_lines) * 25 + 10
            overlay = image.copy()
            cv2.rectangle(overlay, (5, 5), (200, box_height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
            
            # 添加文字
            for i, line in enumerate(info_lines):
                y_pos = 25 + i * 25
                cv2.putText(image, line, (10, y_pos), font, font_scale, color, thickness)
            
            # 添加中心十字
            h, w = image.shape[:2]
            cx, cy = w // 2, h // 2
            cv2.line(image, (cx - 10, cy), (cx + 10, cy), (0, 255, 0), 1)
            cv2.line(image, (cx, cy - 10), (cx, cy + 10), (0, 255, 0), 1)
            
        except Exception as e:
            print(f"[ThermalCamera] 添加叠加信息失败: {e}")
    
    def start_continuous_read(self, interval: float = 0.1):
        """开始连续采集"""
        if self._采集线程 and self._采集线程.is_alive():
            return
        
        self._停止标志.clear()
        self._采集线程 = threading.Thread(target=self._采集循环, args=(interval,))
        self._采集线程.daemon = True
        self._采集线程.start()
        print(f"[ThermalCamera] 开始连续采集，间隔 {interval}s")
    
    def _采集循环(self, interval: float):
        """采集循环"""
        while not self._停止标志.is_set():
            data = self.read_data()
            if data:
                for callback in self._回调列表:
                    try:
                        callback(data)
                    except:
                        pass
            self._停止标志.wait(interval)
    
    def get_latest_data(self) -> Optional[ThermalData]:
        """获取最新数据"""
        with self._数据锁:
            return self._latest_data
    
    def register_callback(self, callback: Callable[[ThermalData], None]):
        """注册回调"""
        if callback not in self._回调列表:
            self._回调列表.append(callback)
    
    def unregister_callback(self, callback: Callable[[ThermalData], None]):
        """取消注册回调"""
        if callback in self._回调列表:
            self._回调列表.remove(callback)


class MockThermalCamera:
    """模拟红外热像仪（用于调试）"""
    
    def __init__(self, sdk_path: str = None, device_index: int = 0,
                 temperature_range: Tuple[float, float] = (-20, 100),
                 temperature_offset: float = 0.0):
        self.sdk_path = sdk_path or r"D:\SLM\SDK"
        self.device_index = device_index
        self.temperature_range = temperature_range
        self.temperature_offset = temperature_offset
        
        self.is_connected = False
        self.initialized = False
        self.last_error = ""
        
        self.width = 382
        self.height = 288
        self.current_fps = 25.0
        
        self._latest_data: Optional[ThermalData] = None
        self._数据锁 = threading.Lock()
        
        self._采集线程 = None
        self._停止标志 = threading.Event()
        self._回调列表: List[Callable[[ThermalData], None]] = []
        
        self._time_offset = 0
    
    def connect(self) -> bool:
        """模拟连接"""
        self.is_connected = True
        self.initialized = True
        self.last_error = ""
        print("[MockThermalCamera] 模拟连接成功")
        return True
    
    def disconnect(self):
        """断开连接"""
        self._停止标志.set()
        if self._采集线程 and self._采集线程.is_alive():
            self._采集线程.join(timeout=2.0)
        self.is_connected = False
        self.initialized = False
        print("[MockThermalCamera] 已断开连接")
    
    def _generate_mock_data(self) -> np.ndarray:
        """生成模拟温度数据"""
        y, x = np.ogrid[:self.height, :self.width]
        center_x, center_y = self.width // 2, self.height // 2
        
        # 基础温度
        base_temp = 35.0
        
        # 时间因子
        t = time.time()
        self._time_offset += 0.05
        
        # 创建多个热点
        temp_data = np.full((self.height, self.width), base_temp, dtype=np.float32)
        
        # 中心热点
        distance1 = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        hot_spot1 = 25.0 * np.exp(-distance1 / 60) * (0.8 + 0.2 * np.sin(self._time_offset))
        temp_data += hot_spot1
        
        # 次要热点
        hot_x2, hot_y2 = self.width // 3, self.height // 3
        distance2 = np.sqrt((x - hot_x2)**2 + (y - hot_y2)**2)
        hot_spot2 = 8.0 * np.exp(-distance2 / 40) * (0.7 + 0.3 * np.cos(self._time_offset * 1.2))
        temp_data += hot_spot2
        
        # 添加噪声
        noise = np.random.normal(0, 0.5, temp_data.shape)
        temp_data += noise
        
        return temp_data
    
    def read_data(self) -> Optional[ThermalData]:
        """读取模拟数据"""
        temp_matrix = self._generate_mock_data()
        
        temp_min = float(np.min(temp_matrix))
        temp_max = float(np.max(temp_matrix))
        temp_avg = float(np.mean(temp_matrix))
        
        center_y, center_x = temp_matrix.shape[0] // 2, temp_matrix.shape[1] // 2
        temp_center = float(temp_matrix[center_y, center_x])
        
        data = ThermalData(
            timestamp=time.time(),
            temperature_matrix=temp_matrix,
            temp_min=temp_min,
            temp_max=temp_max,
            temp_avg=temp_avg,
            temp_center=temp_center,
            width=self.width,
            height=self.height,
            fps=self.current_fps
        )
        
        with self._数据锁:
            self._latest_data = data
        
        return data
    
    def generate_thermal_image(self, display_width: int = 640, display_height: int = 480) -> Optional[np.ndarray]:
        """生成模拟热图"""
        data = self.read_data()
        if data is None:
            return None
        
        try:
            import cv2
            
            temp_matrix = data.temperature_matrix
            
            actual_min = np.percentile(temp_matrix, 5)
            actual_max = np.percentile(temp_matrix, 95)
            
            if actual_max - actual_min < 1.0:
                actual_min = temp_matrix.min()
                actual_max = temp_matrix.max()
                if actual_max - actual_min < 0.5:
                    actual_min -= 0.5
                    actual_max += 0.5
            
            temp_normalized = np.clip(
                (temp_matrix - actual_min) / (actual_max - actual_min) * 255,
                0, 255
            ).astype(np.uint8)
            
            thermal_image = cv2.applyColorMap(temp_normalized, cv2.COLORMAP_JET)
            thermal_image = cv2.resize(thermal_image, (display_width, display_height))
            
            # 添加信息叠加
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            color = (255, 255, 255)
            
            info_lines = [
                f"Range: {actual_min:.1f}-{actual_max:.1f}C",
                f"Center: {data.temp_center:.1f}C",
                f"Avg: {data.temp_avg:.1f}C",
                "[MOCK MODE]"
            ]
            
            overlay = thermal_image.copy()
            cv2.rectangle(overlay, (5, 5), (220, len(info_lines) * 25 + 15), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, thermal_image, 0.4, 0, thermal_image)
            
            for i, line in enumerate(info_lines):
                y_pos = 25 + i * 25
                cv2.putText(thermal_image, line, (10, y_pos), font, font_scale, color, thickness)
            
            # 中心十字
            h, w = thermal_image.shape[:2]
            cx, cy = w // 2, h // 2
            cv2.line(thermal_image, (cx - 10, cy), (cx + 10, cy), (0, 255, 0), 1)
            cv2.line(thermal_image, (cx, cy - 10), (cx, cy + 10), (0, 255, 0), 1)
            
            return thermal_image
            
        except Exception as e:
            print(f"[MockThermalCamera] 生成热图失败: {e}")
            return None
    
    def start_continuous_read(self, interval: float = 0.1):
        """开始连续采集"""
        if self._采集线程 and self._采集线程.is_alive():
            return
        
        self._停止标志.clear()
        self._采集线程 = threading.Thread(target=self._采集循环, args=(interval,))
        self._采集线程.daemon = True
        self._采集线程.start()
    
    def _采集循环(self, interval: float):
        """采集循环"""
        while not self._停止标志.is_set():
            data = self.read_data()
            if data:
                for callback in self._回调列表:
                    try:
                        callback(data)
                    except:
                        pass
            self._停止标志.wait(interval)
    
    def get_latest_data(self) -> Optional[ThermalData]:
        """获取最新数据"""
        with self._数据锁:
            return self._latest_data
    
    def register_callback(self, callback: Callable[[ThermalData], None]):
        """注册回调"""
        if callback not in self._回调列表:
            self._回调列表.append(callback)
    
    def unregister_callback(self, callback: Callable[[ThermalData], None]):
        """取消注册回调"""
        if callback in self._回调列表:
            self._回调列表.remove(callback)
