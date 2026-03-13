"""
图像像素点选择器
点击图像获取像素坐标位置
"""

import cv2
import os
import sys


class PixelPicker:
    def __init__(self, image_path):
        self.image_path = image_path
        self.image = None
        self.display_image = None
        self.points = []
        
    def mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数"""
        if event == cv2.EVENT_LBUTTONDOWN:
            # 左键点击，记录坐标
            self.points.append((x, y))
            print(f"点击位置: ({x}, {y})")
            
            # 在图像上标记点击位置
            cv2.circle(self.display_image, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(self.display_image, f"({x}, {y})", (x + 10, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            cv2.imshow("Image", self.display_image)
            
        elif event == cv2.EVENT_MOUSEMOVE:
            # 鼠标移动时显示当前坐标
            temp_image = self.display_image.copy()
            cv2.putText(temp_image, f"Pos: ({x}, {y})", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Image", temp_image)
    
    def run(self):
        """运行像素选择器"""
        # 检查文件是否存在
        if not os.path.exists(self.image_path):
            print(f"错误: 找不到文件 '{self.image_path}'")
            return
        
        # 读取图像（处理中文路径）
        # OpenCV 在 Windows 上处理中文路径需要特殊处理
        try:
            # 尝试直接读取
            self.image = cv2.imread(self.image_path)
            if self.image is None:
                raise Exception("Direct read failed")
        except:
            # 使用 numpy 从文件读取（支持中文路径）
            import numpy as np
            with open(self.image_path, 'rb') as f:
                img_array = np.frombuffer(f.read(), dtype=np.uint8)
                self.image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if self.image is None:
            print(f"错误: 无法读取图像 '{self.image_path}'")
            return
        
        self.display_image = self.image.copy()
        
        # 创建窗口
        cv2.namedWindow("Image", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("Image", self.mouse_callback)
        
        print("=" * 50)
        print("图像像素点选择器")
        print("=" * 50)
        print(f"图像尺寸: {self.image.shape[1]} x {self.image.shape[0]}")
        print("操作说明:")
        print("  - 左键点击: 获取像素坐标")
        print("  - 鼠标移动: 查看当前位置坐标")
        print("  - 按 'r': 重置所有标记")
        print("  - 按 's': 保存带标记的图像")
        print("  - 按 'q' 或 ESC: 退出")
        print("=" * 50)
        
        while True:
            cv2.imshow("Image", self.display_image)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # q 或 ESC 退出
                break
            elif key == ord('r'):  # r 重置
                self.display_image = self.image.copy()
                self.points = []
                print("已重置所有标记")
            elif key == ord('s'):  # s 保存
                save_path = "marked_image.png"
                cv2.imwrite(save_path, self.display_image)
                print(f"已保存标记图像到: {save_path}")
        
        cv2.destroyAllWindows()
        
        # 打印所有记录的点
        if self.points:
            print("\n记录的所有点:")
            for i, point in enumerate(self.points, 1):
                print(f"  点 {i}: {point}")


def main():
    # 获取图像路径
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # 默认使用当前目录下的第一个图像文件
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif')
        image_files = [f for f in os.listdir('.') 
                      if f.lower().endswith(valid_extensions)]
        
        if image_files:
            image_path = image_files[0]
            print(f"未指定图像文件，使用默认图像: {image_path}")
        else:
            print("用法: python image_pixel_picker.py <图像文件路径>")
            print("或确保当前目录下有图像文件")
            return
    
    # 将路径转换为绝对路径并处理中文编码
    image_path = os.path.abspath(image_path)
    
    # 对于 Windows 上的 OpenCV，需要处理中文路径
    # 使用 numpy 从文件读取再解码
    import numpy as np
    
    # 运行像素选择器
    picker = PixelPicker(image_path)
    picker.run()


if __name__ == "__main__":
    main()
