"""
测试完整工作流程
================
1. 设置视频文件模式
2. 启动采集
3. 验证视频流使用的是视频文件而非mock
"""

import sys
sys.path.insert(0, 'backend')

from core.slm import get_slm_acquisition, reset_slm_acquisition

# 先重置
reset_slm_acquisition()

# 1. 设置视频文件模式
print("=" * 60)
print("步骤1: 设置视频文件模式")
print("=" * 60)

video_files = {
    'CH1': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH1_segment011_20260310_170803.mp4',
    'CH2': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH2_segment011_20260310_170803.mp4',
    'CH3': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH3_segment011_20260310_170803.mp4'
}

acq = get_slm_acquisition(use_mock=True)
result = acq.set_video_file_mode(video_files, enable_correction=True)
print(f"设置视频文件模式结果: {result}")
print(f"配置: {acq.get_video_file_mode_config()}")

# 2. 启动采集
print("\n" + "=" * 60)
print("步骤2: 启动采集")
print("=" * 60)

# 重新获取实例（确保是同一个）
acq = get_slm_acquisition(use_mock=True)
success = acq.initialize(use_mock=True)
print(f"初始化结果: {success}")
print(f"Camera Manager类型: {type(acq.camera_manager).__name__}")

# 3. 开始采集
acq.start()
print(f"采集状态: {acq.is_running}")

# 4. 检查视频流
print("\n" + "=" * 60)
print("步骤3: 验证视频流")
print("=" * 60)

import time
time.sleep(1)  # 等待采集开始

# 获取几帧
for i in range(3):
    frame_ch1 = acq.camera_manager.get_latest_frame('CH1')
    frame_ch2 = acq.camera_manager.get_latest_frame('CH2')
    frame_ch3 = acq.camera_manager.get_latest_frame('CH3')
    
    print(f"\n第{i+1}次获取帧:")
    print(f"  CH1: {frame_ch1.shape if frame_ch1 is not None else 'None'}")
    print(f"  CH2: {frame_ch2.shape if frame_ch2 is not None else 'None'}")
    print(f"  CH3: {frame_ch3.shape if frame_ch3 is not None else 'None'}")
    
    time.sleep(0.5)

# 5. 停止采集
print("\n" + "=" * 60)
print("步骤4: 停止采集")
print("=" * 60)
acq.stop()
reset_slm_acquisition()
print("采集已停止")

print("\n✓ 测试完成！如果看到真实视频帧尺寸(如640x480)，说明视频文件模式正常工作。")
