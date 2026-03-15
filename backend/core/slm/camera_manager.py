"""
摄像头管理模块
==============
管理CH1主摄和CH2副摄两个USB摄像头
"""

import time
import threading
import numpy as np
from typing import Optional, Dict, Tuple, List, Callable
from dataclasses import dataclass
import cv2


@dataclass
class CameraFrame:
    """摄像头帧数据结构"""
    timestamp: float
    frame: np.ndarray
    channel: str  # 'CH1' 或 'CH2'
    frame_number: int
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'channel': self.channel,
            'frame_number': self.frame_number,
            'shape': self.frame.shape if self.frame is not None else None
        }


class CameraManager:
    """摄像头管理器 - 管理CH1主摄和CH2副摄"""
    
    def __init__(self, ch1_index: int = 2, ch2_index: int = 3, 
                 fps: int = 30, display_size: Tuple[int, int] = (640, 480)):
        self.ch1_index = ch1_index
        self.ch2_index = ch2_index
        self.fps = fps
        self.display_size = display_size
        
        self.ch1_camera: Optional[cv2.VideoCapture] = None
        self.ch2_camera: Optional[cv2.VideoCapture] = None
        
        self.ch1_enabled = True
        self.ch2_enabled = True
        
        self.is_connected = False
        self.last_error = ""
        
        # 帧计数
        self.ch1_frame_count = 0
        self.ch2_frame_count = 0
        
        # 最新帧
        self._latest_ch1: Optional[np.ndarray] = None
        self._latest_ch2: Optional[np.ndarray] = None
        self._帧锁 = threading.Lock()
        
        # 采集线程
        self._ch1_thread: Optional[threading.Thread] = None
        self._ch2_thread: Optional[threading.Thread] = None
        self._停止标志 = threading.Event()
        
        # 回调
        self._回调列表: List[Callable[[CameraFrame], None]] = []
        
        # 错误计数
        self.ch1_error_count = 0
        self.ch2_error_count = 0
        self.max_errors = 10
    
    def find_available_cameras(self) -> List[Dict]:
        """查找可用的摄像头 - 带超时机制防止卡死"""
        import concurrent.futures
        
        available = []
        print("[CameraManager] 开始扫描摄像头...")
        
        def test_camera(index):
            """测试单个摄像头，带超时"""
            # 尝试多种后端
            backends = [
                (cv2.CAP_DSHOW, "DirectShow"),
                (cv2.CAP_MSMF, "Media Foundation"),
                (cv2.CAP_ANY, "Auto")
            ]
            
            for backend, backend_name in backends:
                cap = None
                try:
                    cap = cv2.VideoCapture(index, backend)
                    if cap.isOpened():
                        # 尝试读取一帧（带超时保护）
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            h, w = frame.shape[:2]
                            if w >= 160 and h >= 120:
                                return {
                                    'index': index,
                                    'resolution': (w, h),
                                    'name': f'摄像头 {index} ({backend_name})',
                                    'backend': backend_name
                                }
                except Exception as e:
                    pass
                finally:
                    if cap is not None:
                        try:
                            cap.release()
                        except:
                            pass
            return None
        
        # 使用线程池并行检测，带超时
        found_indices = set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # 提交所有检测任务
            future_to_index = {
                executor.submit(test_camera, i): i for i in range(0, 10)
            }
            
            # 收集结果，每个检测最多等待3秒
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result(timeout=3.0)
                    if result and result['index'] not in found_indices:
                        available.append(result)
                        found_indices.add(result['index'])
                        print(f"[CameraManager] 发现摄像头 {result['index']}: {result['resolution'][0]}x{result['resolution'][1]}")
                except concurrent.futures.TimeoutError:
                    print(f"[CameraManager] 摄像头 {index} 检测超时，可能已被占用")
                except Exception as e:
                    print(f"[CameraManager] 摄像头 {index} 检测错误: {e}")
        
        # 按索引排序
        available.sort(key=lambda x: x['index'])
        print(f"[CameraManager] 扫描完成，共发现 {len(available)} 个摄像头")
        return available
    
    def connect(self) -> bool:
        """连接所有启用的摄像头"""
        success = True
        
        if self.ch1_enabled:
            if not self._connect_camera('CH1', self.ch1_index):
                success = False
        
        if self.ch2_enabled:
            if not self._connect_camera('CH2', self.ch2_index):
                success = False
        
        self.is_connected = success
        return success
    
    def _connect_camera(self, channel: str, index: int) -> bool:
        """连接单个摄像头"""
        camera = None
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        
        for backend in backends:
            try:
                camera = cv2.VideoCapture(index, backend)
                if camera.isOpened():
                    ret, test_frame = camera.read()
                    if ret and test_frame is not None:
                        print(f"[CameraManager] {channel} 使用后端 {backend} 连接成功")
                        break
                    else:
                        camera.release()
                        camera = None
            except Exception as e:
                if camera:
                    camera.release()
                camera = None
        
        if camera is None or not camera.isOpened():
            self.last_error = f"{channel} 连接失败"
            print(f"[CameraManager] {self.last_error}")
            return False
        
        # 设置参数
        camera.set(cv2.CAP_PROP_FPS, self.fps)
        
        if channel == 'CH1':
            self.ch1_camera = camera
            self.ch1_frame_count = 0
        else:
            self.ch2_camera = camera
            self.ch2_frame_count = 0
        
        print(f"[CameraManager] {channel} 连接成功")
        return True
    
    def disconnect(self):
        """断开所有摄像头"""
        print("[CameraManager] 开始断开连接...")
        self._停止标志.set()
        
        # 等待采集线程结束
        if self._ch1_thread and self._ch1_thread.is_alive():
            print("[CameraManager] 等待CH1线程结束...")
            self._ch1_thread.join(timeout=2.0)
        if self._ch2_thread and self._ch2_thread.is_alive():
            print("[CameraManager] 等待CH2线程结束...")
            self._ch2_thread.join(timeout=2.0)
        
        # 释放摄像头资源
        if self.ch1_camera:
            try:
                print("[CameraManager] 释放CH1摄像头...")
                self.ch1_camera.release()
            except Exception as e:
                print(f"[CameraManager] 释放CH1摄像头出错: {e}")
            finally:
                self.ch1_camera = None
                
        if self.ch2_camera:
            try:
                print("[CameraManager] 释放CH2摄像头...")
                self.ch2_camera.release()
            except Exception as e:
                print(f"[CameraManager] 释放CH2摄像头出错: {e}")
            finally:
                self.ch2_camera = None
        
        # 给系统一些时间释放资源
        import time
        time.sleep(0.5)
        
        self.is_connected = False
        self._latest_ch1 = None
        self._latest_ch2 = None
        print("[CameraManager] 已断开连接")
    
    def read_frame(self, channel: str) -> Optional[np.ndarray]:
        """读取单帧图像"""
        camera = self.ch1_camera if channel == 'CH1' else self.ch2_camera
        
        if camera is None or not camera.isOpened():
            return None
        
        try:
            ret, frame = camera.read()
            if ret and frame is not None:
                # 转换为RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # 调整大小
                frame_resized = cv2.resize(frame_rgb, self.display_size)
                return frame_resized
            return None
        except Exception as e:
            print(f"[CameraManager] 读取{frame}失败: {e}")
            return None
    
    def start_continuous_capture(self):
        """开始连续采集"""
        self._停止标志.clear()
        
        print(f"[CameraManager] 启动连续采集: CH1_enabled={self.ch1_enabled}, CH2_enabled={self.ch2_enabled}")
        print(f"[CameraManager] CH1_camera={'已初始化' if self.ch1_camera else '未初始化'}, CH2_camera={'已初始化' if self.ch2_camera else '未初始化'}")
        
        if self.ch1_enabled and self.ch1_camera:
            self._ch1_thread = threading.Thread(target=self._capture_loop, args=('CH1',))
            self._ch1_thread.daemon = True
            self._ch1_thread.start()
            print("[CameraManager] CH1 采集线程已启动")
        else:
            print(f"[CameraManager] CH1 未启动: enabled={self.ch1_enabled}, camera={'有' if self.ch1_camera else '无'}")
        
        if self.ch2_enabled and self.ch2_camera:
            self._ch2_thread = threading.Thread(target=self._capture_loop, args=('CH2',))
            self._ch2_thread.daemon = True
            self._ch2_thread.start()
            print("[CameraManager] CH2 采集线程已启动")
        else:
            print(f"[CameraManager] CH2 未启动: enabled={self.ch2_enabled}, camera={'有' if self.ch2_camera else '无'}")
        
        print("[CameraManager] 连续采集启动完成")
    
    def _capture_loop(self, channel: str):
        """采集循环"""
        camera = self.ch1_camera if channel == 'CH1' else self.ch2_camera
        error_count = 0
        frame_count = 0
        success_count = 0
        
        interval = 1.0 / self.fps
        
        print(f"[CameraManager] {channel} 采集循环开始")
        
        while not self._停止标志.is_set():
            if camera is None or not camera.isOpened():
                print(f"[CameraManager] {channel} 摄像头未就绪，等待...")
                self._停止标志.wait(0.5)
                continue
            
            try:
                ret, frame = camera.read()
                if ret and frame is not None and frame.size > 0:
                    error_count = 0
                    frame_count += 1
                    success_count += 1
                    
                    # 处理帧
                    try:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_resized = cv2.resize(frame_rgb, self.display_size)
                        
                        # 保存最新帧
                        with self._帧锁:
                            if channel == 'CH1':
                                self._latest_ch1 = frame_resized
                                self.ch1_frame_count = frame_count
                            else:
                                self._latest_ch2 = frame_resized
                                self.ch2_frame_count = frame_count
                        
                        # 触发回调
                        camera_frame = CameraFrame(
                            timestamp=time.time(),
                            frame=frame_resized,
                            channel=channel,
                            frame_number=frame_count
                        )
                        
                        for callback in self._回调列表:
                            try:
                                callback(camera_frame)
                            except Exception as cb_e:
                                print(f"[CameraManager] {channel} 回调错误: {cb_e}")
                                
                        # 每100帧打印一次日志
                        if success_count % 100 == 0:
                            print(f"[CameraManager] {channel} 已采集 {success_count} 帧")
                            
                    except Exception as proc_e:
                        print(f"[CameraManager] {channel} 帧处理错误: {proc_e}")
                else:
                    error_count += 1
                    if error_count % 10 == 0:
                        print(f"[CameraManager] {channel} 读取失败，错误计数: {error_count}")
                    if error_count > self.max_errors:
                        print(f"[CameraManager] {channel} 连续错误次数过多，停止采集")
                        break
                
                self._停止标志.wait(interval)
                
            except Exception as e:
                error_count += 1
                print(f"[CameraManager] {channel} 采集错误: {e}")
                self._停止标志.wait(0.1)
        
        print(f"[CameraManager] {channel} 采集循环结束，共采集 {success_count} 帧")
    
    def get_latest_frame(self, channel: str) -> Optional[np.ndarray]:
        """获取最新帧"""
        with self._帧锁:
            if channel == 'CH1':
                return self._latest_ch1.copy() if self._latest_ch1 is not None else None
            else:
                return self._latest_ch2.copy() if self._latest_ch2 is not None else None
    
    def get_frame_jpeg(self, channel: str, quality: int = 85) -> Optional[bytes]:
        """获取JPEG格式的帧"""
        frame = self.get_latest_frame(channel)
        if frame is None:
            return None
        
        try:
            # RGB转BGR用于编码
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            ret, jpeg = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if ret:
                return jpeg.tobytes()
            return None
        except Exception as e:
            print(f"[CameraManager] JPEG编码失败: {e}")
            return None
    
    def register_callback(self, callback: Callable[[CameraFrame], None]):
        """注册回调"""
        if callback not in self._回调列表:
            self._回调列表.append(callback)
    
    def unregister_callback(self, callback: Callable[[CameraFrame], None]):
        """取消注册回调"""
        if callback in self._回调列表:
            self._回调列表.remove(callback)
    
    def set_camera_enabled(self, channel: str, enabled: bool):
        """设置摄像头启用状态"""
        if channel == 'CH1':
            self.ch1_enabled = enabled
        elif channel == 'CH2':
            self.ch2_enabled = enabled
    
    def get_status(self) -> Dict:
        """获取摄像头状态"""
        return {
            'CH1': {
                'enabled': self.ch1_enabled,
                'connected': self.ch1_camera is not None and self.ch1_camera.isOpened(),
                'frame_count': self.ch1_frame_count
            },
            'CH2': {
                'enabled': self.ch2_enabled,
                'connected': self.ch2_camera is not None and self.ch2_camera.isOpened(),
                'frame_count': self.ch2_frame_count
            }
        }


class MockCameraManager:
    """模拟摄像头管理器"""
    
    def __init__(self, ch1_index: int = 2, ch2_index: int = 3,
                 fps: int = 30, display_size: Tuple[int, int] = (640, 480)):
        self.ch1_index = ch1_index
        self.ch2_index = ch2_index
        self.fps = fps
        self.display_size = display_size
        
        self.ch1_enabled = True
        self.ch2_enabled = True
        self.is_connected = False
        self.last_error = ""
        
        self.ch1_frame_count = 0
        self.ch2_frame_count = 0
        
        self._latest_ch1: Optional[np.ndarray] = None
        self._latest_ch2: Optional[np.ndarray] = None
        self._帧锁 = threading.Lock()
        
        self._ch1_thread: Optional[threading.Thread] = None
        self._ch2_thread: Optional[threading.Thread] = None
        self._停止标志 = threading.Event()
        
        self._回调列表: List[Callable[[CameraFrame], None]] = []
        
        self._time_offset = 0
    
    def find_available_cameras(self) -> List[Dict]:
        """查找可用摄像头"""
        return [
            {'index': 0, 'resolution': (640, 480), 'name': '模拟摄像头 0'},
            {'index': 1, 'resolution': (640, 480), 'name': '模拟摄像头 1'},
        ]
    
    def connect(self) -> bool:
        """模拟连接"""
        self.is_connected = True
        print("[MockCameraManager] 模拟连接成功")
        return True
    
    def disconnect(self):
        """断开连接"""
        self._停止标志.set()
        if self._ch1_thread and self._ch1_thread.is_alive():
            self._ch1_thread.join(timeout=1.0)
        if self._ch2_thread and self._ch2_thread.is_alive():
            self._ch2_thread.join(timeout=1.0)
        self.is_connected = False
        print("[MockCameraManager] 已断开连接")
    
    def _generate_mock_frame(self, channel: str) -> np.ndarray:
        """生成模拟帧"""
        w, h = self.display_size
        
        # 创建基础图像
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 背景渐变
        for y in range(h):
            frame[y, :] = [50 + y // 5, 50, 100 - y // 10]
        
        # 时间因子
        t = time.time() * 2
        self._time_offset += 0.05
        
        # 绘制模拟内容
        if channel == 'CH1':
            # 模拟SLM打印区域 - 扫描线
            scan_y = int(h / 2 + np.sin(self._time_offset * 0.5) * h / 4)
            cv2.line(frame, (0, scan_y), (w, scan_y), (0, 255, 255), 3)
            
            # 熔池模拟
            center_x = int(w / 2 + np.sin(self._time_offset * 0.3) * w / 6)
            center_y = scan_y
            cv2.circle(frame, (center_x, center_y), 30, (255, 100, 0), -1)
            
            # 添加网格
            for i in range(0, w, 40):
                cv2.line(frame, (i, 0), (i, h), (30, 30, 30), 1)
            for i in range(0, h, 40):
                cv2.line(frame, (0, i), (w, i), (30, 30, 30), 1)
        
        else:  # CH2
            # 整体视角 - 模拟设备
            # 外框
            cv2.rectangle(frame, (w//4, h//6), (w*3//4, h*5//6), (100, 100, 100), 2)
            
            # 激光头
            laser_x = int(w / 2 + np.sin(self._time_offset * 0.4) * w / 8)
            cv2.rectangle(frame, (laser_x - 20, h//4), (laser_x + 20, h//3), (200, 200, 200), -1)
            
            # 激光束
            cv2.line(frame, (laser_x, h//3), (laser_x, h*2//3), (0, 150, 255), 2)
        
        # 添加文字标识
        cv2.putText(frame, f"[MOCK] {channel}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Frame: {int(self._time_offset * 10)}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def read_frame(self, channel: str) -> Optional[np.ndarray]:
        """读取模拟帧"""
        return self._generate_mock_frame(channel)
    
    def start_continuous_capture(self):
        """开始连续采集"""
        self._停止标志.clear()
        
        if self.ch1_enabled:
            self._ch1_thread = threading.Thread(target=self._capture_loop, args=('CH1',))
            self._ch1_thread.daemon = True
            self._ch1_thread.start()
        
        if self.ch2_enabled:
            self._ch2_thread = threading.Thread(target=self._capture_loop, args=('CH2',))
            self._ch2_thread.daemon = True
            self._ch2_thread.start()
    
    def _capture_loop(self, channel: str):
        """采集循环"""
        frame_count = 0
        interval = 1.0 / self.fps
        
        while not self._停止标志.is_set():
            frame = self._generate_mock_frame(channel)
            frame_count += 1
            
            with self._帧锁:
                if channel == 'CH1':
                    self._latest_ch1 = frame
                    self.ch1_frame_count = frame_count
                else:
                    self._latest_ch2 = frame
                    self.ch2_frame_count = frame_count
            
            camera_frame = CameraFrame(
                timestamp=time.time(),
                frame=frame,
                channel=channel,
                frame_number=frame_count
            )
            
            for callback in self._回调列表:
                try:
                    callback(camera_frame)
                except:
                    pass
            
            self._停止标志.wait(interval)
    
    def get_latest_frame(self, channel: str) -> Optional[np.ndarray]:
        """获取最新帧"""
        with self._帧锁:
            if channel == 'CH1':
                return self._latest_ch1.copy() if self._latest_ch1 is not None else None
            else:
                return self._latest_ch2.copy() if self._latest_ch2 is not None else None
    
    def get_frame_jpeg(self, channel: str, quality: int = 85) -> Optional[bytes]:
        """获取JPEG格式的帧"""
        frame = self.get_latest_frame(channel)
        if frame is None:
            # 生成一帧
            frame = self._generate_mock_frame(channel)
        
        try:
            ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if ret:
                return jpeg.tobytes()
            return None
        except Exception as e:
            print(f"[MockCameraManager] JPEG编码失败: {e}")
            return None
    
    def register_callback(self, callback: Callable[[CameraFrame], None]):
        """注册回调"""
        if callback not in self._回调列表:
            self._回调列表.append(callback)
    
    def unregister_callback(self, callback: Callable[[CameraFrame], None]):
        """取消注册回调"""
        if callback in self._回调列表:
            self._回调列表.remove(callback)
    
    def set_camera_enabled(self, channel: str, enabled: bool):
        """设置摄像头启用状态"""
        if channel == 'CH1':
            self.ch1_enabled = enabled
        elif channel == 'CH2':
            self.ch2_enabled = enabled
    
    def get_status(self) -> Dict:
        """获取摄像头状态"""
        return {
            'CH1': {
                'enabled': self.ch1_enabled,
                'connected': self.is_connected,
                'frame_count': self.ch1_frame_count
            },
            'CH2': {
                'enabled': self.ch2_enabled,
                'connected': self.is_connected,
                'frame_count': self.ch2_frame_count
            }
        }
