"""
测试API端点
============
"""

import requests
import time

BASE_URL = "http://localhost:8000/api/slm"

def test_setup_video_file_mode():
    """设置视频文件模式"""
    print("=" * 60)
    print("测试: 设置视频文件模式")
    print("=" * 60)
    
    try:
        response = requests.post(f"{BASE_URL}/video_file_mode/setup", params={
            'ch1_video': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH1_segment011_20260310_170803.mp4',
            'ch2_video': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH2_segment011_20260310_170803.mp4',
            'ch3_video': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH3_segment011_20260310_170803.mp4',
            'enable_correction': True
        })
        result = response.json()
        print(f"响应: {result}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_get_config():
    """获取配置"""
    print("\n" + "=" * 60)
    print("测试: 获取视频文件模式配置")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/video_file_mode/config")
        result = response.json()
        print(f"响应: {result}")
        return result.get('enabled', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_start_acquisition():
    """启动采集"""
    print("\n" + "=" * 60)
    print("测试: 启动采集(模拟模式)")
    print("=" * 60)
    
    try:
        # 先停止
        requests.post(f"{BASE_URL}/stop")
        time.sleep(1)
        
        response = requests.post(f"{BASE_URL}/start", params={
            'use_mock': True
        })
        result = response.json()
        print(f"响应: {result}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_get_status():
    """获取状态"""
    print("\n" + "=" * 60)
    print("测试: 获取采集状态")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/status")
        result = response.json()
        print(f"运行状态: {result.get('is_running')}")
        print(f"摄像头CH1: {result.get('sensor_status', {}).get('camera_ch1')}")
        print(f"摄像头CH2: {result.get('sensor_status', {}).get('camera_ch2')}")
        return result.get('is_running', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == "__main__":
    print("\n开始测试API端点...")
    print("确保后端服务已启动: python -m backend.main\n")
    
    input("按Enter开始测试...")
    
    # 测试设置视频文件模式
    if test_setup_video_file_mode():
        print("\n✓ 视频文件模式设置成功")
    else:
        print("\n✗ 视频文件模式设置失败")
    
    # 获取配置
    if test_get_config():
        print("\n✓ 视频文件模式已启用")
    else:
        print("\n✗ 视频文件模式未启用")
    
    # 启动采集
    if test_start_acquisition():
        print("\n✓ 采集启动成功")
    else:
        print("\n✗ 采集启动失败")
    
    # 等待采集启动
    time.sleep(2)
    
    # 获取状态
    if test_get_status():
        print("\n✓ 采集正在运行")
    else:
        print("\n✗ 采集未运行")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    print("\n现在可以在浏览器中打开视频流查看:")
    print(f"  CH1: http://localhost:8000/api/slm/stream/camera/CH1")
    print(f"  CH2: http://localhost:8000/api/slm/stream/camera/CH2")
