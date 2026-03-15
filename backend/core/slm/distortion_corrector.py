"""
畸变矫正模块
============
基于透视变换的摄像头图像矫正

使用方法：
1. 从 calibration_points.json 加载标定点
2. 计算透视变换矩阵
3. 对图像进行矫正
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List


class DistortionCorrector:
    """畸变矫正器
    
    基于4点透视变换的图像矫正，用于校正摄像头视角畸变
    """
    
    def __init__(self, calibration_file: str = None):
        """
        初始化矫正器
        
        Args:
            calibration_file: 标定点配置文件路径，默认使用项目根目录的 calibration_points.json
        """
        self.calibration_file = calibration_file or self._get_default_calibration_file()
        self.calibration_points: Dict[str, List[List[int]]] = {}
        self.transform_matrices: Dict[str, np.ndarray] = {}
        self.output_sizes: Dict[str, Tuple[int, int]] = {}
        
        # 加载标定点
        self._load_calibration_points()
    
    def _get_default_calibration_file(self) -> str:
        """获取默认标定文件路径"""
        # 从当前文件位置回溯到项目根目录
        # backend/core/slm/distortion_corrector.py -> backend -> 项目根目录
        import os
        current_file = Path(__file__).resolve()
        backend_dir = current_file.parent.parent.parent
        project_root = backend_dir.parent
        
        # 首先尝试项目根目录
        calib_path = project_root / "calibration_points.json"
        if calib_path.exists():
            print(f"[DistortionCorrector] 标定文件路径: {calib_path}")
            return str(calib_path)
        
        # 如果不在根目录，尝试backend目录
        calib_path_backend = backend_dir / "calibration_points.json"
        if calib_path_backend.exists():
            print(f"[DistortionCorrector] 标定文件路径: {calib_path_backend}")
            return str(calib_path_backend)
        
        # 默认返回根目录路径（即使不存在）
        print(f"[DistortionCorrector] 标定文件路径(不存在): {calib_path}")
        return str(calib_path)
    
    def _load_calibration_points(self) -> bool:
        """加载标定点配置文件"""
        try:
            calib_path = Path(self.calibration_file)
            if not calib_path.exists():
                print(f"[DistortionCorrector] 标定文件不存在: {self.calibration_file}")
                return False
            
            with open(calib_path, 'r', encoding='utf-8') as f:
                self.calibration_points = json.load(f)
            
            print(f"[DistortionCorrector] 已加载标定点: {list(self.calibration_points.keys())}")
            
            # 预计算变换矩阵
            self._precompute_transform_matrices()
            
            return True
            
        except Exception as e:
            print(f"[DistortionCorrector] 加载标定点失败: {e}")
            return False
    
    def _precompute_transform_matrices(self):
        """预计算所有通道的透视变换矩阵"""
        for channel, points in self.calibration_points.items():
            if len(points) != 4:
                print(f"[DistortionCorrector] {channel} 标定点数量不正确: {len(points)} (需要4个)")
                continue
            
            try:
                # 将标定点转换为numpy数组
                src_points = np.array(points, dtype='float32')
                
                # 计算输出尺寸（使用原始四边形的外接矩形）
                x_coords = [p[0] for p in points]
                y_coords = [p[1] for p in points]
                width = int(max(x_coords) - min(x_coords))
                height = int(max(y_coords) - min(y_coords))
                
                # 确保尺寸合理
                width = max(width, 320)
                height = max(height, 240)
                
                self.output_sizes[channel] = (width, height)
                
                # 定义目标点（矩形）
                dst_points = np.array([
                    [0, 0],
                    [width - 1, 0],
                    [width - 1, height - 1],
                    [0, height - 1]
                ], dtype='float32')
                
                # 计算透视变换矩阵
                matrix = cv2.getPerspectiveTransform(src_points, dst_points)
                self.transform_matrices[channel] = matrix
                
                print(f"[DistortionCorrector] {channel} 变换矩阵已计算: 输出尺寸 {width}x{height}")
                
            except Exception as e:
                print(f"[DistortionCorrector] {channel} 计算变换矩阵失败: {e}")
    
    def correct_frame(self, frame: np.ndarray, channel: str) -> np.ndarray:
        """
        矫正单帧图像
        
        Args:
            frame: 输入图像 (BGR或RGB格式)
            channel: 通道名称 (CH1, CH2, CH3)
            
        Returns:
            矫正后的图像
        """
        if frame is None:
            return None
        
        # 检查是否有该通道的变换矩阵
        if channel not in self.transform_matrices:
            # 如果没有标定数据，返回原图
            return frame
        
        try:
            matrix = self.transform_matrices[channel]
            output_size = self.output_sizes[channel]
            
            # 应用透视变换
            corrected = cv2.warpPerspective(frame, matrix, output_size)
            
            return corrected
            
        except Exception as e:
            print(f"[DistortionCorrector] {channel} 矫正失败: {e}")
            return frame
    
    def correct_frame_to_size(self, frame: np.ndarray, channel: str, 
                              target_size: Tuple[int, int]) -> np.ndarray:
        """
        矫正图像并调整到指定尺寸
        
        Args:
            frame: 输入图像
            channel: 通道名称
            target_size: 目标尺寸 (width, height)
            
        Returns:
            矫正并调整尺寸后的图像
        """
        # 先进行矫正
        corrected = self.correct_frame(frame, channel)
        
        if corrected is None:
            return None
        
        # 调整到目标尺寸
        if corrected.shape[1] != target_size[0] or corrected.shape[0] != target_size[1]:
            corrected = cv2.resize(corrected, target_size, interpolation=cv2.INTER_LINEAR)
        
        return corrected
    
    def is_channel_calibrated(self, channel: str) -> bool:
        """检查指定通道是否已标定"""
        return channel in self.transform_matrices
    
    def get_calibration_info(self) -> Dict:
        """获取标定信息"""
        info = {
            'calibration_file': self.calibration_file,
            'channels': {}
        }
        
        for channel in self.calibration_points.keys():
            info['channels'][channel] = {
                'calibrated': self.is_channel_calibrated(channel),
                'source_points': self.calibration_points.get(channel, []),
                'output_size': self.output_sizes.get(channel, (0, 0))
            }
        
        return info


# 全局矫正器实例（单例）
_corrector_instance: Optional[DistortionCorrector] = None


def get_distortion_corrector(calibration_file: str = None) -> DistortionCorrector:
    """获取全局畸变矫正器实例"""
    global _corrector_instance
    if _corrector_instance is None:
        _corrector_instance = DistortionCorrector(calibration_file)
    return _corrector_instance


def reset_corrector():
    """重置矫正器实例（用于重新加载配置）"""
    global _corrector_instance
    _corrector_instance = None
