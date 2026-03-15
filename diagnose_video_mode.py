"""
视频文件模式完整诊断
=====================
逐步测试整个流程，追踪问题所在
"""
import sys
import os
sys.path.insert(0, 'backend')

print("=" * 70)
print("视频文件模式诊断")
print("=" * 70)

# 1. 检查视频文件路径
print("\n[1] 检查视频文件路径")
video_files = {
    'CH1': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH1_segment011_20260310_170803.mp4',
    'CH2': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH2_segment011_20260310_170803.mp4',
    'CH3': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH3_segment011_20260310_170803.mp4'
}

for ch, path in video_files.items():
    exists = os.path.exists(path)
    print(f"  {ch}: {exists} - {path[:60]}...")

# 2. 检查 Path 类是否能识别路径
print("\n[2] 检查 Path 类路径识别")
from pathlib import Path
for ch, path in video_files.items():
    p = Path(path)
    print(f"  {ch}: Path.exists() = {p.exists()}")

# 3. 检查全局配置初始状态
print("\n[3] 检查全局配置初始状态")
from core.slm.slm_acquisition import _global_video_file_config, get_slm_acquisition, reset_slm_acquisition
print(f"  初始全局配置: {_global_video_file_config}")

# 4. 创建实例并设置视频文件模式
print("\n[4] 创建实例并设置视频文件模式")
acquisition = get_slm_acquisition(use_mock=False)
print(f"  实例创建完成: {acquisition}")
print(f"  实例 ID: {id(acquisition)}")
print(f"  use_mock: {acquisition.use_mock}")
print(f"  _video_file_mode: {acquisition._video_file_mode}")
print(f"  _video_files: {acquisition._video_files}")

# 设置视频文件模式
print("\n[5] 调用 set_video_file_mode")
result = acquisition.set_video_file_mode(video_files, enable_correction=False)
print(f"  设置结果: {result}")
print(f"  设置后全局配置: {_global_video_file_config}")
print(f"  实例 _video_file_mode: {acquisition._video_file_mode}")
print(f"  实例 _video_files: {acquisition._video_files}")

# 6. 模拟 /start 端点的行为
print("\n[6] 模拟 /start 端点的 reset 行为")
print("  调用 reset_slm_acquisition()...")
reset_slm_acquisition()
print(f"  重置后全局配置: {_global_video_file_config}")

# 7. 创建新实例（模拟 /start 中的 get_slm_acquisition）
print("\n[7] 创建新实例（模拟 /start）")
new_acquisition = get_slm_acquisition(use_mock=False)
print(f"  新实例: {new_acquisition}")
print(f"  新实例 ID: {id(new_acquisition)}")
print(f"  use_mock: {new_acquisition.use_mock}")
print(f"  _video_file_mode: {new_acquisition._video_file_mode}")
print(f"  _video_files: {new_acquisition._video_files}")
print(f"  camera_manager: {new_acquisition.camera_manager}")

# 8. 检查 camera_manager 类型
if new_acquisition.camera_manager:
    print(f"  camera_manager 类型: {type(new_acquisition.camera_manager).__name__}")
    from core.slm.video_file_camera import VideoFileCameraManager
    is_vfc = isinstance(new_acquisition.camera_manager, VideoFileCameraManager)
    print(f"  是 VideoFileCameraManager: {is_vfc}")

print("\n" + "=" * 70)
print("诊断完成")
print("=" * 70)
