"""
视频录制管理模块 V2
==================
支持自动间隔录制和手动录制，优化目录结构和显示控制

功能：
1. 自动录制：按设定间隔自动录制，目录结构为 根目录/时间戳/CH1,CH2,CH3/
2. 手动录制：用户控制开始/停止，用于制作测试样本
3. 显示控制：录制时可暂停实时流以节省带宽
4. 目录持久化：保存上次使用的目录，默认 F:/test/recordings/
"""

import cv2
import numpy as np
import threading
import time
import os
import json
from datetime import datetime
from typing import Dict, Optional, Callable, List
from pathlib import Path
import queue
from enum import Enum

# 默认录制目录
DEFAULT_SAVE_DIR = "F:/test/recordings"
# 配置文件路径（保存上次使用的目录）
CONFIG_FILE = Path(__file__).parent / ".recorder_config.json"


def load_saved_directory() -> str:
    """加载保存的目录，如果不存在则返回默认目录"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                saved_dir = config.get('save_directory', DEFAULT_SAVE_DIR)
                # 检查盘符是否存在
                drive = Path(saved_dir).drive
                if drive and not os.path.exists(drive + '\\'):
                    print(f"[VideoRecorderV2] 警告: 盘符 {drive} 不存在，使用默认目录")
                    return DEFAULT_SAVE_DIR
                return saved_dir
    except Exception as e:
        print(f"[VideoRecorderV2] 加载配置失败: {e}")
    return DEFAULT_SAVE_DIR


def save_directory(save_dir: str):
    """保存目录配置"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'save_directory': save_dir}, f)
    except Exception as e:
        print(f"[VideoRecorderV2] 保存配置失败: {e}")


def check_drive_exists(path: str) -> bool:
    """检查盘符是否存在
    
    Args:
        path: 路径字符串
        
    Returns:
        bool: 盘符是否存在
    """
    try:
        p = Path(path)
        drive = p.drive
        if drive:
            return os.path.exists(drive + '\\')
        # 没有盘符（相对路径）认为有效
        return True
    except:
        return False


def validate_and_create_directory(path: str) -> tuple[bool, str]:
    """验证并创建目录
    
    Args:
        path: 目录路径
        
    Returns:
        (success, message): 是否成功，错误信息
    """
    try:
        p = Path(path)
        
        # 检查盘符
        drive = p.drive
        if drive and not os.path.exists(drive + '\\'):
            return False, f"盘符 {drive} 不存在"
        
        # 创建目录
        p.mkdir(parents=True, exist_ok=True)
        
        # 验证是否可写
        test_file = p / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            return False, f"目录不可写: {e}"
        
        return True, "OK"
        
    except Exception as e:
        return False, f"创建目录失败: {e}"


class RecordingMode(Enum):
    """录制模式"""
    AUTO = "auto"       # 自动间隔录制
    MANUAL = "manual"   # 手动录制
    IDLE = "idle"       # 空闲


class VideoRecorderV2:
    """视频录制管理器 V2
    
    目录结构：
    save_dir/
        YYYYMMDD_HHMMSS/          <- 录制会话（自动录制每次间隔创建新会话）
            CH1/
                clip_001.mp4
                clip_002.mp4
            CH2/
                clip_001.mp4
            CH3/
                clip_001.mp4
        manual_YYYYMMDD_HHMMSS/   <- 手动录制会话
            CH1/
            CH2/
            CH3/
    """
    
    def __init__(self, save_dir: str = None):
        # 使用保存的目录或默认目录
        self._save_dir = save_dir or load_saved_directory()
        
        # 验证并创建目录
        success, msg = validate_and_create_directory(self._save_dir)
        if not success:
            print(f"[VideoRecorderV2] 警告: {msg}，使用默认目录")
            self._save_dir = DEFAULT_SAVE_DIR
            success, msg = validate_and_create_directory(self._save_dir)
            if not success:
                raise RuntimeError(f"无法创建默认目录: {msg}")
        
        self.base_save_dir = Path(self._save_dir)
        print(f"[VideoRecorderV2] 使用保存目录: {self.base_save_dir}")
        
        # 录制配置
        self.interval_seconds = 30  # 自动录制间隔
        self.clip_duration = 5      # 每个视频片段长度（秒）
        self.fps = 10               # 视频帧率
        self.resolution = (640, 480)
        
        # 录制状态
        self.mode = RecordingMode.IDLE
        self.is_recording = False
        self.current_session_dir: Optional[Path] = None
        self._recording_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 手动录制专用
        self._manual_recording = False
        self._manual_start_time: Optional[float] = None
        self._manual_clip_count = 0
        
        # 帧缓冲区
        buffer_size = self.fps * self.clip_duration * 3
        self._frame_buffers: Dict[str, queue.Queue] = {
            'CH1': queue.Queue(maxsize=buffer_size),
            'CH2': queue.Queue(maxsize=buffer_size),
            'CH3': queue.Queue(maxsize=buffer_size)
        }
        
        # 回调函数
        self._frame_callbacks: Dict[str, Callable[[], np.ndarray]] = {}
        
        # 录制历史
        self._recording_history: List[Dict] = []
        
        # 显示控制回调
        self._display_pause_callback: Optional[Callable[[bool], None]] = None
        
        # 锁
        self._lock = threading.Lock()
        
        print(f"[VideoRecorderV2] 初始化完成，保存目录: {self.base_save_dir}")
    
    def _check_directory(self) -> tuple[bool, str]:
        """检查录制目录是否有效
        
        Returns:
            (success, message): 是否有效，错误信息
        """
        # 检查盘符
        if not check_drive_exists(str(self.base_save_dir)):
            drive = self.base_save_dir.drive
            return False, f"盘符 {drive} 不存在"
        
        # 检查目录是否存在，不存在则创建
        success, msg = validate_and_create_directory(str(self.base_save_dir))
        if not success:
            return False, msg
        
        return True, "OK"
    
    def set_save_directory(self, save_dir: str) -> dict:
        """设置保存目录
        
        Args:
            save_dir: 新的保存目录路径
            
        Returns:
            dict: {'success': bool, 'message': str, 'path': str}
        """
        # 检查盘符
        if not check_drive_exists(save_dir):
            drive = Path(save_dir).drive
            return {
                'success': False,
                'message': f'盘符 {drive} 不存在',
                'path': str(self.base_save_dir)
            }
        
        # 验证并创建目录
        success, msg = validate_and_create_directory(save_dir)
        if not success:
            return {
                'success': False,
                'message': msg,
                'path': str(self.base_save_dir)
            }
        
        try:
            path = Path(save_dir)
            with self._lock:
                self.base_save_dir = path
                self._save_dir = str(path)
            
            # 持久化保存
            save_directory(str(path))
            
            print(f"[VideoRecorderV2] 保存目录已更改: {self.base_save_dir}")
            return {
                'success': True,
                'message': '目录设置成功',
                'path': str(self.base_save_dir)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'设置目录失败: {e}',
                'path': str(self.base_save_dir)
            }
    
    def get_save_directory(self) -> str:
        """获取当前保存目录"""
        return str(self.base_save_dir)
    
    def set_interval(self, interval_seconds: int):
        """设置录制间隔"""
        self.interval_seconds = max(10, min(60, interval_seconds))
        print(f"[VideoRecorderV2] 录制间隔设置为: {self.interval_seconds}秒")
    
    def set_clip_duration(self, duration: int):
        """设置视频片段长度"""
        self.clip_duration = max(3, min(10, duration))
        print(f"[VideoRecorderV2] 视频长度设置为: {self.clip_duration}秒")
    
    def register_frame_callback(self, channel: str, callback: Callable[[], np.ndarray]):
        """注册帧获取回调"""
        self._frame_callbacks[channel] = callback
        print(f"[VideoRecorderV2] 已注册 {channel} 帧回调")
    
    def register_display_pause_callback(self, callback: Callable[[bool], None]):
        """注册显示暂停回调
        
        Args:
            callback: 回调函数，参数为 True=暂停显示, False=恢复显示
        """
        self._display_pause_callback = callback
        print("[VideoRecorderV2] 已注册显示控制回调")
    
    def _pause_display(self, pause: bool):
        """暂停/恢复显示"""
        if self._display_pause_callback:
            try:
                self._display_pause_callback(pause)
                print(f"[VideoRecorderV2] 显示已{'暂停' if pause else '恢复'}")
            except Exception as e:
                print(f"[VideoRecorderV2] 显示控制回调错误: {e}")
    
    def _create_session_dir(self, prefix: str = "") -> Path:
        """创建录制会话目录
        
        Returns:
            创建的会话目录路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if prefix:
            session_name = f"{prefix}_{timestamp}"
        else:
            session_name = timestamp
        
        session_dir = self.base_save_dir / session_name
        
        # 创建CH1, CH2, CH3子目录
        for ch in ['CH1', 'CH2', 'CH3']:
            (session_dir / ch).mkdir(parents=True, exist_ok=True)
        
        print(f"[VideoRecorderV2] 创建会话目录: {session_dir}")
        return session_dir
    
    def start_auto_recording(self) -> dict:
        """开始自动录制
        
        按设定的间隔自动录制视频片段
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        if self.is_recording:
            return {'success': False, 'message': '已经在录制中'}
        
        # 检查目录
        success, msg = self._check_directory()
        if not success:
            return {'success': False, 'message': msg}
        
        with self._lock:
            self.mode = RecordingMode.AUTO
            self.is_recording = True
            self._stop_event.clear()
            self.current_session_dir = self._create_session_dir()
        
        self._recording_thread = threading.Thread(target=self._auto_recording_loop)
        self._recording_thread.daemon = True
        self._recording_thread.start()
        
        print(f"[VideoRecorderV2] 自动录制已启动，间隔: {self.interval_seconds}秒")
        return {'success': True, 'message': '自动录制已启动'}
    
    def start_manual_recording(self) -> dict:
        """开始手动录制
        
        用户控制开始和停止，用于制作测试样本
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        if self.is_recording:
            return {'success': False, 'message': '已经在录制中'}
        
        # 检查目录
        success, msg = self._check_directory()
        if not success:
            return {'success': False, 'message': msg}
        
        # 清空之前的帧缓冲区
        for ch in ['CH1', 'CH2', 'CH3']:
            buffer = self._frame_buffers[ch]
            while not buffer.empty():
                try:
                    buffer.get_nowait()
                except queue.Empty:
                    break
        
        with self._lock:
            self.mode = RecordingMode.MANUAL
            self.is_recording = True
            self._manual_recording = True
            self._manual_start_time = time.time()
            self._manual_clip_count = 0
            self._stop_event.clear()
            self.current_session_dir = self._create_session_dir("manual")
        
        self._recording_thread = threading.Thread(target=self._manual_recording_loop)
        self._recording_thread.daemon = True
        self._recording_thread.start()
        
        # 暂停实时显示以节省带宽
        self._pause_display(True)
        
        print(f"[VideoRecorderV2] 手动录制已启动，保存目录: {self.current_session_dir}")
        print(f"[VideoRecorderV2] 已注册回调: {list(self._frame_callbacks.keys())}")
        return {'success': True, 'message': '手动录制已启动'}
    
    def stop_recording(self) -> Dict:
        """停止录制
        
        Returns:
            录制会话信息
        """
        if not self.is_recording:
            return {"success": False, "message": "未在录制中"}
        
        print("[VideoRecorderV2] 停止录制...")
        self._stop_event.set()
        self._manual_recording = False
        
        # 等待录制线程结束（给足够时间保存最后片段）
        if self._recording_thread and self._recording_thread.is_alive():
            print("[VideoRecorderV2] 等待录制线程结束...")
            self._recording_thread.join(timeout=10.0)
            if self._recording_thread.is_alive():
                print("[VideoRecorderV2] 警告: 录制线程未在10秒内结束")
        
        self.is_recording = False
        
        # 恢复实时显示
        self._pause_display(False)
        
        session_info = {
            "success": True,
            "mode": self.mode.value,
            "session_dir": str(self.current_session_dir) if self.current_session_dir else None,
            "duration": time.time() - self._manual_start_time if self._manual_start_time else 0,
            "clip_count": self._manual_clip_count
        }
        
        with self._lock:
            self.mode = RecordingMode.IDLE
            self.current_session_dir = None
            self._manual_start_time = None
        
        print(f"[VideoRecorderV2] 录制已停止，共 {session_info['clip_count']} 个片段")
        return session_info
    
    def _auto_recording_loop(self):
        """自动录制主循环"""
        last_record_time = time.time()
        frame_interval = 1.0 / self.fps
        clip_counter = 0
        
        print(f"[VideoRecorderV2] 自动录制循环启动")
        
        while not self._stop_event.is_set():
            loop_start = time.time()
            
            try:
                current_time = time.time()
                
                # 检查是否到达录制间隔
                if current_time - last_record_time >= self.interval_seconds:
                    last_record_time = current_time
                    clip_counter += 1
                    # 保存当前缓冲区的视频
                    self._save_video_clips(f"clip_{clip_counter:03d}")
                    
                    # 每10个片段创建新会话目录（避免单个目录文件过多）
                    if clip_counter % 10 == 0:
                        with self._lock:
                            self.current_session_dir = self._create_session_dir()
                
                # 采集帧
                for channel, callback in self._frame_callbacks.items():
                    try:
                        frame = callback()
                        if frame is not None:
                            self._add_frame(channel, frame)
                    except:
                        pass
                
                # 控制帧率
                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                print(f"[VideoRecorderV2] 自动录制循环异常: {e}")
                time.sleep(0.1)
        
        # 停止前保存剩余帧
        if clip_counter > 0:
            self._save_video_clips(f"clip_{clip_counter:03d}")
        
        print("[VideoRecorderV2] 自动录制循环结束")
    
    def _manual_recording_loop(self):
        """手动录制主循环"""
        frame_interval = 1.0 / self.fps
        clip_start_time = time.time()
        current_clip_index = 1
        frame_count = {ch: 0 for ch in ['CH1', 'CH2', 'CH3']}
        last_log_time = time.time()
        
        print(f"[VideoRecorderV2] 手动录制循环启动，目标帧率: {self.fps}fps，片段长度: {self.clip_duration}s")
        print(f"[VideoRecorderV2] 已注册的回调: {list(self._frame_callbacks.keys())}")
        
        while not self._stop_event.is_set() and self._manual_recording:
            loop_start = time.time()
            
            try:
                current_time = time.time()
                
                # 检查是否需要切分片段（达到设定长度）
                if current_time - clip_start_time >= self.clip_duration:
                    print(f"[VideoRecorderV2] 片段 {current_clip_index} 时间到，准备保存...")
                    self._save_video_clips(f"clip_{current_clip_index:03d}")
                    current_clip_index += 1
                    self._manual_clip_count += 1
                    clip_start_time = current_time
                    frame_count = {ch: 0 for ch in ['CH1', 'CH2', 'CH3']}  # 重置计数
                
                # 采集帧
                for channel, callback in self._frame_callbacks.items():
                    try:
                        frame = callback()
                        if frame is not None:
                            self._add_frame(channel, frame)
                            frame_count[channel] = frame_count.get(channel, 0) + 1
                        else:
                            print(f"[VideoRecorderV2] {channel} 回调返回 None")
                    except Exception as e:
                        print(f"[VideoRecorderV2] {channel} 回调异常: {e}")
                
                # 每秒打印一次帧采集统计
                if current_time - last_log_time >= 1.0:
                    total = sum(frame_count.values())
                    print(f"[VideoRecorderV2] 已采集帧数: CH1={frame_count.get('CH1',0)}, CH2={frame_count.get('CH2',0)}, CH3={frame_count.get('CH3',0)}, 总计={total}")
                    last_log_time = current_time
                
                # 控制帧率
                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                print(f"[VideoRecorderV2] 手动录制循环异常: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
        
        print(f"[VideoRecorderV2] 录制结束，保存最后一个片段 (clip_{current_clip_index:03d})...")
        print(f"[VideoRecorderV2] 当前缓冲区状态: CH1={self._frame_buffers['CH1'].qsize()}, CH2={self._frame_buffers['CH2'].qsize()}, CH3={self._frame_buffers['CH3'].qsize()}")
        
        # 停止前保存最后一个片段
        self._save_video_clips(f"clip_{current_clip_index:03d}")
        self._manual_clip_count += 1
        
        print(f"[VideoRecorderV2] 手动录制循环结束，共保存 {self._manual_clip_count} 个片段")
    
    def _add_frame(self, channel: str, frame: np.ndarray):
        """添加帧到缓冲区"""
        if channel in self._frame_buffers and frame is not None:
            buffer = self._frame_buffers[channel]
            try:
                if buffer.full():
                    try:
                        buffer.get_nowait()
                    except queue.Empty:
                        pass
                buffer.put_nowait(frame.copy())
            except Exception as e:
                print(f"[VideoRecorderV2] 添加帧到缓冲区失败 {channel}: {e}")
    
    def _save_video_clips(self, filename_prefix: str):
        """保存视频片段到当前会话目录"""
        if not self.current_session_dir:
            print(f"[VideoRecorderV2] 警告: 当前会话目录为空，无法保存")
            return
        
        print(f"[VideoRecorderV2] 开始保存视频片段: {filename_prefix}")
        
        for channel in ['CH1', 'CH2', 'CH3']:
            # 构建文件路径
            channel_dir = self.current_session_dir / channel
            filepath = channel_dir / f"{filename_prefix}.mp4"
            
            # 获取帧
            frames = self._get_frames_from_buffer(channel)
            
            if len(frames) > 0:
                print(f"[VideoRecorderV2] {channel} 缓冲区有 {len(frames)} 帧，开始保存...")
                # 打印第一帧信息用于调试
                first_frame = frames[0]
                print(f"[VideoRecorderV2] {channel} 帧信息: shape={first_frame.shape}, dtype={first_frame.dtype}")
                
                success = self._save_video_file(filepath, frames)
                if success:
                    self._recording_history.append({
                        'channel': channel,
                        'filepath': str(filepath),
                        'filename': f"{filename_prefix}.mp4",
                        'session': self.current_session_dir.name,
                        'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                        'duration': self.clip_duration,
                        'frame_count': len(frames),
                        'mode': self.mode.value
                    })
                    print(f"[VideoRecorderV2] 已保存 {channel}: {filepath}")
                else:
                    print(f"[VideoRecorderV2] 保存失败 {channel}: {filepath}")
            else:
                print(f"[VideoRecorderV2] {channel} 缓冲区为空，跳过保存")
    
    def _get_frames_from_buffer(self, channel: str) -> List[np.ndarray]:
        """从缓冲区获取帧"""
        frames = []
        buffer = self._frame_buffers[channel]
        
        frames_needed = self.fps * self.clip_duration
        temp_frames = []
        
        while not buffer.empty() and len(temp_frames) < frames_needed * 2:
            try:
                frame = buffer.get_nowait()
                temp_frames.append(frame)
            except queue.Empty:
                break
        
        frames = temp_frames[-frames_needed:] if len(temp_frames) > frames_needed else temp_frames
        
        if len(temp_frames) > frames_needed:
            for frame in temp_frames[:-frames_needed]:
                try:
                    buffer.put_nowait(frame)
                except queue.Full:
                    break
        
        return frames
    
    def _save_video_file(self, filepath: Path, frames: List[np.ndarray]) -> bool:
        """保存视频文件"""
        if not frames:
            return False
        
        try:
            height, width = frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(filepath), fourcc, self.fps, (width, height))
            
            if not out.isOpened():
                print(f"[VideoRecorderV2] 无法创建视频文件: {filepath}")
                return False
            
            frame_count = 0
            for frame in frames:
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    # 将 RGB 转换为 BGR (OpenCV VideoWriter 需要 BGR)
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    out.write(frame_bgr)
                    frame_count += 1
            
            out.release()
            print(f"[VideoRecorderV2] 已写入 {frame_count} 帧到 {filepath.name}")
            return frame_count > 0
            
        except Exception as e:
            print(f"[VideoRecorderV2] 保存视频失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_recording_history(self, limit: int = 50, mode: str = None) -> List[Dict]:
        """获取录制历史
        
        Args:
            limit: 返回记录数量限制
            mode: 按模式过滤 ('auto', 'manual', None表示全部)
        """
        history = self._recording_history
        if mode:
            history = [h for h in history if h.get('mode') == mode]
        return history[-limit:]
    
    def get_status(self) -> Dict:
        """获取录制器状态"""
        with self._lock:
            return {
                'is_recording': self.is_recording,
                'mode': self.mode.value,
                'save_directory': str(self.base_save_dir),
                'current_session': str(self.current_session_dir) if self.current_session_dir else None,
                'interval_seconds': self.interval_seconds,
                'clip_duration': self.clip_duration,
                'fps': self.fps,
                'history_count': len(self._recording_history),
                'manual_info': {
                    'duration': time.time() - self._manual_start_time if self._manual_start_time else 0,
                    'clip_count': self._manual_clip_count
                } if self.mode == RecordingMode.MANUAL else None
            }
    
    def clear_history(self):
        """清空录制历史"""
        self._recording_history.clear()


# 单例实例
_video_recorder_v2: Optional[VideoRecorderV2] = None


def get_video_recorder_v2(save_dir: str = None) -> VideoRecorderV2:
    """获取视频录制器实例（单例）"""
    global _video_recorder_v2
    if _video_recorder_v2 is None:
        _video_recorder_v2 = VideoRecorderV2(save_dir or "./recordings")
    return _video_recorder_v2
