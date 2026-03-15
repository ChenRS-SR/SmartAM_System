"""
调试启动流程
"""
import sys
import os
sys.path.insert(0, 'backend')

# 首先设置视频文件配置
from core.slm.slm_acquisition import (
    get_slm_acquisition, 
    reset_slm_acquisition,
    _global_video_file_config
)

video_files = {
    'CH1': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH1_segment011_20260310_170803.mp4',
    'CH2': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH2_segment011_20260310_170803.mp4',
    'CH3': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH3_segment011_20260310_170803.mp4'
}

print("=== 1. 设置全局配置 ===")
acquisition = get_slm_acquisition(use_mock=False)
acquisition.set_video_file_mode(video_files, enable_correction=False)
print(f"全局配置: {_global_video_file_config}")

print("\n=== 2. 检查当前实例状态 ===")
print(f"实例 _video_file_mode: {acquisition._video_file_mode}")
print(f"实例 _video_files: {acquisition._video_files}")

print("\n=== 3. 模拟 /start 流程 ===")
# 重置实例
reset_slm_acquisition()
print("实例已重置")
print(f"重置后全局配置: {_global_video_file_config}")

# 创建新实例
print("\n创建新实例...")
new_acquisition = get_slm_acquisition(use_mock=True)  # 使用 use_mock=True
print(f"新实例 _video_file_mode: {new_acquisition._video_file_mode}")
print(f"新实例 _video_files: {new_acquisition._video_files}")
print(f"新实例 use_mock: {new_acquisition.use_mock}")

# 初始化
print("\n初始化...")
success = new_acquisition.initialize(use_mock=True)
print(f"初始化结果: {success}")
print(f"初始化后 camera_manager: {type(new_acquisition.camera_manager).__name__}")

# 启动
print("\n启动采集...")
new_acquisition.start()
print(f"is_running: {new_acquisition.is_running}")

print("\n=== 测试完成 ===")
