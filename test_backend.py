"""
后端诊断脚本
============
直接测试后端功能，不依赖浏览器
"""
import sys
import os
sys.path.insert(0, 'backend')

# 测试1: 检查文件是否存在
print("=" * 60)
print("1. 检查文件")
print("=" * 60)

project_root = os.path.dirname(os.path.abspath(__file__))
frontend_public = os.path.join(project_root, "frontend", "public")
frontend_dist = os.path.join(project_root, "frontend", "dist")

test_html = os.path.join(frontend_public, "test.html")
video_test_html = os.path.join(frontend_public, "video-test.html")

print(f"project_root: {project_root}")
print(f"frontend_public: {frontend_public}")
print(f"  exists: {os.path.exists(frontend_public)}")
print(f"frontend_dist: {frontend_dist}")
print(f"  exists: {os.path.exists(frontend_dist)}")
print(f"test.html: {test_html}")
print(f"  exists: {os.path.exists(test_html)}")
print(f"video-test.html: {video_test_html}")
print(f"  exists: {os.path.exists(video_test_html)}")

# 测试2: 启动一个简单的HTTP服务器测试视频文件
print("\n" + "=" * 60)
print("2. 测试视频文件读取")
print("=" * 60)

import cv2
video_path = os.path.join(project_root, "simulation_record", "CH1_segment011_20260310_170803.mp4")
print(f"视频路径: {video_path}")
print(f"  exists: {os.path.exists(video_path)}")

if os.path.exists(video_path):
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"  视频信息: {w}x{h}@{fps}fps, {frames}帧")
        
        # 读取一帧
        ret, frame = cap.read()
        if ret:
            print(f"  成功读取第一帧: {frame.shape}")
        else:
            print(f"  读取帧失败")
    else:
        print(f"  无法打开视频")
    cap.release()

# 测试3: 测试VideoFileCameraManager
print("\n" + "=" * 60)
print("3. 测试VideoFileCameraManager")
print("=" * 60)

from core.slm.video_file_camera import VideoFileCameraManager
import time

video_files = {
    'CH1': video_path,
}

manager = VideoFileCameraManager(video_files, enable_correction=False)
print(f"初始化完成")

if manager.connect():
    print("连接成功")
    manager.start_continuous_capture()
    print("采集已启动")
    
    time.sleep(2)
    
    frame = manager.get_latest_frame('CH1')
    jpeg = manager.get_frame_jpeg('CH1')
    
    print(f"CH1帧: {frame.shape if frame is not None else None}")
    print(f"CH1 JPEG: {len(jpeg) if jpeg else 0} bytes")
    
    manager.disconnect()
else:
    print("连接失败")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
