"""
双模式视频播放器
支持两种模式：
1. 预处理模式：使用提前处理好的视频，流畅播放，无实时计算
2. 实时模式：实时畸变矫正，可调参数

用法:
    # 模式1: 预处理视频（推荐用于演示）
    player = DualModePlayer.use_preprocessed('normal', fps=10)
    
    # 模式2: 实时处理（用于调试/标定）
    player = DualModePlayer.use_realtime(video_files, fps=10, enable_correction=True)
"""

import cv2
import numpy as np
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Callable, Tuple
from dataclasses import dataclass


@dataclass
class PlayerConfig:
    """播放器配置"""
    mode: str = 'preprocessed'  # 'preprocessed' 或 'realtime'
    fps: int = 10
    enable_correction: bool = False  # 实时模式才需要
    calibration_file: Optional[str] = None


class DualModePlayer:
    """
    双模式视频播放器
    
    模式1 - 预处理 (推荐):
        - 使用 preprocess_videos.py 生成的视频
        - 零实时计算，流畅播放
        - 适合正式演示
    
    模式2 - 实时处理:
        - 实时畸变矫正和视角调整
        - 可调参数
        - 适合调试和标定
    """
    
    def __init__(self, config: PlayerConfig):
        self.config = config
        self.video_files: Dict[str, str] = {}
        self._captures: Dict[str, cv2.VideoCapture] = {}
        
        # 播放状态
        self.is_playing = False
        self._stop_event = threading.Event()
        self._play_thread: Optional[threading.Thread] = None
        
        # 当前帧号（三通道统一）
        self.current_frame = 0
        self._frame_lock = threading.Lock()
        
        # 回调
        self._frame_callbacks: Dict[str, Callable] = {}
        
        # 实时模式用的矫正器
        self._corrector = None
        if config.mode == 'realtime' and config.enable_correction:
            from .distortion_corrector import get_distortion_corrector
            self._corrector = get_distortion_corrector(config.calibration_file)
        
        print(f"[DualModePlayer] 模式: {config.mode}, FPS: {config.fps}")
    
    @classmethod
    def use_preprocessed(cls, scene_name: str, fps: int = 10) -> 'DualModePlayer':
        """
        使用预处理视频（推荐模式）
        
        Args:
            scene_name: 场景名称 (如 'normal', 'scene_underpower')
            fps: 播放帧率
        
        Returns:
            配置好的播放器实例
        """
        # 查找项目根目录
        script_dir = Path(__file__).parent.parent.parent
        processed_dir = script_dir / "simulation_record" / f"{scene_name}_processed"
        
        config = PlayerConfig(mode='preprocessed', fps=fps)
        player = cls(config)
        
        # 查找预处理后的视频
        channel_map = {
            'CH1': 'CH1_processed.mp4',
            'CH2': 'CH2_processed.mp4',
            'CH3': 'CH3_processed.mp4'
        }
        
        for channel, filename in channel_map.items():
            video_path = processed_dir / filename
            if video_path.exists():
                player.video_files[channel] = str(video_path)
                print(f"[DualModePlayer] {channel}: {video_path}")
            else:
                # 回退到原始视频
                original_dir = script_dir / "simulation_record" / scene_name
                for pattern in [f'{channel}*.mp4', f'{channel.lower()}*.mp4']:
                    files = list(original_dir.glob(pattern))
                    if files:
                        player.video_files[channel] = str(files[0])
                        print(f"[DualModePlayer] {channel}: 使用原始视频 {files[0]}")
                        break
        
        return player
    
    @classmethod
    def use_realtime(cls, video_files: Dict[str, str], fps: int = 10,
                     enable_correction: bool = True,
                     calibration_file: Optional[str] = None) -> 'DualModePlayer':
        """
        使用实时处理模式
        
        Args:
            video_files: {'CH1': 'path/to/ch1.mp4', ...}
            fps: 播放帧率
            enable_correction: 是否启用畸变矫正
            calibration_file: 标定文件路径
        
        Returns:
            配置好的播放器实例
        """
        config = PlayerConfig(
            mode='realtime',
            fps=fps,
            enable_correction=enable_correction,
            calibration_file=calibration_file
        )
        player = cls(config)
        player.video_files = video_files
        
        print(f"[DualModePlayer] 实时模式，视频: {list(video_files.keys())}")
        return player
    
    def open(self) -> bool:
        """打开所有视频文件"""
        for channel, path in self.video_files.items():
            cap = cv2.VideoCapture(path)
            if cap.isOpened():
                self._captures[channel] = cap
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                print(f"[DualModePlayer] {channel}: {total_frames}帧 @ {fps:.1f}fps")
            else:
                print(f"[DualModePlayer] 警告: 无法打开 {path}")
        
        return len(self._captures) > 0
    
    def set_fps(self, fps: int):
        """设置播放帧率"""
        self.config.fps = max(1, min(60, fps))
        print(f"[DualModePlayer] FPS: {self.config.fps}")
    
    def register_callback(self, channel: str, callback: Callable[[np.ndarray, int], None]):
        """注册帧回调"""
        self._frame_callbacks[channel] = callback
    
    def play(self):
        """开始播放"""
        if self.is_playing:
            return
        
        self.is_playing = True
        self._stop_event.clear()
        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()
        print("[DualModePlayer] 开始播放")
    
    def pause(self):
        """暂停播放"""
        self.is_playing = False
        print("[DualModePlayer] 暂停")
    
    def stop(self):
        """停止播放"""
        self.is_playing = False
        self._stop_event.set()
        
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=1.0)
        
        for cap in self._captures.values():
            cap.release()
        self._captures.clear()
        
        print("[DualModePlayer] 停止")
    
    def seek(self, frame_number: int):
        """跳转到指定帧"""
        with self._frame_lock:
            self.current_frame = frame_number
            for cap in self._captures.values():
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    
    def _process_frame(self, frame: np.ndarray, channel: str) -> np.ndarray:
        """处理单帧（仅实时模式）"""
        if self.config.mode == 'preprocessed':
            # 预处理模式：直接返回，无需计算
            return frame
        
        # 实时模式：应用畸变矫正
        if self._corrector and self.config.enable_correction:
            # 这里调用畸变矫正逻辑
            # 简化示例：实际应该调用corrector的方法
            pass
        
        return frame
    
    def _play_loop(self):
        """播放循环"""
        frame_interval = 1.0 / self.config.fps
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
            
            # 读取并处理帧
            with self._frame_lock:
                frame_num = self.current_frame
                
                for channel, cap in self._captures.items():
                    ret, frame = cap.read()
                    
                    if not ret:
                        # 循环播放
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                        if not ret:
                            continue
                    
                    # 处理帧（仅实时模式有计算）
                    processed_frame = self._process_frame(frame, channel)
                    
                    # 回调
                    if channel in self._frame_callbacks:
                        try:
                            self._frame_callbacks[channel](processed_frame, frame_num)
                        except Exception as e:
                            print(f"[DualModePlayer] 回调错误: {e}")
                
                self.current_frame += 1
    
    def get_frame_jpeg(self, channel: str, quality: int = 85) -> Optional[bytes]:
        """获取当前帧的JPEG数据（用于HTTP流）"""
        if channel not in self._captures:
            return None
        
        cap = self._captures[channel]
        ret, frame = cap.read()
        
        if not ret:
            # 循环播放
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                return None
        
        # 处理帧（仅实时模式）
        processed = self._process_frame(frame, channel)
        
        # 编码为JPEG
        ret, jpeg = cv2.imencode('.jpg', processed, [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        if ret:
            return jpeg.tobytes()
        
        return None
    
    def get_synced_frames(self) -> Dict[str, Tuple[np.ndarray, int]]:
        """获取同步的三通道帧"""
        result = {}
        frame_num = self.current_frame
        
        for channel, cap in self._captures.items():
            ret, frame = cap.read()
            if ret:
                processed = self._process_frame(frame, channel)
                result[channel] = (processed, frame_num)
        
        return result


# 全局实例
_player_instance: Optional[DualModePlayer] = None


def init_player(mode: str, **kwargs) -> DualModePlayer:
    """初始化播放器"""
    global _player_instance
    
    # 停止旧实例
    if _player_instance:
        _player_instance.stop()
    
    # 创建新实例
    if mode == 'preprocessed':
        _player_instance = DualModePlayer.use_preprocessed(**kwargs)
    else:
        _player_instance = DualModePlayer.use_realtime(**kwargs)
    
    _player_instance.open()
    return _player_instance


def get_player() -> Optional[DualModePlayer]:
    """获取当前播放器实例"""
    return _player_instance


def stop_player():
    """停止播放器"""
    global _player_instance
    if _player_instance:
        _player_instance.stop()
        _player_instance = None
