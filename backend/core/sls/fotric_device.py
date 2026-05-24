"""
SLS Fotric 628CH 红外热像仪模块（增强版）
==========================================
基于FOTRIC HTTP REST API的Python封装
参考SLS项目中的Fotric_628ch_enhanced.py实现

主要功能:
1. HTTP REST API温度获取
2. 640x480全分辨率温度矩阵
3. 实时温度监控
4. 模拟模式支持
"""

import logging
import requests
import time
import numpy as np
from typing import Optional, Dict, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import threading


logger = logging.getLogger("FotricDevice")


@dataclass
class TemperaturePoint:
    """温度点数据类"""
    x: int
    y: int
    temperature: float
    timestamp: float


@dataclass
class DeviceInfo:
    """设备信息数据类"""
    ip: str
    width: int
    height: int
    firmware_version: str
    is_connected: bool


class FotricDevice:
    """FOTRIC 628ch增强版设备类"""
    
    # REST API路径
    URL_ADMIN_INFO = "/admin/info"
    URL_SENSOR_DIMENSION = "/sensor/dimension"
    URL_ISP_T = "/isp/t?x={}&y={}"
    URL_SENSOR_LUTS = "/sensor/luts"
    
    def __init__(self, 
                 ip: str = "192.168.1.100",
                 port: int = 10080,
                 username: str = "admin",
                 password: str = "admin",
                 simulation_mode: bool = False,
                 update_rate: float = 2.0):
        """
        初始化FOTRIC设备
        
        Args:
            ip: 设备IP地址
            port: 设备端口（默认10080）
            username: 用户名
            password: 密码
            simulation_mode: 是否启用模拟模式
            update_rate: 数据更新频率(Hz)
        """
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.simulation_mode = simulation_mode
        self.update_rate = update_rate
        
        # 设备状态
        self.is_connected = False
        self.device_info: Optional[DeviceInfo] = None
        
        # 会话管理
        self.session = requests.Session()
        self.session.timeout = 10
        
        # 设备参数
        self.width = 640
        self.height = 480
        self.firmware_version = ""
        
        # 温度缓存
        self._temperature_cache: Dict[str, TemperaturePoint] = {}
        self._cache_lock = threading.Lock()
        
        # 数据读取线程
        self.is_running = False
        self.reader_thread: Optional[threading.Thread] = None
        self.latest_frame: Optional[Dict] = None
        self.frame_count = 0
        
        logger.info(f"初始化FOTRIC设备: {ip}:{port}")
    
    def connect(self) -> bool:
        """
        连接设备
        
        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info(f"连接FOTRIC设备: {self.ip}")
            
            if self.simulation_mode:
                logger.info("模拟模式: 跳过实际设备连接")
                self.device_info = DeviceInfo(
                    ip=self.ip,
                    width=self.width,
                    height=self.height,
                    firmware_version="Simulation v1.0",
                    is_connected=True
                )
                self.is_connected = True
                logger.info(f"FOTRIC模拟设备连接成功: {self.width}x{self.height}")
                self._generate_initial_frame()
                return True
            
            # 测试基本连接
            if not self._test_connection():
                logger.error("设备连接测试失败")
                # 如果连接失败，切换到模拟模式
                logger.warning("切换到模拟模式")
                self.simulation_mode = True
                self.device_info = DeviceInfo(
                    ip=self.ip,
                    width=self.width,
                    height=self.height,
                    firmware_version="Simulation v1.0",
                    is_connected=True
                )
                self.is_connected = True
                self._generate_initial_frame()
                return True
            
            # 获取设备信息
            if not self._get_device_info():
                logger.error("获取设备信息失败")
                return False
            
            # 获取传感器尺寸
            if not self._get_sensor_dimension():
                logger.error("获取传感器尺寸失败")
                return False
            
            self.is_connected = True
            logger.info(f"FOTRIC设备连接成功: {self.width}x{self.height}")
            self._generate_initial_frame()
            
            return True
            
        except Exception as e:
            logger.error(f"连接设备失败: {e}")
            # 切换到模拟模式
            logger.warning("切换到模拟模式")
            self.simulation_mode = True
            self.device_info = DeviceInfo(
                ip=self.ip,
                width=self.width,
                height=self.height,
                firmware_version="Simulation v1.0",
                is_connected=True
            )
            self.is_connected = True
            self._generate_initial_frame()
            return True
    
    def disconnect(self) -> None:
        """断开设备连接"""
        self.stop_monitoring()
        self.is_connected = False
        self.session.close()
        logger.info("设备连接已断开")
    
    def _test_connection(self) -> bool:
        """测试设备连接"""
        try:
            url = f"http://{self.ip}:{self.port}{self.URL_ADMIN_INFO}"
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _get_device_info(self) -> bool:
        """获取设备信息"""
        try:
            url = f"http://{self.ip}:{self.port}{self.URL_ADMIN_INFO}"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            self.firmware_version = data.get('firmware_version', 'Unknown')
            
            self.device_info = DeviceInfo(
                ip=self.ip,
                width=self.width,
                height=self.height,
                firmware_version=self.firmware_version,
                is_connected=True
            )
            
            return True
        except:
            return False
    
    def _get_sensor_dimension(self) -> bool:
        """获取传感器尺寸"""
        try:
            url = f"http://{self.ip}:{self.port}{self.URL_SENSOR_DIMENSION}"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            self.width = data.get('width', 640)
            self.height = data.get('height', 480)
            
            return True
        except:
            # 使用默认尺寸
            logger.warning("无法获取传感器尺寸，使用默认值 640x480")
            return True
    
    def get_point_temperature(self, x: int, y: int, use_cache: bool = True) -> Optional[float]:
        """
        获取指定点的温度
        
        Args:
            x: X坐标
            y: Y坐标
            use_cache: 是否使用缓存
            
        Returns:
            float: 温度值(摄氏度)，失败返回None
        """
        if not self.is_connected:
            return None
        
        # 坐标验证
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
        
        cache_key = f"{x}_{y}"
        
        # 检查缓存
        if use_cache:
            with self._cache_lock:
                if cache_key in self._temperature_cache:
                    cached_point = self._temperature_cache[cache_key]
                    if time.time() - cached_point.timestamp < 5.0:
                        return cached_point.temperature
        
        if self.simulation_mode:
            # 模拟模式: 生成模拟温度数据
            base_temp = 25.0
            temp_variation = (x + y) / (self.width + self.height) * 10
            import random
            noise = random.uniform(-2.0, 2.0)
            temperature = base_temp + temp_variation + noise
            
            temperature_point = TemperaturePoint(x, y, temperature, time.time())
            with self._cache_lock:
                self._temperature_cache[cache_key] = temperature_point
            
            return temperature
        
        try:
            # 构建请求URL
            url = f"http://{self.ip}:{self.port}{self.URL_ISP_T.format(x, y)}"
            
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            temperature = data.get('t', 0.0)
            
            # 更新缓存
            temperature_point = TemperaturePoint(x, y, temperature, time.time())
            with self._cache_lock:
                self._temperature_cache[cache_key] = temperature_point
            
            return temperature
            
        except Exception as e:
            logger.error(f"获取温度失败: {e}")
            return None
    
    def _generate_thermal_array(self) -> Optional[np.ndarray]:
        """
        生成热像仪数据数组
        
        Returns:
            np.ndarray: 温度矩阵 (height, width)
        """
        if not self.is_connected:
            return None
        
        try:
            if self.simulation_mode:
                # 模拟模式: 生成模拟数据
                import random
                base_temp = 25.0 + 5 * np.sin(time.time() * 0.5)
                
                height, width = self.height, self.width
                y, x = np.ogrid[:height, :width]
                center_x, center_y = width // 2, height // 2
                
                distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                max_distance = np.sqrt(center_x**2 + center_y**2)
                
                temp_field = base_temp + 15 * np.exp(-distance / max_distance * 3)
                temp_field += np.random.normal(0, 1.0, temp_field.shape)
                
                return temp_field.astype(np.float32)
            
            # 真实模式: 采样获取温度数据
            # 由于无法一次性获取全分辨率数据，使用采样方式
            return self._generate_sampled_data()
            
        except Exception as e:
            logger.error(f"生成热像数组失败: {e}")
            return None
    
    def _generate_sampled_data(self, sample_step: int = 20) -> Optional[np.ndarray]:
        """
        采样方式生成温度数据
        
        Args:
            sample_step: 采样间隔
            
        Returns:
            np.ndarray: 温度矩阵
        """
        if not self.is_connected:
            return None
        
        try:
            # 创建网格
            width, height = self.width, self.height
            temp_grid = np.zeros((height, width), dtype=np.float32)
            
            # 采样点
            sample_points_x = range(0, width, sample_step)
            sample_points_y = range(0, height, sample_step)
            
            # 获取采样点温度
            sampled_temps = {}
            for y in sample_points_y:
                for x in sample_points_x:
                    temp = self.get_point_temperature(x, y, use_cache=False)
                    if temp is not None:
                        sampled_temps[(x, y)] = temp
            
            # 插值填充
            if len(sampled_temps) > 0:
                from scipy.interpolate import griddata
                
                points = np.array(list(sampled_temps.keys()))
                values = np.array(list(sampled_temps.values()))
                
                grid_x, grid_y = np.mgrid[0:width, 0:height]
                
                temp_grid = griddata(points, values, (grid_x, grid_y), method='linear', fill_value=25.0)
                temp_grid = temp_grid.T  # 转置以匹配 (height, width)
            
            return temp_grid.astype(np.float32)
            
        except Exception as e:
            logger.error(f"采样数据生成失败: {e}")
            return None
    
    def _calculate_temp_stats(self, temp_grid: np.ndarray) -> Dict[str, float]:
        """计算温度统计信息"""
        return {
            'temp_min': float(np.min(temp_grid)),
            'temp_max': float(np.max(temp_grid)),
            'temp_avg': float(np.mean(temp_grid)),
            'temp_center': float(temp_grid[temp_grid.shape[0]//2, temp_grid.shape[1]//2])
        }
    
    def _generate_initial_frame(self):
        """生成初始帧数据"""
        try:
            thermal_data = self._generate_thermal_array()
            if thermal_data is not None:
                temp_stats = self._calculate_temp_stats(thermal_data)
                self.frame_count = 1
                self.latest_frame = {
                    'frame': thermal_data,
                    'timestamp': datetime.now(),
                    'frame_id': self.frame_count,
                    **temp_stats
                }
                logger.info(f"初始帧已生成: {thermal_data.shape}")
        except Exception as e:
            logger.error(f"生成初始帧失败: {e}")
    
    def _data_reader_thread(self):
        """数据读取线程"""
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.is_running:
            loop_start_time = time.time()
            try:
                thermal_data = self._generate_thermal_array()
                
                if thermal_data is not None:
                    temp_stats = self._calculate_temp_stats(thermal_data)
                    
                    self.frame_count += 1
                    self.latest_frame = {
                        'frame': thermal_data,
                        'timestamp': datetime.now(),
                        'frame_id': self.frame_count,
                        **temp_stats
                    }
                    
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                
                # 控制帧率
                if self.simulation_mode:
                    time.sleep(0.1)  # 模拟模式: 10 FPS
                else:
                    loop_end_time = time.time()
                    actual_loop_time = loop_end_time - loop_start_time
                    target_interval = 1.0 / self.update_rate if self.update_rate > 0 else 0.5
                    
                    remaining_time = target_interval - actual_loop_time
                    if remaining_time > 0:
                        time.sleep(remaining_time)
                
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    logger.warning(f"数据读取错误 (第{consecutive_errors}次): {e}")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("连续错误太多，停止监控")
                    break
                
                time.sleep(1 if consecutive_errors > 5 else 0.5)
    
    def start_monitoring(self) -> bool:
        """开始监控"""
        if self.is_running:
            return True
        
        self.is_running = True
        self.reader_thread = threading.Thread(target=self._data_reader_thread, daemon=True)
        self.reader_thread.start()
        
        logger.info("开始热像监控")
        return True
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2)
        logger.info("停止热像监控")
    
    def get_latest_frame(self) -> Optional[Dict]:
        """获取最新帧"""
        return self.latest_frame
    
    def get_temperature_data(self) -> Optional[Dict]:
        """获取温度数据"""
        frame = self.get_latest_frame()
        if frame is None:
            return None
        
        return {
            'temp_min': frame.get('temp_min', 0),
            'temp_max': frame.get('temp_max', 0),
            'temp_avg': frame.get('temp_avg', 0),
            'temp_center': frame.get('temp_center', 0),
            'timestamp': frame.get('timestamp', datetime.now()).isoformat() if isinstance(frame.get('timestamp'), datetime) else str(frame.get('timestamp'))
        }
    
    def get_frame_jpeg(self, colormap: int = None) -> Optional[bytes]:
        """
        获取JPEG格式的热成像图像
        
        Returns:
            JPEG字节数据
        """
        import cv2
        
        frame = self.get_latest_frame()
        if frame is None or 'frame' not in frame:
            return None
        
        try:
            temp_data = frame['frame']
            temp_min, temp_max = temp_data.min(), temp_data.max()
            
            # 归一化到0-255
            normalized = ((temp_data - temp_min) / (temp_max - temp_min + 1e-6) * 255).astype(np.uint8)
            
            # 应用色彩映射
            if colormap is None:
                colormap = cv2.COLORMAP_JET
            colored = cv2.applyColorMap(normalized, colormap)
            
            # 编码为JPEG
            result, encoded = cv2.imencode('.jpg', colored, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if result:
                return encoded.tobytes()
        except Exception as e:
            logger.error(f"JPEG编码失败: {e}")
        
        return None
    
    def get_status(self) -> Dict:
        """获取设备状态"""
        return {
            'connected': self.is_connected,
            'streaming': self.is_running,
            'simulation_mode': self.simulation_mode,
            'ip_address': self.ip,
            'port': self.port,
            'frame_count': self.frame_count,
            'temperature': self.get_temperature_data()
        }


class MockFotricDevice(FotricDevice):
    """FOTRIC设备模拟器（用于无硬件测试）"""
    
    def __init__(self, ip: str = "192.168.1.100", **kwargs):
        """
        初始化模拟设备
        
        Args:
            ip: 模拟IP地址
            **kwargs: 其他参数（被忽略）
        """
        super().__init__(ip=ip, simulation_mode=True, update_rate=2.0)
        logger.info(f"创建FOTRIC模拟设备: {ip}")


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("FOTRIC设备测试")
    print("=" * 60)
    
    device = FotricDevice(simulation_mode=True)
    
    if device.connect():
        print("\n启动监控...")
        device.start_monitoring()
        
        print("\n读取10帧数据:")
        for i in range(10):
            time.sleep(0.5)
            temp_data = device.get_temperature_data()
            if temp_data:
                print(f"  帧 {i+1}: 最高={temp_data['temp_max']:.1f}°C, "
                      f"最低={temp_data['temp_min']:.1f}°C, "
                      f"平均={temp_data['temp_avg']:.1f}°C")
        
        print("\n停止监控...")
        device.stop_monitoring()
        device.disconnect()
