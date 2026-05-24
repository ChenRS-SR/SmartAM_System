"""
快速API测试 - 不需要用户输入
"""
import sys
import time
import requests

BASE_URL = "http://localhost:8000/api/slm"

def test_scan():
    """测试扫描视频文件"""
    print("=" * 60)
    print("1. 扫描视频文件")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/video_file_mode/scan", timeout=10)
        result = response.json()
        print(f"成功: {result.get('success')}")
        print(f"找到视频: {list(result.get('videos', {}).keys())}")
        return result.get('videos', {})
    except Exception as e:
        print(f"错误: {e}")
        return {}

def test_setup(videos):
    """测试设置视频文件模式"""
    print("\n" + "=" * 60)
    print("2. 设置视频文件模式")
    print("=" * 60)
    
    try:
        # 提取path字段
        video_files = {}
        for ch in ['CH1', 'CH2', 'CH3']:
            if ch in videos and videos[ch]:
                video_files[ch] = videos[ch]['path'] if isinstance(videos[ch], dict) else videos[ch]
        
        print(f"发送: {video_files}")
        
        response = requests.post(
            f"{BASE_URL}/video_file_mode/setup",
            json={'video_files': video_files, 'enable_correction': True},
            timeout=10
        )
        result = response.json()
        print(f"结果: {result.get('success')}, {result.get('message', 'OK')}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_start():
    """测试启动采集"""
    print("\n" + "=" * 60)
    print("3. 启动采集")
    print("=" * 60)
    
    try:
        # 先停止
        requests.post(f"{BASE_URL}/stop", timeout=5)
        time.sleep(1)
        
        response = requests.post(
            f"{BASE_URL}/start",
            params={'use_mock': True},
            timeout=10
        )
        result = response.json()
        print(f"结果: {result.get('success')}, {result.get('message', 'OK')}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_status():
    """测试获取状态"""
    print("\n" + "=" * 60)
    print("4. 获取状态")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/status", timeout=10)
        result = response.json()
        print(f"运行: {result.get('is_running')}")
        sensors = result.get('sensor_status', {})
        print(f"CH1: {sensors.get('camera_ch1', {})}")
        print(f"CH2: {sensors.get('camera_ch2', {})}")
        print(f"CH3: {sensors.get('thermal', {})}")
        return result.get('is_running', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_stream(channel, seconds=3):
    """测试视频流"""
    print("\n" + "=" * 60)
    print(f"5. 测试{channel}视频流 ({seconds}秒)")
    print("=" * 60)
    
    stream_url = f"{BASE_URL}/stream/camera/{channel}"
    print(f"URL: {stream_url}")
    
    try:
        import cv2
        cap = cv2.VideoCapture(stream_url)
        
        if not cap.isOpened():
            print("无法打开视频流")
            return False
        
        frames = 0
        import time
        start = time.time()
        
        while time.time() - start < seconds:
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

def main():
    print("\n" + "=" * 60)
    print("快速API测试")
    print("=" * 60)
    print("\n确保后端服务已启动: python -m backend.main\n")
    
    # 1. 扫描
    videos = test_scan()
    if not videos:
        print("\n未找到视频文件，测试结束")
        return
    
    # 2. 设置
    if not test_setup(videos):
        print("\n设置失败，测试结束")
        return
    
    # 3. 启动
    if not test_start():
        print("\n启动失败，测试结束")
        return
    
    # 4. 等待并检查状态
    time.sleep(2)
    test_status()
    
    # 5. 测试视频流
    test_stream('CH1', 3)
    test_stream('CH2', 3)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
