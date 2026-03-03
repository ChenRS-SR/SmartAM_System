"""
IDS 相机清晰度调试工具
用于测试不同焦距值和图像处理参数
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import cv2
import numpy as np
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

try:
    from ids_peak import ids_peak
    from ids_peak import ids_peak_ipl_extension
    IDS_AVAILABLE = True
except ImportError:
    IDS_AVAILABLE = False
    print("[错误] IDS Peak 库未安装")
    sys.exit(1)

def apply_sharpen(image, method='unsharp'):
    """应用不同的锐化方法"""
    if method == 'unsharp':
        # Unsharp Mask
        gaussian = cv2.GaussianBlur(image, (0, 0), 2.0)
        return cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
    elif method == 'laplacian':
        # 拉普拉斯锐化
        kernel = np.array([[-1, -1, -1],
                          [-1, 9, -1],
                          [-1, -1, -1]])
        return cv2.filter2D(image, -1, kernel)
    elif method == 'strong':
        # 强力锐化
        kernel = np.array([[-1, -1, -1],
                          [-1, 11, -1],
                          [-1, -1, -1]])
        return cv2.filter2D(image, -1, kernel)
    elif method == 'clahe':
        # CLAHE + 轻微锐化
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge((l, a, b))
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return image

def calculate_sharpness(image):
    """计算图像清晰度（拉普拉斯方差）"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def test_focus_values(device, nodemap, datastream):
    """测试不同焦距值"""
    print("\n" + "="*60)
    print("测试不同焦距值")
    print("="*60)
    
    # 确保自动对焦关闭
    try:
        auto_focus_node = nodemap.FindNode("FocusAuto")
        if auto_focus_node and auto_focus_node.IsAvailable():
            auto_focus_entries = auto_focus_node.Entries()
            for entry in auto_focus_entries:
                if entry.SymbolicValue() == "Off":
                    auto_focus_node.SetCurrentEntry(entry)
                    print("[✓] 自动对焦已关闭")
                    break
    except Exception as e:
        print(f"[!] 关闭自动对焦失败: {e}")
    
    focus_stepper = nodemap.FindNode("FocusStepper")
    if not focus_stepper or not focus_stepper.IsAvailable():
        print("[✗] 无法找到 FocusStepper 节点")
        return
    
    # 获取焦距范围
    min_focus = int(focus_stepper.Minimum())
    max_focus = int(focus_stepper.Maximum())
    print(f"\n焦距范围: {min_focus} - {max_focus}")
    
    # 测试几个关键焦距值
    test_values = [min_focus, 50, 80, 100, 112, 120, 150, 180, max_focus]
    test_values = [v for v in test_values if min_focus <= v <= max_focus]
    
    results = []
    
    for focus_val in test_values:
        try:
            # 设置焦距
            focus_stepper.SetValue(float(focus_val))
            print(f"\n测试焦距: {focus_val}")
            
            # 等待稳定
            import time
            time.sleep(0.5)
            
            # 采集几帧
            sharpness_list = []
            for _ in range(3):
                buffer = datastream.WaitForFinishedBuffer(1000)
                ipl_image = ids_peak_ipl_extension.BufferToImage(buffer)
                image_np = ipl_image.get_numpy()
                
                # 处理图像
                height, width = ipl_image.Height(), ipl_image.Width()
                pixel_format = ipl_image.PixelFormat()
                
                if pixel_format == "RGB8":
                    image_np = image_np.reshape((height, width, 3))
                    image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
                elif pixel_format == "BGR8":
                    image_np = image_np.reshape((height, width, 3))
                
                image_np = cv2.flip(image_np, -1)
                
                # 计算清晰度
                sharpness = calculate_sharpness(image_np)
                sharpness_list.append(sharpness)
                
                datastream.QueueBuffer(buffer)
            
            avg_sharpness = sum(sharpness_list) / len(sharpness_list)
            results.append((focus_val, avg_sharpness))
            print(f"  平均清晰度: {avg_sharpness:.2f}")
            
        except Exception as e:
            print(f"  [✗] 测试失败: {e}")
    
    # 找出最佳焦距
    if results:
        best_focus, best_sharpness = max(results, key=lambda x: x[1])
        print(f"\n[结果] 最佳焦距值: {best_focus} (清晰度: {best_sharpness:.2f})")
        
        # 设置回最佳值
        try:
            focus_stepper.SetValue(float(best_focus))
            print(f"[✓] 已设置焦距为 {best_focus}")
        except:
            pass

def test_sharpen_methods():
    """测试不同锐化方法的效果"""
    print("\n" + "="*60)
    print("锐化方法对比")
    print("="*60)
    print("""
可用方法:
1. unsharp    - Unsharp Mask (推荐，自然清晰)
2. laplacian  - 拉普拉斯锐化 (边缘明显)
3. strong     - 强力锐化 (可能过锐)
4. clahe      - 自适应对比度增强 (暗部细节)

建议组合:
- 一般情况: unsharp + clahe
- 细节观察: laplacian
- 快速检查: strong
""")

def capture_sample_frame(datastream):
    """采集一帧示例图像"""
    try:
        buffer = datastream.WaitForFinishedBuffer(1000)
        ipl_image = ids_peak_ipl_extension.BufferToImage(buffer)
        image_np = ipl_image.get_numpy()
        
        height, width = ipl_image.Height(), ipl_image.Width()
        pixel_format = ipl_image.PixelFormat()
        
        if pixel_format == "RGB8":
            image_np = image_np.reshape((height, width, 3))
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        elif pixel_format == "BGR8":
            image_np = image_np.reshape((height, width, 3))
        
        image_np = cv2.flip(image_np, -1)
        datastream.QueueBuffer(buffer)
        
        return image_np
    except Exception as e:
        print(f"[✗] 采集失败: {e}")
        return None

def main():
    print("="*60)
    print("IDS 相机清晰度调试工具")
    print("="*60)
    
    device = None
    datastream = None
    
    try:
        # 初始化
        print("\n[1] 初始化 IDS Peak 库...")
        ids_peak.Library.Initialize()
        
        print("[2] 查找相机...")
        device_manager = ids_peak.DeviceManager.Instance()
        device_manager.Update()
        
        if device_manager.Devices().empty():
            print("[✗] 未找到 IDS 相机")
            return
        
        print("[3] 打开相机...")
        device = device_manager.Devices()[0].OpenDevice(ids_peak.DeviceAccessType_Exclusive)
        nodemap = device.RemoteDevice().NodeMaps()[0]
        
        print("[4] 启动数据流...")
        datastream = device.DataStreams()[0].OpenDataStream()
        payload_size = nodemap.FindNode("PayloadSize").Value()
        
        for _ in range(5):
            buffer = datastream.AllocAndAnnounceBuffer(payload_size)
            datastream.QueueBuffer(buffer)
        
        datastream.StartAcquisition()
        nodemap.FindNode("AcquisitionStart").Execute()
        
        # 显示菜单
        while True:
            print("\n" + "="*60)
            print("调试选项:")
            print("  1. 测试不同焦距值 (自动扫描)")
            print("  2. 设置特定焦距值")
            print("  3. 显示锐化方法说明")
            print("  4. 采集示例图像并保存")
            print("  0. 退出")
            print("="*60)
            
            choice = input("\n请选择 (0-4): ").strip()
            
            if choice == "1":
                test_focus_values(device, nodemap, datastream)
            elif choice == "2":
                try:
                    val = int(input(f"请输入焦距值: "))
                    focus_stepper = nodemap.FindNode("FocusStepper")
                    focus_stepper.SetValue(float(val))
                    print(f"[✓] 焦距已设置为 {val}")
                except Exception as e:
                    print(f"[✗] 设置失败: {e}")
            elif choice == "3":
                test_sharpen_methods()
            elif choice == "4":
                frame = capture_sample_frame(datastream)
                if frame is not None:
                    filename = f"ids_sample_{int(time.time())}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"[✓] 图像已保存: {filename}")
                    print(f"  清晰度: {calculate_sharpness(frame):.2f}")
            elif choice == "0":
                break
            else:
                print("[!] 无效选择")
        
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        if datastream:
            try:
                datastream.StopAcquisition()
            except:
                pass
        print("\n[✓] 已关闭")
        input("\n按 Enter 退出...")

if __name__ == "__main__":
    import time
    main()
