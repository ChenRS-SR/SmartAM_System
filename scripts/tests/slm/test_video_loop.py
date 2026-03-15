"""
测试视频文件循环播放
=====================
"""

import sys
import time
import cv2
sys.path.insert(0, 'backend')

from core.slm.video_file_camera import VideoFileCameraManager

video_files = {
    'CH1': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH1_segment011_20260310_170803.mp4',
}

print("=" * 60)
print("测试视频文件循环播放")
print("=" * 60)

# 创建管理器
manager = VideoFileCameraManager(
    video_files=video_files,
    fps=30,  # 设置高帧率快速播放
    enable_correction=False
)

# 连接
if not manager.connect():
    print("连接失败!")
    sys.exit(1)

# 快进视频到接近末尾（视频有499帧，快进到480帧）
cap = manager._captures['CH1']
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"\n视频总帧数: {total_frames}")
print("快进到第480帧（接近末尾）...")
cap.set(cv2.CAP_PROP_POS_FRAMES, 480)

print("\n开始连续采集（观察是否循环播放）...")
manager.start_continuous_capture()

# 监控帧计数
for i in range(30):  # 30次检查
    time.sleep(0.2)
    status = manager.get_status()
    current_pos = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    print(f"  CH1: {status['CH1']['frame_count']}帧, 视频位置: {current_pos}/{total_frames}")

print("\n停止采集...")
manager.disconnect()

print("\n测试完成!")
