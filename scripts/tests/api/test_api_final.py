"""测试API端点"""
import requests
import json

BASE_URL = "http://localhost:8000/api/slm"

def test_scan():
    """测试扫描视频文件"""
    print("=" * 60)
    print("测试: 扫描视频文件")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/video_file_mode/scan")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_correction_info():
    """测试获取矫正信息"""
    print("\n" + "=" * 60)
    print("测试: 获取畸变矫正信息")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/capture/correction_info")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_setup():
    """测试设置视频文件模式"""
    print("\n" + "=" * 60)
    print("测试: 设置视频文件模式")
    print("=" * 60)
    
    try:
        video_files = {
            'CH1': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH1_segment011_20260310_170803.mp4',
            'CH2': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH2_segment011_20260310_170803.mp4',
            'CH3': r'D:\FDM_Monitor_Diagnosis\SmartAM_System\simulation_record\CH3_segment011_20260310_170803.mp4'
        }
        
        response = requests.post(
            f"{BASE_URL}/video_file_mode/setup",
            json={
                'video_files': video_files,
                'enable_correction': True
            }
        )
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_config():
    """测试获取配置"""
    print("\n" + "=" * 60)
    print("测试: 获取视频文件模式配置")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/video_file_mode/config")
        result = response.json()
        print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result.get('success', False)
    except Exception as e:
        print(f"错误: {e}")
        return False

if __name__ == "__main__":
    print("\n开始测试API端点...")
    print("确保后端服务已启动: python -m backend.main\n")
    
    input("按Enter开始测试...")
    
    test_scan()
    test_correction_info()
    test_setup()
    test_config()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
