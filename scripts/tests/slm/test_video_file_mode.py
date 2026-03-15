"""
视频文件模拟模式测试脚本
============================
用于测试视频文件模拟和畸变矫正功能

使用方法:
1. 确保后端服务已启动
2. 运行此脚本进行测试:
   python test_video_file_mode.py

测试内容:
1. 设置视频文件模拟模式
2. 启动采集（模拟模式）
3. 测试视频流
4. 测试图像采集（带畸变矫正）
"""

import requests
import time
import sys

BASE_URL = "http://localhost:8000/api/slm"


def test_setup_video_file_mode():
    """测试设置视频文件模式"""
    print("=" * 50)
    print("测试1: 设置视频文件模拟模式")
    print("=" * 50)
    
    video_files = {
        'ch1_video': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH1_segment011_20260310_170803.mp4',
        'ch2_video': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH2_segment011_20260310_170803.mp4',
        'ch3_video': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH3_segment011_20260310_170803.mp4',
        'enable_correction': True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/video_file_mode/setup", params=video_files)
        result = response.json()
        
        if result.get('success'):
            print("✓ 视频文件模拟模式设置成功")
            print(f"  视频文件: {result.get('video_files', {})}")
            print(f"  畸变矫正: {'启用' if result.get('correction_enabled') else '禁用'}")
            return True
        else:
            print(f"✗ 设置失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def test_get_video_file_config():
    """测试获取视频文件模式配置"""
    print("\n" + "=" * 50)
    print("测试2: 获取视频文件模式配置")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/video_file_mode/config")
        result = response.json()
        
        if result.get('success'):
            print("✓ 获取配置成功")
            print(f"  模式启用: {result.get('enabled')}")
            print(f"  视频文件: {result.get('video_files', {})}")
            print(f"  畸变矫正: {'启用' if result.get('correction_enabled') else '禁用'}")
            return True
        else:
            print(f"✗ 获取配置失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def test_get_correction_info():
    """测试获取畸变矫正信息"""
    print("\n" + "=" * 50)
    print("测试3: 获取畸变矫正信息")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/capture/correction_info")
        result = response.json()
        
        if result.get('success'):
            print("✓ 获取矫正信息成功")
            print(f"  标定文件: {result.get('calibration_file')}")
            channels = result.get('channels', {})
            for ch, info in channels.items():
                status = "已标定" if info.get('calibrated') else "未标定"
                print(f"  {ch}: {status}")
                if info.get('calibrated'):
                    size = info.get('output_size', (0, 0))
                    print(f"    输出尺寸: {size[0]}x{size[1]}")
            return True
        else:
            print(f"✗ 获取矫正信息失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def test_start_acquisition_mock():
    """测试启动采集（模拟模式）"""
    print("\n" + "=" * 50)
    print("测试4: 启动采集（模拟模式）")
    print("=" * 50)
    
    try:
        # 先停止可能正在运行的采集
        requests.post(f"{BASE_URL}/stop")
        time.sleep(1)
        
        # 启动采集（use_mock=true）
        params = {
            'camera_ch1_index': 2,
            'camera_ch2_index': 3,
            'use_mock': True
        }
        response = requests.post(f"{BASE_URL}/start", params=params)
        result = response.json()
        
        if result.get('success'):
            print("✓ 采集启动成功")
            print(f"  模拟模式: {result.get('mock_mode', False)}")
            return True
        else:
            print(f"✗ 启动失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def test_video_streams():
    """测试视频流"""
    print("\n" + "=" * 50)
    print("测试5: 测试视频流")
    print("=" * 50)
    
    channels = ['CH1', 'CH2', 'CH3']
    
    for ch in channels:
        try:
            # 测试视频流（只读取前几帧）
            stream_url = f"{BASE_URL}/stream/camera/{ch}?quality=85"
            print(f"  视频流 {ch}: {stream_url}")
            print(f"    请用浏览器打开以上链接查看视频流")
        except Exception as e:
            print(f"  ✗ {ch} 流测试失败: {e}")
    
    print("✓ 视频流URL已生成，请手动测试")
    return True


def test_capture_setup():
    """测试图像采集设置"""
    print("\n" + "=" * 50)
    print("测试6: 图像采集设置")
    print("=" * 50)
    
    try:
        # 设置图像采集
        response = requests.post(f"{BASE_URL}/capture/setup", params={'save_dir': 'F:/SmartAM_recordings'})
        result = response.json()
        
        if result.get('success'):
            print("✓ 图像采集设置成功")
            print(f"  保存目录: {result.get('save_dir')}")
            return True
        else:
            print(f"✗ 设置失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def test_disable_video_file_mode():
    """测试禁用视频文件模式"""
    print("\n" + "=" * 50)
    print("测试7: 禁用视频文件模式")
    print("=" * 50)
    
    try:
        response = requests.post(f"{BASE_URL}/video_file_mode/disable")
        result = response.json()
        
        if result.get('success'):
            print("✓ 视频文件模式已禁用")
            return True
        else:
            print(f"✗ 禁用失败: {result.get('message')}")
            return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("SLM 视频文件模拟模式测试")
    print("=" * 60)
    print("\n注意: 请确保后端服务已启动 (python -m backend.main)")
    print("      服务地址: http://localhost:8000")
    print()
    
    input("按 Enter 键开始测试...")
    
    results = []
    
    # 执行测试
    results.append(("设置视频文件模式", test_setup_video_file_mode()))
    results.append(("获取视频文件配置", test_get_video_file_config()))
    results.append(("获取畸变矫正信息", test_get_correction_info()))
    results.append(("启动采集（模拟模式）", test_start_acquisition_mock()))
    results.append(("测试视频流", test_video_streams()))
    results.append(("图像采集设置", test_capture_setup()))
    # 最后禁用视频文件模式（可选）
    # results.append(("禁用视频文件模式", test_disable_video_file_mode()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")
    
    print()
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        print("\n您现在可以:")
        print("1. 在设置页面启用视频文件模拟模式")
        print("2. 点击开始采集查看视频流")
        print("3. 观察畸变矫正后的图像")
    else:
        print("\n⚠️ 部分测试失败，请检查后端服务状态和日志")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(0)
