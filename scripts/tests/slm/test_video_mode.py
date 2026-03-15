"""
测试视频文件模式完整流程
=========================
"""
import sys
import time
sys.path.insert(0, 'backend')

from core.slm import get_slm_acquisition, reset_slm_acquisition

# 重置实例
reset_slm_acquisition()

print("=" * 60)
print("测试视频文件模式")
print("=" * 60)

# 1. 获取实例
print("\n1. 获取SLMAcquisition实例 (use_mock=True)")
acq = get_slm_acquisition(use_mock=True)
print(f"   实例ID: {id(acq)}, use_mock: {acq.use_mock}")

# 2. 设置视频文件模式
print("\n2. 设置视频文件模式")
video_files = {
    'CH1': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH1_segment011_20260310_170803.mp4',
    'CH2': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH2_segment011_20260310_170803.mp4',
    'CH3': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH3_segment011_20260310_170803.mp4'
}
result = acq.set_video_file_mode(video_files, enable_correction=True)
print(f"   结果: {result}")
print(f"   配置: {acq.get_video_file_mode_config()}")

# 3. 初始化
print("\n3. 初始化传感器")
success = acq.initialize(use_mock=True)
print(f"   初始化结果: {success}")
print(f"   Camera Manager类型: {type(acq.camera_manager).__name__}")

# 4. 开始采集
print("\n4. 开始采集")
acq.start()
print(f"   采集状态: {acq.is_running}")

# 5. 等待并获取帧
print("\n5. 等待并获取帧...")
time.sleep(2)

for ch in ['CH1', 'CH2', 'CH3']:
    frame = acq.camera_manager.get_latest_frame(ch)
    if frame is not None:
        print(f"   {ch}: {frame.shape}")
    else:
        print(f"   {ch}: None (尝试直接读取)")
        frame = acq.camera_manager.read_frame(ch)
        if frame is not None:
            print(f"   {ch} (直接读取): {frame.shape}")
        else:
            print(f"   {ch}: 无法获取帧")

# 6. 测试JPEG编码
print("\n6. 测试JPEG编码")
for ch in ['CH1', 'CH2', 'CH3']:
    jpeg = acq.camera_manager.get_frame_jpeg(ch)
    if jpeg:
        print(f"   {ch}: JPEG {len(jpeg)} bytes")
    else:
        print(f"   {ch}: JPEG编码失败")

# 7. 停止采集
print("\n7. 停止采集")
acq.stop()
reset_slm_acquisition()
print("   采集已停止")

print("\n" + "=" * 60)
print("测试完成!")
print("=" * 60)
