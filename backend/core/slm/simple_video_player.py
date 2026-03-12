"""
简化视频播放器 - 用于向后兼容
如果双模式播放器未初始化，使用此播放器
"""

import cv2
import numpy as np
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple


class SimpleVideoPlayer:
    """
    简化视频播放器
    - 仅播放预处理后的视频（无实时计算）
    - 三通道同步播放
    - 低CPU/GPU占用
    """
    
    def __init__(self, video_files: Dict[str, str], fps: int = 10):
        self.video_files = video_files
        self.fps = fps
        self._captures: Dict[str, cv2.VideoCapture] = {}
        self._current_frames: Dict[str, np.ndarray] = {}
        self._frame_numbers: Dict[str, int] = {}
        
        self.is_playing = False
        self._stop_event = threading.Event()
        self._play_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
    def open(self) -> bool:
        """打开所有视频文件"""
        for channel, path in self.video_files.items():
            cap = cv2.VideoCapture(path)
            if cap.isOpened():
                self._captures[channel] = cap
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                print(f"[SimplePlayer] {channel}: {path} ({total_frames}帧)")
            else:
                print(f"[SimplePlayer] 警告: 无法打开 {path}")
        
        return len(self._captures) > 0
    
    def play(self):
        """开始播放"""
        if self.is_playing:
            return
        
        self.is_playing = True
        self._stop_event.clear()
        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()
        print("[SimplePlayer] 开始播放")
    
    def pause(self):
        """暂停播放"""
        self.is_playing = False
        print("[SimplePlayer] 暂停")
    
    def stop(self):
        """停止播放"""
        self.is_playing = False
        self._stop_event.set()
        
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=1.0)
        
        for cap in self._captures.values():
            cap.release()
        self._captures.clear()
        
        print("[SimplePlayer] 停止")
    
    def _play_loop(self):
        """播放循环 - 简单轮询，无实时计算"""
        frame_interval = 1.0 / self.fps
        last_time = time.time()
        
        while not self._stop_event.is_set():
            if not self.is_playing:
                time.sleep(0.01)
                continue
            
            # 控制帧率
            current_time = time.time()
            elapsed = current_time - last_time
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)
                continue
            
            last_time = current_time
            
            # 读取帧（无处理，直接读取）
            with self._lock:
                for channel, cap in list(self._captures.items()):
                    ret, frame = cap.read()
                    
                    if not ret:
                        # 循环播放
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                    
                    if ret:
                        self._current_frames[channel] = frame
                        self._frame_numbers[channel] = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    
    def get_frame(self, channel: str) -> Optional[np.ndarray]:
        """获取当前帧"""
        with self._lock:
            return self._current_frames.get(channel)
    
    def get_frame_jpeg(self, channel: str, quality: int = 85) -> Optional[bytes]:
        """获取当前帧的JPEG数据"""
        frame = self.get_frame(channel)
        if frame is None:
            return None
        
        ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return jpeg.tobytes() if ret else None
    
    def get_synced_frames(self) -> Dict[str, Tuple[np.ndarray, int]]:
        """获取同步的三通道帧"""
        result = {}
        with self._lock:
            for channel, frame in self._current_frames.items():
                frame_num = self._frame_numbers.get(channel, 0)
                result[channel] = (frame, frame_num)
        return result


# 全局实例
_player_instance: Optional[SimpleVideoPlayer] = None


def init_video_player(video_files: Dict[str, str], fps: int = 10) -> SimpleVideoPlayer:
    """初始化视频播放器"""
    global _player_instance
    
    # 停止旧实例
    if _player_instance:
        _player_instance.stop()
    
    _player_instance = SimpleVideoPlayer(video_files, fps)
    _player_instance.open()
    return _player_instance


def get_video_player() -> Optional[SimpleVideoPlayer]:
    """获取当前播放器实例"""
    return _player_instance


def stop_video_player():
    """停止播放器"""
    global _player_instance
    if _player_instance:
        _player_instance.stop()
        _player_instance = None
