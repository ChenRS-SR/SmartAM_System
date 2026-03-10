"""
振动触发图像采集模块
=====================
基于振动传感器数据触发，在振动下降沿采集图像

核心功能：
1. 实时监测振动强度（vx, vy, vz 三轴）
2. 下降沿触发：振动从高于阈值降到低于阈值
3. 每两次触发为一层（before + after）
4. 防抖处理避免重复触发
5. 屏蔽长时间低振动状态
"""

import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime
from typing import Dict, Optional, Callable, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class CaptureTriggerState(Enum):
    """采集触发状态"""
    IDLE = "idle"           # 空闲，等待振动上升
    HIGH = "high"           # 振动高于阈值（运动中）
    WAIT_BEFORE = "wait_before"  # 等待第一次下降沿（before）
    WAIT_SECOND_RISE = "wait_second_rise"  # 等待第二次上升
    WAIT_AFTER = "wait_after"  # 等待第二次下降沿（after）


@dataclass
class VibrationData:
    """振动数据"""
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    magnitude: float = 0.0  # 综合强度
    timestamp: float = 0.0


class VibrationTriggeredCapture:
    """
    振动触发图像采集器
    
    触发逻辑（下降沿触发）：
    1. 振动强度 > 阈值：进入 HIGH 状态（刮刀运动中）
    2. 振动强度 <= 阈值：触发采集（下降沿）
    3. 第一次下降沿：保存 before 图像
    4. 第二次下降沿：保存 after 图像，完成一层
    
    目录结构：
    E:/SmartAM_recordings/
        YYYYMMDD_HHMMSS/
            CH1/
                Layer0_before_YYYYMMDD_HHMMSS.jpg
                Layer0_after_YYYYMMDD_HHMMSS.jpg
                Layer1_before_YYYYMMDD_HHMMSS.jpg
                ...
            CH2/
                ...
            CH3/
                ...
    """
    
    # 默认保存目录
    DEFAULT_SAVE_DIR = "E:/SmartAM_recordings"
    
    def __init__(self, save_dir: str = None):
        self.save_dir = Path(save_dir or self.DEFAULT_SAVE_DIR)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        # 采集配置
        self.threshold = 0.1  # 振动阈值（默认0.1 mm/s）
        self.debounce_time = 0.5  # 防抖时间（秒）
        self.min_quiet_duration = 1.0  # 最小静止持续时间（秒）
        self.max_layer_wait_time = 30.0  # 最大层等待时间（秒）
        
        # 状态管理
        self.state = CaptureTriggerState.IDLE
        self.layer_count = 0  # 当前层数
        self.trigger_count = 0  # 触发计数（0=before, 1=after）
        self.is_capturing = False
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 时间记录
        self.last_trigger_time = 0.0
        self.state_enter_time = 0.0
        self.quiet_start_time = None  # 静止开始时间
        
        # 帧获取回调
        self._frame_callbacks: Dict[str, Callable[[], np.ndarray]] = {}
        
        # 振动数据回调
        self._vibration_callback: Optional[Callable[[VibrationData], None]] = None
        
        # 采集完成回调
        self._capture_complete_callback: Optional[Callable[[str, int, str], None]] = None
        
        # 当前会话目录
        self.current_session_dir: Optional[Path] = None
        
        # 统计
        self.total_captures = 0
        self.last_vibration = VibrationData()
        
        # 锁
        self._lock = threading.Lock()
        
        print(f"[ImageCapture] 初始化完成，保存目录: {self.save_dir}")
    
    def set_save_directory(self, save_dir: str) -> dict:
        """设置保存目录"""
        try:
            path = Path(save_dir)
            
            # 检查盘符
            drive = path.drive
            if drive and not os.path.exists(drive + '\\'):
                return {'success': False, 'message': f'盘符 {drive} 不存在', 'path': str(self.save_dir)}
            
            path.mkdir(parents=True, exist_ok=True)
            self.save_dir = path
            print(f"[ImageCapture] 保存目录已更改: {self.save_dir}")
            return {'success': True, 'message': '目录设置成功', 'path': str(self.save_dir)}
        except Exception as e:
            return {'success': False, 'message': f'设置目录失败: {e}', 'path': str(self.save_dir)}
    
    def set_threshold(self, threshold: float):
        """设置振动阈值"""
        self.threshold = max(0.01, min(10.0, threshold))
        print(f"[ImageCapture] 振动阈值设置为: {self.threshold}")
    
    def register_frame_callback(self, channel: str, callback: Callable[[], np.ndarray]):
        """注册帧获取回调"""
        self._frame_callbacks[channel] = callback
        print(f"[ImageCapture] 已注册 {channel} 帧回调")
    
    def register_vibration_callback(self, callback: Callable[[VibrationData], None]):
        """注册振动数据回调（用于实时显示）"""
        self._vibration_callback = callback
    
    def register_capture_complete_callback(self, callback: Callable[[str, int, str], None]):
        """注册采集完成回调 (channel, layer, trigger_type)"""
        self._capture_complete_callback = callback
    
    def _create_session_dir(self) -> Path:
        """创建新的采集会话目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.save_dir / timestamp
        
        for ch in ['CH1', 'CH2', 'CH3']:
            (session_dir / ch).mkdir(parents=True, exist_ok=True)
        
        print(f"[ImageCapture] 创建会话目录: {session_dir}")
        return session_dir
    
    def start_capture(self) -> dict:
        """开始振动触发采集"""
        if self.is_capturing:
            return {'success': False, 'message': '已经在采集中'}
        
        # 重置状态
        self.state = CaptureTriggerState.IDLE
        self.layer_count = 0
        self.trigger_count = 0
        self.total_captures = 0
        self.last_trigger_time = 0.0
        
        # 创建新会话目录
        self.current_session_dir = self._create_session_dir()
        
        # 启动采集线程
        self._stop_event.clear()
        self.is_capturing = True
        self._capture_thread = threading.Thread(target=self._capture_loop)
        self._capture_thread.daemon = True
        self._capture_thread.start()
        
        print(f"[ImageCapture] 采集已启动，阈值: {self.threshold}")
        return {
            'success': True,
            'message': '采集已启动',
            'session_dir': str(self.current_session_dir),
            'threshold': self.threshold
        }
    
    def stop_capture(self) -> dict:
        """停止采集"""
        if not self.is_capturing:
            return {'success': False, 'message': '未在采集中'}
        
        print("[ImageCapture] 停止采集...")
        self._stop_event.set()
        self.is_capturing = False
        
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=3.0)
        
        result = {
            'success': True,
            'message': '采集已停止',
            'total_captures': self.total_captures,
            'layer_count': self.layer_count,
            'session_dir': str(self.current_session_dir) if self.current_session_dir else None
        }
        
        print(f"[ImageCapture] 采集已停止，共 {self.total_captures} 张图像，{self.layer_count} 层")
        return result
    
    def update_vibration(self, vx: float, vy: float, vz: float) -> Optional[dict]:
        """
        更新振动数据并检查是否触发采集
        
        Returns:
            如果触发采集，返回 {'triggered': True, 'layer': int, 'type': 'before'|'after'}
            否则返回 None
        """
        # 计算综合振动强度（使用欧几里得范数）
        magnitude = np.sqrt(vx**2 + vy**2 + vz**2)
        
        self.last_vibration = VibrationData(vx, vy, vz, magnitude, time.time())
        
        # 通知振动数据更新
        if self._vibration_callback:
            self._vibration_callback(self.last_vibration)
        
        if not self.is_capturing:
            return None
        
        with self._lock:
            return self._process_vibration_state(magnitude)
    
    def _process_vibration_state(self, magnitude: float) -> Optional[dict]:
        """处理振动状态机"""
        current_time = time.time()
        
        # 防抖检查
        if current_time - self.last_trigger_time < self.debounce_time:
            return None
        
        # 超时检查：如果一层等待太久，重置状态
        if self.state != CaptureTriggerState.IDLE:
            state_duration = current_time - self.state_enter_time
            if state_duration > self.max_layer_wait_time:
                print(f"[ImageCapture] 层等待超时({state_duration:.1f}s)，重置状态")
                self.state = CaptureTriggerState.IDLE
                return None
        
        # 状态机处理
        if self.state == CaptureTriggerState.IDLE:
            # 等待振动上升（超过阈值）
            if magnitude > self.threshold:
                self.state = CaptureTriggerState.HIGH
                self.state_enter_time = current_time
                self.quiet_start_time = None
                print(f"[ImageCapture] 振动上升: {magnitude:.3f} > {self.threshold}")
        
        elif self.state == CaptureTriggerState.HIGH:
            # 振动高于阈值，检测是否开始下降
            if magnitude <= self.threshold:
                # 开始计时静止期
                if self.quiet_start_time is None:
                    self.quiet_start_time = current_time
                
                # 检查是否满足最小静止时间（防抖）
                quiet_duration = current_time - self.quiet_start_time
                if quiet_duration >= self.min_quiet_duration:
                    # 下降沿触发！
                    self.last_trigger_time = current_time
                    
                    if self.trigger_count == 0:
                        # 第一次下降沿：before
                        self.state = CaptureTriggerState.WAIT_BEFORE
                        self._capture_images('before')
                        self.trigger_count = 1
                        self.state = CaptureTriggerState.WAIT_SECOND_RISE
                        self.state_enter_time = current_time
                        print(f"[ImageCapture] 触发 before (层{self.layer_count}), 振动: {magnitude:.3f}")
                        return {'triggered': True, 'layer': self.layer_count, 'type': 'before'}
                    else:
                        # 第二次下降沿：after
                        self._capture_images('after')
                        self.trigger_count = 0
                        self.layer_count += 1
                        self.state = CaptureTriggerState.IDLE
                        print(f"[ImageCapture] 触发 after (层{self.layer_count-1}), 完成一层")
                        return {'triggered': True, 'layer': self.layer_count - 1, 'type': 'after'}
            else:
                # 振动再次升高，重置静止计时
                self.quiet_start_time = None
        
        elif self.state == CaptureTriggerState.WAIT_SECOND_RISE:
            # 等待第二次振动上升
            if magnitude > self.threshold:
                self.state = CaptureTriggerState.HIGH
                self.quiet_start_time = None
                print(f"[ImageCapture] 第二次振动上升: {magnitude:.3f}")
        
        return None
    
    def _capture_images(self, trigger_type: str):
        """采集所有通道的图像"""
        if not self.current_session_dir:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        for channel in ['CH1', 'CH2', 'CH3']:
            callback = self._frame_callbacks.get(channel)
            if callback is None:
                continue
            
            try:
                frame = callback()
                if frame is None:
                    print(f"[ImageCapture] {channel} 帧获取失败")
                    continue
                
                # 构建文件名：Layer{层数}_{before|after}_时间戳.jpg
                filename = f"Layer{self.layer_count}_{trigger_type}_{timestamp}.jpg"
                filepath = self.current_session_dir / channel / filename
                
                # 保存图像（OpenCV需要BGR格式）
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    # 假设输入是RGB，转换为BGR
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(str(filepath), frame_bgr)
                    self.total_captures += 1
                    
                    print(f"[ImageCapture] 已保存 {channel}: {filename}")
                    
                    # 通知采集完成
                    if self._capture_complete_callback:
                        self._capture_complete_callback(channel, self.layer_count, trigger_type)
                
            except Exception as e:
                print(f"[ImageCapture] {channel} 采集失败: {e}")
    
    def _capture_loop(self):
        """采集主循环（主要用于超时检查）"""
        print("[ImageCapture] 采集循环启动")
        
        while not self._stop_event.is_set():
            time.sleep(0.1)
            
            # 检查超时
            if self.state != CaptureTriggerState.IDLE:
                current_time = time.time()
                state_duration = current_time - self.state_enter_time
                
                if state_duration > self.max_layer_wait_time:
                    with self._lock:
                        print(f"[ImageCapture] 采集循环检测到超时，重置状态")
                        self.state = CaptureTriggerState.IDLE
        
        print("[ImageCapture] 采集循环结束")
    
    def get_status(self) -> dict:
        """获取采集器状态"""
        with self._lock:
            return {
                'is_capturing': self.is_capturing,
                'state': self.state.value,
                'layer_count': self.layer_count,
                'trigger_count': self.trigger_count,
                'total_captures': self.total_captures,
                'threshold': self.threshold,
                'current_vibration': {
                    'vx': self.last_vibration.vx,
                    'vy': self.last_vibration.vy,
                    'vz': self.last_vibration.vz,
                    'magnitude': self.last_vibration.magnitude
                },
                'save_directory': str(self.save_dir),
                'current_session': str(self.current_session_dir) if self.current_session_dir else None
            }


# 单例实例
_image_capture_instance: Optional[VibrationTriggeredCapture] = None


def get_image_capture(save_dir: str = None) -> VibrationTriggeredCapture:
    """获取图像采集器实例（单例）"""
    global _image_capture_instance
    if _image_capture_instance is None:
        _image_capture_instance = VibrationTriggeredCapture(save_dir)
    return _image_capture_instance
