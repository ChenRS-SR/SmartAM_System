"""
DAQ 简化测试脚本
===============
快速测试数据采集系统的基本功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("="*60)
print("SmartAM DAQ 简化测试")
print("="*60)

# 1. 测试导入
print("\n[1/5] 测试导入...")
try:
    from core.data_acquisition import get_acquisition, AcquisitionConfig
    print("[OK] 导入成功")
except Exception as e:
    print(f"[ERROR] 导入失败: {e}")
    sys.exit(1)

# 2. 创建实例
print("\n[2/5] 创建 DAQ 实例...")
try:
    config = AcquisitionConfig(
        save_directory="./test_data",
        capture_fps=1.0  # 1fps for testing
    )
    daq = get_acquisition(config)
    print("[OK] DAQ 实例创建成功")
    print(f"  配置: fps={config.capture_fps}, save_dir={config.save_directory}")
except Exception as e:
    print(f"[ERROR] 创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. 初始化
print("\n[3/5] 初始化 DAQ...")
try:
    if daq.initialize():
        print("[OK] 初始化成功")
    else:
        print("[ERROR] 初始化失败")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] 初始化异常: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 启动采集（短暂）
print("\n[4/5] 启动数据采集 (3秒)...")
import time
try:
    if daq.start():
        print("[OK] 采集已启动")
        
        # 运行 3 秒
        for i in range(3):
            time.sleep(1)
            status = daq.get_status()
            print(f"  [{i+1}s] 帧数: {status['frame_count']}, 状态: {status['state']}")
        
        # 停止
        daq.stop()
        print("[OK] 采集已停止")
    else:
        print("[ERROR] 启动失败")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] 采集异常: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. 清理
print("\n[5/5] 清理...")
try:
    daq._close_devices()
    print("[OK] 清理完成")
except Exception as e:
    print(f"[ERROR] 清理失败: {e}")

print("\n" + "="*60)
print("[SUCCESS] 所有测试通过！")
print("="*60)
print("\n你可以运行以下命令进行更详细的测试:")
print("  python test_daq.py --simulation")
print("  python test_daq.py --duration 60")
