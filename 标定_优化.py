import os
import cv2
import numpy as np
import json
import pandas as pd

# ==================== 用户配置区域 ====================
# 基础路径 - 修改这里来切换不同的实验文件夹
# 该路径下需要有 CH1, CH2, 以及 CH3 或 CH3_Raw 子文件夹
BASE_PATH = r"F:\test\experiment_videos\52-57"

# CH3文件夹名称 - 如果为None则自动检测（优先匹配CH3*开头的文件夹）
# 可选项: None(自动检测), "CH3", "CH3_Raw", "CH3_Other" 等
CH3_FOLDER_NAME = None  # 默认自动检测

# 透视变换输出分辨率配置
# 可选值:
#   - None: 自动使用原始图像分辨率（推荐，保持最大清晰度）
#   - (width, height): 指定输出尺寸，如 (640, 480)
# 注意: 如果指定尺寸小于原始图像，可能会丢失纹理细节
OUTPUT_RESOLUTION = None  # 默认自动保持原始分辨率

# 显示配置
# 标定窗口是否全屏显示
FULLSCREEN_CALIBRATION = True
# 浏览窗口最大显示尺寸（自适应缩放，保持原始比例）
MAX_DISPLAY_SIZE = (1920, 1080)  # 最大宽度, 最大高度
# =====================================================

# 全局变量存储标定点
calibration_points = {
    "CH1": [],
    "CH2": [],
    "CH3": []  # CH3名称会动态确定
}


def detect_ch3_folder(base_path, specified_name=None):
    """
    检测CH3文件夹名称
    如果指定了名称，检查是否存在；否则自动检测CH3开头的文件夹
    返回检测到的CH3文件夹名称
    """
    if specified_name:
        # 使用用户指定的名称
        ch3_path = os.path.join(base_path, specified_name)
        if os.path.exists(ch3_path):
            return specified_name
        else:
            raise FileNotFoundError(f"指定的CH3文件夹不存在: {ch3_path}")
    
    # 自动检测：优先查找CH3_Raw，其次是CH3，最后是CH3开头的任意文件夹
    if not os.path.exists(base_path):
        raise FileNotFoundError(f"基础路径不存在: {base_path}")
    
    subdirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    
    # 优先级顺序
    for candidate in ["CH3_Raw", "CH3"]:
        if candidate in subdirs:
            return candidate
    
    # 查找CH3开头的任意文件夹
    for d in subdirs:
        if d.startswith("CH3"):
            return d
    
    raise FileNotFoundError(f"未找到CH3相关文件夹，请检查目录结构: {base_path}")
current_channel = 1  # 当前标定的通道


                  
# 修改鼠标回调函数以支持缩放
def mouse_callback(event, x, y, flags, param):
    global calibration_points, current_channel, zoom_factor, pan_x, pan_y
                                       
    # 调整坐标以考虑缩放和平移
    adj_x = int((x + pan_x) / zoom_factor)
    adj_y = int((y + pan_y) / zoom_factor)

    if event == cv2.EVENT_LBUTTONDOWN:
        channel_name = f"CH{current_channel}"
        if len(calibration_points[channel_name]) < 4:
            calibration_points[channel_name].append((adj_x, adj_y))
            print(f"{channel_name} 点 {len(calibration_points[channel_name])}: ({adj_x}, {adj_y})")

        # 在图片上绘制点
        img_copy = param.copy()

        # 应用缩放和平移
        if zoom_factor != 1.0:
            h, w = img_copy.shape[:2]
            new_w, new_h = int(w * zoom_factor), int(h * zoom_factor)
            resized = cv2.resize(img_copy, (new_w, new_h))

            # 应用平移
            start_x = max(0, min(pan_x, new_w - w))
            start_y = max(0, min(pan_y, new_h - h))
            end_x = min(start_x + w, new_w)
            end_y = min(start_y + h, new_h)

            # 裁剪显示区域
            display_img = resized[start_y:end_y, start_x:end_x]

            # 在显示图像上绘制点（考虑缩放和平移）
            for p in calibration_points[channel_name]:
                p_display = (int(p[0] * zoom_factor) - start_x,
                             int(p[1] * zoom_factor) - start_y)
                cv2.circle(display_img, p_display, int(5 * zoom_factor), (0, 255, 0), -1)

            cv2.imshow(f"标定 {channel_name}", display_img)
        else:
            for p in calibration_points[channel_name]:
                cv2.circle(img_copy, p, 5, (0, 255, 0), -1)
            cv2.imshow(f"标定 {channel_name}", img_copy)


# 透视变换函数
def perspective_transform(img, points, output_resolution=None):
    # 根据配置或原始图像确定输出尺寸
    if output_resolution is None:
        # 自动使用原始图像分辨率，保持最大清晰度
        height, width = img.shape[:2]
    else:
        width, height = output_resolution
    
    # 定义目标点（矩形）
    dst_points = np.array([[0, 0], [width - 1, 0],
                           [width - 1, height - 1], [0, height - 1]], dtype='float32')

    # 转换为numpy数组
    src_points = np.array(points, dtype='float32')

    # 计算透视变换矩阵
    matrix = cv2.getPerspectiveTransform(src_points, dst_points)

    # 应用透视变换
    warped = cv2.warpPerspective(img, matrix, (width, height))

    return warped , matrix


# 保存标定点到文件
def save_calibration_points(calibration_points, file_path):
    with open(file_path, 'w') as f:
        json.dump(calibration_points, f)


# 从文件加载标定点
def load_calibration_points(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return None


def resize_to_fit(img, max_width, max_height):
    """
    将图片等比例缩放到适合指定尺寸
    保持原始宽高比，不会裁剪图片
    """
    h, w = img.shape[:2]
    
    # 计算缩放比例
    scale_w = max_width / w
    scale_h = max_height / h
    
    # 使用较小的缩放比例，确保图片完全在窗口内
    scale = min(scale_w, scale_h, 1.0)  # 不超过原始大小
    
    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img.copy()


# 修改标定函数以支持缩放控制
def browse_and_calibrate_channel(channel_idx, folder_path, image_files, channel_name=None):
    global current_channel, calibration_points, zoom_factor, pan_x, pan_y

    current_channel = channel_idx
    if channel_name is None:
        channel_name = f"CH{channel_idx}"
    calibration_points[channel_name] = []  # 重置标定点
    zoom_factor = 1.0  # 重置缩放
    pan_x, pan_y = 0, 0  # 重置平移

    print(f"\n开始标定 {channel_name}，共有 {len(image_files)} 张图片")
    print("按空格键浏览下一张图片，按 's' 键选择当前图片进行标定，按 'q' 键退出")

    current_image_idx = 0

    while current_image_idx < len(image_files):
        # 读取当前图片
        image_path = os.path.join(folder_path, image_files[current_image_idx])
        img = cv2.imread(image_path)
        if img is None:
            print(f"无法读取图片: {image_path}")
            current_image_idx += 1
            continue

        # 显示当前图片
        window_name = f"浏览 {channel_name} ({current_image_idx + 1}/{len(image_files)})"

        # 自适应缩放图片以适应屏幕，保持原始比例
        display_img = resize_to_fit(img, MAX_DISPLAY_SIZE[0], MAX_DISPLAY_SIZE[1])

        # 创建窗口并设置为可调整大小
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        # 获取图片显示尺寸
        disp_h, disp_w = display_img.shape[:2]
        # 设置窗口大小为图片大小
        cv2.resizeWindow(window_name, disp_w, disp_h)
        cv2.imshow(window_name, display_img)

        # 等待用户按键
        print(f"显示图片: {image_files[current_image_idx]}")
        key = cv2.waitKey(0) & 0xFF

        # 关闭浏览窗口
        cv2.destroyWindow(window_name)

        # 处理按键
        if key == 32:  # 空格键 - 下一张图片
            current_image_idx += 1
        elif key == ord('s'):  # 's' 键 - 选择当前图片进行标定
            print(f"选择图片进行标定: {image_files[current_image_idx]}")

            # 标定当前图片
            img_copy = img.copy()
            calib_window_name = f"标定 {channel_name}"
            
            # 创建窗口，支持全屏或自适应大小
            cv2.namedWindow(calib_window_name, cv2.WINDOW_NORMAL)
            
            if FULLSCREEN_CALIBRATION:
                # 全屏模式
                cv2.setWindowProperty(calib_window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                # 计算缩放比例以适应屏幕
                screen_w, screen_h = MAX_DISPLAY_SIZE
                img_h, img_w = img_copy.shape[:2]
                # 在全屏模式下显示自适应缩放后的图片
                display_img = resize_to_fit(img_copy, screen_w, screen_h)
                # 计算缩放因子用于鼠标坐标转换
                zoom_factor_display = display_img.shape[1] / img_w
            else:
                # 自适应窗口模式 - 图片铺满窗口但保持比例
                display_img = resize_to_fit(img_copy, MAX_DISPLAY_SIZE[0], MAX_DISPLAY_SIZE[1])
                disp_h, disp_w = display_img.shape[:2]
                cv2.resizeWindow(calib_window_name, disp_w, disp_h)
                zoom_factor_display = display_img.shape[1] / img_copy.shape[1]
            
            cv2.setMouseCallback(calib_window_name, mouse_callback, img_copy)
            cv2.imshow(calib_window_name, display_img)

            print(f"请为 {channel_name} 标定四个点 (按顺序点击)")
            if FULLSCREEN_CALIBRATION:
                print("全屏模式: 按 'f' 键切换全屏/窗口模式")
            print("缩放控制: '+' 放大, '-' 缩小, 方向键平移")
            print("完成后按空格键确认标定，按 'r' 键重新标定，按 'q' 键退出")

            while True:
                key2 = cv2.waitKey(0) & 0xFF

                # 缩放控制
                if key2 == ord('+'):  # 放大
                    zoom_factor *= 1.2
                    print(f"放大: 缩放比例 = {zoom_factor:.2f}")
                elif key2 == ord('-'):  # 缩小
                    zoom_factor = max(0.1, zoom_factor / 1.2)
                    print(f"缩小: 缩放比例 = {zoom_factor:.2f}")
                elif key2 == 82:  # 上箭头
                    pan_y = max(0, pan_y - 50)
                    print("向上平移")
                elif key2 == 84:  # 下箭头
                    pan_y += 50
                    print("向下平移")
                elif key2 == 81:  # 左箭头
                    pan_x = max(0, pan_x - 50)
                    print("向左平移")
                elif key2 == 83:  # 右箭头
                    pan_x += 50
                    print("向右平移")
                elif key2 == ord('f') or key2 == ord('F'):  # F键 - 切换全屏
                    is_fullscreen = cv2.getWindowProperty(calib_window_name, cv2.WND_PROP_FULLSCREEN) == 1
                    if is_fullscreen:
                        cv2.setWindowProperty(calib_window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                        # 恢复自适应大小
                        display_img = resize_to_fit(img_copy, MAX_DISPLAY_SIZE[0], MAX_DISPLAY_SIZE[1])
                        disp_h, disp_w = display_img.shape[:2]
                        cv2.resizeWindow(calib_window_name, disp_w, disp_h)
                        print("切换到窗口模式")
                    else:
                        cv2.setWindowProperty(calib_window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                        print("切换到全屏模式")

                # 刷新显示 - 在全屏模式下自适应缩放
                img_h, img_w = img_copy.shape[:2]
                win_w = cv2.getWindowImageRect(calib_window_name)[2] if hasattr(cv2, 'getWindowImageRect') else MAX_DISPLAY_SIZE[0]
                win_h = cv2.getWindowImageRect(calib_window_name)[3] if hasattr(cv2, 'getWindowImageRect') else MAX_DISPLAY_SIZE[1]
                
                # 根据窗口大小和缩放因子计算显示图像
                if zoom_factor != 1.0:
                    # 应用用户设置的缩放
                    new_w, new_h = int(img_w * zoom_factor), int(img_h * zoom_factor)
                    resized = cv2.resize(img_copy, (new_w, new_h))
                    
                    # 应用平移
                    start_x = max(0, min(pan_x, new_w - win_w))
                    start_y = max(0, min(pan_y, new_h - win_h))
                    end_x = min(start_x + win_w, new_w)
                    end_y = min(start_y + win_h, new_h)
                    
                    display_img = resized[start_y:end_y, start_x:end_x]
                    
                    # 在显示图像上绘制点
                    for p in calibration_points[channel_name]:
                        p_display = (int(p[0] * zoom_factor) - start_x,
                                     int(p[1] * zoom_factor) - start_y)
                        cv2.circle(display_img, p_display, max(3, int(5 * zoom_factor)), (0, 255, 0), -1)
                else:
                    # 自适应窗口大小
                    display_img = resize_to_fit(img_copy, win_w, win_h)
                    actual_scale = display_img.shape[1] / img_w
                    for p in calibration_points[channel_name]:
                        p_display = (int(p[0] * actual_scale), int(p[1] * actual_scale))
                        cv2.circle(display_img, p_display, max(3, int(5 * actual_scale)), (0, 255, 0), -1)
                
                cv2.imshow(calib_window_name, display_img)

                # 如果按下空格键，检查是否有四个点
                if key2 == 32:
                    if len(calibration_points[channel_name]) == 4:
                        break
                    else:
                        print("请标定四个点后再按空格键")

                # 如果按下 'r' 键，重新标定当前通道
                elif key2 == ord('r'):
                    calibration_points[channel_name] = []
                    zoom_factor = 1.0
                    pan_x, pan_y = 0, 0
                    # 重新显示原始图像
                    display_img = resize_to_fit(img_copy, MAX_DISPLAY_SIZE[0], MAX_DISPLAY_SIZE[1])
                    cv2.imshow(calib_window_name, display_img)
                    print(f"{channel_name} 标定已重置，请重新标定四个点")

                # 如果按下 'q' 键，退出程序
                elif key2 == ord('q'):
                    cv2.destroyAllWindows()
                    return False

            cv2.destroyWindow(calib_window_name)
            print(f"{channel_name} 标定完成")
            return True  # 标定完成



# 主函数
def main():
    global calibration_points

    # 检测CH3文件夹名称
    ch3_folder = detect_ch3_folder(BASE_PATH, CH3_FOLDER_NAME)
    print(f"检测到CH3文件夹: {ch3_folder}")
    
    # 更新calibration_points的键名
    if ch3_folder != "CH3":
        calibration_points[ch3_folder] = calibration_points.pop("CH3")
    
    # 指定三个文件夹路径
    folder_paths = [                                                          
        os.path.join(BASE_PATH, "CH1"),
        os.path.join(BASE_PATH, "CH2"),
        os.path.join(BASE_PATH, ch3_folder)             
    ]

    # 支持的图片格式
    image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')

    # 检查文件夹是否存在
    for folder_path in folder_paths:
        if not os.path.exists(folder_path):
            print(f"错误: 文件夹不存在: {folder_path}")
            return                  

    # 获取每个文件夹中的图片文件列表
    all_image_files = []
    for folder_path in folder_paths:
        image_files = [f for f in os.listdir(folder_path)
                       if f.lower().endswith(image_extensions)]
        image_files.sort()  # 按文件名排序
        all_image_files.append(image_files)


    # 确定最小图片数量
    min_image_count = min(len(files) for files in all_image_files)
    if min_image_count == 0:
        print("错误: 至少有一个文件夹中没有图片文件")
        return

    print(
        f"每个文件夹中找到图片数量: CH1={len(all_image_files[0])}, CH2={len(all_image_files[1])}, {ch3_folder}={len(all_image_files[2])}")

    # 为每个通道创建输出目录（在原文件夹中创建output文件夹）
    output_dirs = []
    for folder_path in folder_paths:
        output_dir = os.path.join(folder_path, "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_dirs.append(output_dir)
        print(f"创建输出目录: {output_dir}")

    # 标定点文件路径（保存在第一个通道的输出目录中）
    calibration_file = os.path.join(output_dirs[0], "calibration_points.json")

    # 询问用户是否使用已有的标定点
    use_existing = False
    if os.path.exists(calibration_file):
        response = input("找到已有的标定点文件，是否使用？(y/n): ")
        if response.lower() == 'y':
            loaded_points = load_calibration_points(calibration_file)
            if loaded_points:
                calibration_points = loaded_points
                use_existing = True
                print("已加载已有的标定点")

    # 如果需要重新标定
    if not use_existing:
        print("\n请为每个通道选择一张图片进行标定")
        
        # 定义通道名称列表
        channel_names = ["CH1", "CH2", ch3_folder]

        # 为每个通道标定
        for ch in range(1, 4):
            channel_name = channel_names[ch - 1]
            folder_path = folder_paths[ch - 1]
            image_files = all_image_files[ch - 1]

            print(f"\n开始处理 {channel_name}")

            # 浏览和标定当前通道
            calibrated = browse_and_calibrate_channel(ch, folder_path, image_files, channel_name)

            if not calibrated:
                print(f"{channel_name} 未完成标定，是否继续下一个通道？(y/n)")
                response = input()
                if response.lower() != 'y':
                    cv2.destroyAllWindows()
                    return

        # 保存标定点
        save_calibration_points(calibration_points, calibration_file)
        print(f"标定点已保存到: {calibration_file}")

    # 处理图片
    channel_names = ["CH1", "CH2", ch3_folder]
    for ch in range(1, 4):
        channel_name = channel_names[ch - 1]
        folder_path = folder_paths[ch - 1]
        image_files = all_image_files[ch - 1]
        output_dir = output_dirs[ch - 1]

        if len(calibration_points[channel_name]) != 4:
            print(f"跳过 {channel_name}，标定点不足")
            continue

        if not image_files:
            print(f"跳过 {channel_name}，没有图片文件")
            continue

        print(f"\n处理 {channel_name} 的 {len(image_files)} 张图片")

        for i, image_file in enumerate(image_files):
            print(f"处理 {channel_name} 第 {i + 1}/{len(image_files)} 张图片: {image_file}")

            # 读取图片
            image_path = os.path.join(folder_path, image_file)
            img = cv2.imread(image_path)
            if img is None:
                print(f"无法读取图片: {image_path}")
                continue

            # 透视变换
            warped_img, matrix = perspective_transform(img, calibration_points[channel_name], OUTPUT_RESOLUTION)

            source_name, source_ext = os.path.splitext(image_file)
            # 保存处理后的图片
            output_path = os.path.join(output_dir, source_name+"_tf.jpg")
            cv2.imwrite(output_path, warped_img)
            print(f"已保存到 {channel_name} 的输出目录: {output_path}")

            # # 如果是CH3，还需要处理对应的CSV数据
            # if channel_name == "CH3":
            #     # 查找对应的CSV文件
            #     image_name = os.path.splitext(image_file)[0]
            #     csv_path = os.path.join(csv_base_path, f"{image_name}.csv")
            #
            #     if os.path.exists(csv_path):
            #         # 读取CSV数据
            #         csv_data = pd.read_csv(csv_path, header=None).values
            #
            #         # 对CSV数据进行相同的透视变换
            #         if transform_matrices["CH3"] is not None:
            #             # 获取变换后的图像尺寸
            #             h, w = warped_img.shape[:2]
            #
            #             transformed_csv = transform_csv_data(
            #                 csv_data,
            #                 transform_matrices["CH3"],
            #                 (csv_data.shape[0], csv_data.shape[1]),
            #                 (h, w)  # 使用变换后图像的尺寸
            #             )
            #
            #             # 保存变换后的CSV数据
            #             csv_output_path = os.path.join(output_dir, f"{channel_name}_transformed_{i + 1}.csv")
            #             pd.DataFrame(transformed_csv).to_csv(csv_output_path, header=False, index=False)
            #             print(f"已保存变换后的CSV数据: {csv_output_path}")
            #         else:
            #             print(f"警告: 未找到CH3的变换矩阵，无法处理CSV数据")
            #     else:
            #         print(f"警告: 未找到对应的CSV文件: {csv_path}")

    print("\n所有图片处理完成!")

    # 询问用户是否要预览一些处理后的图片
    preview = input("是否要预览一些处理后的图片？(y/n): ")
    if preview.lower() == 'y':
        # 预览每个通道的第一张处理后的图片
        print("预览每个通道的第一张处理后的图片，按任意键关闭窗口")

        preview_images = []
        preview_titles = []
        
        channel_names = ["CH1", "CH2", ch3_folder]
        for ch in range(1, 4):
            channel_name = channel_names[ch - 1]
            output_dir = output_dirs[ch - 1]
            
            # 查找该目录下处理后的第一张图片 (后缀为 _tf.jpg)
            tf_files = [f for f in os.listdir(output_dir) if f.endswith('_tf.jpg')]
            if tf_files:
                preview_path = os.path.join(output_dir, tf_files[0])
                img = cv2.imread(preview_path)
                if img is not None:
                    preview_images.append(img)
                    preview_titles.append(f"{channel_name}_transformed")

        # 显示预览图片
        if preview_images:
            window_positions = [(100, 100), (600, 100), (1100, 100)]

            for j, (preview_img, title) in enumerate(zip(preview_images, preview_titles)):
                cv2.namedWindow(title)
                cv2.moveWindow(title, window_positions[j][0], window_positions[j][1])
                cv2.imshow(title, preview_img)

            # 等待按键后关闭窗口
            cv2.waitKey(0)
            for title in preview_titles:
                cv2.destroyWindow(title)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()