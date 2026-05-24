#!/usr/bin/env python3
"""
IDS UI-1007XS-C 相机对焦优化测试脚本（实际可用版本）
针对 3-5cm 近距离拍摄场景
"""

import os
import sys
import time
import cv2
import numpy as np
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_with_daq():
    """使用现有的 DAQ 系统测试"""
    print("=" * 60)
    print("IDS 相机对焦测试（使用 DAQ 系统）")
    print("=" * 60)
    
    try:
        from core.data_acquisition import get_acquisition
        
        print("\n[1/3] 连接 DAQ 系统...")
        daq = get_acquisition()
        
        # 初始化相机
        print("[2/3] 初始化 IDS 相机...")
        if not daq._ids_camera:
            print("  尝试连接 IDS 相机...")
            daq.connect_device('ids')
        
        if not daq._ids_camera:
            print("[错误] IDS 相机连接失败")
            return
        
        print("  IDS 相机已连接")
        
        # 创建输出目录
        output_dir = f"./ids_focus_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n[3/3] 开始测试...")
        print(f"  输出目录: {output_dir}")
        
        # 测试 1: 当前设置下的图像
        print("\n  [测试 1/4] 当前设置...")
        frame = daq._get_ids_frame()
        if frame is not None:
            cv2.imwrite(os.path.join(output_dir, "01_current_setting.jpg"), frame)
            print("    ✓ 已保存当前设置图像")
        
        # 测试 2: 尝试设置对焦（如果支持）
        print("\n  [测试 2/4] 尝试设置对焦距离...")
        try:
            # 尝试访问相机节点设置对焦
            if hasattr(daq, '_ids_nodemap') and daq._ids_nodemap:
                nodemap = daq._ids_nodemap
                
                # 检查是否支持 FocusDistance
                try:
                    # 关闭自动对焦
                    nodemap.FindNode("FocusAuto").SetCurrentEntry("Off")
                    print("    已关闭自动对焦")
                    
                    # 设置对焦距离 40mm (4cm)
                    nodemap.FindNode("FocusDistance").SetValue(40.0)
                    print("    已设置对焦距离: 40mm")
                    
                    time.sleep(0.5)
                    frame = daq._get_ids_frame()
                    if frame is not None:
                        cv2.imwrite(os.path.join(output_dir, "02_focus_40mm.jpg"), frame)
                        print("    ✓ 已保存 40mm 对焦图像")
                    
                    # 尝试 35mm
                    nodemap.FindNode("FocusDistance").SetValue(35.0)
                    time.sleep(0.5)
                    frame = daq._get_ids_frame()
                    if frame is not None:
                        cv2.imwrite(os.path.join(output_dir, "03_focus_35mm.jpg"), frame)
                        print("    ✓ 已保存 35mm 对焦图像")
                    
                    # 尝试 50mm
                    nodemap.FindNode("FocusDistance").SetValue(50.0)
                    time.sleep(0.5)
                    frame = daq._get_ids_frame()
                    if frame is not None:
                        cv2.imwrite(os.path.join(output_dir, "04_focus_50mm.jpg"), frame)
                        print("    ✓ 已保存 50mm 对焦图像")
                        
                except Exception as e:
                    print(f"    ! 对焦设置可能不支持: {e}")
                    print("    ! 使用自动对焦模式")
                    try:
                        nodemap.FindNode("FocusAuto").SetCurrentEntry("Once")
                        time.sleep(1.0)
                        frame = daq._get_ids_frame()
                        if frame is not None:
                            cv2.imwrite(os.path.join(output_dir, "02_auto_focus.jpg"), frame)
                            print("    ✓ 已保存自动对焦图像")
                    except Exception as e2:
                        print(f"    ! 自动对焦也失败: {e2}")
        except Exception as e:
            print(f"    ! 无法设置对焦: {e}")
        
        # 测试 3: 不同增益
        print("\n  [测试 3/4] 测试不同增益...")
        try:
            if hasattr(daq, '_ids_nodemap') and daq._ids_nodemap:
                nodemap = daq._ids_nodemap
                
                for gain in [0, 10, 20, 30]:
                    try:
                        nodemap.FindNode("Gain").SetValue(float(gain))
                        time.sleep(0.3)
                        frame = daq._get_ids_frame()
                        if frame is not None:
                            cv2.imwrite(os.path.join(output_dir, f"05_gain_{gain:02d}.jpg"), frame)
                            print(f"    ✓ 已保存增益 {gain} 图像")
                    except Exception as e:
                        print(f"    ! 增益 {gain} 设置失败: {e}")
        except Exception as e:
            print(f"    ! 无法测试增益: {e}")
        
        # 测试 4: 后处理锐化
        print("\n  [测试 4/4] 后处理锐化效果...")
        original_file = os.path.join(output_dir, "01_current_setting.jpg")
        if os.path.exists(original_file):
            img = cv2.imread(original_file)
            
            # Unsharp Mask
            gaussian = cv2.GaussianBlur(img, (0, 0), 3)
            unsharp = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
            cv2.imwrite(os.path.join(output_dir, "06_sharpen_unsharp.jpg"), unsharp)
            print("    ✓ 已保存 Unsharp Mask 锐化")
            
            # Laplacian
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            laplacian = cv2.filter2D(img, -1, kernel)
            cv2.imwrite(os.path.join(output_dir, "07_sharpen_laplacian.jpg"), laplacian)
            print("    ✓ 已保存 Laplacian 锐化")
            
            # CLAHE + 锐化
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            enhanced = cv2.filter2D(enhanced, -1, kernel)
            cv2.imwrite(os.path.join(output_dir, "08_sharpen_clahe.jpg"), enhanced)
            print("    ✓ 已保存 CLAHE + 锐化")
        
        # 生成报告
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        print(f"\n输出目录: {output_dir}")
        print("\n文件说明:")
        print("  01_current_setting.jpg   - 当前设置")
        print("  02_focus_40mm.jpg        - 对焦 40mm (如支持)")
        print("  03_focus_35mm.jpg        - 对焦 35mm (如支持)")
        print("  04_focus_50mm.jpg        - 对焦 50mm (如支持)")
        print("  02_auto_focus.jpg        - 自动对焦 (如不支持手动)")
        print("  05_gain_XX.jpg           - 不同增益测试")
        print("  06_sharpen_unsharp.jpg   - Unsharp Mask 锐化")
        print("  07_sharpen_laplacian.jpg - Laplacian 锐化")
        print("  08_sharpen_clahe.jpg     - CLAHE + 锐化")
        
        print("\n建议:")
        print("1. 查看所有图像，选择最清晰的一张")
        print("2. 如果对焦图像有差异，使用该对焦距离")
        print("3. 选择噪点和清晰度平衡的增益值")
        print("4. 如果原图不够清晰，考虑使用锐化后的图像")
        
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_daq()
