"""
视频预处理模块
提前对视频进行畸变矫正和视角调整，避免实时计算
"""

import cv2
import numpy as np
import json
import os
from pathlib import Path


class VideoPreprocessor:
    """视频预处理器"""
    
    def __init__(self, calibration_file=None):
        self.calibration_data = None
        if calibration_file and os.path.exists(calibration_file):
            with open(calibration_file, 'r') as f:
                self.calibration_data = json.load(f)
    
    def preprocess_video(self, input_path, output_path, channel='CH1', 
                         target_size=(640, 480), fps=10):
        """
        预处理视频：畸变矫正 + 视角调整
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径
            channel: 通道名称 (CH1/CH2/CH3)
            target_size: 输出尺寸
            fps: 输出帧率
        """
        print(f"[Preprocessor] 开始处理: {input_path}")
        print(f"[Preprocessor] 输出: {output_path}")
        
        # 打开输入视频
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频: {input_path}")
        
        # 获取视频信息
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"[Preprocessor] 原始视频: {width}x{height} @ {original_fps}fps, {total_frames}帧")
        
        # 创建输出视频
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, target_size)
        
        if not out.isOpened():
            raise ValueError(f"无法创建输出视频: {output_path}")
        
        # 获取变换矩阵（如果有标定数据）
        transform_matrix = None
        if self.calibration_data and channel in self.calibration_data:
            transform_matrix = self._get_transform_matrix(
                self.calibration_data[channel], 
                (width, height), 
                target_size
            )
        
        # 处理每一帧
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 应用变换
            processed_frame = self._process_frame(frame, transform_matrix, target_size)
            
            # 写入输出
            out.write(processed_frame)
            
            frame_count += 1
            if frame_count % 100 == 0:
                progress = frame_count / total_frames * 100
                print(f"[Preprocessor] 进度: {frame_count}/{total_frames} ({progress:.1f}%)")
        
        # 释放资源
        cap.release()
        out.release()
        
        print(f"[Preprocessor] 完成: {frame_count}帧已处理")
        return frame_count
    
    def _get_transform_matrix(self, calib_data, src_size, dst_size):
        """根据标定数据计算透视变换矩阵"""
        src_points = np.array(calib_data['source_points'], dtype=np.float32)
        dst_points = np.array(calib_data['target_points'], dtype=np.float32)
        
        # 缩放到实际尺寸
        src_w, src_h = src_size
        dst_w, dst_h = dst_size
        
        src_points[:, 0] *= src_w / calib_data.get('calib_width', src_w)
        src_points[:, 1] *= src_h / calib_data.get('calib_height', src_h)
        
        dst_points[:, 0] *= dst_w / calib_data.get('target_width', dst_w)
        dst_points[:, 1] *= dst_h / calib_data.get('target_height', dst_h)
        
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        return matrix
    
    def _process_frame(self, frame, transform_matrix, target_size):
        """处理单帧"""
        if transform_matrix is not None:
            # 应用透视变换
            processed = cv2.warpPerspective(frame, transform_matrix, target_size)
        else:
            # 仅调整大小
            processed = cv2.resize(frame, target_size)
        
        return processed
    
    def preprocess_scene(self, scene_folder, output_folder=None, 
                         calibration_file=None, fps=10):
        """
        预处理整个场景的所有视频
        
        Args:
            scene_folder: 场景文件夹路径 (如 'simulation_record/normal')
            output_folder: 输出文件夹，默认为 scene_folder + '_processed'
            calibration_file: 标定文件路径
            fps: 输出帧率
        """
        scene_path = Path(scene_folder)
        if not scene_path.exists():
            raise ValueError(f"场景文件夹不存在: {scene_folder}")
        
        if output_folder is None:
            output_folder = str(scene_path) + '_processed'
        
        os.makedirs(output_folder, exist_ok=True)
        
        # 加载标定数据
        if calibration_file and os.path.exists(calibration_file):
            with open(calibration_file, 'r') as f:
                self.calibration_data = json.load(f)
        
        # 处理每个通道
        channel_files = {
            'CH1': ['CH1*.mp4', 'ch1*.mp4'],
            'CH2': ['CH2*.mp4', 'ch2*.mp4'],
            'CH3': ['CH3*.mp4', 'ch3*.mp4', 'thermal*.mp4']
        }
        
        results = {}
        
        for channel, patterns in channel_files.items():
            for pattern in patterns:
                files = list(scene_path.glob(pattern))
                if files:
                    input_file = files[0]
                    output_file = os.path.join(output_folder, f"{channel}_processed.mp4")
                    
                    try:
                        frame_count = self.preprocess_video(
                            str(input_file), 
                            output_file, 
                            channel,
                            fps=fps
                        )
                        results[channel] = {
                            'input': str(input_file),
                            'output': output_file,
                            'frames': frame_count
                        }
                    except Exception as e:
                        print(f"[Preprocessor] 处理 {channel} 失败: {e}")
                    break
        
        print(f"[Preprocessor] 场景处理完成: {output_folder}")
        return results


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='预处理视频文件')
    parser.add_argument('scene', help='场景文件夹 (如 normal, scene_underpower)')
    parser.add_argument('--calib', '-c', help='标定文件路径')
    parser.add_argument('--fps', '-f', type=int, default=10, help='输出帧率')
    parser.add_argument('--output', '-o', help='输出文件夹')
    
    args = parser.parse_args()
    
    # 查找项目根目录
    script_dir = Path(__file__).parent.parent.parent.parent
    scene_folder = script_dir / "simulation_record" / args.scene
    
    if not scene_folder.exists():
        print(f"错误: 场景文件夹不存在: {scene_folder}")
        return
    
    # 默认标定文件
    calib_file = args.calib
    if not calib_file:
        default_calib = script_dir / "calibration_points.json"
        if default_calib.exists():
            calib_file = str(default_calib)
    
    # 预处理
    preprocessor = VideoPreprocessor()
    results = preprocessor.preprocess_scene(
        str(scene_folder),
        args.output,
        calib_file,
        args.fps
    )
    
    print("\n处理结果:")
    for ch, info in results.items():
        print(f"  {ch}: {info['frames']}帧 -> {info['output']}")


if __name__ == "__main__":
    main()
