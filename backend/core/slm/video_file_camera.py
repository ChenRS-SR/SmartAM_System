"""
视频文件摄像头模拟器 - 使用持久VideoCapture
============================================
修复问题: 每次读取都创建新的VideoCapture导致画面不动
"""

import cv2
import numpy as np
import threading
import time
from pathlib import Path
from typing import Dict, Optional, List, Callable, Tuple
from dataclasses import dataclass

from .distortion_corrector import get_distortion_corrector


@dataclass
class CameraFrame:
    """摄像头帧数据"""
    timestamp: float
    frame: np.ndarray
    channel: str
    frame_number: int


class VideoFileCameraManager:
    """
    视频文件摄像头管理器 - 持久VideoCapture版本
    
    修复: 每个通道使用持久的VideoCapture实例，确保画面连续播放
    """
    
    def __init__(self, video_files: Dict[str, str], fps: int = 30, 
                 display_size: Tuple[int, int] = (640, 480),
                 enable_correction: bool = True):
        """
        初始化
        
        Args:
            video_files: {'CH1': 'path/to/ch1.mp4', ...}
            fps: 播放帧率
            display_size: 输出分辨率
            enable_correction: 是否启用畸变矫正
        """
        self.video_files = video_files
        self.fps = fps
        self.display_size = display_size
        self.enable_correction = enable_correction
        
        # 通道状态
        self.ch1_enabled = 'CH1' in video_files
        self.ch2_enabled = 'CH2' in video_files
        self.ch3_enabled = 'CH3' in video_files
        self.is_connected = False
        self.last_error = ""
        
        # 帧计数
        self.ch1_frame_count = 0
        self.ch2_frame_count = 0
        self.ch3_frame_count = 0
        
        # 最新帧缓存
        self._latest_ch1: Optional[np.ndarray] = None
        self._latest_ch2: Optional[np.ndarray] = None
        self._latest_ch3: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        
        # VideoCapture 实例 (持久化)
        self._captures: Dict[str, cv2.VideoCapture] = {}
        
        # 线程
        self._ch1_thread: Optional[threading.Thread] = None
        self._ch2_thread: Optional[threading.Thread] = None
        self._ch3_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 回调
        self._callbacks: List[Callable[[CameraFrame], None]] = []
        
        # 畸变矫正器
        self._corrector = get_distortion_corrector() if enable_correction else None
        
        print(f"[VideoFileCameraManager] 初始化: {list(video_files.keys())}")
    
    def set_fps(self, fps: int):
        """动态设置播放帧率"""
        self.fps = max(1, min(60, fps))
        print(f"[VideoFileCameraManager] FPS 设置为: {self.fps}")
    
    def find_available_cameras(self) -> List[Dict]:
        """返回可用摄像头列表"""
        available = []
        for i, (channel, path) in enumerate(self.video_files.items()):
            available.append({
                'index': i,
                'resolution': self.display_size,
                'name': f'视频文件 {channel}'
            })
        return available
    
    def connect(self) -> bool:
        """连接（创建持久的VideoCapture）"""
        for channel, path in self.video_files.items():
            if not Path(path).exists():
                self.last_error = f"视频文件不存在: {path}"
                print(f"[VideoFileCameraManager] {self.last_error}")
                return False
            
            # 创建持久的VideoCapture
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                self.last_error = f"无法打开视频: {path}"
                print(f"[VideoFileCameraManager] {self.last_error}")
                return False
            
            self._captures[channel] = cap
            fps = cap.get(cv2.CAP_PROP_FPS)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"[VideoFileCameraManager] {channel}: {self.display_size}@{fps}fps, {frames}帧")
        
        self.is_connected = True
        return True
    
    def disconnect(self):
        """断开连接（释放VideoCapture）"""
        self._stop_event.set()
        
        # 等待线程结束
        for thread in [self._ch1_thread, self._ch2_thread, self._ch3_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=2.0)
        
        # 释放VideoCapture
        for channel, cap in self._captures.items():
            cap.release()
            print(f"[VideoFileCameraManager] {channel} VideoCapture已释放")
        self._captures.clear()
        
        self.is_connected = False
        print("[VideoFileCameraManager] 已断开")
    
    def _read_frame(self, channel: str) -> Optional[np.ndarray]:
        """
        从持久的VideoCapture读取一帧
        """
        if channel not in self._captures:
            return None
        
        cap = self._captures[channel]
        ret, frame = cap.read()
        
        if not ret:
            # 循环播放: 回到第一帧
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                return None
        
        # 畸变矫正
        if self.enable_correction and self._corrector:
            if self._corrector.is_channel_calibrated(channel):
                try:
                    corrected = self._corrector.correct_frame(frame, channel)
                    if corrected is not None:
                        frame = corrected
                except Exception as e:
                    print(f"[VideoFileCameraManager] {channel} 矫正失败: {e}")
        
        # 调整尺寸
        if frame.shape[1] != self.display_size[0] or frame.shape[0] != self.display_size[1]:
            frame = cv2.resize(frame, self.display_size, interpolation=cv2.INTER_LINEAR)
        
        return frame
    
    def start_continuous_capture(self):
        """开始连续采集"""
        self._stop_event.clear()
        
        if self.ch1_enabled:
            self._ch1_thread = threading.Thread(target=self._capture_loop, args=('CH1',))
            self._ch1_thread.daemon = True
            self._ch1_thread.start()
        
        if self.ch2_enabled:
            self._ch2_thread = threading.Thread(target=self._capture_loop, args=('CH2',))
            self._ch2_thread.daemon = True
            self._ch2_thread.start()
        
        if self.ch3_enabled:
            self._ch3_thread = threading.Thread(target=self._capture_loop, args=('CH3',))
            self._ch3_thread.daemon = True
            self._ch3_thread.start()
        
        print("[VideoFileCameraManager] 采集已启动")
    
    def _capture_loop(self, channel: str):
        """采集循环 - 使用持久的VideoCapture"""
        print(f"[VideoFileCameraManager] {channel} 线程启动")
        frame_count = 0
        interval = 1.0 / self.fps
        
        while not self._stop_event.is_set():
            try:
                frame = self._read_frame(channel)
                
                if frame is not None:
                    frame_count += 1
                    
                    with self._frame_lock:
                        if channel == 'CH1':
                            self._latest_ch1 = frame
                            self.ch1_frame_count = frame_count
                        elif channel == 'CH2':
                            self._latest_ch2 = frame
                            self.ch2_frame_count = frame_count
                        elif channel == 'CH3':
                            self._latest_ch3 = frame
                            self.ch3_frame_count = frame_count
                    
                    # 触发回调
                    camera_frame = CameraFrame(
                        timestamp=time.time(),
                        frame=frame,
                        channel=channel,
                        frame_number=frame_count
                    )
                    
                    for callback in self._callbacks:
                        try:
                            callback(camera_frame)
                        except:
                            pass
                
                # 控制帧率
                self._stop_event.wait(interval)
                
            except Exception as e:
                print(f"[VideoFileCameraManager] {channel} 错误: {e}")
                time.sleep(0.1)
        
        print(f"[VideoFileCameraManager] {channel} 线程结束，共{frame_count}帧")
    
    def get_latest_frame(self, channel: str) -> Optional[np.ndarray]:
        """获取最新帧"""
        with self._frame_lock:
            if channel == 'CH1':
                return self._latest_ch1.copy() if self._latest_ch1 is not None else None
            elif channel == 'CH2':
                return self._latest_ch2.copy() if self._latest_ch2 is not None else None
            elif channel == 'CH3':
                return self._latest_ch3.copy() if self._latest_ch3 is not None else None
        return None
    
    def get_frame_jpeg(self, channel: str, quality: int = 85) -> Optional[bytes]:
        """获取JPEG帧 - 用于视频流 (只从缓存获取，不回退到直接读取)"""
        frame = self.get_latest_frame(channel)
        
        if frame is None:
            return None
        
        try:
            # 添加帧计数水印
            display_frame = frame.copy()
            frame_num = 0
            if channel == 'CH1':
                frame_num = self.ch1_frame_count
            elif channel == 'CH2':
                frame_num = self.ch2_frame_count
            elif channel == 'CH3':
                frame_num = self.ch3_frame_count
            
            cv2.putText(display_frame, f"Frame: {frame_num}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 编码为JPEG
            ret, jpeg = cv2.imencode('.jpg', display_frame, 
                                     [cv2.IMWRITE_JPEG_QUALITY, quality])
            if ret:
                return jpeg.tobytes()
        except Exception as e:
            print(f"[VideoFileCameraManager] JPEG编码失败: {e}")
        
        return None
    
    def register_callback(self, callback: Callable[[CameraFrame], None]):
        """注册帧回调"""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[CameraFrame], None]):
        """注销帧回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_frame(self, channel: str) -> Optional[np.ndarray]:
        """兼容接口 - 同 get_latest_frame"""
        return self.get_latest_frame(channel)
