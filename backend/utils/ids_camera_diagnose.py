"""
IDS 相机配置诊断工具 - UI1007XS 专用
此相机使用 UVC 控制而非标准 GenICam 节点
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

try:
    from ids_peak import ids_peak
    IDS_AVAILABLE = True
except ImportError:
    IDS_AVAILABLE = False
    print("[错误] IDS Peak 库未安装")
    sys.exit(1)

def test_uvc_controls(device):
    """测试 UVC 控制接口"""
    print("\n" + "="*60)
    print("测试 UVC 控制接口")
    print("="*60)
    
    # UVC 标准控制 ID
    uvc_controls = {
        "焦距自动": (1, 0x0A0000, "UVC_CT_FOCUS_AUTO_CONTROL"),
        "焦距绝对值": (1, 0x0A0001, "UVC_CT_FOCUS_ABSOLUTE_CONTROL"),
        "焦距相对值": (1, 0x0A0002, "UVC_CT_FOCUS_RELATIVE_CONTROL"),
        "聚焦简单范围": (1, 0x0A0003, "UVC_CT_FOCUS_SIMPLE_RANGE_CONTROL"),
        "聚焦自动速度": (1, 0x0A0004, "UVC_CT_FOCUS_AUTO_SPEED_CONTROL"),
    }
    
    for name, (entity, selector, desc) in uvc_controls.items():
        print(f"\n测试: {name} ({desc})")
        try:
            # 尝试通过 UVC 获取/设置控制
            result = device.UvcGetControl(entity, selector, 1)
            print(f"  [✓] 可以读取，值: {result}")
        except Exception as e:
            print(f"  [✗] 不支持: {str(e)[:50]}")

def test_focus_via_nodemap(nodemap):
    """通过节点映射测试焦距控制"""
    print("\n" + "="*60)
    print("通过节点映射测试焦距")
    print("="*60)
    
    # 尝试获取 FocusAuto 的详细信息
    try:
        focus_auto = nodemap.FindNode("FocusAuto")
        print(f"\n[✓] FocusAuto 节点存在")
        print(f"  类型: {type(focus_auto).__name__}")
        
        # 获取当前值
        if hasattr(focus_auto, 'CurrentEntry'):
            try:
                current = focus_auto.CurrentEntry()
                print(f"  当前值: {current}")
            except Exception as e:
                print(f"  当前值: 无法读取 ({e})")
        
        # 列出所有选项
        if hasattr(focus_auto, 'Entries'):
            try:
                entries = focus_auto.Entries()
                print(f"  可用选项: {list(entries)}")
            except Exception as e:
                print(f"  可用选项: 无法列出 ({e})")
        
        # 尝试设置为 Off
        try:
            focus_auto.SetCurrentEntry("Off")
            print(f"  [✓] 已设置为 Off")
        except Exception as e:
            print(f"  [✗] 无法设置为 Off: {e}")
            
    except Exception as e:
        print(f"[✗] FocusAuto 节点错误: {e}")
    
    # 尝试查找其他可能的节点
    print("\n尝试查找其他控制节点...")
    possible_names = [
        "Focus", "FocusDistance", "FocusPosition", "FocusValue",
        "FocusAbsolute", "FocusRelative", "ManualFocus", "FocusManual",
        "FocusControl", "FocusSetting", "LensFocus", "LensFocusDistance",
        "FocusMotor", "FocusRange", "FocusMode"
    ]
    
    for name in possible_names:
        try:
            node = nodemap.FindNode(name)
            print(f"  [✓] {name}: 存在 ({type(node).__name__})")
            
            # 尝试获取值
            if hasattr(node, 'Value'):
                try:
                    val = node.Value()
                    print(f"      当前值: {val}")
                except:
                    pass
            
        except:
            pass  # 不打印不存在的节点

def test_alternative_methods(device, nodemap):
    """测试其他可能的焦距控制方法"""
    print("\n" + "="*60)
    print("测试替代控制方法")
    print("="*60)
    
    # 方法1: 尝试通过 GenICam 的 Category 查找
    print("\n[方法1] 查找 Focus 相关 Category...")
    try:
        categories = ["FocusControl", "LensControl", "AutoFocusControl", "Controls"]
        for cat in categories:
            try:
                node = nodemap.FindNode(cat)
                print(f"  [✓] 找到 Category: {cat}")
            except:
                pass
    except Exception as e:
        print(f"  [✗] 查找 Category 失败: {e}")
    
    # 方法2: 检查是否有 UVC 扩展控制
    print("\n[方法2] 检查 UVC 扩展控制...")
    try:
        # 尝试获取 UVC 控制列表
        if hasattr(device, 'UvcControls'):
            controls = device.UvcControls()
            print(f"  [✓] 找到 UVC 控制: {controls}")
        else:
            print("  [!] 设备不支持 UvcControls 方法")
    except Exception as e:
        print(f"  [✗] 获取 UVC 控制失败: {e}")
    
    # 方法3: 尝试通过字符串查找所有包含 focus 的节点
    print("\n[方法3] 暴力搜索所有节点...")
    try:
        # 尝试常见的前缀组合
        prefixes = ["", "UVC", "Camera", "Device", "Sensor"]
        suffixes = ["", "Control", "Mode", "Setting", "Value"]
        
        found_any = False
        for prefix in prefixes:
            for base in ["Focus", "AutoFocus", "ManualFocus"]:
                for suffix in suffixes:
                    name = f"{prefix}{base}{suffix}"
                    try:
                        node = nodemap.FindNode(name)
                        print(f"  [✓] 找到节点: {name}")
                        found_any = True
                    except:
                        pass
        
        if not found_any:
            print("  [!] 未找到其他焦距节点")
    except Exception as e:
        print(f"  [✗] 搜索失败: {e}")

def main():
    print("="*60)
    print("IDS UI1007XS 相机配置诊断工具")
    print("="*60)
    
    device = None
    try:
        # 初始化库
        print("\n[1] 初始化 IDS Peak 库...")
        ids_peak.Library.Initialize()
        print("    [✓] 库初始化成功")
        
        # 获取设备管理器
        print("\n[2] 查找相机设备...")
        device_manager = ids_peak.DeviceManager.Instance()
        device_manager.Update()
        
        if device_manager.Devices().empty():
            print("    [✗] 未找到 IDS 相机")
            return
        
        print(f"    [✓] 找到 {device_manager.Devices().size()} 个设备")
        
        # 打开设备
        print("\n[3] 打开相机设备...")
        device = device_manager.Devices()[0].OpenDevice(ids_peak.DeviceAccessType_Exclusive)
        print(f"    [✓] 设备已打开: {device.ModelName()}")
        
        # 获取节点映射
        nodemap = device.RemoteDevice().NodeMaps()[0]
        
        # 测试各种方法
        test_focus_via_nodemap(nodemap)
        test_uvc_controls(device)
        test_alternative_methods(device, nodemap)
        
        # 总结
        print("\n" + "="*60)
        print("总结")
        print("="*60)
        print("UI1007XS 是 UVC 相机，焦距控制可能通过以下方式：")
        print("1. 使用操作系统的摄像头设置（Windows 相机应用）")
        print("2. 使用 OpenCV 的 VideoCapture 设置 UVC 控制")
        print("3. 使用 IDS 的 UVC 扩展控制接口")
        print("\n建议：在 Windows 相机应用中手动设置焦距后")
        print("      在代码中使用相同的设置值")
        
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭设备
        if device:
            print("\n[最后] 关闭设备...")
            device = None
            print("    [✓] 设备已关闭")

if __name__ == "__main__":
    main()
    input("\n按 Enter 键退出...")
