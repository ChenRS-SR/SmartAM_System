"""
SLS摄像头设备模块
=================
基于OpenCV的摄像头控制类
支持主摄像头和副摄像头
"""

import cv2
import numpy as np
from datetime import datetime
import threading
import time
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class CameraFrame:
    """摄像头帧数据结构"""
    frame: np.ndarray
    timestamp: datetime
    frame_id: int


class CameraDevice:
    """摄像头设备类"""
    
    def __init__(self, camera_index: int, camera_name: str = "Camera"):
        """
        初始化摄像头设备
        
        Args:
            camera_index: 摄像头索引
            camera_name: 摄像头名称
        """
        self.camera_index = camera_index
        self.camera_name = camera_name
        self.camera: Optional[cv2.VideoCapture] = None
        self.is_connected = False
        self.error_count = 0
        self.frame_count = 0
        self.lock = threading.Lock()
        self.rotate_180 = True  # 默认启用180度旋转
        
        # 分辨率设置
        self.width = 640
        self.height = 480
        self.fps = 30
    
    @staticmethod
    def scan_available_cameras(max_index: int = 10) -> List[Dict]:
        """
        扫描所有可用的摄像头索引
        
        Args:
            max_index: 最大扫描索引
            
        Returns:
            可用摄像头列表
        """
        print(f"[Camera] 正在扫描系统中所有可用的摄像头（索引 0-{max_index}）...")
        available_cameras = []
        
        # 尝试的后端
        backends_to_try = [
            (cv2.CAP_DSHOW, "DSHOW"),
            (cv2.CAP_MSMF, "MSMF"),
        ]
        
        for backend_id, backend_name in backends_to_try:
            print(f"[Camera] 使用 {backend_name} 后端扫描...")
            for i in range(max_index + 1):
                try:
                    cap = cv2.VideoCapture(i, backend_id)
                    if cap.isOpened():
                        # 尝试读取一帧来验证摄像头是否真正可用
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            height, width = frame.shape[:2]
                            fps = cap.get(cv2.CAP_PROP_FPS)
                            
                            camera_info = {
                                'index': i,
                                'backend': backend_name,
                                'width': width,
                                'height': height,
                                'fps': fps,
                                'working': True
                            }
                            
                            # 检查是否已经在列表中（避免重复）
                            if not any(cam['index'] == i for cam in available_cameras):
                                available_cameras.append(camera_info)
                                print(f"[Camera] 索引 {i}: {width}x{height} @{fps:.1f}fps ({backend_name})")
                        cap.release()
                except Exception:
                    pass
            
            if available_cameras:
                break  # 如果已经找到摄像头，不需要尝试其他后端
        
        print(f"[Camera] 扫描完成，共发现 {len(available_cameras)} 个可用摄像头")
        return available_cameras
    
    def connect(self) -> bool:
        """
        连接摄像头
        
        Returns:
            bool: 连接是否成功
        """
        # 尝试多种后端
        backends_to_try = [
            cv2.CAP_DSHOW,
            cv2.CAP_MSMF,
            cv2.CAP_ANY
        ]
        
        # 首先尝试指定的camera_index，然后尝试其他常见索引
        if "主" in self.camera_name or "CH1" in self.camera_name:
            indices_to_try = [self.camera_index] + [i for i in [0, 1] if i != self.camera_index]
        else:
            indices_to_try = [self.camera_index] + [i for i in [1, 2, 0] if i != self.camera_index]
        
        print(f"[Camera] 正在检测{self.camera_name}的可用索引...")
        
        for backend in backends_to_try:
            backend_name = {cv2.CAP_DSHOW: "DSHOW", cv2.CAP_MSMF: "MSMF", cv2.CAP_ANY: "ANY"}.get(backend, "UNKNOWN")
            
            for index in indices_to_try:
                try:
                    print(f"[Camera] 尝试索引 {index} 使用 {backend_name} 后端...")
                    self.camera = cv2.VideoCapture(index, backend)
                    
                    if self.camera.isOpened():
                        # 读取一帧测试
                        ret, frame = self.camera.read()
                        if ret and frame is not None:
                            # 设置摄像头参数
                            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                            
                            # 等待摄像头初始化
                            time.sleep(0.5)
                            
                            # 读取几帧以确保摄像头已经准备好
                            for _ in range(3):
                                self.camera.read()
                            
                            self.camera_index = index
                            self.is_connected = True
                            self.error_count = 0
                            print(f"[Camera] {self.camera_name}连接成功（索引: {index}, 后端: {backend_name}）")
                            return True
                        else:
                            print(f"[Camera] 索引 {index} 打开但无法读取帧")
                            self.camera.release()
                    else:
                        print(f"[Camera] 索引 {index} 无法打开")
                        
                except Exception as e:
                    print(f"[Camera] 索引 {index} 尝试失败: {e}")
                    if self.camera:
                        self.camera.release()
        
        print(f"[Camera] {self.camera_name}所有索引和后端都尝试失败")
        return False
    
    def disconnect(self) -> None:
        """断开摄像头连接"""
        with self.lock:
            if self.camera is not None:
                self.camera.release()
                self.camera = None
                self.is_connected = False
                print(f"[Camera] {self.camera_name}已断开")
    
    def read_frame(self) -> Optional[np.ndarray]:
        """
        读取一帧图像
        
        Returns:
            图像帧，如果失败返回None
        """
        if not self.is_connected or self.camera is None:
            return None
        
        with self.lock:
            try:
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    self.error_count = 0
                    self.frame_count += 1
                    
                    # 旋转180度（如果需要）
                    if self.rotate_180:
                        frame = cv2.rotate(frame, cv2.ROTATE_180)
                    
                    return frame
                else:
                    self.error_count += 1
                    return None
            except Exception as e:
                print(f"[Camera] 读取帧失败: {e}")
                self.error_count += 1
                return None
    
    def get_frame_jpeg(self, quality: int = 85) -> Optional[bytes]:
        """
        获取JPEG格式的帧
        
        Args:
            quality: JPEG质量 (0-100)
            
        Returns:
            JPEG字节数据
        """
        frame = self.read_frame()
        if frame is None:
            return None
        
        try:
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            result, encoded = cv2.imencode('.jpg', frame, encode_params)
            if result:
                return encoded.tobytes()
        except Exception as e:
            print(f"[Camera] JPEG编码失败: {e}")
        
        return None
    
    def get_status(self) -> Dict:
        """获取摄像头状态"""
        return {
            'camera_index': self.camera_index,
            'camera_name': self.camera_name,
            'is_connected': self.is_connected,
            'frame_count': self.frame_count,
            'error_count': self.error_count,
            'width': self.width,
            'height': self.height,
            'fps': self.fps
        }


class CameraManager:
    """摄像头管理器 - 管理多个摄像头"""
    
    def __init__(self, ch1_index: int = 0, ch2_index: int = 1):
        """
        初始化摄像头管理器
        
        Args:
            ch1_index: CH1摄像头索引
            ch2_index: CH2摄像头索引
        """
        self.ch1 = CameraDevice(ch1_index, "CH1主摄像头")
        self.ch2 = CameraDevice(ch2_index, "CH2副摄像头")
        self.cameras = {
            'CH1': self.ch1,
            'CH2': self.ch2
        }
    
    def connect_all(self) -> bool:
        """连接所有摄像头"""
        results = []
        for name, camera in self.cameras.items():
            result = camera.connect()
            results.append(result)
            print(f"[CameraManager] {name}: {'成功' if result else '失败'}")
        
        return any(results)  # 至少一个成功就算成功
    
    def disconnect_all(self) -> None:
        """断开所有摄像头"""
        for camera in self.cameras.values():
            camera.disconnect()
    
    def get_frame(self, channel: str) -> Optional[np.ndarray]:
        """
        获取指定通道的帧
        
        Args:
            channel: 通道名称 ('CH1' 或 'CH2')
            
        Returns:
            图像帧
        """
        camera = self.cameras.get(channel)
        if camera:
            return camera.read_frame()
        return None
    
    def get_frame_jpeg(self, channel: str) -> Optional[bytes]:
        """
        获取指定通道的JPEG帧
        
        Args:
            channel: 通道名称 ('CH1' 或 'CH2')
            
        Returns:
            JPEG字节数据
        """
        camera = self.cameras.get(channel)
        if camera:
            return camera.get_frame_jpeg()
        return None
    
    def get_status(self) -> Dict:
        """获取所有摄像头状态"""
        return {
            name: camera.get_status()
            for name, camera in self.cameras.items()
        }


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("摄像头设备测试")
    print("=" * 60)
    
    # 扫描可用摄像头
    cameras = CameraDevice.scan_available_cameras()
    print(f"\n发现 {len(cameras)} 个摄像头")
    
    if cameras:
        # 测试第一个摄像头
        cam = CameraDevice(cameras[0]['index'], "测试摄像头")
        if cam.connect():
            print("\n读取10帧测试:")
            for i in range(10):
                frame = cam.read_frame()
                if frame is not None:
                    print(f"  帧 {i+1}: {frame.shape}")
                time.sleep(0.1)
            cam.disconnect()
