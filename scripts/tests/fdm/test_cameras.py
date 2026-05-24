"""
相机测试脚本
============
测试旁轴相机和 IDS 相机，并保存图片

使用方法:
    python test_cameras.py

测试结果将保存在 ./test_images/ 目录下
"""

import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_side_camera():
    """测试旁轴相机"""
    print("\n" + "="*60)
    print("测试 1: 旁轴相机 (罗技 USB 摄像头)")
    print("="*60)
    
    try:
        from core.side_camera import test_camera_and_save_images
        count = test_camera_and_save_images(save_dir="./test_images/side", num_images=2)
        return count > 0
    except Exception as e:
        print(f"[错误] 旁轴相机测试失败: {e}")
        return False


def test_ids_camera():
    """测试 IDS 相机"""
    print("\n" + "="*60)
    print("测试 2: IDS 工业相机 (随轴相机)")
    print("="*60)
    
    try:
        from core.ids_camera import test_camera_and_save_images
        count = test_camera_and_save_images(save_dir="./test_images/ids", num_images=2)
        return count > 0
    except Exception as e:
        print(f"[错误] IDS 相机测试失败: {e}")
        return False


def main():
    """主函数"""
    print("="*60)
    print("SmartAM 相机测试工具")
    print("="*60)
    print("\n[说明] 此脚本将测试两个相机并保存图片")
    print("[说明] 如果没有连接相机，会显示错误信息")
    print("[说明] 图片将保存在 ./test_images/ 目录下\n")
    
    # 测试旁轴相机
    side_ok = test_side_camera()
    
    # 测试 IDS 相机
    ids_ok = test_ids_camera()
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    
    if side_ok:
        print("[✓] 旁轴相机: 成功")
        print(f"    图片位置: {os.path.abspath('./test_images/side')}")
    else:
        print("[✗] 旁轴相机: 失败或未连接")
    
    if ids_ok:
        print("[✓] IDS 相机: 成功")
        print(f"    图片位置: {os.path.abspath('./test_images/ids')}")
    else:
        print("[✗] IDS 相机: 失败或未连接")
    
    if side_ok or ids_ok:
        print("\n[成功] 至少有一个相机工作正常！")
        print("[提示] 请查看 ./test_images/ 目录下的图片")
    else:
        print("\n[注意] 两个相机都未连接或初始化失败")
        print("[提示] 这是正常的，如果你现在没有连接硬件")
    
    print("\n" + "="*60)
    input("按回车键退出...")


if __name__ == "__main__":
    main()
