"""
视频播放器管理器
===============
统一管理所有视频播放器，避免全局实例冲突

这是唯一的视频播放器入口，所有其他播放器（DualModePlayer、SimpleVideoPlayer）
都通过这个管理器访问。
"""

import threading
import time
from typing import Optional, Dict, Callable, Tuple
from pathlib import Path


class VideoPlayerManager:
    """
    视频播放器管理器（单例）
    
    职责:
    1. 统一管理视频播放器实例
    2. 确保只有一个播放器在运行
    3. 提供统一的播放控制接口
    4. 处理场景切换时的资源清理
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._player = None
        self._player_type = None  # 'preprocessed' 或 'realtime'
        self._current_folder = None
        self._fps = 10
        self._is_playing = False
        self._current_frame = 0
        
        # 状态回调
        self._status_callbacks: list = []
        
        # 帧获取线程
        self._frame_thread = None
        self._stop_event = threading.Event()
        
        print("[VideoPlayerManager] 初始化完成")
    
    def setup_preprocessed(self, folder: str, fps: int = 10) -> bool:
        """设置预处理模式播放器"""
        # 清理旧播放器
        self._cleanup()
        
        try:
            from .dual_mode_player import DualModePlayer
            
            self._player = DualModePlayer.use_preprocessed(folder, fps)
            self._player_type = 'preprocessed'
            self._current_folder = folder
            self._fps = fps
            
            if not self._player.open():
                print(f"[VideoPlayerManager] 无法打开视频文件")
                self._cleanup()
                return False
            
            print(f"[VideoPlayerManager] 预处理模式已设置: {folder}, {fps}fps")
            self._notify_status_change('ready', {'folder': folder, 'fps': fps})
            return True
            
        except Exception as e:
            print(f"[VideoPlayerManager] 设置预处理模式失败: {e}")
            import traceback
            traceback.print_exc()
            self._cleanup()
            return False
    
    def setup_realtime(self, video_files: Dict[str, str], fps: int = 10, 
                       enable_correction: bool = False) -> bool:
        """设置实时处理模式播放器"""
        self._cleanup()
        
        try:
            from .dual_mode_player import DualModePlayer
            
            self._player = DualModePlayer.use_realtime(
                video_files=video_files,
                fps=fps,
                enable_correction=enable_correction
            )
            self._player_type = 'realtime'
            self._fps = fps
            
            if not self._player.open():
                print(f"[VideoPlayerManager] 无法打开视频文件")
                self._cleanup()
                return False
            
            print(f"[VideoPlayerManager] 实时模式已设置, {fps}fps")
            self._notify_status_change('ready', {'fps': fps})
            return True
            
        except Exception as e:
            print(f"[VideoPlayerManager] 设置实时模式失败: {e}")
            self._cleanup()
            return False
    
    def play(self) -> bool:
        """开始播放"""
        if self._player is None:
            print("[VideoPlayerManager] 播放器未初始化")
            return False
        
        try:
            self._player.play()
            self._is_playing = True
            self._start_frame_updater()
            self._notify_status_change('playing', {})
            return True
        except Exception as e:
            print(f"[VideoPlayerManager] 播放失败: {e}")
            return False
    
    def pause(self) -> bool:
        """暂停播放"""
        if self._player is None:
            return False
        
        try:
            self._player.pause()
            self._is_playing = False
            self._stop_frame_updater()
            self._notify_status_change('paused', {})
            return True
        except Exception as e:
            print(f"[VideoPlayerManager] 暂停失败: {e}")
            return False
    
    def stop(self) -> bool:
        """停止播放"""
        if self._player is None:
            return False
        
        try:
            self._player.stop()
            self._is_playing = False
            self._current_frame = 0
            self._stop_frame_updater()
            self._notify_status_change('stopped', {})
            return True
        except Exception as e:
            print(f"[VideoPlayerManager] 停止失败: {e}")
            return False
    
    def get_frame_jpeg(self, channel: str, quality: int = 85) -> Optional[bytes]:
        """获取当前帧的JPEG数据"""
        if self._player is None:
            return None
        
        try:
            return self._player.get_frame_jpeg(channel, quality)
        except Exception as e:
            print(f"[VideoPlayerManager] 获取帧失败: {e}")
            return None
    
    def get_synced_frames(self) -> Dict[str, Tuple]:
        """获取同步的三通道帧"""
        if self._player is None:
            return {}
        
        try:
            if hasattr(self._player, 'get_synced_frames'):
                return self._player.get_synced_frames()
            return {}
        except Exception as e:
            print(f"[VideoPlayerManager] 获取同步帧失败: {e}")
            return {}
    
    def get_status(self) -> dict:
        """获取播放器状态"""
        return {
            'initialized': self._player is not None,
            'is_playing': self._is_playing,
            'mode': self._player_type,
            'folder': self._current_folder,
            'fps': self._fps,
            'current_frame': self._current_frame
        }
    
    def register_status_callback(self, callback: Callable[[str, dict], None]):
        """注册状态变化回调"""
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable[[str, dict], None]):
        """取消注册状态变化回调"""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    def _notify_status_change(self, status: str, data: dict):
        """通知状态变化"""
        for callback in self._status_callbacks:
            try:
                callback(status, data)
            except Exception as e:
                print(f"[VideoPlayerManager] 回调错误: {e}")
    
    def _start_frame_updater(self):
        """启动帧号更新线程"""
        self._stop_frame_updater()
        self._stop_event.clear()
        
        def update_frame():
            while not self._stop_event.is_set():
                if self._player and hasattr(self._player, 'current_frame'):
                    self._current_frame = self._player.current_frame
                time.sleep(0.1)
        
        self._frame_thread = threading.Thread(target=update_frame, daemon=True)
        self._frame_thread.start()
    
    def _stop_frame_updater(self):
        """停止帧号更新线程"""
        if self._frame_thread:
            self._stop_event.set()
            self._frame_thread.join(timeout=0.5)
            self._frame_thread = None
    
    def _cleanup(self):
        """清理资源"""
        self._stop_frame_updater()
        
        if self._player is not None:
            try:
                self._player.stop()
            except:
                pass
            self._player = None
        
        self._player_type = None
        self._current_folder = None
        self._is_playing = False
        self._current_frame = 0
    
    def reset(self):
        """完全重置管理器"""
        self._cleanup()
        self._status_callbacks.clear()
        print("[VideoPlayerManager] 已重置")


# 全局实例函数
def get_player_manager() -> VideoPlayerManager:
    """获取播放器管理器实例"""
    return VideoPlayerManager()


def reset_player_manager():
    """重置播放器管理器"""
    manager = VideoPlayerManager()
    manager.reset()
