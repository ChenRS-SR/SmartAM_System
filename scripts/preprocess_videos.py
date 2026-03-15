#!/usr/bin/env python3
"""
视频预处理脚本
提前进行畸变矫正和视角调整，生成优化后的视频

用法:
    python preprocess_videos.py normal --calib calibration_points.json
    python preprocess_videos.py scene_underpower --fps 10
"""

import cv2
import numpy as np
import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional
import argparse


def load_calibration(calib_file: str) -> Dict:
    """加载标定数据"""
    with open(calib_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_perspective_matrix(calib_data: dict, channel: str, src_size: Tuple[int, int], 
                           dst_size: Tuple[int, int] = (640, 480)) -> np.ndarray:
    """计算透视变换矩阵
    
    支持两种格式:
    1. 简单格式: {"CH1": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]], ...}
    2. 完整格式: {"CH1": {"source_points": [...], "target_points": [...]}, ...}
    """
    channel_data = calib_data.get(channel)
    if channel_data is None:
        raise ValueError(f"通道 {channel} 的标定数据不存在")
    
    # 检查是简单格式还是完整格式
    if isinstance(channel_data, list) and len(channel_data) == 4:
        # 简单格式：直接是4个角点坐标
        src_points = np.array(channel_data, dtype=np.float32)
        # 默认目标点为全图
        dst_points = np.array([
            [0, 0],
            [dst_size[0], 0],
            [dst_size[0], dst_size[1]],
            [0, dst_size[1]]
        ], dtype=np.float32)
    elif isinstance(channel_data, dict):
        # 完整格式
        src_points = np.array(channel_data['source_points'], dtype=np.float32)
        dst_points = np.array(channel_data['target_points'], dtype=np.float32)
        
        # 缩放到实际尺寸
        src_w, src_h = src_size
        calib_w = channel_data.get('calib_width', src_w)
        calib_h = channel_data.get('calib_height', src_h)
        
        src_points[:, 0] *= src_w / calib_w
        src_points[:, 1] *= src_h / calib_h
        
        dst_points[:, 0] *= dst_size[0] / channel_data.get('target_width', dst_size[0])
        dst_points[:, 1] *= dst_size[1] / channel_data.get('target_height', dst_size[1])
    else:
        raise ValueError(f"通道 {channel} 的标定数据格式不正确")
    
    return cv2.getPerspectiveTransform(src_points, dst_points)


def preprocess_video(input_path: str, output_path: str, 
                     calib_data: Optional[dict] = None,
                     channel: str = None,
                     target_size: Tuple[int, int] = (640, 480),
                     fps: int = 10) -> bool:
    """
    预处理单个视频
    
    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        calib_data: 标定数据（可选）
        target_size: 输出分辨率
        fps: 输出帧率
    
    Returns:
        是否成功
    """
    print(f"\n[处理] {Path(input_path).name}")
    print(f"  [输入] {input_path}")
    print(f"  [输出] {output_path}")
    
    # 打开输入视频
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"  [错误] 无法打开视频")
        return False
    
    # 获取视频信息
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"  [信息] {width}x{height} @ {original_fps:.1f}fps, {total_frames}帧")
    
    # 计算变换矩阵
    transform_matrix = None
    if calib_data and channel:
        try:
            transform_matrix = get_perspective_matrix(calib_data, channel, (width, height), target_size)
            print(f"  [标定] 已应用畸变矫正和视角调整")
        except Exception as e:
            print(f"  [警告] 标定失败: {e}, 仅调整大小")
    
    # 创建输出视频
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, target_size)
    
    if not out.isOpened():
        print(f"  ❌ 错误: 无法创建输出视频")
        cap.release()
        return False
    
    # 处理每一帧
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 应用变换
        if transform_matrix is not None:
            processed = cv2.warpPerspective(frame, transform_matrix, target_size)
        else:
            processed = cv2.resize(frame, target_size)
        
        out.write(processed)
        
        frame_count += 1
        if frame_count % 100 == 0:
            progress = frame_count / total_frames * 100
            print(f"  [进度] {frame_count}/{total_frames} ({progress:.1f}%)")
    
    # 释放资源
    cap.release()
    out.release()
    
    print(f"  [完成] {frame_count}帧 -> {output_path}")
    return True


def preprocess_scene(scene_name: str, calib_file: Optional[str] = None,
                     fps: int = 10, force: bool = False) -> bool:
    """
    预处理整个场景
    
    Args:
        scene_name: 场景名称 (如 'normal', 'scene_underpower')
        calib_file: 标定文件路径
        fps: 输出帧率
        force: 强制重新处理
    
    Returns:
        是否成功
    """
    # 查找项目根目录
    script_dir = Path(__file__).parent.parent
    scene_dir = script_dir / "simulation_record" / scene_name
    output_dir = script_dir / "simulation_record" / f"{scene_name}_processed"
    
    if not scene_dir.exists():
        print(f"❌ 错误: 场景文件夹不存在: {scene_dir}")
        return False
    
    print(f"\n{'='*60}")
    print(f"预处理场景: {scene_name}")
    print(f"{'='*60}")
    
    # 创建输出目录
    output_dir.mkdir(exist_ok=True)
    
    # 加载标定数据
    calib_data = None
    if calib_file and Path(calib_file).exists():
        calib_data = load_calibration(calib_file)
        print(f"标定文件: {calib_file}")
    else:
        # 尝试默认标定文件
        default_calib = script_dir / "calibration_points.json"
        if default_calib.exists():
            calib_data = load_calibration(str(default_calib))
            print(f"标定文件: {default_calib}")
        else:
            print("⚠️ 未找到标定文件，仅调整视频大小")
    
    # 查找视频文件
    channel_patterns = {
        'CH1': ['CH1*.mp4', 'ch1*.mp4'],
        'CH2': ['CH2*.mp4', 'ch2*.mp4'],
        'CH3': ['CH3*.mp4', 'ch3*.mp4', 'thermal*.mp4']
    }
    
    results = {}
    
    for channel, patterns in channel_patterns.items():
        # 查找输入文件
        input_file = None
        for pattern in patterns:
            files = list(scene_dir.glob(pattern))
            if files:
                input_file = files[0]
                break
        
        if not input_file:
            print(f"\n⚠️ 未找到 {channel} 视频文件")
            continue
        
        # 检查是否已处理
        output_file = output_dir / f"{channel}_processed.mp4"
        if output_file.exists() and not force:
            print(f"\n[跳过] {channel} 已处理，跳过 (使用 --force 重新处理)")
            results[channel] = str(output_file)
            continue
        
        # 预处理（传入整个calib_data和channel名称）
        success = preprocess_video(
            str(input_file),
            str(output_file),
            calib_data,
            channel,
            fps=fps
        )
        
        if success:
            results[channel] = str(output_file)
    
    # 保存处理信息
    info_file = output_dir / "process_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump({
            'scene': scene_name,
            'fps': fps,
            'calibration_used': calib_file is not None,
            'channels': results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"预处理完成!")
    print(f"输出目录: {output_dir}")
    print(f"处理通道: {list(results.keys())}")
    print(f"{'='*60}\n")
    
    return len(results) > 0


def main():
    parser = argparse.ArgumentParser(
        description='预处理视频：畸变矫正 + 视角调整',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预处理 normal 场景（使用默认标定）
  python preprocess_videos.py normal
  
  # 预处理并指定标定文件
  python preprocess_videos.py scene_underpower --calib my_calib.json
  
  # 指定帧率并强制重新处理
  python preprocess_videos.py normal --fps 10 --force
        """
    )
    
    parser.add_argument('scene', help='场景名称 (如 normal, scene_underpower)')
    parser.add_argument('-c', '--calib', help='标定文件路径')
    parser.add_argument('-f', '--fps', type=int, default=10, help='输出帧率 (默认10)')
    parser.add_argument('--force', action='store_true', help='强制重新处理')
    
    args = parser.parse_args()
    
    success = preprocess_scene(args.scene, args.calib, args.fps, args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
