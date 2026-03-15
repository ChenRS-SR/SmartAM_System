#!/usr/bin/env python3
"""
Normal 视频截取
CH1: 基准
CH2: 比 CH1 快 1 帧
CH3: 比 CH1 慢 5 帧
"""

import cv2
import os

def trim_video_cv(input_file, output_file, start_frame, end_frame, fps=10):
    """使用 OpenCV 截取视频"""
    
    print(f"Processing {input_file}:")
    print(f"  Start frame: {start_frame} ({start_frame/fps:.1f}s)")
    print(f"  End frame: {end_frame} ({end_frame/fps:.1f}s)")
    print(f"  Duration: {(end_frame-start_frame)/fps:.1f}s")
    
    cap = cv2.VideoCapture(input_file)
    if not cap.isOpened():
        print(f"  [ERROR] Cannot open: {input_file}\n")
        return False
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"  Original: {width}x{height} @ {original_fps}fps, total {total_frames} frames")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"  [ERROR] Cannot create output: {output_file}\n")
        cap.release()
        return False
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    frame_count = 0
    target_frames = end_frame - start_frame
    
    while frame_count < target_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        out.write(frame)
        frame_count += 1
        
        if frame_count % 100 == 0:
            print(f"  Progress: {frame_count}/{target_frames} frames ({frame_count*100//target_frames}%)")
    
    cap.release()
    out.release()
    
    print(f"  [OK] Saved: {output_file} ({frame_count} frames)\n")
    return True

def main():
    # CH1 基准 (10fps)
    # 开始: 2秒7帧 = 27帧
    # 结束: 1分53秒5帧 = 1135帧
    ch1_start = 27
    ch1_end = 1135
    duration = ch1_end - ch1_start  # 1108帧
    
    # CH2: 比 CH1 快 0 帧
    ch2_start = ch1_start   # 27
    ch2_end = ch2_start + duration  # 1135
    
    # CH3: 比 CH1 慢 5 帧
    ch3_start = ch1_start + 5  # 32
    ch3_end = ch3_start + duration  # 1140
    
    configs = [
        {
            'name': 'CH1 (基准)',
            'input': 'CH1_segment029_20260310_180512.mp4',
            'output': 'ch1_underpower.mp4',
            'start_frame': ch1_start,
            'end_frame': ch1_end
        },
        {
            'name': 'CH2 (快0帧)',
            'input': 'CH2_segment029_20260310_180512.mp4',
            'output': 'ch2_underpower.mp4',
            'start_frame': ch2_start,
            'end_frame': ch2_end
        },
        {
            'name': 'CH3 (慢5帧)',
            'input': 'CH3_segment029_20260310_180512.mp4',
            'output': 'ch3_underpower.mp4',
            'start_frame': ch3_start,
            'end_frame': ch3_end
        }
    ]
    
    print("=" * 60)
    print("Normal Video Trimming (Final)")
    print("=" * 60)
    print()
    print(f"CH1: {ch1_start}-{ch1_end} ({duration} frames) - 基准")
    print(f"CH2: {ch2_start}-{ch2_end} ({duration} frames) - 快0帧")
    print(f"CH3: {ch3_start}-{ch3_end} ({duration} frames) - 慢5帧")
    print()
    
    for config in configs:
        if os.path.exists(config['input']):
            trim_video_cv(
                config['input'],
                config['output'],
                config['start_frame'],
                config['end_frame']
            )
        else:
            print(f"[ERROR] Input file not found: {config['input']}\n")
    
    print("=" * 60)
    print("Trimming Complete")
    print("=" * 60)

if __name__ == "__main__":
    main()
