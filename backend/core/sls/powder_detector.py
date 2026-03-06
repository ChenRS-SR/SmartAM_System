"""
扑粉检测器 - SLS核心逻辑
基于振动传感器的刮刀运动检测状态机
"""

import time
import threading
from enum import Enum
from typing import Optional, Callable
import logging


class MotionState(Enum):
    """扑粉运动状态"""
    IDLE = "idle"                    # 空闲状态
    FIRST_MOTION = "first_motion"    # 第一次振动（刮刀运动开始）
    BETWEEN_MOTIONS = "between_motions"  # 两次振动之间
    SECOND_MOTION = "second_motion"   # 第二次振动（刮刀返回）


class PowderDetector:
    """
    SLS扑粉检测器
    
    功能：
    1. 监测振动传感器数据
    2. 状态机判断扑粉周期
    3. 触发图像采集回调
    
    状态机流程（简单模式）：
    IDLE → FIRST_MOTION → idle → (完成一个周期)
    
    状态机流程（复杂模式）：
    IDLE → FIRST_MOTION → BETWEEN_MOTIONS → SECOND_MOTION → IDLE
    """
    
    def __init__(self, vibration_sensor, config: Optional[dict] = None):
        """
        初始化扑粉检测器
        
        Args:
            vibration_sensor: 振动传感器实例
            config: 检测配置参数
        """
        self.vibration_sensor = vibration_sensor
        self.config = config or self._default_config()
        
        # 状态变量
        self.current_state = MotionState.IDLE
        self.detection_active = False
        self._thread_running = False
        self._detection_thread: Optional[threading.Thread] = None
        
        # 时间记录
        self.last_trigger_time = 0
        self.motion_start_time = 0
        self.first_motion_time = 0
        
        # 回调函数
        self.on_first_motion: Optional[Callable] = None   # 刮刀开始运动
        self.on_second_motion: Optional[Callable] = None  # 刮刀返回
        self.on_cycle_complete: Optional[Callable] = None # 完成一个周期
        
        # 统计
        self.stats = {
            'total_cycles': 0,
            'successful_cycles': 0,
            'last_cycle_time': 0
        }
        
        self._lock = threading.Lock()
        
        logging.info("[PowderDetector] 初始化完成")
    
    @staticmethod
    def _default_config() -> dict:
        """默认配置"""
        return {
            'motion_threshold': 0.05,           # 振动触发阈值
            'motion_threshold_factor': 0.3,     # 静止判断阈值系数
            'debounce_time': 1.0,               # 防抖时间（秒）
            'first_motion_min_duration': 2.0,   # 第一次振动最小持续时间
            'between_motions_min_wait': 0.8,    # 两次振动之间最小等待
            'between_motions_timeout': 15.0,    # 等待第二次振动超时
            'second_motion_settle_time': 0.5,   # 第二次振动停止后稳定时间
            'first_motion_settle_time': 0.3,    # 第一次振动停止后拍照等待时间
            'required_consecutive_low': 20,     # 连续低于阈值次数
            'main_loop_delay': 0.02,            # 主循环延迟（50Hz）
            'state_machine_mode': 'simple',     # 'simple' 或 'complex'
        }
    
    def start_detection(self):
        """启动扑粉检测"""
        if self._thread_running:
            logging.warning("[PowderDetector] 检测已在运行中")
            return
        
        self.detection_active = True
        self._thread_running = True
        self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._detection_thread.start()
        
        logging.info("[PowderDetector] 检测已启动")
    
    def stop_detection(self):
        """停止扑粉检测"""
        self._thread_running = False
        self.detection_active = False
        
        if self._detection_thread:
            self._detection_thread.join(timeout=2.0)
        
        logging.info("[PowderDetector] 检测已停止")
    
    def _detection_loop(self):
        """检测主循环"""
        while self._thread_running:
            try:
                if not self.detection_active:
                    time.sleep(0.1)
                    continue
                
                # 更新振动数据并检查触发
                is_triggered, magnitude = self.vibration_sensor.check_vibration_trigger(
                    self.config['motion_threshold']
                )
                
                current_time = time.time()
                
                # 根据模式选择状态机
                if self.config.get('state_machine_mode', 'simple') == 'simple':
                    self._handle_simple_state_machine(is_triggered, magnitude, current_time)
                else:
                    self._handle_complex_state_machine(is_triggered, magnitude, current_time)
                
                time.sleep(self.config['main_loop_delay'])
                
            except Exception as e:
                logging.error(f"[PowderDetector] 检测循环错误: {e}")
                time.sleep(0.1)
    
    def _handle_simple_state_machine(self, is_triggered: bool, magnitude: float, current_time: float):
        """
        简单状态机: idle → motion → idle
        适用于单向刮刀
        """
        with self._lock:
            if self.current_state == MotionState.IDLE:
                # 等待运动开始
                if is_triggered:
                    self.current_state = MotionState.FIRST_MOTION
                    self.motion_start_time = current_time
                    self.last_trigger_time = current_time
                    
                    logging.info(f"[PowderDetector] 状态: IDLE → FIRST_MOTION (强度: {magnitude:.3f})")
                    
                    # 触发回调
                    if self.on_first_motion:
                        try:
                            self.on_first_motion()
                        except Exception as e:
                            logging.error(f"[PowderDetector] first_motion回调错误: {e}")
            
            elif self.current_state == MotionState.FIRST_MOTION:
                # 运动中，等待停止
                if is_triggered:
                    # 仍在运动中，更新时间
                    self.last_trigger_time = current_time
                else:
                    # 检查是否稳定停止
                    time_since_last = current_time - self.last_trigger_time
                    
                    if time_since_last >= self.config['debounce_time']:
                        # 运动停止，完成一个周期
                        cycle_time = current_time - self.motion_start_time
                        
                        logging.info(f"[PowderDetector] 状态: FIRST_MOTION → IDLE (周期: {cycle_time:.2f}s)")
                        
                        self.current_state = MotionState.IDLE
                        self.stats['total_cycles'] += 1
                        self.stats['successful_cycles'] += 1
                        self.stats['last_cycle_time'] = cycle_time
                        
                        # 触发完成回调
                        if self.on_cycle_complete:
                            try:
                                self.on_cycle_complete(cycle_time)
                            except Exception as e:
                                logging.error(f"[PowderDetector] cycle_complete回调错误: {e}")
    
    def _handle_complex_state_machine(self, is_triggered: bool, magnitude: float, current_time: float):
        """
        复杂状态机: idle → first_motion → between_motions → second_motion → idle
        适用于双向刮刀（去程和回程）
        """
        with self._lock:
            if self.current_state == MotionState.IDLE:
                if is_triggered:
                    self.current_state = MotionState.FIRST_MOTION
                    self.motion_start_time = current_time
                    self.last_trigger_time = current_time
                    self.first_motion_time = current_time
                    
                    logging.info(f"[PowderDetector] 状态: IDLE → FIRST_MOTION")
                    
                    if self.on_first_motion:
                        self.on_first_motion()
            
            elif self.current_state == MotionState.FIRST_MOTION:
                if is_triggered:
                    self.last_trigger_time = current_time
                else:
                    time_since_last = current_time - self.last_trigger_time
                    min_duration = self.config['first_motion_min_duration']
                    
                    if time_since_last >= self.config['debounce_time'] and \
                       (current_time - self.motion_start_time) >= min_duration:
                        # 第一次运动结束
                        self.current_state = MotionState.BETWEEN_MOTIONS
                        logging.info(f"[PowderDetector] 状态: FIRST_MOTION → BETWEEN_MOTIONS")
            
            elif self.current_state == MotionState.BETWEEN_MOTIONS:
                # 等待第二次运动或超时
                time_since_first = current_time - self.first_motion_time
                
                if is_triggered and time_since_first >= self.config['between_motions_min_wait']:
                    # 检测到第二次运动
                    self.current_state = MotionState.SECOND_MOTION
                    self.last_trigger_time = current_time
                    logging.info(f"[PowderDetector] 状态: BETWEEN_MOTIONS → SECOND_MOTION")
                    
                    if self.on_second_motion:
                        self.on_second_motion()
                
                elif time_since_first >= self.config['between_motions_timeout']:
                    # 超时，重置到IDLE
                    logging.warning(f"[PowderDetector] 等待第二次振动超时")
                    self.current_state = MotionState.IDLE
            
            elif self.current_state == MotionState.SECOND_MOTION:
                if is_triggered:
                    self.last_trigger_time = current_time
                else:
                    time_since_last = current_time - self.last_trigger_time
                    
                    if time_since_last >= self.config['second_motion_settle_time']:
                        # 完成整个周期
                        cycle_time = current_time - self.motion_start_time
                        
                        logging.info(f"[PowderDetector] 状态: SECOND_MOTION → IDLE (周期: {cycle_time:.2f}s)")
                        
                        self.current_state = MotionState.IDLE
                        self.stats['total_cycles'] += 1
                        self.stats['successful_cycles'] += 1
                        self.stats['last_cycle_time'] = cycle_time
                        
                        if self.on_cycle_complete:
                            self.on_cycle_complete(cycle_time)
    
    def get_status(self) -> dict:
        """获取检测器状态"""
        with self._lock:
            return {
                'state': self.current_state.value,
                'active': self.detection_active,
                'stats': self.stats.copy(),
                'config': {
                    'threshold': self.config['motion_threshold'],
                    'mode': self.config.get('state_machine_mode', 'simple')
                }
            }
    
    def reset_state(self):
        """重置状态机"""
        with self._lock:
            self.current_state = MotionState.IDLE
            logging.info("[PowderDetector] 状态机已重置")
