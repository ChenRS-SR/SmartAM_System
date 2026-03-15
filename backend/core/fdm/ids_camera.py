"""
IDS 工业相机驱动模块
===================
随轴相机（跟随打印头运动）
使用 ids_peak 库进行图像采集

基于 pacnet_project/hardware/ids_driver_old.py 封装
"""

import os
import sys
import time
import logging
import threading
from typing import Optional, Tuple, Callable
from pathlib import Path

import numpy as np
import cv2

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入 ids_peak
try:
    from ids_peak import ids_peak
    from ids_peak import ids_peak_ipl_extension
    IDS_PEAK_AVAILABLE = True
    logger.info("[IDS] ids_peak 库加载成功")
except ImportError as e:
    IDS_PEAK_AVAILABLE = False
    logger.warning(f"[IDS] ids_peak 库不可用: {e}")


class IDSCamera:
    """
    IDS 工业相机驱动类
    
    功能：
    1. 自动发现并连接 IDS 相机
    2. 实时图像采集（随轴视角）
    3. 自动对焦关闭（固定焦距）
    4. 缓冲区管理
    
    使用示例：
        camera = IDSCamera()
        if camera.initialize():
            frame = camera.get_frame()
            # 处理 frame...
        camera.close()
    """
    
    def __init__(self, device_index: int = 0):
        """
        初始化 IDS 相机
        
        Args:
            device_index: 设备索引，默认为0（第一个相机）
        """
        self.device_index = device_index
        self.is_initialized = False
        self.is_running = False
        
        # IDS 设备对象
        self.device_manager = None
        self.device = None
        self.datastream = None
        self.nodemap_remote = None
        
        # 最新帧缓存
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_lock = threading.Lock()
        self._frame_count = 0
        
        # 采集线程
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # 回调函数
        self._frame_callbacks: list[Callable[[np.ndarray], None]] = []
        
        logger.info(f"[IDS] 相机对象已创建 (device_index={device_index})")
    
    def initialize(self) -> bool:
        """
        初始化 IDS 相机
        
        Returns:
            bool: 初始化是否成功
        """
        if not IDS_PEAK_AVAILABLE:
            logger.error("[IDS] ids_peak 库不可用，无法初始化")
            return False
        
        if self.is_initialized:
            logger.warning("[IDS] 相机已经初始化")
            return True
        
        try:
            logger.info("[IDS] 正在初始化相机...")
            
            # 1. 初始化库
            ids_peak.Library.Initialize()
            
            # 2. 创建设备管理器
            self.device_manager = ids_peak.DeviceManager.Instance()
            self.device_manager.Update()
            
            # 3. 检查设备
            if self.device_manager.Devices().empty():
                logger.error("[IDS] 未找到 IDS 相机")
                return False
            
            device_count = len(self.device_manager.Devices())
            logger.info(f"[IDS] 找到 {device_count} 个 IDS 相机")
            
            # 4. 打开指定设备
            if self.device_index >= device_count:
                logger.error(f"[IDS] 设备索引 {self.device_index} 超出范围 (共 {device_count} 个)")
                return False
            
            device_info = self.device_manager.Devices()[self.device_index]
            self.device = device_info.OpenDevice(ids_peak.DeviceAccessType_Exclusive)
            logger.info(f"[IDS] 已打开设备: {device_info.ModelName()}")
            
            # 5. 获取远程节点映射
            self.nodemap_remote = self.device.RemoteDevice().NodeMaps()[0]
            
            # 6. 关闭自动对焦（如果支持）
            self._configure_focus()
            
            # 7. 设置固定焦距
            self._set_focus(112)  # 原有代码中的焦距值
            
            # 8. 创建数据流
            self.datastream = self.device.DataStreams()[0].OpenDataStream()
            
            # 9. 申请缓冲区
            payload_size = self.nodemap_remote.FindNode("PayloadSize").Value()
            for i in range(10):
                buffer = self.datastream.AllocAndAnnounceBuffer(payload_size)
                self.datastream.QueueBuffer(buffer)
            logger.info(f"[IDS] 已分配 10 个缓冲区 (payload_size={payload_size})")
            
            # 10. 开始采集
            self.datastream.StartAcquisition()
            self.nodemap_remote.FindNode("AcquisitionStart").Execute()
            
            self.is_initialized = True
            self.is_running = True
            
            # 11. 启动采集线程
            self._stop_event.clear()
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
            
            logger.info("[IDS] 相机初始化成功，采集已启动")
            return True
            
        except Exception as e:
            logger.error(f"[IDS] 初始化失败: {e}")
            self.close()
            return False
    
    def _configure_focus(self):
        """配置对焦设置（关闭自动对焦）"""
        try:
            auto_focus_node = self.nodemap_remote.FindNode("FocusAuto")
            if auto_focus_node.IsAvailable():
                auto_focus_entries = auto_focus_node.Entries()
                for entry in auto_focus_entries:
                    if entry.SymbolicValue() == "Off":
                        auto_focus_node.SetCurrentEntry(entry)
                        logger.info("[IDS] 已关闭自动对焦")
                        break
            else:
                logger.info("[IDS] 该相机不支持自动对焦功能")
        except Exception as e:
            logger.warning(f"[IDS] 配置对焦设置失败: {e}")
    
    def _set_focus(self, focus_value: int):
        """设置固定焦距"""
        try:
            focus_node = self.nodemap_remote.FindNode("FocusStepper")
            if focus_node.IsAvailable():
                focus_node.SetValue(focus_value)
                logger.info(f"[IDS] 已设置焦距: {focus_value}")
            else:
                logger.warning("[IDS] 该相机不支持手动设置焦距")
        except Exception as e:
            logger.warning(f"[IDS] 设置焦距失败: {e}")
    
    def _capture_loop(self):
        """
        后台采集循环
        持续从数据流获取图像并缓存
        """
        logger.info("[IDS] 采集循环已启动")
        
        consecutive_errors = 0
        max_errors = 10
        
        while not self._stop_event.is_set() and self.is_running:
            try:
                frame = self._grab_frame()
                if frame is not None:
                    with self._frame_lock:
                        self._latest_frame = frame
                        self._frame_count += 1
                    
                    # 触发回调
                    for callback in self._frame_callbacks:
                        try:
                            callback(frame)
                        except Exception as e:
                            logger.error(f"[IDS] 回调执行错误: {e}")
                    
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    logger.warning(f"[IDS] 采集错误 ({consecutive_errors}/{max_errors}): {e}")
                
                if consecutive_errors >= max_errors:
                    logger.error("[IDS] 连续错误过多，停止采集")
                    break
                
                time.sleep(0.1)
        
        logger.info("[IDS] 采集循环已停止")
    
    def _grab_frame(self) -> Optional[np.ndarray]:
        """
        从数据流抓取一帧图像
        
        Returns:
            np.ndarray: BGR 格式图像，失败返回 None
        """
        if not self.datastream:
            return None
        
        try:
            # 等待缓冲区（1000ms超时）
            buffer = self.datastream.WaitForFinishedBuffer(1000)
            if buffer is None:
                raise Exception("WaitForFinishedBuffer 返回 None")
            
            # 转换为图像
            image_data = ids_peak_ipl_extension.BufferToImage(buffer)
            if image_data is None:
                raise Exception("BufferToImage 返回 None")
            
            # 获取图像尺寸
            width = image_data.Width()
            height = image_data.Height()
            pixel_format = image_data.PixelFormat()
            
            if width <= 0 or height <= 0:
                raise Exception(f"无效的图像尺寸: {width}x{height}")
            
            # 获取 numpy 数组
            image_np = image_data.get_numpy()
            if image_np is None:
                raise Exception("get_numpy() 返回 None")
            
            # 根据像素格式处理
            if pixel_format == "RGB8":
                image_np = image_np.reshape((height, width, 3))
                image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            elif pixel_format == "Mono8":
                image_np = image_np.reshape((height, width))
                # 转换为 3 通道（如果需要）
                image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
            
            # 重新排队缓冲区
            self.datastream.QueueBuffer(buffer)
            
            return image_np
            
        except Exception as e:
            logger.error(f"[IDS] 抓取帧失败: {e}")
            return None
    
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
        logger.debug(f"[IDS] 注册回调，当前 {len(self._frame_callbacks)} 个")
    
    def unregister_callback(self, callback: Callable[[np.ndarray], None]):
        """注销回调函数"""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)
    
    def close(self):
        """关闭相机并释放资源"""
        logger.info("[IDS] 正在关闭相机...")
        
        # 停止采集线程
        self.is_running = False
        self._stop_event.set()
        
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2)
        
        # 停止采集
        if self.nodemap_remote:
            try:
                self.nodemap_remote.FindNode("AcquisitionStop").Execute()
                logger.info("[IDS] 已停止采集")
            except Exception as e:
                logger.warning(f"[IDS] 停止采集失败: {e}")
        
        if self.datastream:
            try:
                self.datastream.StopAcquisition()
                logger.info("[IDS] 已停止数据流")
            except Exception as e:
                logger.warning(f"[IDS] 停止数据流失败: {e}")
        
        # 关闭库
        try:
            ids_peak.Library.Close()
            logger.info("[IDS] 库已关闭")
        except Exception as e:
            logger.warning(f"[IDS] 关闭库失败: {e}")
        
        self.is_initialized = False
        logger.info("[IDS] 相机已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# ========== 单例模式 ==========

_ids_camera: Optional[IDSCamera] = None


def get_ids_camera(device_index: int = 0) -> IDSCamera:
    """获取 IDS 相机单例"""
    global _ids_camera
    if _ids_camera is None:
        _ids_camera = IDSCamera(device_index)
    return _ids_camera


def reset_ids_camera():
    """重置 IDS 相机单例"""
    global _ids_camera
    if _ids_camera:
        _ids_camera.close()
    _ids_camera = None


# ========== 测试代码 ==========

def test_camera_and_save_images(save_dir: str = "./camera_test", num_images: int = 2):
    """
    测试 IDS 相机并保存图片
    
    Args:
        save_dir: 图片保存目录
        num_images: 保存图片数量
    """
    import os
    from datetime import datetime
    
    print("=" * 60)
    print("IDS 工业相机驱动测试 + 图片保存")
    print("=" * 60)
    
    # 检查 ids_peak 库是否可用
    if not IDS_PEAK_AVAILABLE:
        print("\n[错误] ids_peak 库不可用！")
        print("[可能原因]")
        print("  1. 没有安装 IDS 相机驱动")
        print("  2. 没有安装 ids_peak Python 包")
        print("\n[安装步骤]")
        print("  1. 从 IDS 官网下载并安装 IDS Peak 软件")
        print("  2. 安装 Python 绑定: pip install ids_peak")
        print("\n[跳过测试]")
        return 0
    
    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)
    print(f"[信息] 图片将保存到: {os.path.abspath(save_dir)}")
    
    # 创建相机对象
    camera = IDSCamera()
    
    # 初始化
    if camera.initialize():
        print(f"\n[测试] 相机初始化成功，准备采集 {num_images} 张图片...")
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
                        filename = f"ids_camera_{timestamp}.jpg"
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
        print("\n[错误] 相机初始化失败！")
        print("[可能原因]")
        print("  1. 没有连接 IDS 相机")
        print("  2. 相机被其他程序占用")
        print("  3. 驱动问题")
    
    # 关闭
    camera.close()
    print("\n[测试] 已完成")
    return saved_count


if __name__ == "__main__":
    # 运行测试并保存2张图片
    test_camera_and_save_images(save_dir="./test_images/ids", num_images=2)
