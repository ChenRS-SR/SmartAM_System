"""
FOTRIC 红外相机测试脚本
========================
测试红外相机连接并保存热像图

使用方法:
    python test_fotric.py

测试结果将保存在 ./test_images/fotric/ 目录下
"""

import os
import sys
import time
import cv2
import numpy as np
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def save_thermal_image(thermal_data, save_path, temp_min=None, temp_max=None):
    """
    将温度数据保存为伪彩色热像图
    
    Args:
        thermal_data: 温度矩阵 (numpy array)
        save_path: 保存路径
        temp_min: 最小温度（用于归一化）
        temp_max: 最大温度（用于归一化）
    """
    if thermal_data is None or thermal_data.size == 0:
        print("[错误] 没有有效的温度数据")
        return False
    
    # 计算温度范围
    if temp_min is None:
        temp_min = np.min(thermal_data)
    if temp_max is None:
        temp_max = np.max(thermal_data)
    
    # 归一化到 0-255
    if temp_max > temp_min:
        normalized = ((thermal_data - temp_min) / (temp_max - temp_min) * 255).astype(np.uint8)
    else:
        normalized = np.zeros_like(thermal_data, dtype=np.uint8)
    
    # 应用伪彩色映射 (JET)
    colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
    
    # 添加温度信息文字
    height, width = colored.shape[:2]
    info_text = f"Temp: {temp_min:.1f} ~ {temp_max:.1f}°C"
    cv2.putText(colored, info_text, (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # 保存图片
    cv2.imwrite(save_path, colored)
    return True


def test_fotric_camera(save_dir: str = "./test_images/fotric", num_images: int = 2, 
                       use_simulation: bool = False):
    """
    测试 FOTRIC 红外相机
    
    Args:
        save_dir: 图片保存目录
        num_images: 保存图片数量
        use_simulation: 是否使用模拟模式（没有真实设备时使用）
    """
    print("=" * 60)
    print("FOTRIC 红外相机测试 + 图片保存")
    print("=" * 60)
    
    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)
    print(f"[信息] 图片将保存到: {os.path.abspath(save_dir)}")
    
    try:
        from core.fotric_driver import FotricEnhancedDevice
    except ImportError as e:
        print(f"\n[错误] 无法导入 fotric_driver: {e}")
        return False
    
    # 创建设备对象
    print(f"\n[连接] 正在连接红外相机 (IP: 192.168.1.100, 模拟模式: {use_simulation})...")
    
    device = FotricEnhancedDevice(
        ip="192.168.1.100",
        port=10080,
        simulation_mode=use_simulation
    )
    
    # 连接状态在构造函数中已经确定
    if not device.is_connected:
        print("\n[错误] 无法连接到红外相机！")
        if not use_simulation:
            print("\n[建议]")
            print("  1. 检查相机是否通电并连接到网络")
            print("  2. 检查电脑和相机是否在同一网段（192.168.1.x）")
            print("  3. 尝试 ping 192.168.1.100 测试网络连通性")
            print("  4. 如果没有相机，可以添加 --simulation 参数使用模拟模式")
        return False
    
    print("\n[成功] 红外相机连接成功！")
    print(f"  - 分辨率: {device.width}x{device.height}")
    print(f"  - 模拟模式: {device.simulation_mode}")
    
    # 等待数据就绪
    print("\n[采集] 等待数据采集...")
    max_wait = 30 if not use_simulation else 3  # 真实设备等待更长时间
    waited = 0
    while device.get_thermal_data() is None and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5
        if int(waited) % 2 == 0:
            print(f"  等待中... ({int(waited)}/{max_wait}秒)")
    
    # 采集并保存图片
    print(f"\n[采集] 准备采集 {num_images} 张热像图...")
    print("[提示] 按 Ctrl+C 可随时中断\n")
    
    saved_count = 0
    
    try:
        while saved_count < num_images:
            # 获取最新热像数据
            thermal_data = device.get_thermal_data()
            
            if thermal_data is not None:
                # 获取温度统计
                stats = device.get_temperature_stats()
                if stats:
                    temp_min = stats['min_temp']
                    temp_max = stats['max_temp']
                    temp_avg = stats['avg_temp']
                else:
                    temp_min = np.min(thermal_data)
                    temp_max = np.max(thermal_data)
                    temp_avg = np.mean(thermal_data)
                
                # 生成文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"fotric_thermal_{timestamp}.png"
                filepath = os.path.join(save_dir, filename)
                
                # 保存热像图
                if save_thermal_image(thermal_data, filepath, temp_min, temp_max):
                    saved_count += 1
                    
                    print(f"[保存 {saved_count}/{num_images}] {filename}")
                    print(f"  - 分辨率: {thermal_data.shape[1]}x{thermal_data.shape[0]}")
                    print(f"  - 温度范围: {temp_min:.1f} ~ {temp_max:.1f}°C")
                    print(f"  - 平均温度: {temp_avg:.1f}°C")
                    print(f"  - 路径: {filepath}")
                    print()
                
                # 同时保存原始温度数据（NPZ格式，可用于后续分析）
                npz_filename = f"fotric_data_{timestamp}.npz"
                npz_filepath = os.path.join(save_dir, npz_filename)
                np.savez_compressed(npz_filepath, 
                                   thermal_data=thermal_data,
                                   temp_min=temp_min,
                                   temp_max=temp_max,
                                   timestamp=timestamp)
                print(f"  - 原始数据: {npz_filename}")
                print()
            else:
                print("[等待] 暂无热像数据...")
            
            # 间隔 2 秒采集下一张
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n[测试] 用户中断")
    
    # 断开连接
    device.disconnect()
    
    print(f"\n[完成] 共保存 {saved_count} 张热像图")
    
    if saved_count > 0:
        print(f"\n[成功] 图片已保存到: {os.path.abspath(save_dir)}")
        print("[提示] 热像图使用伪彩色显示（蓝色=低温，红色=高温）")
        print("[提示] 原始数据(.npz)可用 numpy 加载分析")
        return True
    else:
        print("\n[失败] 未能保存任何图片")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='FOTRIC 红外相机测试工具')
    parser.add_argument('--simulation', '-s', action='store_true', 
                        help='使用模拟模式（不需要真实设备）')
    parser.add_argument('--count', '-c', type=int, default=2,
                        help='保存图片数量 (默认: 2)')
    parser.add_argument('--output', '-o', type=str, default='./test_images/fotric',
                        help='输出目录 (默认: ./test_images/fotric)')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("SmartAM FOTRIC 红外相机测试工具")
    print("=" * 60)
    print()
    
    if args.simulation:
        print("[模式] 模拟模式 - 将生成模拟的热像数据")
    else:
        print("[模式] 真实设备模式 - 将尝试连接 192.168.1.100")
        print("[提示] 如果没有连接相机，请使用 --simulation 参数")
    print()
    
    # 运行测试
    success = test_fotric_camera(
        save_dir=args.output,
        num_images=args.count,
        use_simulation=args.simulation
    )
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试完成！")
    else:
        print("❌ 测试失败或未连接设备")
    print("=" * 60)


if __name__ == "__main__":
    main()
