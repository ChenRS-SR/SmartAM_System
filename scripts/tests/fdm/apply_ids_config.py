#!/usr/bin/env python3
"""
应用 IDS 相机配置文件
加载在官方软件中调好的参数
"""

import os
import sys
import time

def apply_config_from_software():
    """
    应用官方软件中的参数设置
    参考值：焦距 226，边缘增强 50-100
    """
    print("=" * 60)
    print("应用 IDS 相机优化配置")
    print("=" * 60)
    
    try:
        from core.data_acquisition import get_acquisition
        
        print("\n[1/2] 连接相机...")
        daq = get_acquisition()
        
        if not daq._ids_camera:
            print("  连接 IDS 相机...")
            daq.connect_device('ids')
        
        if not daq._ids_camera:
            print("[错误] 相机连接失败")
            return False
        
        print("  相机已连接")
        
        if not hasattr(daq, '_ids_nodemap') or not daq._ids_nodemap:
            print("[错误] 无法访问相机节点")
            return False
        
        nodemap = daq._ids_nodemap
        
        print("\n[2/2] 应用优化参数...")
        
        # 1. 设置焦距（根据官方软件参考值 226）
        print("\n  设置焦距...")
        focus_set = False
        for focus_val in [226, 220, 240]:
            try:
                # 尝试 Focus 节点
                nodemap.FindNode("Focus").SetValue(float(focus_val))
                print(f"    ✓ 焦距设置为: {focus_val}")
                focus_set = True
                break
            except:
                try:
                    nodemap.FindNode("FocusDistance").SetValue(float(focus_val))
                    print(f"    ✓ 焦距设置为: {focus_val}")
                    focus_set = True
                    break
                except:
                    continue
        
        if not focus_set:
            print("    ! 无法设置焦距，使用默认值")
        
        # 2. 设置边缘增强
        print("\n  设置边缘增强...")
        edge_set = False
        for edge_val in [50, 75, 100]:
            try:
                nodemap.FindNode("EdgeEnhancement").SetValue(float(edge_val))
                print(f"    ✓ 边缘增强设置为: {edge_val}")
                edge_set = True
                break
            except:
                try:
                    nodemap.FindNode("Sharpening").SetValue(float(edge_val))
                    print(f"    ✓ 锐化设置为: {edge_val}")
                    edge_set = True
                    break
                except:
                    continue
        
        if not edge_set:
            print("    ! 无法设置边缘增强")
        
        # 3. 设置增益（关闭自动，手动设置）
        print("\n  设置增益...")
        try:
            nodemap.FindNode("GainAuto").SetCurrentEntry("Off")
            nodemap.FindNode("Gain").SetValue(6.0)
            print("    ✓ 增益设置为: 6dB")
        except Exception as e:
            print(f"    ! 无法设置增益: {e}")
        
        # 4. 设置曝光（可选，保持自动可能更好）
        # print("\n  设置曝光...")
        # try:
        #     nodemap.FindNode("ExposureAuto").SetCurrentEntry("Off")
        #     nodemap.FindNode("ExposureTime").SetValue(66520.0)
        #     print("    ✓ 曝光设置为: 66.52ms")
        # except Exception as e:
        #     print(f"    ! 无法设置曝光: {e}")
        
        # 5. 保存设置到相机内存（如果支持）
        print("\n  保存设置...")
        try:
            nodemap.FindNode("UserSetSelector").SetCurrentEntry("UserSet1")
            nodemap.FindNode("UserSetSave").Execute()
            print("    ✓ 设置已保存到 UserSet1")
        except Exception as e:
            print(f"    ! 无法保存设置: {e}")
        
        # 测试拍摄
        print("\n  测试拍摄...")
        time.sleep(0.5)
        frame = daq._get_ids_frame()
        if frame is not None:
            output_file = "./ids_optimized.jpg"
            import cv2
            cv2.imwrite(output_file, frame)
            print(f"    ✓ 测试图像已保存: {output_file}")
        
        print("\n" + "=" * 60)
        print("配置应用完成!")
        print("=" * 60)
        print("\n当前设置:")
        print("  焦距: 226 (或最接近值)")
        print("  边缘增强: 50-100 (如支持)")
        print("  增益: 6dB")
        print("  曝光: 自动")
        
        return True
        
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        return False

def check_current_settings():
    """查看当前相机设置"""
    print("\n查看当前相机设置...")
    
    try:
        from core.data_acquisition import get_acquisition
        daq = get_acquisition()
        
        if not daq._ids_camera:
            print("  相机未连接")
            return
        
        if not hasattr(daq, '_ids_nodemap') or not daq._ids_nodemap:
            print("  无法访问节点")
            return
        
        nodemap = daq._ids_nodemap
        
        settings = {}
        
        # 尝试读取各种参数
        params_to_check = [
            ("Focus", "焦距"),
            ("FocusDistance", "对焦距离"),
            ("Gain", "增益"),
            ("ExposureTime", "曝光时间"),
            ("EdgeEnhancement", "边缘增强"),
            ("Sharpening", "锐化"),
        ]
        
        for param, name in params_to_check:
            try:
                value = nodemap.FindNode(param).Value()
                settings[name] = value
            except:
                pass
        
        if settings:
            print("\n  当前设置:")
            for name, value in settings.items():
                print(f"    {name}: {value}")
        else:
            print("  无法读取设置")
            
    except Exception as e:
        print(f"  错误: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="IDS 相机配置工具")
    parser.add_argument("--check", action="store_true", help="查看当前设置")
    parser.add_argument("--apply", action="store_true", help="应用优化配置")
    
    args = parser.parse_args()
    
    if args.check:
        check_current_settings()
    elif args.apply:
        apply_config_from_software()
    else:
        # 默认执行应用配置
        apply_config_from_software()
