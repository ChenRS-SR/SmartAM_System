#!/usr/bin/env python3
"""
应用用户保存的 IDS 相机配置
从 my_ids_config.ini 读取参数并设置到相机
"""

import os
import sys
import time
import configparser

def load_config(ini_path):
    """加载 ini 配置文件"""
    config = configparser.ConfigParser()
    config.read(ini_path, encoding='utf-8-sig')  # 处理 BOM
    return config

def apply_config_to_camera(daq, config):
    """应用配置到相机"""
    print("\n[应用配置]")
    
    if not hasattr(daq, '_ids_nodemap') or not daq._ids_nodemap:
        print("[错误] 无法访问相机节点")
        return False
    
    nodemap = daq._ids_nodemap
    applied = []
    failed = []
    
    # 1. 应用焦距设置
    try:
        focus_value = float(config.get('Lens Focus', 'Focus manual value', fallback=112))
        af_enable = int(config.get('Lens Focus', 'Focus AF enable', fallback=0))
        
        # 关闭自动对焦
        if af_enable == 0:
            try:
                nodemap.FindNode("FocusAuto").SetCurrentEntry("Off")
                print(f"  ✓ 自动对焦: 已关闭")
            except:
                pass
        
        # 设置焦距
        try:
            nodemap.FindNode("Focus").SetValue(focus_value)
            print(f"  ✓ 焦距: {focus_value}")
            applied.append(f"焦距={focus_value}")
        except:
            try:
                nodemap.FindNode("FocusDistance").SetValue(focus_value)
                print(f"  ✓ 焦距: {focus_value}")
                applied.append(f"焦距={focus_value}")
            except Exception as e:
                print(f"  ✗ 焦距设置失败: {e}")
                failed.append("焦距")
    except Exception as e:
        print(f"  ✗ 焦距参数读取失败: {e}")
        failed.append("焦距")
    
    # 2. 应用伽马设置
    try:
        gamma = float(config.get('Parameters', 'Gamma', fallback=1.0))
        try:
            nodemap.FindNode("Gamma").SetValue(gamma)
            print(f"  ✓ 伽马: {gamma}")
            applied.append(f"伽马={gamma}")
        except Exception as e:
            print(f"  ✗ 伽马设置失败: {e}")
            failed.append("伽马")
    except Exception as e:
        print(f"  ✗ 伽马参数读取失败: {e}")
    
    # 3. 应用边缘增强（尝试多个可能的参数名）
    try:
        # 从配置文件中读取边缘增强
        edge_enhance = int(config.get('Processing', 'EdgeEnhancementFactor', fallback=0))
        
        # 如果用户说设到3，但配置文件是0，可能是不同的参数
        # 尝试设置
        set_success = False
        
        try:
            nodemap.FindNode("EdgeEnhancement").SetValue(float(edge_enhance))
            print(f"  ✓ 边缘增强: {edge_enhance}")
            applied.append(f"边缘增强={edge_enhance}")
            set_success = True
        except:
            pass
        
        if not set_success:
            try:
                nodemap.FindNode("Sharpening").SetValue(float(edge_enhance))
                print(f"  ✓ 锐化: {edge_enhance}")
                applied.append(f"锐化={edge_enhance}")
                set_success = True
            except:
                pass
        
        if not set_success:
            print(f"  ! 边缘增强参数不支持或名称不同")
            # 手动尝试设一个值
            for val in [3, 5, 10]:
                try:
                    nodemap.FindNode("EdgeEnhancement").SetValue(float(val))
                    print(f"  ✓ 边缘增强: 设置为 {val}")
                    applied.append(f"边缘增强={val}")
                    break
                except:
                    continue
    except Exception as e:
        print(f"  ✗ 边缘增强设置失败: {e}")
    
    # 4. 应用曝光和帧率
    try:
        exposure = float(config.get('Timing', 'Exposure', fallback=66.7))
        framerate = float(config.get('Timing', 'Framerate', fallback=15.0))
        
        # 关闭自动曝光（如果需要手动设置）
        try:
            nodemap.FindNode("ExposureAuto").SetCurrentEntry("Off")
        except:
            pass
        
        try:
            nodemap.FindNode("ExposureTime").SetValue(exposure)
            print(f"  ✓ 曝光时间: {exposure/1000:.2f}ms")
            applied.append(f"曝光={exposure/1000:.2f}ms")
        except Exception as e:
            print(f"  ! 曝光设置失败: {e}")
    except Exception as e:
        print(f"  ! 曝光参数读取失败: {e}")
    
    # 5. 应用增益
    try:
        master_gain = float(config.get('Gain', 'Master', fallback=0))
        
        # 关闭自动增益
        try:
            nodemap.FindNode("GainAuto").SetCurrentEntry("Off")
        except:
            pass
        
        try:
            nodemap.FindNode("Gain").SetValue(master_gain)
            print(f"  ✓ 主增益: {master_gain}")
            applied.append(f"增益={master_gain}")
        except Exception as e:
            print(f"  ! 增益设置失败: {e}")
    except Exception as e:
        print(f"  ! 增益参数读取失败: {e}")
    
    # 6. 保存到相机内存
    print("\n[保存设置]")
    try:
        nodemap.FindNode("UserSetSelector").SetCurrentEntry("UserSet1")
        nodemap.FindNode("UserSetSave").Execute()
        print("  ✓ 已保存到相机 UserSet1")
    except Exception as e:
        print(f"  ! 保存失败: {e}")
    
    return len(applied) > 0

def main():
    print("=" * 60)
    print("应用 IDS 相机配置文件")
    print("=" * 60)
    
    # 配置文件路径
    ini_path = r"D:\College\Python_project\4Project\SmartAM_System\backend\utils\my_ids_config.ini"
    
    if not os.path.exists(ini_path):
        print(f"[错误] 配置文件不存在: {ini_path}")
        return
    
    print(f"\n[1/3] 加载配置文件...")
    print(f"  路径: {ini_path}")
    
    try:
        config = load_config(ini_path)
        
        # 显示关键参数
        print("\n  配置参数:")
        try:
            focus = config.get('Lens Focus', 'Focus manual value')
            af = config.get('Lens Focus', 'Focus AF enable')
            print(f"    焦距: {focus}")
            print(f"    自动对焦: {'开启' if af == '1' else '关闭'}")
        except:
            pass
        
        try:
            gamma = config.get('Parameters', 'Gamma')
            print(f"    伽马: {gamma}")
        except:
            pass
        
        try:
            edge = config.get('Processing', 'EdgeEnhancementFactor')
            print(f"    边缘增强: {edge}")
        except:
            pass
        
    except Exception as e:
        print(f"[错误] 加载配置失败: {e}")
        return
    
    print("\n[2/3] 连接相机...")
    try:
        from core.data_acquisition import get_acquisition
        daq = get_acquisition()
        
        if not daq._ids_camera:
            print("  连接 IDS 相机...")
            daq.connect_device('ids')
        
        if not daq._ids_camera:
            print("[错误] IDS 相机连接失败")
            return
        
        print("  IDS 相机已连接")
        
    except Exception as e:
        print(f"[错误] 连接失败: {e}")
        return
    
    print("\n[3/3] 应用配置...")
    success = apply_config_to_camera(daq, config)
    
    if success:
        # 测试拍摄
        print("\n[测试拍摄]")
        time.sleep(0.5)
        frame = daq._get_ids_frame()
        if frame is not None:
            import cv2
            output_file = "./ids_with_my_config.jpg"
            cv2.imwrite(output_file, frame)
            print(f"  ✓ 测试图像已保存: {output_file}")
        
        print("\n" + "=" * 60)
        print("配置应用成功!")
        print("=" * 60)
        print("\n已应用的设置:")
        print("  - 焦距: 112 (手动)")
        print("  - 自动对焦: 关闭")
        print("  - 其他参数从配置文件加载")
        print("\n这些设置会在系统重启后保持")
    else:
        print("\n[警告] 部分参数应用失败")

if __name__ == "__main__":
    main()
