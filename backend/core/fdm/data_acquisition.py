"""
数据采集模块 - 无界面版本
基于 VB02_ids_websocket.py 和 ids_websocket.py 重构
支持 Web 界面控制

数据保存格式与之前保持一致：
- IDS相机图像 (随轴)
- 旁轴RGB照片
- 旁轴红外伪彩色图像
- 旁轴红外温度矩阵 (.npz)
- print_message.csv (包含所有列)
"""
import os
import cv2
import time
import threading
import queue
import csv
import json
import requests
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Callable, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# IDS 相机
try:
    from ids_peak import ids_peak
    from ids_peak import ids_peak_ipl_extension
    IDS_AVAILABLE = True
except ImportError:
    IDS_AVAILABLE = False
    logging.warning("IDS Peak 库不可用")

# 尝试导入其他硬件模块
try:
    from core.fdm.fotric_driver import FotricEnhancedDevice
    FOTRIC_AVAILABLE = True
except ImportError:
    FOTRIC_AVAILABLE = False
    logging.warning("Fotric 驱动不可用")

# 导入模拟生成器
try:
    from core.simulation import SimulationGenerator, SimulationConfig, get_simulation_generator
    SIMULATION_AVAILABLE = True
except ImportError:
    SIMULATION_AVAILABLE = False
    logging.warning("模拟生成器不可用")

# 导入 OctoPrint 模拟器
try:
    from core.octoprint_simulation import OctoPrintSimulator, OctoPrintSimulationConfig, get_octoprint_simulator
    OCTOPRINT_SIMULATION_AVAILABLE = True
except ImportError:
    OCTOPRINT_SIMULATION_AVAILABLE = False
    logging.warning("OctoPrint 模拟器不可用")

try:
    from hardware.vibration_sensor import DeviceModel as VibrationDevice
    VIBRATION_AVAILABLE = True
except ImportError:
    VIBRATION_AVAILABLE = False
    logging.warning("振动传感器驱动不可用")

try:
    from core.fdm.coordinator import M114Coordinator
    M114_AVAILABLE = True
except ImportError:
    M114_AVAILABLE = False
    logging.warning("M114协调器不可用")

try:
    from core.fdm.parameter_manager import ParameterManager, ParameterMode, STANDARD_TOWERS, HEIGHT_SEGMENTS
    PARAM_MANAGER_AVAILABLE = True
except ImportError:
    PARAM_MANAGER_AVAILABLE = False
    STANDARD_TOWERS = []
    HEIGHT_SEGMENTS = []
    logging.warning("参数管理器不可用")

# 参数阈值配置 (从 config.py 迁移)
PARAM_THRESHOLDS = {
    "flow_rate": [90, 110],     # 流量: <90为低, 90-110为正常, >110为高
    "feed_rate": [80, 120],     # 速度: <80为低, 80-120为正常, >120为高
    "z_offset": [-0.05, 0.15],  # Z偏移: <-0.05为低, -0.05~0.15为正常, >0.15为高
    "hotend": [200, 230]        # 温度: <200为低, 200-230为正常, >230为高
}


class AcquisitionState(Enum):
    """采集状态"""
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 采集中
    PAUSED = "paused"       # 暂停
    STOPPING = "stopping"   # 正在停止


@dataclass
class AcquisitionConfig:
    """采集配置"""
    # 保存路径 - 默认保存到项目根目录的 data 文件夹 (backend 的父目录)
    save_directory: str = "../data"
    
    # 采集帧率 (fps) - 实际为每帧间隔时间 = 1/fps
    capture_fps: float = 2.0  # 默认2fps (0.5秒/帧)
    
    # 采集间隔计算
    @property
    def capture_interval(self) -> float:
        return 1.0 / self.capture_fps
    
    # 是否启用各设备
    enable_ids: bool = True
    enable_side_camera: bool = True
    enable_fotric: bool = True
    enable_vibration: bool = False  # 默认不启用振动传感器
    
    # OctoPrint 配置
    octoprint_url: str = "http://127.0.0.1:5000"
    octoprint_api_key: str = ""
    
    # IDS 相机配置
    ids_exposure_time: float = 8000.0  # 曝光时间(us)
    ids_gain: float = 1.0
    
    # 旁轴相机配置
    side_camera_index: int = 0
    side_camera_resolution: tuple = (1920, 1080)
    
    # Fotric 配置
    fotric_ip: str = "192.168.1.100"
    fotric_port: int = 10080
    
    # 振动传感器配置
    vibration_port: str = "COM9"
    vibration_baudrate: int = 115200
    
    # 当前打印参数 (用于class计算)
    flow_rate: float = 100.0      # 当前流量倍率
    feed_rate: float = 100.0      # 当前打印速度
    z_offset: float = 0.0         # 当前Z偏移(相对于initial_z_offset的调节值)
    target_hotend: float = 200.0  # 目标热端温度
    
    # 初始Z补偿 (打印机调平后的基准值，只发送一次M290)
    initial_z_offset: float = -2.55
    
    # 参数模式配置
    param_mode: str = "fixed"     # fixed/random/tower
    random_interval_sec: float = 120
    current_tower: int = 1
    
    # 时空同步缓冲配置
    stability_z_diff_mm: float = 0.6  # 参数变化后Z轴变化多少mm开始采集 (约3层，0.2mm/层)
    silent_height_mm: float = 0.5     # 静默区高度 (参数变化后不采集，适配5mm段高)
    
    # IDS 图像处理配置
    ids_sharpen_enabled: bool = True   # 启用锐化
    ids_sharpen_method: str = "unsharp"  # unsharp/laplacian/strong
    ids_gamma: float = 0.8             # 伽马校正 (0.5-1.5, <1提亮暗部)
    ids_clahe_enabled: bool = True     # 启用自适应对比度增强
    ids_denoise_enabled: bool = False  # 启用降噪 (会稍微模糊)
    
    # 模拟模式配置
    simulation_mode: bool = False      # 启用模拟模式（无硬件调试）
    simulation_auto_fallback: bool = True  # 硬件连接失败时自动切换到模拟模式
    
    # OctoPrint 模拟配置
    octoprint_simulation: bool = False  # 启用 OctoPrint 模拟（无需真实打印机）
    octoprint_simulation_auto_fallback: bool = True  # OctoPrint 连接失败时自动使用模拟


@dataclass
class FrameData:
    """单帧数据结构 - 对应print_message.csv的一行"""
    frame_number: int
    timestamp: str
    
    # 图像路径 (相对路径)
    ids_image_path: str = ""           # IDS相机图像路径
    side_image_path: str = ""          # 旁轴相机图像路径
    fotric_image_path: str = ""        # 红外伪彩色图像路径
    fotric_data_path: str = ""         # 红外温度矩阵路径
    
    # 打印机坐标
    current_x: float = 0.0
    current_y: float = 0.0
    current_z: float = 0.0
    
    # 打印参数设定值
    flow_rate: float = 100.0
    feed_rate: float = 100.0
    z_offset: float = 0.0
    target_hotend: float = 200.0
    
    # 打印参数实际值
    hot_end: float = 0.0
    bed: float = 0.0
    
    # 参数分类 (0=低, 1=正常, 2=高)
    flow_rate_class: int = 1
    feed_rate_class: int = 1
    z_offset_class: int = 1
    hotend_class: int = 1
    
    # 红外温度统计
    fotric_temp_min: float = 0.0
    fotric_temp_max: float = 0.0
    fotric_temp_avg: float = 0.0
    
    # 图像数据 (保存时使用)
    ids_image: Optional[np.ndarray] = None
    side_image: Optional[np.ndarray] = None
    fotric_image: Optional[np.ndarray] = None
    fotric_data: Optional[np.ndarray] = None


class DataAcquisition:
    """
    数据采集主类
    管理所有硬件设备的数据采集和保存
    """
    
    def __init__(self, config: AcquisitionConfig = None):
        self.config = config or AcquisitionConfig()
        self.state = AcquisitionState.IDLE
        self.frame_count = 0
        self.start_time = None
        self.current_task_dir = None
        
        # 回调函数
        self.on_frame_captured: Optional[Callable] = None
        self.on_state_changed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # 线程控制
        self._acquisition_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        # 设备实例
        self._ids_camera = None
        self._side_camera = None
        self._fotric_device = None
        self._vibration_device = None
        self._m114_coord = None  # 已废弃：使用 DisplayLayerProgress 插件获取 Z 高度
        
        # 数据队列
        self._save_queue = queue.Queue(maxsize=100)
        self._save_thread: Optional[threading.Thread] = None
        
        # CSV文件
        self._csv_file = None
        self._csv_writer = None
        
        # 线程锁
        self._state_lock = threading.Lock()
        self._frame_lock = threading.Lock()
        
        # WebSocket 状态缓存
        self._current_position = {"X": 0.0, "Y": 0.0, "Z": 0.0, "E": 0.0}
        
        # 模拟生成器（仅在模拟模式或硬件不可用时使用）
        self._simulation_generator = None
        self._simulation_mode_active = False
        
        # OctoPrint 模拟器
        self._octoprint_simulator = None
        self._octoprint_simulation_active = False
        
        # OctoPrint 缓存和连接控制
        self._octoprint_cache = {
            "printer": {"hotend": 0, "bed": 0, "hotend_target": 0, "bed_target": 0},
            "job": {"state": "Unknown", "progress": 0, "filename": ""}
        }
        self._octoprint_last_success = 0
        self._octoprint_backoff = 1  # 指数退避初始值（秒）
        
        # 初始化 PacNet 推理引擎
        self._inference_engine = None
        self._init_inference_engine()
        
        # 最新预测结果
        self._latest_prediction = None
        
        self._octoprint_cache_ttl = 5  # 缓存有效期（秒）
        
        # 参数管理器
        self._param_manager: Optional[ParameterManager] = None
        if PARAM_MANAGER_AVAILABLE:
            self._param_manager = ParameterManager()
            # 设置参数变化回调
            self._param_manager.on_param_change = self._on_param_changed
        
        logging.info("[DataAcquisition] 初始化完成")
    
    def _init_inference_engine(self):
        """初始化 PacNet 推理引擎"""
        try:
            # 动态导入以避免循环依赖
            from core.pacnet_inference import get_inference_engine
            self._inference_engine = get_inference_engine()
            if self._inference_engine and self._inference_engine.is_loaded:
                logging.info("[DataAcquisition] PacNet 推理引擎初始化成功")
            else:
                logging.warning("[DataAcquisition] PacNet 推理引擎未加载，将在首次推理时尝试加载")
        except Exception as e:
            logging.error(f"[DataAcquisition] PacNet 推理引擎初始化失败: {e}")
            self._inference_engine = None
    
    def _run_inference(self, ids_frame, side_frame, fotric_frame, thermal_data, params=None):
        """运行模型推理"""
        if self._inference_engine is None:
            return None
        
        try:
            # 准备输入数据
            if thermal_data and isinstance(thermal_data, dict):
                thermal_matrix = thermal_data.get("matrix")
            else:
                thermal_matrix = None
            
            # 获取当前打印参数（如果没有提供）
            if params is None:
                params = np.array([
                    self.config.flow_rate,
                    self.config.feed_rate,
                    self.config.z_offset,
                    self.config.target_hotend,
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0  # 填充到10维
                ], dtype=np.float32)
            
            # 执行推理
            result = self._inference_engine.inference(
                ids_frame=ids_frame,
                computer_frame=side_frame,
                fotric_frame=fotric_frame,
                thermal_matrix=thermal_matrix,
                params=params
            )
            
            if result:
                self._latest_prediction = result
                logging.debug(f"[Inference] 推理完成: Flow={result.flow_rate_label}, Feed={result.feed_rate_label}")
            
            return result
            
        except Exception as e:
            logging.error(f"[Inference] 推理失败: {e}")
            return None
    
    def _enable_simulation_mode(self):
        """启用模拟模式"""
        if not SIMULATION_AVAILABLE:
            logging.error("[模拟模式] 模拟生成器不可用，无法启用模拟模式")
            return
        
        self._simulation_mode_active = True
        self._simulation_generator = get_simulation_generator()
        logging.info("[模拟模式] ========== 已启用 ==========")
        logging.info("[模拟模式] 系统将生成模拟数据用于调试")
        logging.info("[模拟模式] IDS相机: 模拟")
        logging.info("[模拟模式] 旁轴相机: 模拟")
        logging.info("[模拟模式] 热像相机: 模拟")
        logging.info("[模拟模式] 打印机位置: 模拟")
        
        # 同时启用 OctoPrint 模拟
        self._enable_octoprint_simulation()
    
    def _enable_octoprint_simulation(self):
        """启用 OctoPrint 模拟模式"""
        if not OCTOPRINT_SIMULATION_AVAILABLE:
            logging.error("[OctoPrint模拟] OctoPrint 模拟器不可用")
            return
        
        self._octoprint_simulation_active = True
        self._octoprint_simulator = get_octoprint_simulator()
        logging.info("[OctoPrint模拟] ========== 已启用 ==========")
        logging.info("[OctoPrint模拟] 打印机状态: 模拟")
        logging.info("[OctoPrint模拟] 温度数据: 模拟")
        logging.info("[OctoPrint模拟] 位置数据: 模拟")
        logging.info("[OctoPrint模拟] G-code命令: 记录（不实际执行）")
    
    def _get_param_class(self, param_value: float, thresholds: List[float]) -> int:
        """
        将连续值离散化为 0, 1, 2
        0: 低于阈值下限 (偏低)
        1: 在阈值范围内 (正常)
        2: 高于阈值上限 (偏高)
        """
        if param_value <= thresholds[0]:
            return 0
        elif param_value > thresholds[1]:
            return 2
        else:
            return 1
    
    def _on_param_changed(self, new_params):
        """
        参数变化回调
        将新参数发送到打印机
        """
        # 检查当前Z高度
        current_z = self._current_position.get('Z', 0.0)
        
        # 塔模式下，Z < 5mm 不发送参数修改
        if self.config.param_mode == "tower" and current_z < 5.0:
            logging.info(f"[_on_param_changed] Z={current_z:.2f}mm < 5mm，缓存参数不发送: "
                        f"T={new_params.target_hotend}°C, Z={new_params.z_offset}mm")
            # 只更新配置，不发送到打印机
            self.config.flow_rate = new_params.flow_rate
            self.config.feed_rate = new_params.feed_rate
            self.config.z_offset = new_params.z_offset
            self.config.target_hotend = new_params.target_hotend
            return
        
        logging.info(f"[_on_param_changed] Z={current_z:.2f}mm，开始处理参数变化: "
                    f"T={new_params.target_hotend}°C, Z={new_params.z_offset}mm, "
                    f"F={new_params.feed_rate}, E={new_params.flow_rate}")
        
        # OctoPrint 模拟模式：发送命令到模拟器
        if self._octoprint_simulation_active and self._octoprint_simulator:
            self._send_gcode_to_simulator(new_params)
            return
        
        try:
            import requests
            url = f"{self.config.octoprint_url}/api/printer/command"
            headers = {
                "X-Api-Key": self.config.octoprint_api_key,
                "Content-Type": "application/json"
            }
            
            # 发送流量倍率
            if hasattr(new_params, 'flow_rate'):
                gcode = f"M221 S{int(new_params.flow_rate)}"
                requests.post(url, headers=headers, json={"command": gcode}, timeout=2)
                logging.info(f"[参数] 流量倍率: {new_params.flow_rate}%")
            
            # 发送速度倍率
            if hasattr(new_params, 'feed_rate'):
                gcode = f"M220 S{int(new_params.feed_rate)}"
                requests.post(url, headers=headers, json={"command": gcode}, timeout=2)
                logging.info(f"[参数] 速度倍率: {new_params.feed_rate}%")
            
            # 发送Z偏移（直接使用 M290 相对调整，不再使用 M114 查询）
            if hasattr(new_params, 'z_offset'):
                target_display_offset = new_params.z_offset  # 目标显示值（如0.25）
                logging.info(f"[参数] Z偏移处理开始: 目标显示值={target_display_offset:.2f}mm")
                
                # 安全检查：显示值必须在安全范围内 (-0.5 到 +0.5)
                if not (-0.5 <= target_display_offset <= 0.5):
                    logging.error(f"[参数] Z偏移值 ({target_display_offset}mm) 超出安全范围 [-0.5, +0.5]，已拒绝发送！")
                    return
                
                # 计算需要调整的差值（相对于当前配置值）
                current_display = self.config.z_offset
                delta = target_display_offset - current_display
                
                # 如果差值很小，跳过
                if abs(delta) < 0.01:
                    logging.info(f"[参数] Z偏移无需调整: 当前={current_display:.2f}, 目标={target_display_offset:.2f}")
                else:
                    # 使用 M290 相对调整
                    logging.info(f"[参数] 准备发送M290 Z{delta:+.2f}")
                    try:
                        gcode = f"M290 Z{delta:+.2f}"
                        response = requests.post(url, headers=headers, json={"command": gcode}, timeout=2)
                        if response.status_code == 204:
                            # 更新配置为目标值（假设命令成功）
                            self.config.z_offset = target_display_offset
                            logging.info(f"[参数] Z偏移调整成功: {current_display:.2f} -> {target_display_offset:.2f}")
                        else:
                            logging.warning(f"[参数] Z偏移调整失败: HTTP {response.status_code}")
                    except Exception as e:
                        logging.error(f"[参数] Z偏移调整异常: {e}")
            
            # 发送热端温度
            if hasattr(new_params, 'target_hotend'):
                temp = int(new_params.target_hotend)
                # 安全检查：温度必须在合理范围内 (150-300°C)
                if 150 <= temp <= 300:
                    gcode = f"M104 S{temp}"
                    requests.post(url, headers=headers, json={"command": gcode}, timeout=2)
                    logging.info(f"[参数] 热端温度: {temp}°C")
                else:
                    logging.error(f"[参数] 温度值异常 ({temp}°C)，已拒绝发送！范围应在 150-300 之间")
            
        except Exception as e:
            logging.error(f"[DataAcquisition] 发送参数到打印机失败: {e}")
    
    def _send_gcode_to_simulator(self, new_params):
        """将 G-code 命令发送给 OctoPrint 模拟器"""
        if not self._octoprint_simulator:
            return
        
        logging.info("[OctoPrint模拟] 发送参数到模拟器")
        
        # 发送流量倍率
        if hasattr(new_params, 'flow_rate'):
            gcode = f"M221 S{int(new_params.flow_rate)}"
            self._octoprint_simulator.send_command(gcode)
            logging.info(f"[OctoPrint模拟] 流量倍率: {new_params.flow_rate}%")
        
        # 发送速度倍率
        if hasattr(new_params, 'feed_rate'):
            gcode = f"M220 S{int(new_params.feed_rate)}"
            self._octoprint_simulator.send_command(gcode)
            logging.info(f"[OctoPrint模拟] 速度倍率: {new_params.feed_rate}%")
        
        # 发送Z偏移
        if hasattr(new_params, 'z_offset'):
            target_display_offset = new_params.z_offset
            if -0.5 <= target_display_offset <= 0.5:
                # 计算差值（简化处理，模拟器中直接设置）
                current_offset = self._octoprint_simulator._z_offset
                delta = target_display_offset - current_offset
                if abs(delta) >= 0.01:
                    gcode = f"M290 Z{delta:+.2f}"
                    self._octoprint_simulator.send_command(gcode)
                    logging.info(f"[OctoPrint模拟] Z偏移调整: {current_offset:.2f} -> {target_display_offset:.2f}")
                self.config.z_offset = target_display_offset
            else:
                logging.error(f"[OctoPrint模拟] Z偏移值超出安全范围: {target_display_offset}")
        
        # 发送热端温度
        if hasattr(new_params, 'target_hotend'):
            temp = int(new_params.target_hotend)
            if 150 <= temp <= 300:
                gcode = f"M104 S{temp}"
                self._octoprint_simulator.send_command(gcode)
                logging.info(f"[OctoPrint模拟] 热端温度: {temp}°C")
            else:
                logging.error(f"[OctoPrint模拟] 温度值异常: {temp}°C")
    
    def _update_params_from_manager(self, current_z: float):
        """
        从参数管理器更新参数
        根据当前Z高度和模式决定是否需要更新参数
        
        标准塔模式逻辑：
        - Z < 5mm: 使用默认参数（200°C，流量100，速度100），不发送任何修改
        - Z >= 5mm: 开始应用塔的参数（温度、Z偏移只修改一次，流量速度每段修改）
        
        Args:
            current_z: 当前Z高度
        """
        if not self._param_manager or not PARAM_MANAGER_AVAILABLE:
            return
        
        mode = self.config.param_mode
        
        if mode == "random":
            # 随机模式: 检查是否应该随机变化
            current_time = time.time()
            if self._param_manager.check_should_change_random(current_time):
                new_params = self._param_manager.generate_random_params()
                self._param_manager.apply_param_change(new_params, current_z)
                # 更新配置中的参数
                self.config.flow_rate = new_params.flow_rate
                self.config.feed_rate = new_params.feed_rate
                self.config.z_offset = new_params.z_offset
                self.config.target_hotend = new_params.target_hotend
                
        elif mode == "tower":
            # 标准塔模式: Z < 5mm 不修改任何参数（使用打印机当前设置）
            if current_z < 5.0:
                logging.debug(f"[塔模式] Z={current_z:.2f}mm < 5mm，不修改参数，"
                            f"current_segment={self._param_manager.current_segment_idx}")
                return
            
            # Z >= 5mm: 根据高度自动切换区间
            logging.info(f"[塔模式] Z={current_z:.2f}mm >= 5mm，"
                       f"current_segment={self._param_manager.current_segment_idx}, "
                       f"last_change_z={self._param_manager.last_param_change_z}")
            
            new_params = self._param_manager.get_next_standard_params(current_z)
            
            if new_params:
                logging.info(f"[塔模式] 获取到新参数: Tower={self.config.current_tower}, "
                           f"T={new_params.target_hotend}°C, Z={new_params.z_offset}mm, "
                           f"F={new_params.feed_rate}, E={new_params.flow_rate}")
                # 检查是否是第一次进入 >=5mm 的区域（需要发送温度和Z偏移）
                is_first_tower_segment = (
                    self._param_manager.last_param_change_z is None or 
                    self._param_manager.last_param_change_z < 5.0
                )
                
                if is_first_tower_segment:
                    logging.info(f"[塔模式] Z={current_z:.2f}mm，首次进入采集区间，应用塔参数: "
                               f"T={new_params.target_hotend}°C, Z偏移={new_params.z_offset}mm, "
                               f"F={new_params.feed_rate}, E={new_params.flow_rate}")
                else:
                    logging.info(f"[塔模式] Z={current_z:.2f}mm，切换到新区间: "
                               f"F={new_params.feed_rate}, E={new_params.flow_rate}, "
                               f"Z偏移={new_params.z_offset}mm")
                
                self._param_manager.apply_param_change(new_params, current_z)
                # 更新配置中的参数（用于class计算）
                self.config.flow_rate = new_params.flow_rate
                self.config.feed_rate = new_params.feed_rate
                self.config.z_offset = new_params.z_offset
                self.config.target_hotend = new_params.target_hotend
    
    def initialize(self) -> bool:
        """
        初始化 DAQ 系统（软初始化，不连接设备）
        
        Returns:
            bool: 始终返回 True，表示 DAQ 实例已创建
        """
        # 只初始化配置，不连接设备
        # 设备连接将在 start() 或 connect_device() 中进行
        return True
    
    def connect_device(self, device_type: str) -> bool:
        """
        手动连接指定设备
        
        Args:
            device_type: 设备类型 ('ids', 'side_camera', 'fotric', 'vibration')
                        注意：'m114' 已废弃，使用 DisplayLayerProgress 插件获取 Z 高度
            
        Returns:
            bool: 连接是否成功
        """
        try:
            if device_type == 'ids' and IDS_AVAILABLE:
                if self._init_ids_camera():
                    logging.info("[设备] IDS相机已手动连接")
                    return True
            elif device_type == 'side_camera':
                if self._init_side_camera():
                    logging.info("[设备] 旁轴相机已手动连接")
                    return True
            elif device_type == 'fotric' and FOTRIC_AVAILABLE:
                if self._init_fotric():
                    logging.info("[设备] Fotric相机已手动连接")
                    return True
            elif device_type == 'vibration' and VIBRATION_AVAILABLE:
                if self._init_vibration():
                    logging.info("[设备] 振动传感器已手动连接")
                    return True
            elif device_type == 'm114':
                # M114 已废弃，使用 DisplayLayerProgress 插件获取 Z 高度
                logging.info("[设备] M114 已废弃，使用 DisplayLayerProgress 插件获取 Z 高度")
                return True
        except Exception as e:
            logging.error(f"[设备] 连接 {device_type} 失败: {e}")
        
        return False
    
    def get_device_status(self) -> Dict[str, Any]:
        """获取所有设备的连接状态"""
        # 检查 OctoPrint 连接状态（通过 DisplayLayerProgress 插件）
        octoprint_connected = self._check_octoprint_connection()
        
        # 模拟模式下所有设备都报告为可用
        if self._simulation_mode_active:
            return {
                "ids": True,
                "side_camera": True,
                "fotric": True,
                "vibration": False,  # 振动传感器暂不模拟
                "m114": True,  # 已废弃，保留兼容
                "octoprint": True,
                "displaylayerprogress": True,  # 使用 DisplayLayerProgress 获取 Z 高度
                "simulation": True,  # 标记当前为模拟模式
                "octoprint_simulation": self._octoprint_simulation_active
            }
        
        # OctoPrint 单独模拟模式
        if self._octoprint_simulation_active:
            return {
                "ids": self._ids_camera is not None,
                "side_camera": self._side_camera is not None,
                "fotric": self._fotric_device is not None and (hasattr(self._fotric_device, 'is_connected') and self._fotric_device.is_connected),
                "vibration": self._vibration_device is not None,
                "m114": True,  # 已废弃，保留兼容
                "octoprint": True,
                "displaylayerprogress": True,
                "simulation": False,
                "octoprint_simulation": True
            }
        
        # 真实模式：检查 OctoPrint 连接
        # 注意：如果之前能获取到文件列表，说明连接是成功的
        # 这里简化判断：只要配置了 API Key 就认为已连接（避免频繁请求）
        octoprint_configured = bool(self.config.octoprint_api_key and len(self.config.octoprint_api_key) >= 20)
        
        return {
            "ids": self._ids_camera is not None,
            "side_camera": self._side_camera is not None,
            "fotric": self._fotric_device is not None and (hasattr(self._fotric_device, 'is_connected') and self._fotric_device.is_connected),
            "vibration": self._vibration_device is not None,
            "m114": True,  # 已废弃，使用 DisplayLayerProgress，保留字段兼容
            "octoprint": octoprint_connected or octoprint_configured,
            "displaylayerprogress": octoprint_connected or octoprint_configured,
            "simulation": False,
            "octoprint_simulation": False
        }
    
    def _check_octoprint_connection(self) -> bool:
        """检查 OctoPrint 连接状态"""
        try:
            import requests
            api_key = self.config.octoprint_api_key
            if not api_key or len(api_key) < 20:
                return False
            
            url = f"{self.config.octoprint_url}/api/printer"
            headers = {"X-Api-Key": api_key}
            response = requests.get(url, headers=headers, timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def initialize_devices(self) -> Dict[str, bool]:
        """初始化所有设备（串行执行，带超时控制）
        
        支持模拟模式：当 hardware_available 为 False 时，使用模拟数据
        """
        results = {
            "ids": False,
            "side_camera": False,
            "fotric": False,
            "vibration": False
            # 注意：m114 已废弃，使用 DisplayLayerProgress 插件
        }
        
        # 检查是否应该使用模拟模式
        if self.config.simulation_mode:
            logging.info("[设备] ========== 模拟模式已启用 ==========")
            self._enable_simulation_mode()
            # 模拟模式下所有设备都标记为可用
            return {k: True for k in results.keys()}
        
        # 检查是否仅启用 OctoPrint 模拟
        if self.config.octoprint_simulation:
            logging.info("[设备] ========== OctoPrint 模拟模式已启用 ==========")
            self._enable_octoprint_simulation()
        
        start_time = time.time()
        any_device_connected = False
        
        # 首先扫描所有可用摄像头，明确分配给 IDS 和旁轴
        available_cameras = self._scan_available_cameras()
        logging.warning(f"[设备] 扫描到可用摄像头: {available_cameras}")
        
        # 分配摄像头：
        # 索引 0：旁轴相机（电脑自带摄像头）
        # 索引 1：IDS 随轴相机（USB 摄像头）
        ids_camera_index = None
        side_camera_index = None
        
        # 查找索引 0 和索引 1
        cam_0 = next((cam for cam in available_cameras if cam[0] == 0), None)
        cam_1 = next((cam for cam in available_cameras if cam[0] == 1), None)
        
        if cam_0 and cam_1:
            # 两个都有，按正确分配
            side_camera_index = 0   # 旁轴用索引 0
            ids_camera_index = 1    # IDS 随轴用索引 1
            logging.warning(f"[设备] 分配: 旁轴=索引0({cam_0[1]}x{cam_0[2]}), IDS随轴=索引1({cam_1[1]}x{cam_1[2]})")
        elif cam_0:
            # 只有索引 0，给旁轴
            side_camera_index = 0
            logging.warning(f"[设备] 警告: 只有索引0，分配给旁轴")
        elif cam_1:
            # 只有索引 1，给 IDS
            ids_camera_index = 1
            logging.warning(f"[设备] 警告: 只有索引1，分配给IDS随轴")
        elif len(available_cameras) >= 1:
            # 使用第一个可用摄像头
            ids_camera_index = available_cameras[0][0]
            logging.warning(f"[设备] 警告: 使用第一个可用摄像头索引{ids_camera_index}给IDS")
        
        logging.warning(f"[设备] 摄像头分配: IDS={ids_camera_index}, 旁轴={side_camera_index}")
        
        # 保存旁轴相机索引，供 IDS 初始化时跳过
        self._side_camera_index = side_camera_index
        
        # 初始化 IDS 相机（传入指定的首选索引）
        if self.config.enable_ids and ids_camera_index is not None:
            try:
                logging.warning(f"[设备] 正在初始化IDS相机 (首选索引 {ids_camera_index})")
                results["ids"] = self._init_ids_camera(preferred_index=ids_camera_index)
                if results["ids"]:
                    logging.warning(f"[设备] IDS相机初始化成功")
                else:
                    logging.warning("[设备] IDS相机初始化失败")
            except Exception as e:
                logging.error(f"[设备] IDS相机初始化异常: {e}")
        else:
            logging.warning(f"[设备] 跳过IDS相机初始化")
        
        # 初始化旁轴相机（传入指定的索引）
        if self.config.enable_side_camera and side_camera_index is not None:
            try:
                logging.warning(f"[设备] 正在初始化旁轴相机 (索引 {side_camera_index})")
                results["side_camera"] = self._init_side_camera_with_index(side_camera_index)
                if results["side_camera"]:
                    logging.info("[设备] 旁轴相机初始化成功")
            except Exception as e:
                logging.error(f"[设备] 旁轴相机初始化失败: {e}")
        elif self.config.enable_side_camera:
            # 没有指定索引，使用默认扫描逻辑
            try:
                results["side_camera"] = self._init_side_camera()
                if results["side_camera"]:
                    logging.info("[设备] 旁轴相机初始化成功")
            except Exception as e:
                logging.error(f"[设备] 旁轴相机初始化失败: {e}")
        
        # 初始化 Fotric
        if self.config.enable_fotric and FOTRIC_AVAILABLE:
            try:
                results["fotric"] = self._init_fotric()
                if results["fotric"]:
                    logging.info("[设备] Fotric相机初始化成功")
            except Exception as e:
                logging.error(f"[设备] Fotric相机初始化失败: {e}")
        
        # 初始化振动传感器
        if self.config.enable_vibration and VIBRATION_AVAILABLE:
            try:
                results["vibration"] = self._init_vibration()
                if results["vibration"]:
                    logging.info("[设备] 振动传感器初始化成功")
            except Exception as e:
                logging.error(f"[设备] 振动传感器初始化失败: {e}")
        
        # 注意：M114 轮询已废弃，改用 DisplayLayerProgress 插件获取 Z 高度
        # Z offset 通过 OctoPrint API 直接发送 G-code (M851) 设置
        logging.info("[设备] 使用 DisplayLayerProgress 插件获取 Z 高度（M114 已废弃）")
        
        elapsed = time.time() - start_time
        connected = sum(1 for v in results.values() if v)
        logging.info(f"[设备] 初始化完成，耗时 {elapsed:.1f}s，成功 {connected}/5")
        
        # 如果没有设备连接且启用了自动回退，切换到模拟模式
        if connected == 0 and self.config.simulation_auto_fallback and not self._simulation_mode_active:
            logging.warning("[设备] 没有真实设备连接，自动切换到模拟模式")
            self._enable_simulation_mode()
            return {k: True for k in results.keys()}
        
        return results
    
    def disconnect_all_devices(self) -> Dict[str, bool]:
        """断开所有设备连接
        
        Returns:
            Dict[str, bool]: 各设备断开结果
        """
        results = {
            "ids": False,
            "side_camera": False,
            "fotric": False,
            "vibration": False,
            "m114": False
        }
        
        # 先停止采集（如果正在运行）
        if self.state == AcquisitionState.RUNNING:
            self.stop()
        
        # 断开 IDS 相机
        if self._ids_camera:
            try:
                # 停止采集
                if hasattr(self, '_ids_nodemap') and self._ids_nodemap:
                    try:
                        self._ids_nodemap.FindNode("AcquisitionStop").Execute()
                    except:
                        pass
                self._ids_camera.StopAcquisition()
                self._ids_camera = None
                results["ids"] = True
                logging.info("[设备] IDS相机已断开")
            except Exception as e:
                logging.error(f"[设备] IDS相机断开失败: {e}")
        else:
            results["ids"] = True  # 本来就没连接
        
        # 关闭 IDS 设备
        if hasattr(self, '_ids_device') and self._ids_device:
            try:
                self._ids_device.Close()
                self._ids_device = None
            except:
                pass
        
        # 关闭 IDS 库
        if IDS_AVAILABLE:
            try:
                ids_peak.Library.Close()
            except:
                pass
        
        # 断开旁轴相机
        if self._side_camera:
            try:
                if hasattr(self._side_camera, 'close'):
                    self._side_camera.close()
                else:
                    self._side_camera.release()
                self._side_camera = None
                results["side_camera"] = True
                logging.info("[设备] 旁轴相机已断开")
            except Exception as e:
                logging.error(f"[设备] 旁轴相机断开失败: {e}")
        else:
            results["side_camera"] = True
        
        # 断开 Fotric
        if self._fotric_device:
            try:
                self._fotric_device.disconnect()
                self._fotric_device = None
                results["fotric"] = True
                logging.info("[设备] Fotric已断开")
            except Exception as e:
                logging.error(f"[设备] Fotric断开失败: {e}")
        else:
            results["fotric"] = True
        
        # 断开振动传感器
        if self._vibration_device:
            try:
                self._vibration_device.stopLoopRead()
                self._vibration_device.closeDevice()
                self._vibration_device = None
                results["vibration"] = True
                logging.info("[设备] 振动传感器已断开")
            except Exception as e:
                logging.error(f"[设备] 振动传感器断开失败: {e}")
        else:
            results["vibration"] = True
        
        # M114 已废弃，使用 DisplayLayerProgress 插件获取 Z 高度
        results["m114"] = True  # 标记为已处理（实际无操作）
        
        return results
    
    def _init_ids_camera(self, preferred_index: int = None) -> bool:
        """初始化 IDS 相机（或回退到 USB 摄像头）
        
        Args:
            preferred_index: 首选的 USB 摄像头索引（USB 回退时使用）
        """
        # 检查是否已初始化
        if self._ids_camera is not None:
            logging.info("[IDS] 相机已初始化，跳过")
            return True
        
        # 尝试初始化 IDS 工业相机
        if IDS_AVAILABLE:
            try:
                ids_peak.Library.Initialize()
                device_manager = ids_peak.DeviceManager.Instance()
                device_manager.Update()
                
                if not device_manager.Devices().empty():
                    # 使用 Exclusive 模式打开设备以获得完整控制权限
                    device = device_manager.Devices()[0].OpenDevice(ids_peak.DeviceAccessType_Exclusive)
                    logging.info("[IDS] 设备已打开")
                    
                    # 配置相机
                    remote_device_nodemap = device.RemoteDevice().NodeMaps()[0]
                    
                    # 尝试设置曝光时间和增益（非关键参数，失败不影响功能）
                    for param_name, param_value in [("ExposureTime", self.config.ids_exposure_time), 
                                                    ("Gain", self.config.ids_gain)]:
                        try:
                            node = remote_device_nodemap.FindNode(param_name)
                            if node.IsAvailable():
                                current = node.Value()
                                if abs(current - param_value) > 0.1:
                                    node.SetValue(param_value)
                                    logging.info(f"[IDS] {param_name} 设置为 {param_value}")
                        except Exception:
                            # 简化错误信息，只记录 DEBUG 级别
                            logging.debug(f"[IDS] {param_name} 使用默认值")
                    
                    # 获取数据流描述符并打开数据流
                    datastream_descriptor = device.DataStreams()[0]
                    datastream = datastream_descriptor.OpenDataStream()
                    
                    # 分配缓冲区
                    payload_size = remote_device_nodemap.FindNode("PayloadSize").Value()
                    for i in range(10):
                        buffer = datastream.AllocAndAnnounceBuffer(payload_size)
                        datastream.QueueBuffer(buffer)
                    logging.info(f"[IDS] 已分配 10 个缓冲区 (payload_size={payload_size})")
                    
                    # 启动采集
                    datastream.StartAcquisition()
                    remote_device_nodemap.FindNode("AcquisitionStart").Execute()
                    
                    # 保存设备引用（用于后续关闭）
                    self._ids_device = device
                    self._ids_nodemap = remote_device_nodemap
                    # 保存数据流引用（这是关键！）
                    self._ids_camera = datastream
                    
                    # 应用用户自定义配置
                    self._apply_ids_user_config()
                    
                    logging.info("[IDS] 工业相机初始化成功")
                    return True
                else:
                    logging.warning("[IDS] 未找到 IDS 工业相机，将尝试 USB 摄像头")
            except Exception as e:
                logging.warning(f"[IDS] IDS 工业相机初始化失败: {e}，将尝试 USB 摄像头")
        else:
            logging.warning("[IDS] IDS Peak 库不可用，将尝试 USB 摄像头")
        
        # 回退到 USB 摄像头（使用 OpenCV）
        if preferred_index is not None:
            logging.warning(f"[IDS] 使用指定索引 {preferred_index} 进行 USB 回退...")
            return self._init_ids_camera_with_index(preferred_index)
        else:
            logging.warning("[IDS] 调用 USB 回退（自动扫描）...")
            return self._init_ids_camera_usb_fallback()
    
    def _init_ids_camera_usb_fallback(self) -> bool:
        """IDS 相机初始化失败时，使用 USB 摄像头作为替代"""
        try:
            logging.info("[IDS-USB] 正在尝试使用 USB 摄像头作为 IDS 替代...")
            
            # 获取旁轴相机使用的索引（如果有）
            side_index = getattr(self, '_side_camera_index', None)
            if side_index is not None:
                logging.info(f"[IDS-USB] 旁轴相机使用索引 {side_index}，IDS 将跳过")
            
            # 首先扫描所有可用摄像头
            available_cameras = []
            for i in range(10):
                if side_index is not None and i == side_index:
                    continue
                try:
                    # 先尝试 DirectShow，如果失败则尝试默认后端
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        cap.release()
                        cap = cv2.VideoCapture(i)
                    
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None and frame.size > 0:
                            height, width = frame.shape[:2]
                            available_cameras.append((i, width, height))
                        cap.release()
                except:
                    pass
            
            logging.info(f"[IDS-USB] 发现可用摄像头: {available_cameras}")
            
            # 尝试每个可用摄像头
            for camera_index, width, height in available_cameras:
                try:
                    logging.info(f"[IDS-USB] 尝试索引 {camera_index} ({width}x{height})...")
                    
                    # 先尝试 DirectShow
                    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        cap.release()
                        cap = cv2.VideoCapture(camera_index)
                    
                    if cap.isOpened():
                        # 设置分辨率（使用摄像头原生分辨率）
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                        cap.set(cv2.CAP_PROP_FPS, 30)
                        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        
                        # 测试读取多帧
                        time.sleep(0.1)
                        for frame_idx in range(5):
                            ret, frame = cap.read()
                            if ret and frame is not None and frame.size > 0:
                                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                logging.info(f"[IDS-USB] USB 摄像头初始化成功 (索引 {camera_index}): {actual_width}x{actual_height}")
                                
                                # 保存为 IDS 相机引用
                                self._ids_camera_usb = cap
                                self._ids_camera = self._create_usb_camera_wrapper(cap)
                                self._ids_usb_fallback = True
                                return True
                            time.sleep(0.05)
                        
                        cap.release()
                        
                except Exception as e:
                    logging.debug(f"[IDS-USB] 索引 {camera_index} 失败: {e}")
                    continue
            
            logging.warning("[IDS-USB] 未找到可用的 USB 摄像头")
            return False
            
        except Exception as e:
            logging.error(f"[IDS-USB] USB 摄像头初始化失败: {e}")
            return False
    
    def _create_usb_camera_wrapper(self, cap):
        """为 USB 摄像头创建一个包装器，使其接口与 IDS 数据流兼容"""
        class USBCameraWrapper:
            def __init__(self, video_capture):
                self._cap = video_capture
                self._frame = None
                self._lock = threading.Lock()
                self._running = True
                self._thread = threading.Thread(target=self._update, daemon=True)
                self._thread.start()
            
            def _update(self):
                """后台线程持续读取帧"""
                while self._running:
                    ret, frame = self._cap.read()
                    if ret:
                        with self._lock:
                            self._frame = frame
                    time.sleep(0.033)  # ~30fps
            
            def WaitForFinishedBuffer(self, timeout_ms=1000):
                """模拟 IDS 接口：获取最新帧"""
                start = time.time()
                while (time.time() - start) * 1000 < timeout_ms:
                    with self._lock:
                        if self._frame is not None:
                            return self._frame
                    time.sleep(0.001)
                return None
            
            def StopAcquisition(self):
                """停止采集"""
                self._running = False
                if self._thread:
                    self._thread.join(timeout=1)
            
            def get_numpy(self):
                """模拟 IDS 接口：返回 numpy 数组"""
                with self._lock:
                    return self._frame.copy() if self._frame is not None else None
        
        return USBCameraWrapper(cap)
    
    def _apply_ids_user_config(self):
        """应用 IDS 相机用户配置（焦距112，关闭自动对焦）
        
        参考 VB02_ids.py 中的正确用法：
        - FocusAuto 节点：枚举类型，通过 Entries() 获取选项后设置
        - FocusStepper 节点：数值类型，直接 SetValue(112)
        """
        if not self._ids_nodemap:
            return
        
        nodemap = self._ids_nodemap
        focus_val = 112  # 你的最佳焦距值
        
        try:
            # 1. 关闭自动对焦 (FocusAuto 是枚举节点)
            autofocus_off = False
            try:
                auto_focus_node = nodemap.FindNode("FocusAuto")
                if auto_focus_node and auto_focus_node.IsAvailable():
                    # 获取所有枚举选项
                    auto_focus_entries = auto_focus_node.Entries()
                    for entry in auto_focus_entries:
                        if entry.SymbolicValue() == "Off":
                            auto_focus_node.SetCurrentEntry(entry)
                            logging.info("[IDS] 自动对焦: 已关闭")
                            autofocus_off = True
                            break
            except Exception as e:
                logging.debug(f"[IDS] 关闭自动对焦失败: {e}")
            
            # 2. 设置固定焦距 (FocusStepper 节点)
            focus_set = False
            try:
                focus_stepper = nodemap.FindNode("FocusStepper")
                if focus_stepper and focus_stepper.IsAvailable():
                    focus_stepper.SetValue(float(focus_val))
                    logging.info(f"[IDS] 焦距: 设置为 {focus_val}")
                    focus_set = True
            except Exception as e:
                logging.debug(f"[IDS] 设置焦距失败: {e}")
            
            # 3. 记录结果
            if autofocus_off and focus_set:
                logging.info("[IDS] 相机配置应用成功（焦距=112，自动对焦=关闭）")
            elif not autofocus_off:
                logging.warning("[IDS] 自动对焦关闭失败")
            elif not focus_set:
                logging.warning("[IDS] 焦距设置失败")
            
            # 4. 加载配置文件中的其他参数
            self._load_ids_config_file()
            
        except Exception as e:
            logging.warning(f"[IDS] 应用用户配置失败: {e}")
    
    def _load_ids_config_file(self):
        """从ini文件加载额外配置"""
        import configparser
        
        ini_path = r"D:\College\Python_project\4Project\SmartAM_System\backend\utils\my_ids_config.ini"
        
        if not os.path.exists(ini_path):
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(ini_path, encoding='utf-8-sig')
            
            # 读取并应用伽马值
            try:
                gamma = float(config.get('Parameters', 'Gamma', fallback=1.0))
                if gamma != 1.0:
                    self._ids_nodemap.FindNode("Gamma").SetValue(gamma)
                    logging.info(f"[IDS] 伽马: 设置为 {gamma}")
            except:
                pass
            
            logging.info("[IDS] 已从配置文件加载额外参数")
            
        except Exception as e:
            logging.debug(f"[IDS] 读取配置文件失败: {e}")
    
    def _scan_available_cameras(self) -> list:
        """扫描所有可用的 USB 摄像头"""
        available_cameras = []
        for i in range(10):
            try:
                # 先尝试 DirectShow 后端
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap.release()
                    # 回退到默认后端
                    cap = cv2.VideoCapture(i)
                
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        height, width = frame.shape[:2]
                        available_cameras.append((i, width, height))
                        logging.info(f"[摄像头扫描] 索引 {i}: {width}x{height}")
                    cap.release()
            except Exception as e:
                logging.debug(f"[摄像头扫描] 索引 {i} 不可用: {e}")
        
        return available_cameras
    
    def _init_ids_camera_with_index(self, camera_index: int) -> bool:
        """使用指定索引初始化 IDS 相机（USB 回退模式）"""
        try:
            logging.warning(f"[IDS-USB] 正在使用索引 {camera_index} 初始化...")
            
            # 尝试 DirectShow 后端
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(camera_index)
            
            if not cap.isOpened():
                logging.error(f"[IDS-USB] 无法打开摄像头索引 {camera_index}")
                return False
            
            # 设置分辨率
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # 预热并测试读取
            time.sleep(0.2)
            for _ in range(5):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    logging.warning(f"[IDS-USB] 初始化成功 (索引 {camera_index}): {actual_width}x{actual_height}")
                    
                    # 保存引用
                    self._ids_camera_usb = cap
                    self._ids_camera = self._create_usb_camera_wrapper(cap)
                    self._ids_usb_fallback = True
                    return True
                time.sleep(0.05)
            
            cap.release()
            return False
            
        except Exception as e:
            logging.error(f"[IDS-USB] 初始化失败: {e}")
            return False
    
    def _init_side_camera_with_index(self, camera_index: int) -> bool:
        """使用指定索引初始化旁轴相机"""
        try:
            logging.warning(f"[旁轴相机] 正在使用索引 {camera_index} 初始化...")
            
            # 尝试 DirectShow 后端
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(camera_index)
            
            if not cap.isOpened():
                logging.error(f"[旁轴相机] 无法打开摄像头索引 {camera_index}")
                return False
            
            # 设置参数
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.side_camera_resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.side_camera_resolution[1])
            
            # 测试读取
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                height, width = frame.shape[:2]
                logging.warning(f"[旁轴相机] 初始化成功 (索引 {camera_index}): {width}x{height}")
                self._side_camera = cap
                self._side_camera_index = camera_index
                return True
            
            cap.release()
            return False
            
        except Exception as e:
            logging.error(f"[旁轴相机] 初始化失败: {e}")
            return False
    
    def _init_side_camera(self) -> bool:
        """初始化旁轴相机（自动查找USB摄像头，跳过IDS使用的设备）"""
        logging.info("[旁轴相机] 开始扫描USB摄像头...")
        
        # 首先扫描所有可用摄像头
        available_cameras = []
        for i in range(10):
            try:
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        height, width = frame.shape[:2]
                        available_cameras.append((i, width, height))
                    cap.release()
                else:
                    cap.release()
            except:
                pass
        
        logging.info(f"[旁轴相机] 发现 {len(available_cameras)} 个摄像头: {available_cameras}")
        
        # 旁轴相机优先使用索引 1（如果可用），否则使用其他非0索引
        preferred_indices = [1, 2, 3, 4]
        for idx in preferred_indices:
            for cam_idx, width, height in available_cameras:
                if cam_idx == idx:
                    try:
                        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                        if cap.isOpened():
                            logging.info(f"[旁轴相机] 使用设备 {idx}: {width}x{height}")
                            self._side_camera = cap
                            self._side_camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.side_camera_resolution[0])
                            self._side_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.side_camera_resolution[1])
                            # 记录旁轴使用的索引，以便IDS跳过
                            self._side_camera_index = idx
                            return True
                    except Exception as e:
                        logging.warning(f"[旁轴相机] 设备 {idx} 打开失败: {e}")
                        continue
        
        logging.error("[旁轴相机] 未找到可用的USB摄像头")
        return False
    
    def _init_fotric(self) -> bool:
        """初始化 Fotric 相机"""
        if not FOTRIC_AVAILABLE:
            logging.warning("[Fotric] 驱动不可用，跳过初始化")
            return False
        
        logging.info(f"[Fotric] 正在连接 {self.config.fotric_ip}:{self.config.fotric_port}...")
        
        try:
            # FotricEnhancedDevice 在构造函数中自动连接
            self._fotric_device = FotricEnhancedDevice(
                ip=self.config.fotric_ip,
                port=self.config.fotric_port,
                username="admin",
                password="admin",
                simulation_mode=False,
                high_resolution=True,
                update_rate=2.0
            )
            
            if self._fotric_device.is_connected:
                logging.info(f"[Fotric] 连接成功: {self._fotric_device.width}x{self._fotric_device.height}")
            else:
                logging.warning(f"[Fotric] 连接失败，请检查:")
                logging.warning(f"  1. Fotric 相机是否开机并连接到网络")
                logging.warning(f"  2. IP 地址 {self.config.fotric_ip} 是否正确")
                logging.warning(f"  3. 电脑和相机是否在同一个网段")
            
            return self._fotric_device.is_connected
        except Exception as e:
            logging.error(f"[Fotric] 初始化异常: {e}")
            return False
    
    def _init_vibration(self) -> bool:
        """初始化振动传感器"""
        if not VIBRATION_AVAILABLE:
            return False
        
        self._vibration_device = VibrationDevice(
            "振动传感器",
            self.config.vibration_port,
            self.config.vibration_baudrate,
            0x50
        )
        self._vibration_device.openDevice()
        self._vibration_device.startLoopRead()
        return True
    
    def start_acquisition(self) -> bool:
        """开始采集"""
        with self._state_lock:
            if self.state == AcquisitionState.RUNNING:
                logging.warning("采集已在进行中")
                return False
            
            # 初始化设备
            device_status = self.initialize_devices()
            if not any(device_status.values()):
                logging.error("没有可用的采集设备")
                return False
            
            # 创建任务目录
            self._create_task_directory()
            
            # 初始化CSV文件
            self._init_csv()
            
            # 重置计数
            self.frame_count = 0
            self.start_time = time.time()
            
            # 启动保存线程
            self._stop_event.clear()
            self._pause_event.clear()
            self._save_thread = threading.Thread(target=self._save_worker, daemon=True)
            self._save_thread.start()
            
            # 初始化参数管理器
            if self._param_manager and PARAM_MANAGER_AVAILABLE:
                mode = ParameterMode.FIXED
                if self.config.param_mode == "random":
                    mode = ParameterMode.RANDOM
                elif self.config.param_mode == "tower":
                    mode = ParameterMode.STANDARD_TOWER
                
                self._param_manager.set_mode(
                    mode,
                    random_interval_sec=self.config.random_interval_sec,
                    tower_id=self.config.current_tower
                )
                # 更新同步缓冲配置
                self._param_manager.sync_config.stability_z_diff_mm = self.config.stability_z_diff_mm
                self._param_manager.sync_config.silent_height_mm = self.config.silent_height_mm
                
                # 设置初始参数（标准塔模式下Z<5mm使用默认参数，不发送命令）
                from core.fdm.parameter_manager import ParameterSet, STANDARD_TOWERS
                
                if mode == ParameterMode.STANDARD_TOWER:
                    tower = STANDARD_TOWERS[self.config.current_tower - 1]
                    logging.info(f"[采集] 标准塔模式 Tower {self.config.current_tower} 已选择: "
                               f"T={tower.hotend_temp}°C, Z偏移={tower.z_offset_fixed}mm "
                               f"(将在Z>=5mm时应用)")
                    
                    # Z<5mm时使用默认参数（200°C，标准流量速度）
                    initial_params = ParameterSet(
                        flow_rate=100,
                        feed_rate=100,
                        z_offset=0.0,
                        target_hotend=200
                    )
                    # 不在这里应用塔参数，让_update_params_from_manager在Z>=5时处理
                else:
                    initial_params = ParameterSet(
                        flow_rate=self.config.flow_rate,
                        feed_rate=self.config.feed_rate,
                        z_offset=self.config.z_offset,
                        target_hotend=self.config.target_hotend
                    )
                
                # 只设置current_params，不触发回调（避免在Z=0时发送命令到打印机）
                self._param_manager.current_params = initial_params
                
                logging.info(f"[采集] 参数管理器初始化完成，模式: {mode.value}, "
                           f"Z<5mm使用默认参数: F={initial_params.feed_rate}, E={initial_params.flow_rate}, "
                           f"T={initial_params.target_hotend}")
            
            # 启动采集线程
            self._acquisition_thread = threading.Thread(target=self._acquisition_loop, daemon=True)
            self._acquisition_thread.start()
            
            self._set_state(AcquisitionState.RUNNING)
            logging.info(f"[采集] 开始采集，保存路径: {self.current_task_dir}")
            return True
    
    def pause_acquisition(self) -> bool:
        """暂停采集"""
        with self._state_lock:
            if self.state != AcquisitionState.RUNNING:
                return False
            
            self._pause_event.set()
            self._set_state(AcquisitionState.PAUSED)
            logging.info("[采集] 已暂停")
            return True
    
    def resume_acquisition(self) -> bool:
        """恢复采集"""
        with self._state_lock:
            if self.state != AcquisitionState.PAUSED:
                return False
            
            self._pause_event.clear()
            self._set_state(AcquisitionState.RUNNING)
            logging.info("[采集] 已恢复")
            return True
    
    def stop_acquisition(self) -> bool:
        """停止采集"""
        with self._state_lock:
            if self.state in [AcquisitionState.IDLE, AcquisitionState.STOPPING]:
                return False
            
            self._set_state(AcquisitionState.STOPPING)
            self._stop_event.set()
            self._pause_event.clear()
            
            logging.info("[采集] 正在停止...")
            
            # 注意：M114 已废弃，使用 DisplayLayerProgress 插件获取 Z 高度
            
            # 等待采集线程结束
            if self._acquisition_thread and self._acquisition_thread.is_alive():
                self._acquisition_thread.join(timeout=5.0)
            
            # 等待保存线程结束
            if self._save_thread and self._save_thread.is_alive():
                self._save_queue.put(None)  # 发送结束信号
                self._save_thread.join(timeout=5.0)
            
            # 关闭设备
            self._close_devices()
            
            # 关闭CSV文件
            if self._csv_file:
                self._csv_file.close()
                self._csv_file = None
            
            self._set_state(AcquisitionState.IDLE)
            logging.info("[采集] 已停止")
            return True
    
    # ========== 别名方法（兼容 main.py）==========
    
    def start(self) -> bool:
        """开始采集（start_acquisition 的别名）"""
        return self.start_acquisition()
    
    def stop(self) -> bool:
        """停止采集（stop_acquisition 的别名）"""
        return self.stop_acquisition()
    
    def register_callback(self, callback: Callable):
        """注册数据回调函数（供 WebSocket 使用）"""
        if not hasattr(self, '_callbacks'):
            self._callbacks = []
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """注销数据回调函数"""
        if hasattr(self, '_callbacks') and callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self, packet):
        """通知所有回调函数有新数据"""
        # 保存最新数据
        self._latest_data = packet
        
        if hasattr(self, '_callbacks'):
            for callback in self._callbacks:
                try:
                    callback(packet)
                except Exception as e:
                    logging.error(f"[回调] 执行回调失败: {e}")
    
    def _acquisition_loop(self):
        """采集主循环"""
        last_param_update_z = 0.0
        
        while not self._stop_event.is_set():
            try:
                # 检查暂停
                if self._pause_event.is_set():
                    time.sleep(0.1)
                    continue
                
                loop_start = time.time()
                
                # 再次检查停止标志（避免在调用前被停止）
                if self._stop_event.is_set():
                    break
                
                # 获取当前位置
                position = self._get_printer_position()
                current_z = position.get("Z", 0.0)
                
                # 更新参数 (根据参数管理器模式)
                if self._param_manager and PARAM_MANAGER_AVAILABLE:
                    self._update_params_from_manager(current_z)
                
                # 检查是否应该采集 (时空同步缓冲)
                should_capture = True
                skip_reason = ""
                
                if self._param_manager and PARAM_MANAGER_AVAILABLE:
                    should_capture, skip_reason = self._param_manager.should_capture(current_z)
                
                if should_capture:
                    # 采集一帧
                    frame_data = self._capture_frame()
                    
                    if frame_data:
                        # 添加到保存队列
                        try:
                            self._save_queue.put(frame_data, block=False)
                        except queue.Full:
                            logging.warning("保存队列已满，丢弃一帧")
                        
                        # 回调
                        if self.on_frame_captured:
                            self.on_frame_captured(frame_data)
                else:
                    # 记录跳过原因
                    if self.frame_count % 50 == 0:  # 每50帧记录一次，避免日志过多
                        logging.debug(f"[采集] 跳过采集: {skip_reason}")
                
                # 计算下次采集时间
                elapsed = time.time() - loop_start
                sleep_time = self.config.capture_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logging.error(f"采集循环错误: {e}")
                if self.on_error:
                    self.on_error(str(e))
                time.sleep(1)
    
    def _capture_frame(self) -> Optional[FrameData]:
        """采集一帧数据"""
        with self._frame_lock:
            self.frame_count += 1
        
        frame_number = self.frame_count
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-%f")[:-2]
        
        # 获取打印机状态
        printer_status = self._get_printer_status()
        
        # 计算参数分类
        flow_rate_class = self._get_param_class(
            self.config.flow_rate, 
            PARAM_THRESHOLDS["flow_rate"]
        )
        feed_rate_class = self._get_param_class(
            self.config.feed_rate,
            PARAM_THRESHOLDS["feed_rate"]
        )
        z_offset_class = self._get_param_class(
            self.config.z_offset,
            PARAM_THRESHOLDS["z_offset"]
        )
        hotend_class = self._get_param_class(
            printer_status.get("hotend", 200),
            PARAM_THRESHOLDS["hotend"]
        )
        
        # 获取坐标
        position = self._get_printer_position()
        
        frame_data = FrameData(
            frame_number=frame_number,
            timestamp=timestamp,
            current_x=position.get("X", 0.0),
            current_y=position.get("Y", 0.0),
            current_z=position.get("Z", 0.0),
            flow_rate=self.config.flow_rate,
            feed_rate=self.config.feed_rate,
            z_offset=self.config.z_offset,
            target_hotend=self.config.target_hotend,
            hot_end=printer_status.get("hotend", 0.0),
            bed=printer_status.get("bed", 0.0),
            flow_rate_class=flow_rate_class,
            feed_rate_class=feed_rate_class,
            z_offset_class=z_offset_class,
            hotend_class=hotend_class
        )
        
        # 采集 IDS 图像
        if self._ids_camera:
            try:
                frame_data.ids_image = self._get_ids_frame()
                if frame_data.ids_image is not None and frame_number % 10 == 1:
                    logging.debug(f"[采集] IDS图像已采集 (shape={frame_data.ids_image.shape})")
            except Exception as e:
                logging.error(f"IDS采集失败: {e}")
        elif self._simulation_mode_active and self._simulation_generator:
            # 模拟模式：生成模拟图像
            frame_data.ids_image = self._simulation_generator.generate_ids_frame()
        else:
            if frame_number % 10 == 1:
                logging.debug(f"[采集] IDS相机未初始化，跳过采集")
        
        # 采集旁轴相机图像
        if self._side_camera:
            try:
                # 检查是 SideCamera 对象还是 cv2.VideoCapture 对象
                if hasattr(self._side_camera, 'get_frame'):
                    # SideCamera 对象
                    frame = self._side_camera.get_frame()
                    if frame is not None:
                        frame_data.side_image = frame
                else:
                    # cv2.VideoCapture 对象
                    ret, frame = self._side_camera.read()
                    if ret and frame is not None:
                        frame_data.side_image = frame
            except Exception as e:
                logging.error(f"旁轴相机采集失败: {e}")
        elif self._simulation_mode_active and self._simulation_generator:
            # 模拟模式：生成模拟图像
            frame_data.side_image = self._simulation_generator.generate_side_frame()
        
        # 采集 Fotric 数据
        if self._fotric_device and self._fotric_device.is_connected:
            try:
                thermal_data = self._fotric_device.get_thermal_data()
                if thermal_data is not None:
                    frame_data.fotric_data = thermal_data
                    frame_data.fotric_image = self._thermal_to_image(thermal_data)
                    frame_data.fotric_temp_min = float(np.min(thermal_data))
                    frame_data.fotric_temp_max = float(np.max(thermal_data))
                    frame_data.fotric_temp_avg = float(np.mean(thermal_data))
            except Exception as e:
                logging.error(f"Fotric采集失败: {e}")
        elif self._simulation_mode_active and self._simulation_generator:
            # 模拟模式：生成模拟热像数据
            thermal_data = self._simulation_generator.generate_thermal_data()
            frame_data.fotric_data = thermal_data
            frame_data.fotric_image = self._thermal_to_image(thermal_data)
            frame_data.fotric_temp_min = float(np.min(thermal_data))
            frame_data.fotric_temp_max = float(np.max(thermal_data))
            frame_data.fotric_temp_avg = float(np.mean(thermal_data))
        
        # 运行模型推理（如果有图像数据）
        if (frame_data.ids_image is not None or 
            frame_data.side_image is not None or 
            frame_data.fotric_image is not None):
            try:
                inference_result = self._run_inference(
                    ids_frame=frame_data.ids_image,
                    side_frame=frame_data.side_image,
                    fotric_frame=frame_data.fotric_image,
                    thermal_data=frame_data.fotric_data
                )
                if inference_result:
                    # 更新 frame_data 的预测类别
                    frame_data.flow_rate_class = inference_result.flow_rate_class
                    frame_data.feed_rate_class = inference_result.feed_rate_class
                    frame_data.z_offset_class = inference_result.z_offset_class
                    frame_data.hotend_class = inference_result.hot_end_class
                    # 保存推理结果供后续使用
                    self._latest_prediction = inference_result
            except Exception as e:
                logging.error(f"[采集] 推理失败: {e}")
        
        # 每10帧记录一次，减少日志
        if frame_number % 10 == 1:
            logging.info(f"[采集] 第{frame_number}帧完成")
        
        # 通知回调（供 WebSocket 使用）
        self._notify_callbacks(frame_data)
        
        return frame_data
    
    def _get_ids_frame(self) -> Optional[np.ndarray]:
        """获取 IDS 相机帧（支持 USB 摄像头回退）"""
        if not self._ids_camera:
            return None
        
        # 检查是否是 USB 摄像头回退模式（通过检查是否有 _ids_camera_usb 属性）
        if hasattr(self, '_ids_camera_usb') and self._ids_camera_usb is not None:
            # USB 摄像头模式
            try:
                frame = self._ids_camera.WaitForFinishedBuffer(1000)
                if frame is not None:
                    # USB 摄像头返回的是 BGR 格式（OpenCV 默认），不需要转换
                    # 但某些摄像头可能返回 RGB，所以如果颜色看起来不对，需要检查
                    
                    # 旋转180度（相机倒装）
                    frame = cv2.flip(frame, -1)
                    
                    # 应用图像处理
                    frame = self._apply_host_image_processing(frame)
                    return frame
                return None
            except Exception as e:
                logging.error(f"[IDS-USB] 获取帧错误: {e}")
                return None
        
        # IDS 工业相机模式（需要 IDS_AVAILABLE）
        if not IDS_AVAILABLE:
            return None
        
        try:
            # self._ids_camera 现在直接是数据流对象
            datastream = self._ids_camera
            buffer = datastream.WaitForFinishedBuffer(5000)
            
            ipl_image = ids_peak_ipl_extension.BufferToImage(buffer)
            
            # 获取图像尺寸和像素格式
            width = ipl_image.Width()
            height = ipl_image.Height()
            pixel_format = ipl_image.PixelFormat()
            
            # 获取 numpy 数组
            image_np = ipl_image.get_numpy()
            
            # 根据像素格式处理（pixel_format 是字符串）
            if pixel_format == "RGB8":
                image_np = image_np.reshape((height, width, 3))
                image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            elif pixel_format == "Mono8":
                image_np = image_np.reshape((height, width))
                image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
            elif pixel_format == "BGR8":
                image_np = image_np.reshape((height, width, 3))
                # BGR8 不需要转换
            else:
                # 对于其他格式，尝试自动处理
                image_np = image_np.reshape((height, width, -1))
                if image_np.shape[2] == 4:  # BGRA/BGRa8
                    image_np = cv2.cvtColor(image_np, cv2.COLOR_BGRA2BGR)
                    logging.debug(f"[IDS] 转换 BGRA -> BGR")
                elif image_np.shape[2] == 3:  # RGB/BGR
                    # 假设是 RGB，转换为 BGR
                    image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
                    logging.debug(f"[IDS] 转换 RGB -> BGR")
                elif image_np.shape[2] == 1:  # 单通道
                    image_np = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
                    logging.debug(f"[IDS] 转换 Gray -> BGR")
            
            # 翻转180度
            image_np = cv2.flip(image_np, -1)
            
            # 应用主机端图像处理（边缘增强、伽马校正）
            image_np = self._apply_host_image_processing(image_np)
            
            datastream.QueueBuffer(buffer)
            return image_np
        except Exception as e:
            logging.error(f"获取IDS帧错误: {e}")
            return None
    
    def _apply_host_image_processing(self, image: np.ndarray) -> np.ndarray:
        """
        应用主机端图像处理（可配置版本）
        根据 self.config 中的图像处理参数进行调整
        """
        if image is None or image.size == 0:
            return image
        
        try:
            cfg = self.config
            
            # 1. 自适应对比度增强（CLAHE）
            if cfg.ids_clahe_enabled:
                lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l = clahe.apply(l)
                lab = cv2.merge((l, a, b))
                image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            # 2. 伽马校正
            if cfg.ids_gamma != 1.0:
                gamma = max(0.5, min(cfg.ids_gamma, 1.5))  # 限制范围 0.5-1.5
                inv_gamma = 1.0 / gamma
                table = np.array([(i / 255.0) ** inv_gamma * 255 for i in np.arange(0, 256)]).astype("uint8")
                image = cv2.LUT(image, table)
            
            # 3. 锐化增强
            if cfg.ids_sharpen_enabled:
                if cfg.ids_sharpen_method == "unsharp":
                    # Unsharp Mask - 自然清晰
                    gaussian = cv2.GaussianBlur(image, (0, 0), 2.0)
                    image = cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
                elif cfg.ids_sharpen_method == "laplacian":
                    # 拉普拉斯锐化 - 边缘明显
                    kernel = np.array([[-1, -1, -1],
                                      [-1, 9, -1],
                                      [-1, -1, -1]])
                    sharpened = cv2.filter2D(image, -1, kernel)
                    image = cv2.addWeighted(image, 0.7, sharpened, 0.3, 0)
                elif cfg.ids_sharpen_method == "strong":
                    # 强力锐化 - 高对比度
                    kernel = np.array([[-1, -1, -1],
                                      [-1, 11, -1],
                                      [-1, -1, -1]])
                    sharpened = cv2.filter2D(image, -1, kernel)
                    image = cv2.addWeighted(image, 0.5, sharpened, 0.5, 0)
            
            # 4. 降噪（可选，会稍微模糊）
            if cfg.ids_denoise_enabled:
                image = cv2.fastNlMeansDenoisingColored(image, None, 5, 5, 7, 21)
            
        except Exception as e:
            logging.debug(f"[IDS] 图像后处理失败: {e}")
        
        return image
    
    def _thermal_to_image(self, thermal_data: np.ndarray) -> np.ndarray:
        """将热像数据转换为可视化图像 (伪彩色)"""
        temp_min = np.min(thermal_data)
        temp_max = np.max(thermal_data)
        
        if temp_max > temp_min:
            normalized = ((thermal_data - temp_min) / (temp_max - temp_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(thermal_data, dtype=np.uint8)
        
        colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
        return colored
    
    def _is_printer_ready(self) -> bool:
        """
        检查打印机是否就绪（不在加热/调零等忙碌状态）
        根据实际 API 返回：printing=true 表示正在打印，ready=false 表示忙碌
        """
        try:
            url = f"{self.config.octoprint_url}/api/printer"
            headers = {"X-Api-Key": self.config.octoprint_api_key}
            response = requests.get(url, headers=headers, timeout=2)
            if response.status_code == 200:
                data = response.json()
                state_text = data.get("state", {}).get("text", "").lower()
                flags = data.get("state", {}).get("flags", {})
                
                # 如果正在打印，可以发送 G-code 命令
                if flags.get("printing", False):
                    return True
                
                # 如果处于操作状态且没有忙碌标志
                if flags.get("operational", False):
                    # 检查状态文本是否包含忙碌关键词
                    busy_keywords = ["busy", "processing", "heating", "?", "offline"]
                    if any(x in state_text for x in busy_keywords):
                        logging.debug(f"[位置] 打印机状态忙碌: {state_text}")
                        return False
                    return True
                
                # 其他情况（出错、关闭等）
                logging.debug(f"[位置] 打印机未就绪: {state_text}")
                return False
        except Exception as e:
            logging.debug(f"[位置] 检查打印机状态失败: {e}")
        
        # 默认返回 True，避免阻塞
        return True
    
    def _get_printer_position(self) -> Dict:
        """
        获取打印机位置
        使用 DisplayLayerProgress 插件获取当前 Z 高度（无需轮询 M114）
        
        DisplayLayerProgress 插件提供的信息：
        - currentHeight: 当前 Z 高度（来自 GCode 分析）
        - totalHeight: 总高度
        - currentLayer: 当前层数
        - totalLayer: 总层数
        
        模拟模式：返回模拟位置数据
        """
        # 模拟模式：直接返回模拟位置
        if self._simulation_mode_active and self._simulation_generator:
            sim_pos = self._simulation_generator.generate_printer_position()
            self._current_position.update(sim_pos)
            return self._current_position
        
        # OctoPrint 模拟模式
        if self._octoprint_simulation_active and self._octoprint_simulator:
            status = self._octoprint_simulator.get_printer_status()
            pos = status.get("position", {})
            self._current_position.update({
                "X": pos.get("x", 0),
                "Y": pos.get("y", 0),
                "Z": pos.get("z", 0),
                "E": pos.get("e", 0)
            })
            return self._current_position
        
        # 如果正在停止，直接返回缓存位置
        if hasattr(self, '_stop_event') and self._stop_event.is_set():
            return self._current_position
        
        # 初始化时间跟踪（首次调用）
        if not hasattr(self, '_last_dlp_time'):
            self._last_dlp_time = 0
            self._dlp_backoff_until = 0
        
        current_time = time.time()
        
        # 检查是否在退避期（之前请求失败）
        if current_time < self._dlp_backoff_until:
            logging.debug(f"[位置] DLP退避中，剩余{self._dlp_backoff_until - current_time:.1f}秒")
            return self._current_position
        
        # 限制请求频率（每2秒最多一次）
        if current_time - self._last_dlp_time < 2.0:
            return self._current_position
        
        # 从 DisplayLayerProgress 插件获取 Z 高度
        try:
            self._last_dlp_time = current_time
            z_height = self._get_z_from_display_layer_progress()
            
            if z_height is not None and z_height >= 0:
                # 只更新 Z，X/Y/E 保持缓存值或设为0
                self._current_position.update({
                    "Z": z_height
                })
                logging.debug(f"[位置] DLP更新: Z={z_height:.2f}mm")
            else:
                # 获取失败，退避5秒
                logging.debug(f"[位置] DLP无响应，退避5秒")
                self._dlp_backoff_until = current_time + 5.0
                
        except Exception as e:
            logging.debug(f"[位置] DLP异常: {e}，退避5秒")
            self._dlp_backoff_until = current_time + 5.0
        
        # 返回缓存的位置
        return self._current_position
    
    def _get_z_from_display_layer_progress(self) -> Optional[float]:
        """
        从 DisplayLayerProgress 插件获取当前 Z 高度
        
        插件 API:
        - GET /plugin/DisplayLayerProgress/values
        返回: {
            "layer": {"current": "12", "total": "256"},
            "height": {"current": "2.40", "total": "50.00"}
        }
        
        或者在 /api/printer 的响应中也有相关信息
        """
        try:
            import requests
            
            api_key = self.config.octoprint_api_key
            if not api_key or len(api_key) < 20:
                # 尝试从环境变量获取
                try:
                    import os
                    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
                    if os.path.exists(env_path):
                        with open(env_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith('OCTOPRINT_API_KEY='):
                                    api_key = line.split('=', 1)[1].strip()
                                    break
                except:
                    pass
            
            headers = {"X-Api-Key": api_key}
            
            # 首先尝试 DisplayLayerProgress 插件的专用端点
            try:
                url = f"{self.config.octoprint_url}/plugin/DisplayLayerProgress/values"
                response = requests.get(url, headers=headers, timeout=3)
                
                if response.status_code == 200:
                    data = response.json()
                    height_data = data.get("height", {})
                    current_height = height_data.get("current")
                    
                    if current_height:
                        try:
                            z = float(current_height)
                            logging.debug(f"[DLP] 从插件获取 Z={z:.2f}mm")
                            return z
                        except (ValueError, TypeError):
                            pass
            except requests.exceptions.RequestException:
                pass  # 插件可能未安装，尝试备用方法
            
            # 备用：从 /api/printer 获取（某些版本的 OctoPrint 或插件会在这里提供）
            try:
                url = f"{self.config.octoprint_url}/api/printer"
                response = requests.get(url, headers=headers, timeout=3)
                
                if response.status_code == 200:
                    data = response.json()
                    # 检查是否有 DisplayLayerProgress 提供的数据
                    if "displaylayerprogress" in data:
                        dlp_data = data["displaylayerprogress"]
                        current_height = dlp_data.get("current_height") or dlp_data.get("height", {}).get("current")
                        if current_height:
                            try:
                                z = float(current_height)
                                logging.debug(f"[DLP] 从 /api/printer 获取 Z={z:.2f}mm")
                                return z
                            except (ValueError, TypeError):
                                pass
            except requests.exceptions.RequestException:
                pass
            
            # 如果都失败了，尝试从 GCode 分析估算（基于打印进度）
            try:
                url = f"{self.config.octoprint_url}/api/job"
                response = requests.get(url, headers=headers, timeout=3)
                
                if response.status_code == 200:
                    data = response.json()
                    progress_data = data.get("progress", {})
                    completion = progress_data.get("completion", 0)
                    
                    # 如果有文件名，尝试从 GCode 估算总高度
                    job_data = data.get("job", {})
                    file_data = job_data.get("file", {})
                    
                    # 简化处理：假设最大高度为 100mm（需要根据实际情况调整）
                    # 或者从之前成功的 DLP 调用中获取总高度
                    estimated_z = (completion / 100.0) * 100.0  # 默认估算
                    logging.debug(f"[DLP] 从进度估算 Z={estimated_z:.2f}mm (完成度 {completion:.1f}%)")
                    return estimated_z
            except requests.exceptions.RequestException:
                pass
            
            logging.warning("[DLP] 无法从任何来源获取 Z 高度")
            return None
            
        except Exception as e:
            logging.error(f"[DLP] 获取 Z 高度失败: {e}")
            return None
    
    def _get_printer_status(self) -> Dict:
        """获取打印机温度状态（带缓存和指数退避）
        
        模拟模式：返回模拟温度数据
        """
        # 模拟模式：返回模拟状态
        if self._simulation_mode_active and self._simulation_generator:
            return self._simulation_generator.generate_printer_status()
        
        # OctoPrint 模拟模式
        if self._octoprint_simulation_active and self._octoprint_simulator:
            status = self._octoprint_simulator.get_printer_status()
            temp = status.get("temperature", {})
            return {
                "hotend": temp.get("tool0", {}).get("actual", 0),
                "bed": temp.get("bed", {}).get("actual", 0),
                "hotend_target": temp.get("tool0", {}).get("target", 0),
                "bed_target": temp.get("bed", {}).get("target", 0)
            }
        
        current_time = time.time()
        
        # 检查缓存是否有效
        if current_time - self._octoprint_last_success < self._octoprint_cache_ttl:
            return self._octoprint_cache["printer"]
        
        try:
            url = f"{self.config.octoprint_url}/api/printer"
            headers = {"X-Api-Key": self.config.octoprint_api_key}
            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                temp = data.get("temperature", {})
                result = {
                    "hotend": temp.get("tool0", {}).get("actual", 0),
                    "bed": temp.get("bed", {}).get("actual", 0),
                    "hotend_target": temp.get("tool0", {}).get("target", 0),
                    "bed_target": temp.get("bed", {}).get("target", 0)
                }
                # 更新缓存
                self._octoprint_cache["printer"] = result
                self._octoprint_last_success = current_time
                self._octoprint_backoff = 1  # 重置退避时间
                return result
        except Exception as e:
            # 失败时使用缓存，增加退避时间
            if current_time - self._octoprint_last_success > self._octoprint_backoff:
                self._octoprint_backoff = min(self._octoprint_backoff * 2, 30)
                logging.debug(f"[DAQ] 获取温度失败，使用缓存，退避: {self._octoprint_backoff}s")
        
        return self._octoprint_cache["printer"]
    
    def _get_job_status(self) -> Dict:
        """获取当前打印任务状态（任务状态更新频繁，使用短缓存）
        
        模拟模式：返回模拟任务状态
        """
        # 模拟模式：返回模拟任务状态
        if self._simulation_mode_active and self._simulation_generator:
            t = time.time() - self._simulation_generator.start_time
            return {
                "state": "Printing (Simulation)",
                "progress": min(100, t * 0.1),
                "print_time": int(t),
                "print_time_left": int(3600 - t) if t < 3600 else 0,
                "filename": "simulation_test.gcode",
                "estimated_print_time": 3600
            }
        
        # OctoPrint 模拟模式
        if self._octoprint_simulation_active and self._octoprint_simulator:
            return self._octoprint_simulator.get_job_status()
        
        current_time = time.time()
        
        # 任务状态变化快，但失败时增加缓存时间避免刷屏
        # 成功时缓存 2 秒，失败时缓存 10 秒
        cache_ttl = 2.0 if self._octoprint_backoff <= 1 else 10.0
        if current_time - self._octoprint_last_success < cache_ttl:
            return self._octoprint_cache["job"]
        
        try:
            url = f"{self.config.octoprint_url}/api/job"
            headers = {"X-Api-Key": self.config.octoprint_api_key}
            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                job = data.get("job", {})
                progress = data.get("progress", {})
                state = data.get("state", "Unknown")
                filename = job.get("file", {}).get("name", "")
                completion = progress.get("completion", 0) or 0
                
                # 调试输出（仅首次或状态变化时）
                if not hasattr(self, '_last_job_log') or self._last_job_log != state:
                    logging.info(f"[OctoPrint] 状态: {state}, 进度: {completion:.1f}%, 文件: {filename}")
                    self._last_job_log = state
                
                result = {
                    "state": state,
                    "progress": completion,
                    "print_time": progress.get("printTime", 0) or 0,
                    "print_time_left": progress.get("printTimeLeft", 0) or 0,
                    "filename": filename,
                    "estimated_print_time": job.get("estimatedPrintTime", 0) or 0
                }
                # 更新缓存
                self._octoprint_cache["job"] = result
                self._octoprint_last_success = current_time
                self._octoprint_backoff = 1  # 重置退避
                return result
            else:
                # 403 错误说明 API Key 权限不足，降低日志级别避免刷屏
                if response.status_code == 403:
                    # 只在首次失败时记录一次
                    if not hasattr(self, '_job_403_logged'):
                        logging.warning(f"[OctoPrint] API Key 权限不足 (403)，任务状态查询将使用缓存")
                        self._job_403_logged = True
                else:
                    logging.warning(f"[OctoPrint] 获取任务状态失败: HTTP {response.status_code}")
        except Exception as e:
            logging.debug(f"[DAQ] 获取任务状态失败: {e}")
        
        # 失败时增加退避
        self._octoprint_backoff = min(self._octoprint_backoff * 2, 60)
        
        # 失败时返回缓存
        return self._octoprint_cache["job"]
    
    def _save_worker(self):
        """保存工作线程"""
        logging.info("[保存线程] 已启动")
        frame_count = 0
        
        while True:
            try:
                frame_data = self._save_queue.get(timeout=1.0)
                
                if frame_data is None:  # 结束信号
                    logging.info(f"[保存线程] 收到结束信号，共保存{frame_count}帧")
                    break
                
                self._save_frame(frame_data)
                frame_count += 1
                
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"保存线程错误: {e}")
        
        logging.info("[保存线程] 已停止")
    
    def _save_frame(self, frame_data: FrameData):
        """保存一帧数据 - 保持与之前一致的格式"""
        if not self.current_task_dir:
            return
        
        try:
            # 创建图像目录
            ids_dir = os.path.join(self.current_task_dir, "images", "IDS_Camera")
            side_dir = os.path.join(self.current_task_dir, "images", "Side_Camera")
            fotric_dir = os.path.join(self.current_task_dir, "images", "Fotric_Camera")
            fotric_data_dir = os.path.join(self.current_task_dir, "images", "Fotric_Data")
            
            # 保存 IDS 图像 (随轴相机)
            if frame_data.ids_image is not None:
                os.makedirs(ids_dir, exist_ok=True)
                ids_filename = f"image-{frame_data.frame_number}.jpg"
                ids_path = os.path.join(ids_dir, ids_filename)
                success = cv2.imwrite(ids_path, frame_data.ids_image)
                if success:
                    frame_data.ids_image_path = f"IDS_Camera/{ids_filename}"
                    if frame_data.frame_number % 10 == 1:
                        logging.info(f"[保存] IDS图像已保存: {ids_path} (shape={frame_data.ids_image.shape})")
                else:
                    logging.error(f"[保存] IDS图像保存失败: {ids_path}")
            else:
                if frame_data.frame_number % 10 == 1:
                    logging.debug(f"[保存] 第{frame_data.frame_number}帧无IDS图像")
            
            # 保存旁轴相机图像
            if frame_data.side_image is not None:
                os.makedirs(side_dir, exist_ok=True)
                side_filename = f"image-{frame_data.frame_number}.jpg"
                side_path = os.path.join(side_dir, side_filename)
                cv2.imwrite(side_path, frame_data.side_image)
                frame_data.side_image_path = f"Side_Camera/{side_filename}"
            
            # 保存 Fotric 图像和数据
            if frame_data.fotric_data is not None:
                os.makedirs(fotric_dir, exist_ok=True)
                os.makedirs(fotric_data_dir, exist_ok=True)
                
                # 保存彩色热像图 (JPG 格式用于直观查看)
                fotric_filename = f"image-{frame_data.frame_number}.jpg"
                fotric_path = os.path.join(fotric_dir, fotric_filename)
                if frame_data.fotric_image is not None:
                    cv2.imwrite(fotric_path, frame_data.fotric_image)
                    frame_data.fotric_image_path = f"Fotric_Camera/{fotric_filename}"
                
                # 保存原始热像数据为 NPZ 格式
                data_filename = f"thermal_data-{frame_data.frame_number}.npz"
                data_path = os.path.join(fotric_data_dir, data_filename)
                np.savez_compressed(
                    data_path,
                    thermal_data=frame_data.fotric_data.astype(np.float32),
                    timestamp=frame_data.timestamp,
                    temp_min=frame_data.fotric_temp_min,
                    temp_max=frame_data.fotric_temp_max,
                    temp_avg=frame_data.fotric_temp_avg
                )
                frame_data.fotric_data_path = f"Fotric_Data/{data_filename}"
            
            # 写入 CSV
            self._write_csv_row(frame_data)
            
            if frame_data.frame_number % 50 == 0:
                logging.info(f"[保存] 已保存 {frame_data.frame_number} 帧")
            
        except Exception as e:
            logging.error(f"保存帧错误: {e}")
    
    def _create_task_directory(self):
        """创建任务目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_task_dir = os.path.join(
            self.config.save_directory,
            f"task_{timestamp}"
        )
        os.makedirs(self.current_task_dir, exist_ok=True)
        os.makedirs(os.path.join(self.current_task_dir, "images"), exist_ok=True)
        logging.info(f"[采集] 任务目录: {self.current_task_dir}")
    
    def _init_csv(self):
        """初始化 CSV 文件 - 与之前格式一致"""
        csv_path = os.path.join(self.current_task_dir, "print_message.csv")
        self._csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
        self._csv_writer = csv.writer(self._csv_file)
        
        # 写入表头 - 与之前代码完全一致
        header = [
            'image_path',           # IDS相机图像路径
            'side_image_path',      # 旁轴相机图像路径
            'timestamp',            # 时间戳
            'current_x',            # X坐标
            'current_y',            # Y坐标
            'current_z',            # Z坐标
            'flow_rate',            # 流量设定值
            'feed_rate',            # 速度设定值
            'z_offset',             # Z偏移设定值
            'target_hotend',        # 目标热端温度
            'hot_end',              # 实际热端温度
            'bed',                  # 热床温度
            'img_num',              # 图像编号
            'flow_rate_class',      # 流量分类 (0/1/2)
            'feed_rate_class',      # 速度分类 (0/1/2)
            'z_offset_class',       # Z偏移分类 (0/1/2)
            'hotend_class',         # 温度分类 (0/1/2)
            'fotric_temp_min',      # 红外最小温度
            'fotric_temp_max',      # 红外最大温度
            'fotric_temp_avg',      # 红外平均温度
            'fotric_image_path',    # 红外图像路径
            'fotric_data_path'      # 红外数据路径
        ]
        
        self._csv_writer.writerow(header)
        self._csv_file.flush()
        logging.info(f"[采集] CSV文件创建: {csv_path}")
    
    def _write_csv_row(self, frame_data: FrameData):
        """写入 CSV 行 - 与之前格式一致"""
        if not self._csv_writer:
            return
        
        row = [
            frame_data.ids_image_path,          # image_path
            frame_data.side_image_path,         # side_image_path
            frame_data.timestamp,               # timestamp
            frame_data.current_x,               # current_x
            frame_data.current_y,               # current_y
            frame_data.current_z,               # current_z
            frame_data.flow_rate,               # flow_rate
            frame_data.feed_rate,               # feed_rate
            frame_data.z_offset,                # z_offset
            frame_data.target_hotend,           # target_hotend
            frame_data.hot_end,                 # hot_end
            frame_data.bed,                     # bed
            frame_data.frame_number,            # img_num
            frame_data.flow_rate_class,         # flow_rate_class
            frame_data.feed_rate_class,         # feed_rate_class
            frame_data.z_offset_class,          # z_offset_class
            frame_data.hotend_class,            # hotend_class
            frame_data.fotric_temp_min,         # fotric_temp_min
            frame_data.fotric_temp_max,         # fotric_temp_max
            frame_data.fotric_temp_avg,         # fotric_temp_avg
            frame_data.fotric_image_path,       # fotric_image_path
            frame_data.fotric_data_path         # fotric_data_path
        ]
        
        self._csv_writer.writerow(row)
        self._csv_file.flush()
    
    def _close_devices(self):
        """关闭所有设备"""
        # 关闭 IDS
        if self._ids_camera:
            try:
                if IDS_AVAILABLE:
                    # 停止采集
                    if hasattr(self, '_ids_nodemap') and self._ids_nodemap:
                        try:
                            self._ids_nodemap.FindNode("AcquisitionStop").Execute()
                        except:
                            pass
                    # 停止数据流
                    self._ids_camera.StopAcquisition()
            except:
                pass
            self._ids_camera = None
        
        # 关闭 IDS 设备
        if hasattr(self, '_ids_device') and self._ids_device:
            try:
                self._ids_device.Close()
            except:
                pass
            self._ids_device = None
        
        # 关闭 IDS 库
        if IDS_AVAILABLE:
            try:
                ids_peak.Library.Close()
            except:
                pass
        
        # 关闭旁轴相机
        if self._side_camera:
            try:
                # 检查是 SideCamera 对象还是 cv2.VideoCapture 对象
                if hasattr(self._side_camera, 'close'):
                    # SideCamera 对象
                    self._side_camera.close()
                else:
                    # cv2.VideoCapture 对象
                    self._side_camera.release()
            except:
                pass
            self._side_camera = None
        
        # 关闭 Fotric
        if self._fotric_device:
            try:
                self._fotric_device.disconnect()
            except:
                pass
            self._fotric_device = None
        
        # 关闭振动传感器
        if self._vibration_device:
            try:
                self._vibration_device.stopLoopRead()
                self._vibration_device.closeDevice()
            except:
                pass
            self._vibration_device = None
        
        # 注意：M114 已废弃，使用 DisplayLayerProgress 插件获取 Z 高度
        # 无需关闭任何资源
    
    def _set_state(self, new_state: AcquisitionState):
        """设置状态并触发回调"""
        old_state = self.state
        self.state = new_state
        
        if self.on_state_changed and old_state != new_state:
            self.on_state_changed(old_state, new_state)
    
    def get_status(self) -> Dict:
        """获取采集状态"""
        with self._state_lock:
            duration = 0
            if self.start_time and self.state != AcquisitionState.IDLE:
                duration = time.time() - self.start_time
            
            status = {
                "state": self.state.value,
                "frame_count": self.frame_count,
                "duration": round(duration, 2),
                "fps": self.config.capture_fps,
                "save_directory": self.current_task_dir,
                "queue_size": self._save_queue.qsize(),
                "param_mode": self.config.param_mode,
                "current_params": {
                    "flow_rate": self.config.flow_rate,
                    "feed_rate": self.config.feed_rate,
                    "z_offset": self.config.z_offset,
                    "target_hotend": self.config.target_hotend
                }
            }
            
            # 添加参数管理器状态
            if self._param_manager and PARAM_MANAGER_AVAILABLE:
                status["param_manager"] = self._param_manager.get_status()
                # 添加当前区间信息(标准塔模式)
                segment_info = self._param_manager.get_current_segment_info()
                if segment_info:
                    status["current_segment"] = segment_info
            
            return status
    
    def update_print_params(self, flow_rate: float = None, feed_rate: float = None, 
                          z_offset: float = None, target_hotend: float = None):
        """更新当前打印参数 (用于计算class)"""
        if flow_rate is not None:
            self.config.flow_rate = flow_rate
        if feed_rate is not None:
            self.config.feed_rate = feed_rate
        if z_offset is not None:
            self.config.z_offset = z_offset
        if target_hotend is not None:
            self.config.target_hotend = target_hotend
    
    # ========== 公共 API 方法 (供 main.py 使用) ==========
    
    def get_latest_frame(self, camera_type: str = "ids") -> Optional[np.ndarray]:
        """获取最新帧（供视频流使用）
        
        Args:
            camera_type: 'ids' 或 'side'
            
        Returns:
            numpy.ndarray: 图像帧，如果不可用返回 None
        """
        if camera_type == "ids":
            return self._get_ids_frame()
        elif camera_type == "side":
            return self._get_side_camera_frame()
        return None
    
    def _get_side_camera_frame(self) -> Optional[np.ndarray]:
        """获取旁轴相机帧"""
        if not self._side_camera:
            return None
        
        try:
            if hasattr(self._side_camera, 'get_frame'):
                return self._side_camera.get_frame()
            else:
                ret, frame = self._side_camera.read()
                if ret:
                    return frame
        except Exception as e:
            logging.debug(f"[SideCamera] 获取帧失败: {e}")
        return None
    
    def get_thermal_data(self) -> Optional[Dict]:
        """获取热像数据"""
        if self._simulation_mode_active and self._simulation_generator:
            return self._simulation_generator.generate_thermal_data()
        
        if not self._fotric_device or not self._fotric_device.is_connected:
            return None
        
        try:
            thermal_matrix = self._fotric_device.get_thermal_data()
            if thermal_matrix is not None:
                # 获取温度统计信息
                temp_stats = self._fotric_device.get_temperature_stats()
                if temp_stats:
                    return {
                        "available": True,
                        "matrix": thermal_matrix,
                        "min": temp_stats.get('min_temp', 0),
                        "max": temp_stats.get('max_temp', 100),
                        "melt_pool": temp_stats.get('max_temp', 0)  # 熔池温度使用最高温度
                    }
        except Exception as e:
            logging.debug(f"[Fotric] 获取热像数据失败: {e}")
        return None
    
    def get_latest_prediction(self) -> Optional[Dict]:
        """获取最新预测结果"""
        if self._simulation_mode_active and self._simulation_generator:
            return self._simulation_generator.generate_prediction()
        
        # 如果有推理结果，返回
        if self._latest_prediction:
            pred = self._latest_prediction
            return {
                "available": True,
                "flow_rate_label": pred.flow_rate_label,
                "flow_rate_conf": pred.flow_rate_conf,
                "feed_rate_label": pred.feed_rate_label,
                "feed_rate_conf": pred.feed_rate_conf,
                "z_offset_label": pred.z_offset_label,
                "z_offset_conf": pred.z_offset_conf,
                "hot_end_label": pred.hot_end_label,
                "hot_end_conf": pred.hot_end_conf,
                "inference_time_ms": pred.inference_time_ms
            }
        return None
    
    def get_printer_data(self) -> Optional[Dict]:
        """获取打印机数据"""
        return self.get_printer_status()
    
    def register_callback(self, callback):
        """注册数据回调（供 WebSocket 使用）"""
        if not hasattr(self, '_callbacks'):
            self._callbacks = []
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback):
        """注销数据回调"""
        if hasattr(self, '_callbacks') and callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_printer_status(self) -> Dict:
        """获取打印机状态（公共API）"""
        status = self._get_printer_status()
        job = self._get_job_status()
        
        # 判断连接状态（通过 DisplayLayerProgress 插件）
        is_connected = self._check_octoprint_connection() or self._octoprint_simulation_active
        
        result = {
            "connected": is_connected,
            "position": self._current_position,
            "hotend_actual": status.get("hotend", 0),
            "bed_actual": status.get("bed", 0),
            "hotend_target": status.get("hotend_target", 0),
            "bed_target": status.get("bed_target", 0),
            "state": job.get("state", "Unknown"),
            "progress": job.get("progress", 0),
            "filename": job.get("filename", ""),
            "print_time": job.get("print_time", 0),
            "print_time_left": job.get("print_time_left", 0)
        }
        
        # 添加模拟状态标记
        if self._octoprint_simulation_active:
            result["simulation"] = True
            result["state"] = "Printing (OctoPrint Simulation)"
        
        return result
    
    def get_thermal_status(self) -> Dict:
        """获取热像相机状态（公共API）"""
        # 模拟模式
        if self._simulation_mode_active:
            return {
                "available": True,
                "connected": True,
                "ip": "simulation",
                "simulation": True
            }
        
        if self._fotric_device and hasattr(self._fotric_device, 'is_connected'):
            return {
                "available": self._fotric_device.is_connected,
                "connected": self._fotric_device.is_connected,
                "ip": getattr(self._fotric_device, 'ip', 'unknown'),
                "simulation": getattr(self._fotric_device, 'simulation_mode', False)
            }
        return {"available": False, "connected": False}
    
    def get_camera_status(self) -> Dict:
        """获取相机状态（公共API）"""
        # 模拟模式
        if self._simulation_mode_active:
            return {
                "ids": {
                    "available": True,
                    "connected": True,
                    "frame_count": self._simulation_generator.frame_count if self._simulation_generator else 0,
                    "simulation": True
                },
                "side": {
                    "available": True,
                    "connected": True,
                    "frame_count": self._simulation_generator.frame_count if self._simulation_generator else 0,
                    "simulation": True
                }
            }
        
        # 获取各相机的帧数
        ids_frame_count = 0
        side_frame_count = 0
        
        # 检查 IDS 相机（包括 USB 回退模式）
        if self._ids_camera:
            try:
                # 如果是数据流对象，尝试获取统计信息
                if hasattr(self._ids_camera, 'get_frame_count'):
                    ids_frame_count = self._ids_camera.get_frame_count()
            except:
                pass
        
        if self._side_camera:
            try:
                if hasattr(self._side_camera, 'get_frame_count'):
                    side_frame_count = self._side_camera.get_frame_count()
            except:
                pass
        
        # 判断是否使用 USB 摄像头回退模式
        is_usb_fallback = hasattr(self, '_ids_camera_usb') and self._ids_camera_usb is not None
        
        return {
            "ids": {
                "available": self._ids_camera is not None,
                "connected": self._ids_camera is not None,
                "frame_count": ids_frame_count,
                "simulation": False,
                "usb_fallback": is_usb_fallback  # 标记是否使用 USB 回退
            },
            "side": {
                "available": self._side_camera is not None,
                "connected": self._side_camera is not None,
                "frame_count": side_frame_count,
                "simulation": False
            }
        }


# 全局实例（单例模式）
_acquisition_instance: Optional[DataAcquisition] = None

def _load_config_from_env(config: AcquisitionConfig):
    """从 .env 文件加载配置到 AcquisitionConfig"""
    try:
        import os
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' not in line:
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # OctoPrint 配置
                    if key == 'OCTOPRINT_API_KEY' and value and len(value) > 20:
                        config.octoprint_api_key = value
                        print(f"[DAQ] 从 .env 加载 API Key: {value[:30]}...")
                    elif key == 'OCTOPRINT_URL' and value:
                        config.octoprint_url = value
                        print(f"[DAQ] 从 .env 加载 URL: {value}")
                    
                    # 模拟模式配置
                    elif key == 'SIMULATION_MODE':
                        config.simulation_mode = value.lower() in ('true', '1', 'yes', 'on')
                        if config.simulation_mode:
                            print(f"[DAQ] 从 .env 加载: 模拟模式已启用")
                    elif key == 'SIMULATION_AUTO_FALLBACK':
                        config.simulation_auto_fallback = value.lower() in ('true', '1', 'yes', 'on')
                    
                    # OctoPrint 模拟配置
                    elif key == 'OCTOPRINT_SIMULATION':
                        config.octoprint_simulation = value.lower() in ('true', '1', 'yes', 'on')
                        if config.octoprint_simulation:
                            print(f"[DAQ] 从 .env 加载: OctoPrint模拟已启用")
                    elif key == 'OCTOPRINT_SIMULATION_AUTO_FALLBACK':
                        config.octoprint_simulation_auto_fallback = value.lower() in ('true', '1', 'yes', 'on')
                    
                    # 设备启用配置
                    elif key == 'IDS_ENABLE':
                        config.enable_ids = value.lower() in ('true', '1', 'yes', 'on')
                    elif key == 'SIDE_CAMERA_ENABLE':
                        config.enable_side_camera = value.lower() in ('true', '1', 'yes', 'on')
                    elif key == 'FOTRIC_ENABLE':
                        config.enable_fotric = value.lower() in ('true', '1', 'yes', 'on')
                    
                    # 数值配置
                    elif key == 'CAPTURE_FPS':
                        try:
                            config.capture_fps = float(value)
                        except:
                            pass
                    elif key == 'FOTRIC_IP':
                        config.fotric_ip = value
                    elif key == 'FOTRIC_PORT':
                        try:
                            config.fotric_port = int(value)
                        except:
                            pass
        return True
    except Exception as e:
        print(f"[DAQ] 从 .env 加载失败: {e}")
        return False


def get_acquisition(config: AcquisitionConfig = None) -> DataAcquisition:
    """获取数据采集实例
    
    如果没有提供配置，自动从 .env 文件加载 OctoPrint 配置
    """
    global _acquisition_instance
    if _acquisition_instance is None:
        if config is None:
            config = AcquisitionConfig()
        
        # 总是尝试从 .env 文件加载（覆盖默认值）
        _load_config_from_env(config)
        
        _acquisition_instance = DataAcquisition(config)
    return _acquisition_instance


def reset_acquisition():
    """重置采集实例"""
    global _acquisition_instance
    if _acquisition_instance:
        _acquisition_instance.stop()
        _acquisition_instance = None


# 兼容别名（用于 main.py）
get_daq_system = get_acquisition
