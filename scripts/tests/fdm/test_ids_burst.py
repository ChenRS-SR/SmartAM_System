#!/usr/bin/env python3
"""
IDS UI-1007XS-C 连拍测试脚本
针对不支持手动对焦的定焦镜头，通过多张拍摄选择最清晰图像
"""

import os
import sys
import time
import cv2
import numpy as np
from datetime import datetime

def capture_burst(daq, output_dir, prefix="burst", count=10, interval=0.5):
    """连拍多张图像"""
    print(f"\n  连拍 {count} 张图像，间隔 {interval} 秒...")
    
    captured = []
    for i in range(count):
        try:
            frame = daq._get_ids_frame()
            if frame is not None:
                filename = f"{prefix}_{i+1:02d}.jpg"
                filepath = os.path.join(output_dir, filename)
                cv2.imwrite(filepath, frame)
                captured.append(filepath)
                print(f"    ✓ [{i+1}/{count}] {filename}")
            else:
                print(f"    ✗ [{i+1}/{count}] 获取失败")
        except Exception as e:
            print(f"    ✗ [{i+1}/{count}] 错误: {e}")
        
        if i < count - 1:
            time.sleep(interval)
    
    return captured

def apply_sharpening(image, method="unsharp"):
    """应用锐化算法"""
    if method == "unsharp":
        gaussian = cv2.GaussianBlur(image, (0, 0), 3)
        return cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
    elif method == "laplacian":
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(image, -1, kernel)
    elif method == "clahe":
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(enhanced, -1, kernel)
    return image

def main():
    print("=" * 60)
    print("IDS 相机连拍测试（定焦镜头优化）")
    print("=" * 60)
    
    try:
        from core.data_acquisition import get_acquisition
        
        print("\n[1/4] 连接 DAQ 系统...")
        daq = get_acquisition()
        
        print("[2/4] 初始化 IDS 相机...")
        if not daq._ids_camera:
            print("  尝试连接 IDS 相机...")
            daq.connect_device('ids')
        
        if not daq._ids_camera:
            print("[错误] IDS 相机连接失败")
            return
        
        print("  IDS 相机已连接")
        print("  注意: 该相机为定焦镜头，不支持手动对焦调节")
        
        # 创建输出目录
        output_dir = f"./ids_burst_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(output_dir, exist_ok=True)
        print(f"\n[3/4] 输出目录: {output_dir}")
        
        # 测试 1: 快速连拍（0.5秒间隔）
        print("\n  [测试 1/5] 快速连拍 10 张（间隔 0.5秒）...")
        print("  提示: 打印头移动中拍摄，观察运动模糊情况")
        burst_files = capture_burst(daq, output_dir, "burst_fast", 10, 0.5)
        
        # 测试 2: 慢速连拍（2秒间隔）
        print("\n  [测试 2/5] 慢速连拍 5 张（间隔 2秒）...")
        print("  提示: 打印头静止时拍摄，观察最佳清晰度")
        burst_slow_files = capture_burst(daq, output_dir, "burst_slow", 5, 2.0)
        
        # 测试 3: 长时间曝光测试
        print("\n  [测试 3/5] 检查曝光设置...")
        try:
            if hasattr(daq, '_ids_nodemap') and daq._ids_nodemap:
                nodemap = daq._ids_nodemap
                
                # 尝试读取当前曝光
                try:
                    exposure = nodemap.FindNode("ExposureTime").Value()
                    print(f"    当前曝光时间: {exposure} μs")
                except:
                    print("    无法读取曝光时间")
                
                # 尝试读取增益
                try:
                    gain = nodemap.FindNode("Gain").Value()
                    print(f"    当前增益: {gain} dB")
                except:
                    print("    无法读取增益")
                
                # 保存当前设置图像
                frame = daq._get_ids_frame()
                if frame is not None:
                    cv2.imwrite(os.path.join(output_dir, "current_settings.jpg"), frame)
                    print("    ✓ 已保存当前设置图像")
        except Exception as e:
            print(f"    无法获取参数: {e}")
        
        # 测试 4: 后处理锐化（使用第一张快速连拍图像）
        print("\n  [测试 4/5] 后处理锐化效果...")
        if burst_files:
            img = cv2.imread(burst_files[0])
            
            # 轻度锐化
            light = apply_sharpening(img, "unsharp")
            cv2.imwrite(os.path.join(output_dir, "sharpen_light.jpg"), light)
            print("    ✓ 轻度锐化 (unsharp)")
            
            # 中度锐化
            medium = apply_sharpening(img, "laplacian")
            cv2.imwrite(os.path.join(output_dir, "sharpen_medium.jpg"), medium)
            print("    ✓ 中度锐化 (laplacian)")
            
            # 强力锐化
            strong = apply_sharpening(img, "clahe")
            cv2.imwrite(os.path.join(output_dir, "sharpen_strong.jpg"), strong)
            print("    ✓ 强力锐化 (clahe)")
        
        # 测试 5: 图像质量分析
        print("\n  [测试 5/5] 图像质量分析...")
        if burst_files:
            print("\n    图像清晰度评分（越高越清晰）:")
            scores = []
            for f in burst_files:
                img = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    # 使用 Laplacian 方差评估清晰度
                    score = cv2.Laplacian(img, cv2.CV_64F).var()
                    scores.append((os.path.basename(f), score))
            
            # 排序
            scores.sort(key=lambda x: x[1], reverse=True)
            
            print("\n    排名:")
            for i, (name, score) in enumerate(scores[:5], 1):
                marker = " ★" if i == 1 else ""
                print(f"      {i}. {name}: {score:.2f}{marker}")
            
            # 推荐最佳图像
            if scores:
                best_file = scores[0][0]
                print(f"\n    推荐最佳图像: {best_file}")
        
        # 生成报告
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        print(f"\n输出目录: {output_dir}")
        
        print("\n文件说明:")
        print("  burst_fast_XX.jpg    - 快速连拍（0.5秒间隔）")
        print("  burst_slow_XX.jpg    - 慢速连拍（2秒间隔，推荐选最清晰的）")
        print("  current_settings.jpg - 当前相机设置")
        print("  sharpen_light.jpg    - 轻度锐化")
        print("  sharpen_medium.jpg   - 中度锐化")
        print("  sharpen_strong.jpg   - 强力锐化")
        
        print("\n建议:")
        print("1. 查看 burst_slow_XX.jpg 系列，选择最清晰的一张")
        print("2. 对比 sharpen_XXX.jpg，选择最佳锐化效果")
        print("3. 如果原图不清晰，考虑在系统中启用实时锐化")
        print("4. 连拍可以在打印头静止时捕捉到更清晰的图像")
        
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
