"""
视频诊断引擎模块
================
基于ONNX分类模型的视频帧诊断系统
支持实时视频和预存视频两种诊断模式
"""

import cv2
import numpy as np
import threading
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import asyncio


class DiagnosisMode(Enum):
    """诊断模式"""
    REALTIME = "realtime"      # 实时视频诊断
    SIMULATION = "simulation"  # 模拟模式（预存视频）


class DiagnosisStatus(Enum):
    """诊断状态"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class DiagnosisResult:
    """诊断结果"""
    status_code: int           # 0-4 状态码
    status_label: str          # 状态标签
    confidence: float          # 置信度
    frame_count: int           # 处理的帧数
    timestamp: float           # 诊断时间戳
    details: Dict              # 详细结果
    
    def to_dict(self) -> Dict:
        return {
            'status_code': self.status_code,
            'status_label': self.status_label,
            'confidence': self.confidence,
            'frame_count': self.frame_count,
            'timestamp': self.timestamp,
            'details': self.details
        }


class VideoDiagnosisEngine:
    """
    视频诊断引擎
    
    功能：
    1. 从视频文件中抽取指定数量的帧
    2. 使用ONNX模型对帧进行分类
    3. 聚合多帧结果输出最终状态码
    4. 支持实时视频和预存视频两种模式
    """
    
    # 状态码映射
    STATUS_CODES = {
        0: {'label': '健康', 'name': 'healthy'},
        1: {'label': '刮刀磨损', 'name': 'powder_fault'},
        2: {'label': '激光功率异常', 'name': 'laser_fault'},
        3: {'label': '保护气体异常', 'name': 'gas_fault'},
        4: {'label': '复合故障', 'name': 'compound_fault'}
    }
    
    def __init__(self, model_path: str = None, frame_count: int = 50):
        """
        初始化诊断引擎
        
        Args:
            model_path: ONNX模型路径（None则使用模拟模式）
            frame_count: 每个通道抽取的帧数（默认50帧）
        """
        self.model_path = model_path
        self.frame_count = frame_count  # 每个通道50帧
        self.model = None               # ONNX模型
        self.input_shape = (224, 224)   # 模型输入尺寸
        
        # 诊断状态
        self.status = DiagnosisStatus.IDLE
        self.progress = 0.0             # 诊断进度 0-100
        self.current_frame = 0          # 当前处理帧数
        self.fault_count = 0            # 发现异常次数
        
        # 回调函数
        self._progress_callback: Optional[Callable[[float, int, int], None]] = None
        self._result_callback: Optional[Callable[[DiagnosisResult], None]] = None
        self._frame_callback: Optional[Callable[[str, np.ndarray, int], None]] = None
        
        # 线程
        self._diagnosis_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 加载模型
        if model_path and os.path.exists(model_path):
            self._load_model()
        else:
            print(f"[DiagnosisEngine] 未找到模型文件，使用模拟模式: {model_path}")
    
    def _load_model(self):
        """加载ONNX模型"""
        try:
            import onnxruntime as ort
            
            # 使用CPU推理
            providers = ['CPUExecutionProvider']
            self.model = ort.InferenceSession(self.model_path, providers=providers)
            
            # 获取输入输出信息
            self.input_name = self.model.get_inputs()[0].name
            self.input_shape = tuple(self.model.get_inputs()[0].shape[2:4])  # H, W
            
            print(f"[DiagnosisEngine] ONNX模型加载成功: {self.model_path}")
            print(f"[DiagnosisEngine] 输入尺寸: {self.input_shape}")
            
        except ImportError:
            print("[DiagnosisEngine] 警告: 未安装onnxruntime，使用模拟模式")
            self.model = None
        except Exception as e:
            print(f"[DiagnosisEngine] 模型加载失败: {e}")
            self.model = None
    
    def register_callbacks(
        self,
        progress_callback: Callable[[float, int, int], None] = None,
        result_callback: Callable[[DiagnosisResult], None] = None,
        frame_callback: Callable[[str, np.ndarray, int], None] = None
    ):
        """注册回调函数"""
        self._progress_callback = progress_callback
        self._result_callback = result_callback
        self._frame_callback = frame_callback
    
    def start_diagnosis(
        self,
        video_files: Dict[str, str],
        mode: DiagnosisMode = DiagnosisMode.REALTIME
    ) -> bool:
        """
        开始视频诊断
        
        Args:
            video_files: {'CH1': 'path/to/video1.mp4', 'CH2': '...', 'CH3': '...'}
            mode: 诊断模式（实时/模拟）
        
        Returns:
            bool: 是否成功启动
        """
        if self.status == DiagnosisStatus.RUNNING:
            print("[DiagnosisEngine] 诊断已在运行中")
            return False
        
        # 验证视频文件
        valid_videos = {}
        for ch, path in video_files.items():
            if path and os.path.exists(path):
                valid_videos[ch] = path
            else:
                print(f"[DiagnosisEngine] 视频文件不存在: {ch} -> {path}")
        
        if not valid_videos:
            print("[DiagnosisEngine] 没有有效的视频文件")
            return False
        
        # 重置状态
        self.status = DiagnosisStatus.RUNNING
        self.progress = 0.0
        self.current_frame = 0
        self.fault_count = 0
        self._stop_event.clear()
        
        # 启动诊断线程
        self._diagnosis_thread = threading.Thread(
            target=self._diagnosis_loop,
            args=(valid_videos, mode)
        )
        self._diagnosis_thread.daemon = True
        self._diagnosis_thread.start()
        
        print(f"[DiagnosisEngine] 开始{mode.value}模式诊断: {valid_videos}")
        return True
    
    def stop_diagnosis(self):
        """停止诊断"""
        if self.status != DiagnosisStatus.RUNNING:
            return
        
        print("[DiagnosisEngine] 停止诊断...")
        self._stop_event.set()
        
        if self._diagnosis_thread and self._diagnosis_thread.is_alive():
            self._diagnosis_thread.join(timeout=5.0)
        
        self.status = DiagnosisStatus.IDLE
        print("[DiagnosisEngine] 诊断已停止")
    
    def _diagnosis_loop(self, video_files: Dict[str, str], mode: DiagnosisMode):
        """诊断主循环"""
        try:
            # 1. 从所有视频抽取帧
            all_frames = self._extract_frames(video_files)
            
            if self._stop_event.is_set():
                return
            
            if not all_frames:
                self._notify_error("无法从视频中抽取帧")
                return
            
            # 2. 对帧进行分类推理
            result = self._inference(all_frames)
            
            if self._stop_event.is_set():
                return
            
            # 3. 通知结果
            self.status = DiagnosisStatus.COMPLETED
            if self._result_callback:
                self._result_callback(result)
            
            print(f"[DiagnosisEngine] 诊断完成: {result.status_label} (置信度: {result.confidence:.2f})")
            
        except Exception as e:
            print(f"[DiagnosisEngine] 诊断异常: {e}")
            self._notify_error(str(e))
    
    def _extract_frames(self, video_files: Dict[str, str]) -> Dict[str, List[np.ndarray]]:
        """
        从视频中抽取帧
        
        从每个通道的视频中均匀抽取self.frame_count帧
        
        Returns:
            {'CH1': [frame1, frame2, ...], 'CH2': [...], 'CH3': [...]}
        """
        all_frames = {}
        total_videos = len(video_files)
        
        for idx, (channel, video_path) in enumerate(video_files.items()):
            print(f"[DiagnosisEngine] 正在抽取 {channel} 帧...")
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"[DiagnosisEngine] 无法打开视频: {video_path}")
                continue
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            print(f"[DiagnosisEngine] {channel}: {total_frames}帧, {fps:.1f}fps, {duration:.1f}秒")
            
            # 均匀抽取帧
            frames = []
            if total_frames > 0:
                # 计算抽取间隔
                step = max(1, total_frames // self.frame_count)
                
                for i in range(self.frame_count):
                    if self._stop_event.is_set():
                        break
                    
                    frame_idx = min(i * step, total_frames - 1)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # 预处理帧
                        frame_processed = self._preprocess_frame(frame)
                        frames.append(frame_processed)
                        
                        # 更新进度
                        self.current_frame += 1
                        progress = (idx * self.frame_count + len(frames)) / (total_videos * self.frame_count) * 50
                        self._update_progress(progress, self.current_frame, 0)
                        
                        # 回调显示帧
                        if self._frame_callback:
                            self._frame_callback(channel, frame, len(frames))
                    
                    # 短暂休眠避免阻塞
                    time.sleep(0.001)
            
            cap.release()
            all_frames[channel] = frames
            print(f"[DiagnosisEngine] {channel} 抽取完成: {len(frames)}帧")
        
        return all_frames
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """预处理帧用于模型输入"""
        # 调整尺寸
        frame_resized = cv2.resize(frame, self.input_shape)
        
        # 归一化
        frame_normalized = frame_resized.astype(np.float32) / 255.0
        
        # 调整通道顺序 (H, W, C) -> (C, H, W)
        frame_transposed = np.transpose(frame_normalized, (2, 0, 1))
        
        # 添加batch维度
        frame_batch = np.expand_dims(frame_transposed, axis=0)
        
        return frame_batch
    
    def _inference(self, all_frames: Dict[str, List[np.ndarray]]) -> DiagnosisResult:
        """
        对抽取的帧进行推理
        
        Args:
            all_frames: {'CH1': [frame1, ...], 'CH2': [...], 'CH3': [...]}
        
        Returns:
            DiagnosisResult: 诊断结果
        """
        print("[DiagnosisEngine] 开始推理...")
        
        total_frames = sum(len(frames) for frames in all_frames.values())
        processed = 0
        predictions = []
        
        # 对每个通道的每帧进行推理
        for channel, frames in all_frames.items():
            for frame in frames:
                if self._stop_event.is_set():
                    break
                
                if self.model is not None:
                    # 使用ONNX模型推理
                    outputs = self.model.run(None, {self.input_name: frame})
                    pred = np.argmax(outputs[0], axis=1)[0]
                    confidence = float(np.max(outputs[0]))
                else:
                    # 模拟模式：随机生成预测
                    import random
                    pred = random.choices(
                        [0, 1, 2, 3, 4],
                        weights=[0.6, 0.1, 0.1, 0.1, 0.1]
                    )[0]
                    confidence = random.uniform(0.7, 0.95)
                
                predictions.append({
                    'channel': channel,
                    'prediction': int(pred),
                    'confidence': confidence
                })
                
                if pred != 0:
                    self.fault_count += 1
                
                processed += 1
                progress = 50 + (processed / total_frames) * 50
                self._update_progress(progress, self.current_frame, self.fault_count)
                
                time.sleep(0.001)
        
        # 聚合预测结果（投票机制）
        final_result = self._aggregate_predictions(predictions)
        
        return DiagnosisResult(
            status_code=final_result['status_code'],
            status_label=final_result['label'],
            confidence=final_result['confidence'],
            frame_count=total_frames,
            timestamp=time.time(),
            details={
                'predictions': predictions,
                'mode': 'onnx' if self.model else 'simulation'
            }
        )
    
    def _aggregate_predictions(self, predictions: List[Dict]) -> Dict:
        """
        聚合多帧预测结果
        
        使用投票机制，选择出现次数最多的类别
        如果出现次数相同，选择置信度最高的
        """
        if not predictions:
            return {'status_code': 0, 'label': '健康', 'confidence': 0.0}
        
        # 统计每个类别的出现次数和平均置信度
        class_stats = {}
        for pred in predictions:
            cls = pred['prediction']
            conf = pred['confidence']
            
            if cls not in class_stats:
                class_stats[cls] = {'count': 0, 'confidence_sum': 0.0}
            
            class_stats[cls]['count'] += 1
            class_stats[cls]['confidence_sum'] += conf
        
        # 找出出现次数最多的类别
        max_count = max(stats['count'] for stats in class_stats.values())
        candidates = [
            cls for cls, stats in class_stats.items()
            if stats['count'] == max_count
        ]
        
        # 如果有多个候选，选择平均置信度最高的
        if len(candidates) > 1:
            best_class = max(
                candidates,
                key=lambda cls: class_stats[cls]['confidence_sum'] / class_stats[cls]['count']
            )
        else:
            best_class = candidates[0]
        
        avg_confidence = class_stats[best_class]['confidence_sum'] / class_stats[best_class]['count']
        
        return {
            'status_code': best_class,
            'label': self.STATUS_CODES[best_class]['label'],
            'confidence': avg_confidence
        }
    
    def _update_progress(self, progress: float, current_frame: int, fault_count: int):
        """更新进度"""
        self.progress = min(100.0, max(0.0, progress))
        self.current_frame = current_frame
        self.fault_count = fault_count
        
        if self._progress_callback:
            try:
                self._progress_callback(self.progress, current_frame, fault_count)
            except Exception as e:
                print(f"[DiagnosisEngine] 进度回调错误: {e}")
    
    def _notify_error(self, message: str):
        """通知错误"""
        self.status = DiagnosisStatus.ERROR
        result = DiagnosisResult(
            status_code=-1,
            status_label='诊断失败',
            confidence=0.0,
            frame_count=0,
            timestamp=time.time(),
            details={'error': message}
        )
        
        if self._result_callback:
            self._result_callback(result)
        
        print(f"[DiagnosisEngine] 错误: {message}")
    
    def get_status(self) -> Dict:
        """获取诊断引擎状态"""
        return {
            'status': self.status.value,
            'progress': self.progress,
            'current_frame': self.current_frame,
            'fault_count': self.fault_count,
            'has_model': self.model is not None,
            'model_path': self.model_path
        }
    
    def reload_model(self, model_path: str) -> bool:
        """重新加载模型"""
        self.model_path = model_path
        self._load_model()
        return self.model is not None


# 单例实例
_diagnosis_engine: Optional[VideoDiagnosisEngine] = None


def get_diagnosis_engine(model_path: str = None, frame_count: int = 50) -> VideoDiagnosisEngine:
    """获取诊断引擎实例（单例）"""
    global _diagnosis_engine
    if _diagnosis_engine is None:
        _diagnosis_engine = VideoDiagnosisEngine(model_path, frame_count)
    return _diagnosis_engine
