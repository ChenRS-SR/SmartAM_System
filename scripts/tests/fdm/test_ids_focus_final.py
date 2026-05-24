#!/usr/bin/env python3
"""
IDS UI-1007XS-C 对焦优化测试（最终版）
根据官方软件参数设置
"""

import os
import sys
import time
import cv2
import numpy as np
from datetime import datetime

def test_focus_settings():
    print("=" * 60)
    print("IDS 相机对焦优化测试")
    print("=" * 60)
    
    try:
        from core.data_acquisition import get_acquisition
        
        print("\n[1/3] 连接 DAQ 系统...")
        daq = get_acquisition()
        
        print("[2/3] 初始化 IDS 相机...")
        if not daq._ids_camera:
            print("  尝试连接 IDS 相机...")
            daq.connect_device('ids')
        
        if not daq._ids_camera:
            print("[错误] IDS 相机连接失败")
            return
        
        print("  IDS 相机已连接")
        
        # 创建输出目录
        output_dir = f"./ids_focus_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n[3/3] 测试目录: {output_dir}")
        
        # 获取节点映射
        if not hasattr(daq, '_ids_nodemap') or not daq._ids_nodemap:
            print("[错误] 无法访问相机节点")
            return
        
        nodemap = daq._ids_nodemap
        
        # 测试 1: 当前设置
        print("\n  [测试 1/6] 保存当前设置图像...")
        frame = daq._get_ids_frame()
        if frame is not None:
            cv2.imwrite(os.path.join(output_dir, "01_current.jpg"), frame)
            print("    ✓ 已保存")
        
        # 测试 2: 尝试设置焦距（根据官方软件，参数名为 Focus）
        print("\n  [测试 2/6] 测试不同焦距...")
        print("    参考: 官方软件中当前焦距为 226")
        
        focus_values = [200, 220, 226, 240, 260]
        for focus in focus_values:
            try:
                # 尝试不同的节点名称
                success = False
                
                # 尝试 1: Focus
                try:
                    nodemap.FindNode("Focus").SetValue(float(focus))
                    success = True
                except:
                    pass
                
                # 尝试 2: FocusDistance
                if not success:
                    try:
                        nodemap.FindNode("FocusDistance").SetValue(float(focus))
                        success = True
                    except:
                        pass
                
                # 尝试 3: FocusPosition
                if not success:
                    try:
                        nodemap.FindNode("FocusPosition").SetValue(float(focus))
                        success = True
                    except:
                        pass
                
                if success:
                    time.sleep(0.5)
                    frame = daq._get_ids_frame()
                    if frame is not None:
                        cv2.imwrite(os.path.join(output_dir, f"02_focus_{focus}.jpg"), frame)
                        print(f"    ✓ 焦距 {focus}: 已保存")
                else:
                    print(f"    ! 焦距 {focus}: 无法设置")
                    
            except Exception as e:
                print(f"    ! 焦距 {focus}: {e}")
        
        # 测试 3: 尝试开启边缘增强
        print("\n  [测试 3/6] 测试边缘增强...")
        try:
            # 先恢复默认焦距
            try:
                nodemap.FindNode("Focus").SetValue(226.0)
            except:
                pass
            
            # 尝试设置边缘增强
            enhancement_values = [0, 50, 100, 150, 200]
            
            for enh in enhancement_values:
                try:
                    # 尝试不同的节点名称
                    success = False
                    
                    try:
                        nodemap.FindNode("EdgeEnhancement").SetValue(float(enh))
                        success = True
                    except:
                        pass
                    
                    try:
                        nodemap.FindNode("Sharpening").SetValue(float(enh))
                        success = True
                    except:
                        pass
                    
                    try:
                        nodemap.FindNode("EdgeEnhancementLevel").SetValue(float(enh))
                        success = True
                    except:
                        pass
                    
                    if success:
                        time.sleep(0.3)
                        frame = daq._get_ids_frame()
                        if frame is not None:
                            cv2.imwrite(os.path.join(output_dir, f"03_edge_{enh:03d}.jpg"), frame)
                            print(f"    ✓ 边缘增强 {enh}: 已保存")
                    else:
                        print(f"    ! 边缘增强 {enh}: 不支持")
                        break
                        
                except Exception as e:
                    print(f"    ! 边缘增强 {enh}: {e}")
                    break
        except Exception as e:
            print(f"    ! 边缘增强测试失败: {e}")
        
        # 测试 4: 尝试设置增益
        print("\n  [测试 4/6] 测试不同增益...")
        try:
            # 关闭自动增益
            try:
                nodemap.FindNode("GainAuto").SetCurrentEntry("Off")
                print("    已关闭自动增益")
            except:
                pass
            
            gain_values = [0, 6, 12, 18]
            for gain in gain_values:
                try:
                    nodemap.FindNode("Gain").SetValue(float(gain))
                    time.sleep(0.3)
                    frame = daq._get_ids_frame()
                    if frame is not None:
                        cv2.imwrite(os.path.join(output_dir, f"04_gain_{gain:02d}.jpg"), frame)
                        print(f"    ✓ 增益 {gain}dB: 已保存")
                except Exception as e:
                    print(f"    ! 增益 {gain}: {e}")
        except Exception as e:
            print(f"    ! 增益测试失败: {e}")
        
        # 测试 5: 尝试设置曝光
        print("\n  [测试 5/6] 测试不同曝光...")
        try:
            # 关闭自动曝光
            try:
                nodemap.FindNode("ExposureAuto").SetCurrentEntry("Off")
                print("    已关闭自动曝光")
            except:
                pass
            
            # 当前曝光约 66ms，测试附近值
            exposure_values = [50000, 66520, 80000]  # 单位：微秒
            for exp in exposure_values:
                try:
                    nodemap.FindNode("ExposureTime").SetValue(float(exp))
                    time.sleep(0.3)
                    frame = daq._get_ids_frame()
                    if frame is not None:
                        cv2.imwrite(os.path.join(output_dir, f"05_exp_{exp}.jpg"), frame)
                        print(f"    ✓ 曝光 {exp/1000:.1f}ms: 已保存")
                except Exception as e:
                    print(f"    ! 曝光 {exp}: {e}")
        except Exception as e:
            print(f"    ! 曝光测试失败: {e}")
        
        # 测试 6: 后处理锐化对比
        print("\n  [测试 6/6] 后处理锐化效果...")
        base_file = os.path.join(output_dir, "01_current.jpg")
        if os.path.exists(base_file):
            img = cv2.imread(base_file)
            
            # 轻度锐化
            gaussian = cv2.GaussianBlur(img, (0, 0), 3)
            light = cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)
            cv2.imwrite(os.path.join(output_dir, "06_sharpen_light.jpg"), light)
            print("    ✓ 轻度锐化")
            
            # 中度锐化
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            medium = cv2.filter2D(img, -1, kernel)
            cv2.imwrite(os.path.join(output_dir, "06_sharpen_medium.jpg"), medium)
            print("    ✓ 中度锐化")
            
            # 强力锐化（CLAHE）
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            enhanced = cv2.filter2D(enhanced, -1, kernel)
            cv2.imwrite(os.path.join(output_dir, "06_sharpen_strong.jpg"), enhanced)
            print("    ✓ 强力锐化 (CLAHE)")
        
        # 生成报告
        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)
        print(f"\n输出目录: {output_dir}")
        
        print("\n查看建议:")
        print("1. 查看 02_focus_XXX.jpg - 选择最清晰焦距")
        print("2. 查看 03_edge_XXX.jpg - 选择最佳边缘增强")
        print("3. 查看 04_gain_XX.jpg - 选择噪点少的增益")
        print("4. 查看 05_exp_XXXXX.jpg - 选择合适曝光")
        print("5. 查看 06_sharpen_XXX.jpg - 选择后处理效果")
        
        print("\n推荐设置（根据官方软件）:")
        print("  焦距: 226 (当前值)")
        print("  边缘增强: 50-100 (如支持)")
        print("  增益: 6dB (当前值)")
        print("  曝光: 66ms (当前值)")
        
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_focus_settings()
