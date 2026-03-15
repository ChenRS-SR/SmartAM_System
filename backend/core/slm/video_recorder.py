"""
视频录制管理模块
================
管理CH1、CH2、CH3三个通道的视频录制、保存和回放诊断
"""

import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime
from typing import Dict, Optional, Callable, List
from pathlib import Path
import queue


class VideoRecorder:
    """视频录制管理器 - 与实时显示独立运行，互不干扰
    
    设计特点：
    1. 录制在独立线程中运行，不会阻塞主采集循环
    2. 通过回调函数获取帧，回调函数返回帧的拷贝，不影响原始帧
    3. 使用有界队列作为缓冲区，避免内存无限增长
    4. 视频编码在录制线程中异步执行，不影响实时数据流
    """
    
    def __init__(self, save_dir: str = "./recordings"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # 录制配置
        self.interval_seconds = 30  # 默认30秒间隔
        self.clip_duration = 5      # 每个视频5秒
        self.fps = 10               # 视频帧率
        self.resolution = (640, 480)  # 视频分辨率
        
        # 录制状态
        self.is_recording = False
        self._recording_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 帧缓冲区（每个通道一个队列）- 使用有界队列防止内存溢出
        # 缓冲区大小 = fps * 视频长度 * 2（留有余量）
        buffer_size = self.fps * self.clip_duration * 2
        self._frame_buffers: Dict[str, queue.Queue] = {
            'CH1': queue.Queue(maxsize=buffer_size),
            'CH2': queue.Queue(maxsize=buffer_size),
            'CH3': queue.Queue(maxsize=buffer_size)
        }
        
        # 回调函数（用于获取实时帧）- 这些回调应该快速返回，避免阻塞
        self._frame_callbacks: Dict[str, Callable[[], np.ndarray]] = {}
        
        # 录制历史记录
        self._recording_history: List[Dict] = []
        
        # 锁
        self._lock = threading.Lock()
        
        print(f"[VideoRecorder] 初始化完成，保存目录: {self.save_dir}")
        print(f"[VideoRecorder] 缓冲区大小: 每通道{buffer_size}帧")
    
    def set_save_directory(self, save_dir: str) -> bool:
        """设置保存目录"""
        try:
            path = Path(save_dir)
            path.mkdir(parents=True, exist_ok=True)
            with self._lock:
                self.save_dir = path
            print(f"[VideoRecorder] 保存目录已更改: {self.save_dir}")
            return True
        except Exception as e:
            print(f"[VideoRecorder] 设置目录失败: {e}")
            return False
    
    def get_save_directory(self) -> str:
        """获取当前保存目录"""
        return str(self.save_dir)
    
    def set_interval(self, interval_seconds: int):
        """设置录制间隔（10-60秒）"""
        self.interval_seconds = max(10, min(60, interval_seconds))
        print(f"[VideoRecorder] 录制间隔设置为: {self.interval_seconds}秒")
    
    def set_clip_duration(self, duration: int):
        """设置每个视频片段长度（秒）"""
        self.clip_duration = max(3, min(10, duration))
        print(f"[VideoRecorder] 视频长度设置为: {self.clip_duration}秒")
    
    def register_frame_callback(self, channel: str, callback: Callable[[], np.ndarray]):
        """注册帧获取回调函数"""
        self._frame_callbacks[channel] = callback
        print(f"[VideoRecorder] 已注册 {channel} 帧回调")
    
    def unregister_frame_callback(self, channel: str):
        """注销帧获取回调函数"""
        if channel in self._frame_callbacks:
            del self._frame_callbacks[channel]
            print(f"[VideoRecorder] 已注销 {channel} 帧回调")
    
    def add_frame(self, channel: str, frame: np.ndarray):
        """添加帧到缓冲区（供外部调用）- 非阻塞，队列满时丢弃旧帧
        
        注意：
        - 此方法被主采集循环调用，必须保持高效
        - 使用 copy() 创建帧的副本，避免影响原始帧
        - 队列满时丢弃最旧帧，确保实时性
        """
        if channel in self._frame_buffers:
            buffer = self._frame_buffers[channel]
            try:
                # 如果队列满，丢弃最旧的帧
                if buffer.full():
                    try:
                        buffer.get_nowait()
                    except queue.Empty:
                        pass
                # 添加新帧（copy确保不影响原始帧）
                buffer.put_nowait(frame.copy())
            except (queue.Full, queue.Empty):
                # 队列操作失败，跳过此帧
                pass
    
    def start_recording(self) -> bool:
        """开始录制"""
        if self.is_recording:
            print("[VideoRecorder] 已经在录制中")
            return False
        
        self._stop_event.clear()
        self.is_recording = True
        self._recording_thread = threading.Thread(target=self._recording_loop)
        self._recording_thread.daemon = True
        self._recording_thread.start()
        print(f"[VideoRecorder] 开始录制，间隔: {self.interval_seconds}秒，视频长度: {self.clip_duration}秒")
        return True
    
    def stop_recording(self):
        """停止录制"""
        if not self.is_recording:
            return
        
        print("[VideoRecorder] 停止录制...")
        self._stop_event.set()
        self.is_recording = False
        
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=5.0)
        
        print("[VideoRecorder] 录制已停止")
    
    def _recording_loop(self):
        """录制主循环 - 独立线程运行，不影响实时显示
        
        工作流程：
        1. 以指定fps从回调获取帧（非阻塞）
        2. 将帧存入缓冲区（队列满时丢弃旧帧）
        3. 到达录制间隔时，异步保存视频文件
        """
        last_record_time = time.time()
        frame_interval = 1.0 / self.fps
        
        print(f"[VideoRecorder] 录制循环启动，目标帧率: {self.fps}fps")
        
        while not self._stop_event.is_set():
            loop_start = time.time()
            
            try:
                current_time = time.time()
                
                # 检查是否到达录制间隔
                if current_time - last_record_time >= self.interval_seconds:
                    last_record_time = current_time
                    # 在后台线程保存视频，不阻塞采集
                    threading.Thread(
                        target=self._save_video_clips,
                        daemon=True
                    ).start()
                
                # 从回调获取帧并添加到缓冲区（非阻塞）
                for channel, callback in self._frame_callbacks.items():
                    try:
                        frame = callback()
                        if frame is not None:
                            # 非阻塞添加，队列满时自动丢弃最旧帧
                            self.add_frame(channel, frame)
                    except Exception as e:
                        # 获取帧失败不中断录制循环
                        pass
                
                # 精确控制帧率
                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                print(f"[VideoRecorder] 录制循环异常: {e}")
                time.sleep(0.1)
        
        print("[VideoRecorder] 录制循环结束")
    
    def _save_video_clips(self):
        """保存视频片段"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for channel in ['CH1', 'CH2', 'CH3']:
            # 构建文件名
            filename = f"{channel}_{timestamp}.mp4"
            filepath = self.save_dir / filename
            
            # 从缓冲区获取帧
            frames = self._get_frames_from_buffer(channel)
            
            if len(frames) > 0:
                # 保存视频
                success = self._save_video_file(filepath, frames)
                if success:
                    # 记录历史
                    self._recording_history.append({
                        'channel': channel,
                        'filepath': str(filepath),
                        'filename': filename,
                        'timestamp': timestamp,
                        'duration': self.clip_duration,
                        'frame_count': len(frames)
                    })
                    print(f"[VideoRecorder] 已保存 {channel} 视频: {filename} ({len(frames)}帧)")
            else:
                print(f"[VideoRecorder] {channel} 缓冲区为空，跳过保存")
    
    def _get_frames_from_buffer(self, channel: str) -> List[np.ndarray]:
        """从缓冲区获取帧（获取最后clip_duration秒的帧）"""
        frames = []
        buffer = self._frame_buffers[channel]
        
        # 计算需要获取的帧数
        frames_needed = self.fps * self.clip_duration
        
        # 从队列中获取帧（不阻塞）
        temp_frames = []
        while not buffer.empty() and len(temp_frames) < frames_needed * 2:
            try:
                frame = buffer.get_nowait()
                temp_frames.append(frame)
            except queue.Empty:
                break
        
        # 取最后需要的帧数
        frames = temp_frames[-frames_needed:] if len(temp_frames) > frames_needed else temp_frames
        
        # 将多余的帧放回队列
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
            # 获取帧尺寸
            height, width = frames[0].shape[:2]
            
            # 创建VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(filepath), fourcc, self.fps, (width, height))
            
            if not out.isOpened():
                print(f"[VideoRecorder] 无法创建视频文件: {filepath}")
                return False
            
            # 写入帧
            for frame in frames:
                # 确保是BGR格式
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    out.write(frame)
            
            out.release()
            return True
            
        except Exception as e:
            print(f"[VideoRecorder] 保存视频失败: {e}")
            return False
    
    def get_recording_history(self, limit: int = 50) -> List[Dict]:
        """获取录制历史"""
        return self._recording_history[-limit:]
    
    def get_status(self) -> Dict:
        """获取录制器状态"""
        return {
            'is_recording': self.is_recording,
            'save_directory': str(self.save_dir),
            'interval_seconds': self.interval_seconds,
            'clip_duration': self.clip_duration,
            'fps': self.fps,
            'history_count': len(self._recording_history)
        }
    
    def clear_history(self):
        """清空录制历史"""
        self._recording_history.clear()
        print("[VideoRecorder] 录制历史已清空")


class VideoDiagnoser:
    """视频诊断器 - 从视频文件中抽帧并进行诊断"""
    
    def __init__(self):
        self._diagnosis_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.is_diagnosing = False
        
        # 诊断回调
        self._frame_callback: Optional[Callable[[str, np.ndarray, int], None]] = None
        self._result_callback: Optional[Callable[[Dict], None]] = None
        
        print("[VideoDiagnoser] 初始化完成")
    
    def register_callbacks(self, 
                          frame_callback: Callable[[str, np.ndarray, int], None],
                          result_callback: Callable[[Dict], None]):
        """注册回调函数
        
        Args:
            frame_callback: 帧回调 (channel, frame, frame_number)
            result_callback: 结果回调 (diagnosis_result)
        """
        self._frame_callback = frame_callback
        self._result_callback = result_callback
    
    def start_diagnosis(self, video_files: Dict[str, str]) -> bool:
        """开始诊断视频文件
        
        Args:
            video_files: {'CH1': 'path/to/video1.mp4', 'CH2': '...', 'CH3': '...'}
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_diagnosing:
            print("[VideoDiagnoser] 已经在诊断中")
            return False
        
        self._stop_event.clear()
        self.is_diagnosing = True
        self._diagnosis_thread = threading.Thread(
            target=self._diagnosis_loop, 
            args=(video_files,)
        )
        self._diagnosis_thread.daemon = True
        self._diagnosis_thread.start()
        
        print(f"[VideoDiagnoser] 开始诊断: {video_files}")
        return True
    
    def stop_diagnosis(self):
        """停止诊断"""
        if not self.is_diagnosing:
            return
        
        print("[VideoDiagnoser] 停止诊断...")
        self._stop_event.set()
        self.is_diagnosing = False
        
        if self._diagnosis_thread and self._diagnosis_thread.is_alive():
            self._diagnosis_thread.join(timeout=5.0)
        
        print("[VideoDiagnoser] 诊断已停止")
    
    def _diagnosis_loop(self, video_files: Dict[str, str]):
        """诊断主循环"""
        # 打开视频文件
        caps = {}
        for channel, filepath in video_files.items():
            if filepath and os.path.exists(filepath):
                cap = cv2.VideoCapture(filepath)
                if cap.isOpened():
                    caps[channel] = cap
                    print(f"[VideoDiagnoser] 已打开 {channel}: {filepath}")
                else:
                    print(f"[VideoDiagnoser] 无法打开 {channel}: {filepath}")
        
        if not caps:
            print("[VideoDiagnoser] 没有可用的视频文件")
            self.is_diagnosing = False
            return
        
        frame_count = 0
        
        try:
            while not self._stop_event.is_set():
                all_finished = True
                
                for channel, cap in list(caps.items()):
                    ret, frame = cap.read()
                    
                    if ret and frame is not None:
                        all_finished = False
                        frame_count += 1
                        
                        # 调用帧回调（用于显示或进一步处理）
                        if self._frame_callback:
                            try:
                                self._frame_callback(channel, frame, frame_count)
                            except Exception as e:
                                print(f"[VideoDiagnoser] 帧回调错误: {e}")
                        
                        # 每10帧进行一次诊断（模拟）
                        if frame_count % 10 == 0:
                            self._perform_diagnosis(channel, frame, frame_count)
                    
                    else:
                        # 视频结束
                        print(f"[VideoDiagnoser] {channel} 视频播放结束")
                        caps[channel].release()
                        del caps[channel]
                
                if all_finished:
                    print("[VideoDiagnoser] 所有视频诊断完成")
                    break
                
                time.sleep(0.1)  # 控制播放速度
        
        finally:
            # 清理
            for cap in caps.values():
                cap.release()
            
            self.is_diagnosing = False
            
            # 发送诊断完成消息
            if self._result_callback:
                self._result_callback({
                    'status': 'completed',
                    'total_frames': frame_count,
                    'message': '视频诊断完成'
                })
    
    def _perform_diagnosis(self, channel: str, frame: np.ndarray, frame_number: int):
        """执行诊断（模拟）"""
        # 这里可以接入真实的诊断模型
        # 目前使用模拟数据
        
        # 模拟诊断结果
        import random
        fault_probability = random.random()
        
        if fault_probability > 0.8:
            status_code = random.choice([1, 2, 3])  # 随机故障
            status_labels = {
                1: ['刮刀磨损'],
                2: ['激光功率异常'],
                3: ['保护气体异常']
            }.get(status_code, ['未知故障'])
        else:
            status_code = 0
            status_labels = ['系统健康']
        
        result = {
            'channel': channel,
            'frame_number': frame_number,
            'timestamp': time.time(),
            'status_code': status_code,
            'status_labels': status_labels,
            'confidence': fault_probability,
            'message': f'{channel} 第{frame_number}帧诊断完成'
        }
        
        if self._result_callback:
            self._result_callback(result)
    
    def get_status(self) -> Dict:
        """获取诊断器状态"""
        return {
            'is_diagnosing': self.is_diagnosing
        }


# 单例实例
_video_recorder: Optional[VideoRecorder] = None
_video_diagnoser: Optional[VideoDiagnoser] = None


def get_video_recorder(save_dir: str = None) -> VideoRecorder:
    """获取视频录制器实例（单例）"""
    global _video_recorder
    if _video_recorder is None:
        _video_recorder = VideoRecorder(save_dir or "./recordings")
    return _video_recorder


def get_video_diagnoser() -> VideoDiagnoser:
    """获取视频诊断器实例（单例）"""
    global _video_diagnoser
    if _video_diagnoser is None:
        _video_diagnoser = VideoDiagnoser()
    return _video_diagnoser
