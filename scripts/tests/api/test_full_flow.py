"""
完整流程测试 - 验证视频文件模式
"""
import sys
import time
import asyncio
sys.path.insert(0, 'backend')

from core.slm import get_slm_acquisition, reset_slm_acquisition

print("=" * 60)
print("完整流程测试")
print("=" * 60)

# 步骤1: 重置并设置视频文件模式
print("\n1. 设置视频文件模式")
reset_slm_acquisition()

acq = get_slm_acquisition(use_mock=True)
video_files = {
    'CH1': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH1_segment011_20260310_170803.mp4',
    'CH2': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH2_segment011_20260310_170803.mp4',
    'CH3': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH3_segment011_20260310_170803.mp4'
}

result = acq.set_video_file_mode(video_files, True)
print(f"设置结果: {result}")
print(f"配置: {acq.get_video_file_mode_config()}")

# 步骤2: 创建新实例（模拟API的start_acquisition行为）
print("\n2. 创建新实例并初始化")
reset_slm_acquisition()

acq2 = get_slm_acquisition(use_mock=True)
print(f"新实例ID: {id(acq2)}")
print(f"视频文件配置（初始化前）: video_file_mode={acq2._video_file_mode}, video_files={acq2._video_files}")

# 初始化
success = acq2.initialize(use_mock=True)
print(f"初始化结果: {success}")
print(f"视频文件配置（初始化后）: video_file_mode={acq2._video_file_mode}, video_files={acq2._video_files}")
print(f"Camera Manager类型: {type(acq2.camera_manager).__name__}")

if acq2.camera_manager:
    print(f"Camera Manager连接状态: {acq2.camera_manager.is_connected}")

# 步骤3: 启动采集
print("\n3. 启动采集")
acq2.start()
print(f"采集状态: {acq2.is_running}")

# 步骤4: 等待并检查帧
print("\n4. 等待2秒后检查帧")
time.sleep(2)

for ch in ['CH1', 'CH2', 'CH3']:
    frame = acq2.camera_manager.get_latest_frame(ch) if acq2.camera_manager else None
    jpeg = acq2.camera_manager.get_frame_jpeg(ch) if acq2.camera_manager else None
    print(f"{ch}: frame={frame is not None}, jpeg={len(jpeg) if jpeg else 0} bytes")

# 步骤5: 检查视频流生成器
print("\n5. 测试视频流生成器")

async def test_stream():
    from api.slm import video_stream_generator, get_acquisition
    
    # 检查API获取的实例
    api_acq = get_acquisition(create_if_none=False)
    print(f"API获取的实例ID: {id(api_acq) if api_acq else None}")
    print(f"与我们创建的实例相同: {api_acq is acq2}")
    
    if api_acq is None:
        print("错误: API无法获取实例！")
        return
    
    if api_acq.camera_manager is None:
        print("错误: API实例的camera_manager为None！")
        return
    
    # 测试生成器
    gen = video_stream_generator('CH1', 85)
    count = 0
    
    async for chunk in gen:
        count += 1
        print(f'收到第{count}个chunk, {len(chunk)} bytes')
        if count >= 3:
            break

asyncio.run(test_stream())

# 清理
print("\n6. 停止采集")
acq2.stop()
reset_slm_acquisition()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
