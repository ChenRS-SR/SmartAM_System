"""
API 端到端测试
=============
直接测试后端 API，不依赖独立进程
"""
import sys
import os
sys.path.insert(0, 'backend')

# 模拟 API 调用流程
from api.slm import get_acquisition, setup_video_file_mode, start_acquisition
import asyncio

video_files = {
    'CH1': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH1_segment011_20260310_170803.mp4',
    'CH2': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH2_segment011_20260310_170803.mp4',
    'CH3': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH3_segment011_20260310_170803.mp4'
}

async def test():
    print("=== 1. 设置视频文件模式 ===")
    result = await setup_video_file_mode(video_files=video_files, enable_correction=False)
    print(f"Result: {result}")
    
    print("\n=== 2. 检查配置 ===")
    acquisition = get_acquisition(create_if_none=False)
    if acquisition:
        print(f"Instance _video_file_mode: {acquisition._video_file_mode}")
        print(f"Instance _video_files: {acquisition._video_files}")
    else:
        print("No instance yet")
    
    print("\n=== 3. 启动采集 ===")
    result = await start_acquisition(use_mock=True)
    print(f"Result: {result}")
    
    print("\n=== 4. 检查状态 ===")
    acquisition = get_acquisition(create_if_none=False)
    if acquisition:
        print(f"is_running: {acquisition.is_running}")
        print(f"camera_manager: {type(acquisition.camera_manager).__name__ if acquisition.camera_manager else None}")
    
    print("\n=== 测试完成 ===")

asyncio.run(test())
