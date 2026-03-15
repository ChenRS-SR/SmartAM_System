"""
完整流程测试
============
测试视频文件模拟模式的完整流程
"""
import sys
import time
import requests
sys.path.insert(0, 'backend')

BASE_URL = "http://localhost:8000/api/slm"

def test_api_scan():
    """测试API扫描视频文件"""
    print("=" * 60)
    print("1. 测试API扫描视频文件")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/video_file_mode/scan")
        result = response.json()
        print(f"扫描结果: {result}")
        return result.get('success', False), result.get('videos', {})
    except Exception as e:
        print(f"错误: {e}")
        return False, {}

def test_api_setup(videos):
    """测试API设置视频文件模式"""
    print("\n" + "=" * 60)
    print("2. 测试API设置视频文件模式")
    print("=" * 60)
    
    try:
        # 提取path字段，构建正确的格式
        video_files = {}
        if 'CH1' in videos and videos['CH1']:
            video_files['CH1'] = videos['CH1']['path'] if isinstance(videos['CH1'], dict) else videos['CH1']
        if 'CH2' in videos and videos['CH2']:
            video_files['CH2'] = videos['CH2']['path'] if isinstance(videos['CH2'], dict) else videos['CH2']
        if 'CH3' in videos and videos['CH3']:
            video_files['CH3'] = videos['CH3']['path'] if isinstance(videos['CH3'], dict) else videos['CH3']
        
        print(f"发送的视频文件路径: {video_files}")
        
        response = requests.post(
            f"{BASE_URL}/video_file_mode/setup",
            json={
                'video_files': video_files,
                'enable_correction': True
            }
        )
        result = response.json()
        print(f"设置结果: {result}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_api_correction_info():
    """测试API获取畸变矫正信息"""
    print("\n" + "=" * 60)
    print("3. 测试API获取畸变矫正信息")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/capture/correction_info")
        result = response.json()
        print(f"矫正信息: {result}")
        return result.get('success', False), result
    except Exception as e:
        print(f"错误: {e}")
        return False, {}

def test_api_start():
    """测试API启动采集"""
    print("\n" + "=" * 60)
    print("4. 测试API启动采集")
    print("=" * 60)
    
    try:
        # 先停止
        requests.post(f"{BASE_URL}/stop")
        time.sleep(1)
        
        response = requests.post(
            f"{BASE_URL}/start",
            params={'use_mock': True}
        )
        result = response.json()
        print(f"启动结果: {result}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_api_status():
    """测试API获取状态"""
    print("\n" + "=" * 60)
    print("5. 测试API获取状态")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/status")
        result = response.json()
        print(f"运行状态: {result.get('is_running')}")
        print(f"传感器状态:")
        print(f"  camera_ch1: {result.get('sensor_status', {}).get('camera_ch1')}")
        print(f"  camera_ch2: {result.get('sensor_status', {}).get('camera_ch2')}")
        print(f"  thermal: {result.get('sensor_status', {}).get('thermal')}")
        return result.get('is_running', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_video_stream(channel, duration=3):
    """测试视频流"""
    print("\n" + "=" * 60)
    print(f"6. 测试视频流 ({channel})")
    print("=" * 60)
    
    try:
        import cv2
        
        stream_url = f"{BASE_URL}/stream/camera/{channel}"
        print(f"视频流URL: {stream_url}")
        
        # 使用OpenCV读取视频流
        cap = cv2.VideoCapture(stream_url)
        
        if not cap.isOpened():
            print(f"无法打开视频流: {stream_url}")
            return False
        
        frames = 0
        start_time = time.time()
        
        while time.time() - start_time < duration:
            ret, frame = cap.read()
            if ret:
                frames += 1
                if frames == 1:
                    print(f"第一帧: {frame.shape}")
        
        cap.release()
        print(f"共读取 {frames} 帧")
        return frames > 0
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_api_stop():
    """测试API停止采集"""
    print("\n" + "=" * 60)
    print("7. 测试API停止采集")
    print("=" * 60)
    
    try:
        response = requests.post(f"{BASE_URL}/stop")
        result = response.json()
        print(f"停止结果: {result}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("完整流程测试")
    print("=" * 60)
    print("\n确保后端服务已启动: python -m backend.main")
    print("")
    
    input("按Enter开始测试...")
    
    # 1. 扫描视频文件
    success, videos = test_api_scan()
    if not success or not videos:
        print("\n扫描视频文件失败，使用默认路径")
        videos = {
            'CH1': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH1_segment011_20260310_170803.mp4',
            'CH2': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH2_segment011_20260310_170803.mp4',
            'CH3': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH3_segment011_20260310_170803.mp4'
        }
    
    # 2. 设置视频文件模式
    if test_api_setup(videos):
        print("\n✓ 视频文件模式设置成功")
    else:
        print("\n✗ 视频文件模式设置失败")
    
    # 3. 获取畸变矫正信息
    if test_api_correction_info()[0]:
        print("\n✓ 获取畸变矫正信息成功")
    else:
        print("\n✗ 获取畸变矫正信息失败")
    
    # 4. 启动采集
    if test_api_start():
        print("\n✓ 采集启动成功")
    else:
        print("\n✗ 采集启动失败")
    
    # 5. 等待采集启动
    time.sleep(2)
    
    # 6. 获取状态
    if test_api_status():
        print("\n✓ 采集正在运行")
    else:
        print("\n✗ 采集未运行")
    
    # 7. 测试视频流
    if test_video_stream('CH1'):
        print("\n✓ CH1视频流正常")
    else:
        print("\n✗ CH1视频流异常")
    
    if test_video_stream('CH2'):
        print("\n✓ CH2视频流正常")
    else:
        print("\n✗ CH2视频流异常")
    
    # 8. 停止采集
    test_api_stop()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
