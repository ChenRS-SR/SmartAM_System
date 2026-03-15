"""调试视频流"""
import sys
import time
import asyncio
sys.path.insert(0, 'backend')

from core.slm import get_slm_acquisition, reset_slm_acquisition

# 重置
reset_slm_acquisition()

# 获取实例
acq = get_slm_acquisition(use_mock=True)

# 设置视频文件
video_files = {
    'CH1': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH1_segment011_20260310_170803.mp4',
    'CH2': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH2_segment011_20260310_170803.mp4',
    'CH3': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH3_segment011_20260310_170803.mp4'
}
acq.set_video_file_mode(video_files, True)

# 初始化
acq.initialize(use_mock=True)
print(f'初始化完成: camera_manager={type(acq.camera_manager).__name__}')
print(f'连接状态: {acq.camera_manager.is_connected}')

# 启动
acq.start()
print('采集已启动')

# 等待
time.sleep(2)

# 检查帧
for ch in ['CH1', 'CH2', 'CH3']:
    frame = acq.camera_manager.get_latest_frame(ch)
    jpeg = acq.camera_manager.get_frame_jpeg(ch)
    print(f'{ch}: frame={frame is not None}, jpeg={len(jpeg) if jpeg else 0} bytes')

# 测试视频流生成器
print('\n=== 测试视频流生成器 ===')

async def test_generator():
    from api.slm import video_stream_generator
    
    gen = video_stream_generator('CH1', 85)
    count = 0
    
    async for chunk in gen:
        count += 1
        print(f'收到第{count}个chunk, {len(chunk)} bytes')
        if count >= 3:
            break

asyncio.run(test_generator())

acq.stop()
print('测试完成')
