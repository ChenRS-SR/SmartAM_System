"""
SLS (选择性激光烧结) 采集系统

核心功能：
1. 振动传感器监测刮刀运动
2. 扑粉检测状态机触发采集
3. 双摄像头 + 热像仪图像采集
4. 数据记录 (CSV + 图像)

采集流程：
1. 启动振动监测
2. 检测到刮刀运动 → 拍摄before图像
3. 刮刀停止 → 拍摄after图像
4. 保存数据到CSV
"""

import os
import csv
import time
import json
import threading
import logging
from datetime import datetime
from typing import Optional, Dict, List, Callable
from pathlib import Path

import cv2
import numpy as np

from .vibration_sensor import VibrationSensor
from .powder_detector import PowderDetector, MotionState


class SLSConfig:
    """SLS采集配置"""
    
    def __init__(self):
        # 振动传感器配置
        self.vibration_port = "COM3"
        self.vibration_baudrate = 9600
        self.motion_threshold = 0.05
        
        # 摄像头配置
        self.main_camera_index = 0
        self.secondary_camera_index = 1
        self.camera_resolution = (1920, 1080)
        
        # 热像仪配置（复用FDM的Fotric）
        self.thermal_enabled = True
        
        # 保存路径
        self.save_base_path = "./data/sls"
        
        # 状态机模式
        self.state_machine_mode = "simple"  # 'simple' 或 'complex'


class SLSAcquisition:
    """
    SLS采集系统主类
    """
    
    def __init__(self, config: Optional[SLSConfig] = None):
        self.config = config or SLSConfig()
        
        # 设备
        self.vibration_sensor: Optional[VibrationSensor] = None
        self.powder_detector: Optional[PowderDetector] = None
        self.main_camera: Optional[cv2.VideoCapture] = None
        self.secondary_camera: Optional[cv2.VideoCapture] = None
        self.thermal_camera = None  # Fotric设备，外部传入
        
        # 采集状态
        self.is_running = False
        self.current_layer = 0
        self.recording_dir: Optional[str] = None
        self.csv_file: Optional[str] = None
        self.csv_writer = None
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 回调函数
        self.on_status_changed: Optional[Callable] = None
        self.on_image_captured: Optional[Callable] = None
        
        # 统计数据
        self.stats = {
            'total_cycles': 0,
            'images_captured': 0,
            'start_time': None
        }
        
        # main_data记录缓存
        self.main_data_records: List[dict] = []
        
        logging.info("[SLSAcquisition] 初始化完成")
    
    def initialize_devices(self) -> dict:
        """
        初始化所有设备
        
        Returns:
            设备状态字典
        """
        status = {
            'vibration': False,
            'main_camera': False,
            'secondary_camera': False,
            'thermal': False
        }
        
        try:
            # 1. 初始化振动传感器
            logging.info("[SLSAcquisition] 初始化振动传感器...")
            try:
                self.vibration_sensor = VibrationSensor(
                    port=self.config.vibration_port,
                    baudrate=self.config.vibration_baudrate
                )
                status['vibration'] = self.vibration_sensor.connect()
            except Exception as e:
                logging.error(f"[SLSAcquisition] 振动传感器初始化异常: {e}")
                status['vibration'] = True  # 模拟模式下也算成功
                # 创建一个模拟的振动传感器
                self.vibration_sensor = VibrationSensor()
                self.vibration_sensor.simulation_mode = True
                self.vibration_sensor.connected = True
                self.vibration_sensor._running = True
                self.vibration_sensor._start_simulation()
            
            # 2. 初始化扑粉检测器
            if status['vibration'] and self.vibration_sensor:
                try:
                    detector_config = {
                        'motion_threshold': self.config.motion_threshold,
                        'state_machine_mode': self.config.state_machine_mode,
                    }
                    self.powder_detector = PowderDetector(
                        self.vibration_sensor,
                        detector_config
                    )
                    # 设置回调
                    self.powder_detector.on_first_motion = self._on_first_motion
                    self.powder_detector.on_cycle_complete = self._on_cycle_complete
                    logging.info("[SLSAcquisition] 扑粉检测器初始化完成")
                except Exception as e:
                    logging.error(f"[SLSAcquisition] 扑粉检测器初始化失败: {e}")
                    self.powder_detector = None
            
            # 3. 初始化主摄像头
            logging.info("[SLSAcquisition] 初始化主摄像头...")
            self.main_camera = cv2.VideoCapture(self.config.main_camera_index)
            if self.main_camera.isOpened():
                self.main_camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera_resolution[0])
                self.main_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera_resolution[1])
                status['main_camera'] = True
            
            # 4. 初始化副摄像头
            logging.info("[SLSAcquisition] 初始化副摄像头...")
            self.secondary_camera = cv2.VideoCapture(self.config.secondary_camera_index)
            if self.secondary_camera.isOpened():
                self.secondary_camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera_resolution[0])
                self.secondary_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera_resolution[1])
                status['secondary_camera'] = True
            
            logging.info(f"[SLSAcquisition] 设备初始化完成: {status}")
            return status
            
        except Exception as e:
            logging.error(f"[SLSAcquisition] 设备初始化失败: {e}")
            return status
    
    def set_thermal_camera(self, thermal_device):
        """设置热像仪设备（复用FDM的Fotric）"""
        self.thermal_camera = thermal_device
        logging.info("[SLSAcquisition] 热像仪已设置")
    
    def start_acquisition(self, layer: int = 0) -> bool:
        """
        开始采集
        
        Args:
            layer: 起始层数
        
        Returns:
            是否成功启动
        """
        if self.is_running:
            logging.warning("[SLSAcquisition] 采集已在运行中")
            return False
        
        try:
            self.current_layer = layer
            
            # 创建记录目录
            self._create_recording_dir()
            
            # 初始化CSV文件
            self._init_csv()
            
            # 启动扑粉检测
            self.powder_detector.start_detection()
            
            self.is_running = True
            self.stats['start_time'] = time.time()
            
            logging.info(f"[SLSAcquisition] 采集已启动，从第{layer}层开始")
            return True
            
        except Exception as e:
            logging.error(f"[SLSAcquisition] 启动采集失败: {e}")
            return False
    
    def stop_acquisition(self):
        """停止采集"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 停止扑粉检测
        if self.powder_detector:
            self.powder_detector.stop_detection()
        
        # 保存剩余的main_data
        self._save_main_data_to_csv()
        
        # 关闭CSV文件
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
        
        logging.info("[SLSAcquisition] 采集已停止")
    
    def _create_recording_dir(self):
        """创建记录目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.recording_dir = os.path.join(
            self.config.save_base_path,
            f"sls_recording_{timestamp}"
        )
        
        # 创建子目录
        subdirs = [
            "images/CH1",      # 主摄像头
            "images/CH2",      # 副摄像头
            "images/CH3",      # 热像仪
            "images/CH3_Data", # 热像仪数据
            "csv_data"
        ]
        
        for subdir in subdirs:
            os.makedirs(os.path.join(self.recording_dir, subdir), exist_ok=True)
        
        logging.info(f"[SLSAcquisition] 记录目录: {self.recording_dir}")
    
    def _init_csv(self):
        """初始化CSV文件"""
        csv_path = os.path.join(self.recording_dir, "csv_data", "main_data.csv")
        
        self.csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
        
        # SLS的main_data列定义（与FDM不同）
        fieldnames = [
            'timestamp',
            'layer',
            'phase',           # 'before' 或 'after'
            'vibration_x',     # 振动数据
            'vibration_y',
            'vibration_z',
            'vibration_magnitude',
            'cycle_time',      # 周期时间
            'ch1_image',       # 图像路径
            'ch2_image',
            'ch3_image',
            'ch3_data',
        ]
        
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        
        logging.info(f"[SLSAcquisition] CSV文件: {csv_path}")
    
    def _on_first_motion(self):
        """
        刮刀开始运动回调
        拍摄before图像
        """
        logging.info(f"[SLSAcquisition] 检测到刮刀运动，层{self.current_layer}")
        
        # 等待稳定时间后拍摄
        time.sleep(0.3)  # first_motion_settle_time
        
        # 异步拍摄
        threading.Thread(
            target=self._capture_images,
            args=(self.current_layer, "before"),
            daemon=True
        ).start()
    
    def _on_cycle_complete(self, cycle_time: float):
        """
        完成一个周期回调
        拍摄after图像并增加层数
        """
        logging.info(f"[SLSAcquisition] 完成层{self.current_layer}，周期{cycle_time:.2f}s")
        
        # 拍摄after图像
        threading.Thread(
            target=self._capture_images,
            args=(self.current_layer, "after"),
            daemon=True
        ).start()
        
        # 层数+1
        self.current_layer += 1
        self.stats['total_cycles'] += 1
    
    def _capture_images(self, layer: int, phase: str):
        """
        采集图像
        
        Args:
            layer: 层数
            phase: 'before' 或 'after'
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            layer_str = f"L{layer:04d}"
            filename_base = f"{layer_str}_{phase}_{timestamp}"
            
            record = {
                'timestamp': timestamp,
                'layer': layer,
                'phase': phase,
                'cycle_time': 0,
                'ch1_image': '',
                'ch2_image': '',
                'ch3_image': '',
                'ch3_data': '',
            }
            
            # 获取振动数据
            if self.vibration_sensor:
                vib_data = self.vibration_sensor.get_current_data()
                record['vibration_x'] = vib_data.velocity_x
                record['vibration_y'] = vib_data.velocity_y
                record['vibration_z'] = vib_data.velocity_z
                record['vibration_magnitude'] = self.vibration_sensor.vibration_magnitude
            
            # CH1 - 主摄像头
            if self.main_camera and self.main_camera.isOpened():
                ret, frame = self.main_camera.read()
                if ret:
                    ch1_path = os.path.join(self.recording_dir, "images", "CH1", f"{filename_base}.png")
                    cv2.imwrite(ch1_path, frame)
                    record['ch1_image'] = f"images/CH1/{filename_base}.png"
                    logging.info(f"[SLSAcquisition] CH1已保存: {filename_base}")
            
            # CH2 - 副摄像头
            if self.secondary_camera and self.secondary_camera.isOpened():
                ret, frame = self.secondary_camera.read()
                if ret:
                    ch2_path = os.path.join(self.recording_dir, "images", "CH2", f"{filename_base}.png")
                    cv2.imwrite(ch2_path, frame)
                    record['ch2_image'] = f"images/CH2/{filename_base}.png"
            
            # CH3 - 热像仪（复用FDM的Fotric）
            if self.thermal_camera:
                try:
                    ch3_path = os.path.join(self.recording_dir, "images", "CH3", f"{filename_base}")
                    # 调用Fotric的保存方法
                    if hasattr(self.thermal_camera, 'save_current_frame'):
                        self.thermal_camera.save_current_frame(ch3_path)
                        record['ch3_image'] = f"images/CH3/{filename_base}.png"
                        record['ch3_data'] = f"images/CH3_Data/{filename_base}.npy"
                except Exception as e:
                    logging.error(f"[SLSAcquisition] 热像仪保存失败: {e}")
            
            # 添加到记录缓存
            with self._lock:
                self.main_data_records.append(record)
                self.stats['images_captured'] += 1
            
            # 实时保存到CSV
            self._append_to_csv(record)
            
            # 通知回调
            if self.on_image_captured:
                self.on_image_captured(layer, phase, record)
            
        except Exception as e:
            logging.error(f"[SLSAcquisition] 图像采集失败: {e}")
    
    def _append_to_csv(self, record: dict):
        """追加记录到CSV"""
        if self.csv_writer:
            self.csv_writer.writerow(record)
            self.csv_file.flush()
    
    def _save_main_data_to_csv(self):
        """保存所有缓存的main_data到CSV"""
        # 已经在_append_to_csv中实时保存了
        pass
    
    def get_status(self) -> dict:
        """获取采集状态"""
        return {
            'is_running': self.is_running,
            'current_layer': self.current_layer,
            'recording_dir': self.recording_dir,
            'stats': self.stats.copy(),
            'powder_detector': self.powder_detector.get_status() if self.powder_detector else None,
            'vibration': {
                'magnitude': self.vibration_sensor.vibration_magnitude if self.vibration_sensor else 0,
                'connected': self.vibration_sensor.connected if self.vibration_sensor else False
            }
        }
    
    def get_device_status(self) -> dict:
        """获取设备连接状态"""
        return {
            'vibration': {
                'connected': self.vibration_sensor.connected if self.vibration_sensor else False,
                'magnitude': self.vibration_sensor.vibration_magnitude if self.vibration_sensor else 0
            },
            'main_camera': {
                'connected': self.main_camera.isOpened() if self.main_camera else False
            },
            'secondary_camera': {
                'connected': self.secondary_camera.isOpened() if self.secondary_camera else False
            },
            'thermal': {
                'connected': self.thermal_camera is not None
            }
        }
    
    def set_layer(self, layer: int):
        """设置当前层数"""
        self.current_layer = layer
        logging.info(f"[SLSAcquisition] 层数设置为: {layer}")
    
    def disconnect_all(self):
        """断开所有设备"""
        self.stop_acquisition()
        
        if self.vibration_sensor:
            self.vibration_sensor.disconnect()
        
        if self.main_camera:
            self.main_camera.release()
        
        if self.secondary_camera:
            self.secondary_camera.release()
        
        logging.info("[SLSAcquisition] 所有设备已断开")


# 单例实例
_sls_acquisition: Optional[SLSAcquisition] = None


def get_sls_acquisition(config: Optional[SLSConfig] = None) -> SLSAcquisition:
    """获取SLS采集单例"""
    global _sls_acquisition
    if _sls_acquisition is None:
        _sls_acquisition = SLSAcquisition(config)
    return _sls_acquisition
