"""
旁轴摄像头驱动模块
==================
罗技 USB 网络摄像头（远处拍摄打印机整体状态）
使用 OpenCV 进行图像采集

基于 pacnet_project/hardware/ids_driver_old.py 中的旁轴相机代码封装
"""

import time
import logging
import threading
from typing import Optional, Callable, List

import numpy as np
import cv2

# 配置日志
logger = logging.getLogger(__name__)


class SideCamera:
    """
    旁轴摄像头驱动类（罗技 USB 摄像头）
    
    功能：
    1. 自动发现可用的 USB 摄像头（跳过设备0，通常是电脑自带相机）
    2. 实时图像采集（旁轴视角，远处拍摄打印机）
    3. 缓冲区清理（减少延迟）
    4. 分辨率设置（支持自动降级）
    
    使用示例：
        camera = SideCamera()
        if camera.initialize():
            frame = camera.get_frame()
            # 处理 frame...
        camera.close()
    """
    
    def __init__(self, 
                 target_width: int = 1280,
                 target_height: int = 720,
                 fps: int = 30,
                 start_index: int = 1):
        """
        初始化旁轴摄像头
        
        Args:
            target_width: 目标分辨率宽度，默认 1280
            target_height: 目标分辨率高度，默认 720
            fps: 目标帧率，默认 30
            start_index: 开始搜索的设备索引，默认 1（跳过设备0，通常是电脑自带相机）
        """
        self.target_width = target_width
        self.target_height = target_height
        self.fps = fps
        self.start_index = start_index
        
        # OpenCV 视频捕获对象
        self.cap: Optional[cv2.VideoCapture] = None
        self.device_index: Optional[int] = None
        
        # 状态
        self.is_initialized = False
        self.actual_width = 0
        self.actual_height = 0
        self.actual_fps = 0
        
        # 最新帧缓存
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._frame_count = 0
        
        # 采集线程
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 回调函数
        self._frame_callbacks: List[Callable[[np.ndarray], None]] = []
        
        logger.info(f"[Side] 旁轴摄像头对象已创建 (target={target_width}x{target_height})")
    
    def _find_camera(self) -> Optional[int]:
        """
        自动查找可用的摄像头
        
        Returns:
            int: 可用的设备索引，未找到返回 None
        """
        logger.info(f"[Side] 扫描摄像头（从设备 {self.start_index} 开始）...")
        
        for i in range(self.start_index, 10):  # 扫描设备 1-9
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # 测试读取一帧
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        height, width = frame.shape[:2]
                        logger.info(f"[Side] 发现设备 {i}: {width}x{height}")
                        cap.release()
                        return i
                    else:
                        cap.release()
                else:
                    cap.release()
            except Exception as e:
                logger.debug(f"[Side] 设备 {i} 检测异常: {e}")
                continue
        
        logger.error("[Side] 未找到可用的旁轴摄像头")
        return None
    
    def initialize(self) -> bool:
        """
        初始化旁轴摄像头
        
        Returns:
            bool: 初始化是否成功
        """
        if self.is_initialized:
            logger.warning("[Side] 摄像头已经初始化")
            return True
        
        try:
            logger.info("[Side] 正在初始化摄像头...")
            
            # 1. 查找摄像头
            self.device_index = self._find_camera()
            if self.device_index is None:
                return False
            
            # 2. 打开摄像头
            self.cap = cv2.VideoCapture(self.device_index)
            if not self.cap.isOpened():
                logger.error(f"[Side] 无法打开设备 {self.device_index}")
                return False
            
            time.sleep(1.5)  # 等待摄像头初始化（虚拟摄像头需要较长时间）
            
            # 3. 设置参数
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲区，降低延迟
            
            # 4. 获取实际参数
            self.actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            logger.info(f"[Side] 摄像头参数: {self.actual_width}x{self.actual_height} @ {self.actual_fps}fps")
            
            # 5. 预热：清除缓冲区
            logger.info("[Side] 预热中，清除缓冲区...")
            for i in range(50):
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    if i % 10 == 0:
                        logger.debug(f"[Side] 预热 {i}/50")
                time.sleep(0.05)
            
            # 6. 测试读取
            test_frame = self._read_frame()
            if test_frame is None:
                logger.error("[Side] 无法读取测试帧")
                self.close()
                return False
            
            logger.info(f"[Side] 摄像头初始化成功 (设备 {self.device_index})")
            
            # 7. 启动采集线程
            self.is_initialized = True
            self._stop_event.clear()
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"[Side] 初始化失败: {e}")
            self.close()
            return False
    
    def _read_frame(self) -> Optional[np.ndarray]:
        """
        读取一帧图像
        
        Returns:
            np.ndarray: BGR 格式图像，失败返回 None
        """
        if self.cap is None or not self.cap.isOpened():
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None and frame.size > 0:
                # 检查是否是黑屏
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = cv2.mean(gray)[0]
                
                if brightness < 5:  # 画面太暗
                    logger.warning(f"[Side] 画面太暗 (亮度: {brightness:.1f})")
                    return frame  # 仍然返回，让调用方决定
                
                return frame
            else:
                return None
        except Exception as e:
            logger.error(f"[Side] 读取帧失败: {e}")
            return None
    
    def _capture_loop(self):
        """
        后台采集循环
        持续从摄像头获取图像并缓存
        """
        logger.info("[Side] 采集循环已启动")
        
        consecutive_errors = 0
        max_errors = 10
        
        while not self._stop_event.is_set():
            try:
                frame = self._read_frame()
                if frame is not None:
                    with self._frame_lock:
                        self._latest_frame = frame
                        self._frame_count += 1
                    
                    # 触发回调
                    for callback in self._frame_callbacks:
                        try:
                            callback(frame)
                        except Exception as e:
                            logger.error(f"[Side] 回调执行错误: {e}")
                    
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    logger.warning(f"[Side] 采集错误 ({consecutive_errors}/{max_errors}): {e}")
                
                if consecutive_errors >= max_errors:
                    logger.error("[Side] 连续错误过多，停止采集")
                    break
                
                time.sleep(0.1)
        
        logger.info("[Side] 采集循环已停止")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        获取最新一帧图像
        
        Returns:
            np.ndarray: 最新图像（BGR格式），未初始化返回 None
        """
        with self._frame_lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
            return None
    
    def get_frame_count(self) -> int:
        """获取已采集的帧数"""
        return self._frame_count
    
    def register_callback(self, callback: Callable[[np.ndarray], None]):
        """注册帧回调函数"""
        self._frame_callbacks.append(callback)
        logger.debug(f"[Side] 注册回调，当前 {len(self._frame_callbacks)} 个")
    
    def unregister_callback(self, callback: Callable[[np.ndarray], None]):
        """注销回调函数"""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)
    
    def is_available(self) -> bool:
        """检查摄像头是否可用"""
        return self.is_initialized and self.cap is not None and self.cap.isOpened()
    
    def close(self):
        """关闭摄像头并释放资源"""
        logger.info("[Side] 正在关闭摄像头...")
        
        # 停止采集线程
        self.is_initialized = False
        self._stop_event.set()
        
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2)
        
        # 释放摄像头
        if self.cap:
            try:
                self.cap.release()
                logger.info("[Side] 摄像头已释放")
            except Exception as e:
                logger.warning(f"[Side] 释放摄像头失败: {e}")
        
        self.cap = None
        logger.info("[Side] 摄像头已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# ========== 单例模式 ==========

_side_camera: Optional[SideCamera] = None


def get_side_camera(**kwargs) -> SideCamera:
    """获取旁轴摄像头单例"""
    global _side_camera
    if _side_camera is None:
        _side_camera = SideCamera(**kwargs)
    return _side_camera


def reset_side_camera():
    """重置旁轴摄像头单例"""
    global _side_camera
    if _side_camera:
        _side_camera.close()
    _side_camera = None


# ========== 测试代码 ==========

def test_camera_and_save_images(save_dir: str = "./camera_test", num_images: int = 2):
    """
    测试旁轴摄像头并保存图片
    
    Args:
        save_dir: 图片保存目录
        num_images: 保存图片数量
    """
    import os
    from datetime import datetime
    
    print("=" * 60)
    print("旁轴摄像头驱动测试 + 图片保存")
    print("=" * 60)
    
    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)
    print(f"[信息] 图片将保存到: {os.path.abspath(save_dir)}")
    
    # 创建摄像头对象
    camera = SideCamera()
    
    # 初始化
    if camera.initialize():
        print(f"\n[测试] 摄像头初始化成功，准备采集 {num_images} 张图片...")
        print("[提示] 按 Ctrl+C 可随时中断\n")
        
        saved_count = 0
        frame_count = 0
        
        try:
            while saved_count < num_images:
                frame = camera.get_frame()
                if frame is not None:
                    frame_count += 1
                    
                    # 每30帧保存一张图片（约1秒）
                    if frame_count % 30 == 0:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                        filename = f"side_camera_{timestamp}.jpg"
                        filepath = os.path.join(save_dir, filename)
                        
                        # 保存图片
                        cv2.imwrite(filepath, frame)
                        saved_count += 1
                        
                        print(f"[保存 {saved_count}/{num_images}] {filename}")
                        print(f"  - 分辨率: {frame.shape[1]}x{frame.shape[0]}")
                        print(f"  - 路径: {filepath}")
                        
                time.sleep(0.033)  # 30fps
                
        except KeyboardInterrupt:
            print("\n[测试] 用户中断")
        
        print(f"\n[测试] 共采集 {frame_count} 帧，成功保存 {saved_count} 张图片")
        
        if saved_count > 0:
            print(f"\n[成功] 图片已保存到: {os.path.abspath(save_dir)}")
            print("[提示] 请检查该目录下的 .jpg 文件")
        
    else:
        print("\n[错误] 摄像头初始化失败！")
        print("[可能原因]")
        print("  1. 没有连接 USB 摄像头")
        print("  2. 摄像头被其他程序占用")
        print("  3. 驱动问题")
    
    # 关闭
    camera.close()
    print("\n[测试] 已完成")
    return saved_count


if __name__ == "__main__":
    # 运行测试并保存2张图片
    test_camera_and_save_images(save_dir="./test_images/side", num_images=2)
