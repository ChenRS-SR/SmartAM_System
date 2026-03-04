"""
模拟数据生成器 - 用于无硬件调试
生成模拟图像和传感器数据，使系统可以在没有硬件的情况下运行
"""
import numpy as np
import cv2
import time
import random
from typing import Optional, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SimulationConfig:
    """模拟配置"""
    ids_resolution: Tuple[int, int] = (1920, 1080)  # IDS 相机分辨率
    side_resolution: Tuple[int, int] = (1920, 1080)  # 旁轴相机分辨率
    thermal_resolution: Tuple[int, int] = (640, 480)  # 热像分辨率
    
    # 模拟参数
    enable_noise: bool = True  # 添加噪声
    enable_movement: bool = True  # 模拟运动
    frame_rate: float = 30.0  # 模拟帧率


class SimulationGenerator:
    """
    模拟数据生成器
    生成逼真的模拟图像和数据用于调试
    """
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        self.frame_count = 0
        self.start_time = time.time()
        
        # 生成固定的背景图案（避免每帧都重新生成）
        self._ids_background = self._generate_ids_background()
        self._side_background = self._generate_side_background()
        
    def _generate_ids_background(self) -> np.ndarray:
        """生成 IDS 相机背景（模拟打印头视角）"""
        h, w = self.config.ids_resolution[1], self.config.ids_resolution[0]
        
        # 创建渐变背景
        bg = np.zeros((h, w, 3), dtype=np.uint8)
        
        # 模拟打印平台纹理
        for i in range(0, h, 20):
            cv2.line(bg, (0, i), (w, i), (40, 40, 40), 1)
        for i in range(0, w, 20):
            cv2.line(bg, (i, 0), (i, h), (40, 40, 40), 1)
        
        # 添加一些"已打印"的区域（模拟层纹）
        for i in range(h // 3, 2 * h // 3, 5):
            cv2.line(bg, (w // 4, i), (3 * w // 4, i), (60, 60, 70), 2)
        
        return bg
    
    def _generate_side_background(self) -> np.ndarray:
        """生成旁轴相机背景（模拟整体视角）"""
        h, w = self.config.side_resolution[1], self.config.side_resolution[0]
        
        # 深色背景
        bg = np.zeros((h, w, 3), dtype=np.uint8)
        bg[:] = (30, 30, 35)
        
        # 模拟打印机框架
        cv2.rectangle(bg, (w // 4, h // 4), (3 * w // 4, 3 * h // 4), (50, 50, 55), 3)
        
        # 模拟打印件（一个立方体形状）
        cube_x = w // 2
        cube_y = 2 * h // 3
        cv2.rectangle(bg, (cube_x - 50, cube_y - 80), (cube_x + 50, cube_y), (80, 80, 85), -1)
        cv2.rectangle(bg, (cube_x - 50, cube_y - 80), (cube_x + 50, cube_y), (100, 100, 105), 2)
        
        return bg
    
    def generate_ids_frame(self) -> np.ndarray:
        """生成 IDS 相机模拟帧（随轴视角）"""
        self.frame_count += 1
        
        # 复制背景
        frame = self._ids_background.copy()
        h, w = frame.shape[:2]
        
        # 模拟时间变化
        t = time.time() - self.start_time
        
        # 添加模拟的打印头
        nozzle_x = int(w // 2 + 100 * np.sin(t * 0.5))
        nozzle_y = int(h // 2 + 50 * np.cos(t * 0.3))
        
        # 打印头主体
        cv2.circle(frame, (nozzle_x, nozzle_y), 30, (100, 100, 110), -1)
        cv2.circle(frame, (nozzle_x, nozzle_y), 30, (150, 150, 160), 2)
        
        # 喷嘴（发光效果模拟热量）
        glow_intensity = int(128 + 127 * np.sin(t * 2))
        cv2.circle(frame, (nozzle_x, nozzle_y + 20), 8, (0, glow_intensity, 255), -1)
        
        # 添加已打印的丝材（随着时间增长）
        if self.config.enable_movement:
            progress = (t * 10) % w
            cv2.line(frame, (w // 4, h // 2), (w // 4 + int(progress), h // 2), (200, 200, 210), 4)
        
        # 添加噪声
        if self.config.enable_noise:
            noise = np.random.normal(0, 5, frame.shape).astype(np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # 添加文字标识
        cv2.putText(frame, "[SIMULATION] IDS Camera", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Frame: {self.frame_count}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return frame
    
    def generate_side_frame(self) -> np.ndarray:
        """生成旁轴相机模拟帧（整体视角）"""
        frame = self._side_background.copy()
        h, w = frame.shape[:2]
        
        t = time.time() - self.start_time
        
        # 模拟打印头运动
        nozzle_x = int(w // 2 + 150 * np.sin(t * 0.5))
        nozzle_y = int(2 * h // 3 - 100)
        
        # 打印头
        cv2.rectangle(frame, (nozzle_x - 20, nozzle_y - 30), (nozzle_x + 20, nozzle_y + 30), (120, 120, 130), -1)
        
        # 连接线
        cv2.line(frame, (nozzle_x, nozzle_y - 30), (nozzle_x, 0), (80, 80, 90), 4)
        
        # 添加噪声
        if self.config.enable_noise:
            noise = np.random.normal(0, 3, frame.shape).astype(np.int16)
            frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        # 添加文字标识
        cv2.putText(frame, "[SIMULATION] Side Camera", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return frame
    
    def generate_thermal_data(self) -> np.ndarray:
        """生成热像模拟数据（温度矩阵）"""
        h, w = self.config.thermal_resolution[1], self.config.thermal_resolution[0]
        t = time.time() - self.start_time
        
        # 基础温度（室温 ~25°C）
        base_temp = 25.0
        data = np.ones((h, w), dtype=np.float32) * base_temp
        
        # 添加温度渐变
        y_coords, x_coords = np.ogrid[:h, :w]
        
        # 模拟热床加热区域（底部高温）
        bed_temp = 60.0
        bed_mask = (y_coords > h * 0.7).astype(np.float32)
        data += bed_temp * bed_mask
        
        # 模拟熔池（移动的热点）
        pool_x = int(w // 2 + 100 * np.sin(t * 0.5))
        pool_y = int(h // 2 + 50 * np.cos(t * 0.3))
        
        # 高斯分布模拟热源
        sigma = 30.0
        heat_distribution = np.exp(-((x_coords - pool_x)**2 + (y_coords - pool_y)**2) / (2 * sigma**2))
        data += 200.0 * heat_distribution  # 熔池温度可达 200°C+
        
        # 添加随机噪声
        if self.config.enable_noise:
            data += np.random.normal(0, 2, (h, w))
        
        return data
    
    def get_temperature_stats(self, thermal_data: np.ndarray = None) -> Dict:
        """获取温度统计信息"""
        if thermal_data is None:
            thermal_data = self.generate_thermal_data()
        
        return {
            'min_temp': float(np.min(thermal_data)),
            'max_temp': float(np.max(thermal_data)),
            'avg_temp': float(np.mean(thermal_data)),
        }
    
    def generate_printer_position(self) -> Dict[str, float]:
        """生成模拟的打印机位置"""
        t = time.time() - self.start_time
        
        # 模拟打印头在打印一个方形
        cycle = 10  # 10秒一个周期
        phase = (t % cycle) / cycle
        
        if phase < 0.25:
            # 从左到右
            x = 50 + phase * 4 * 100
            y = 50
        elif phase < 0.5:
            # 从右到左（下一行）
            x = 150 - (phase - 0.25) * 4 * 100
            y = 70
        elif phase < 0.75:
            # 从左到右
            x = 50 + (phase - 0.5) * 4 * 100
            y = 90
        else:
            # 从右到左
            x = 150 - (phase - 0.75) * 4 * 100
            y = 110
        
        # Z 缓慢上升（模拟打印过程）
        z = 5.0 + t * 0.1  # 每秒上升 0.1mm
        
        return {
            'X': x,
            'Y': y,
            'Z': z,
            'E': t * 0.5  # 挤出量
        }
    
    def generate_printer_status(self) -> Dict:
        """生成模拟的打印机状态"""
        t = time.time() - self.start_time
        
        # 模拟温度波动
        base_hotend = 200.0
        base_bed = 60.0
        
        return {
            'hotend': base_hotend + 5 * np.sin(t),
            'bed': base_bed + 2 * np.sin(t * 0.7),
            'hotend_target': base_hotend,
            'bed_target': base_bed,
            'state': 'Printing',
            'progress': min(100, t * 0.1),  # 每秒增加 0.1% 进度
        }


# 全局模拟生成器实例
_simulation_instance: Optional[SimulationGenerator] = None


def get_simulation_generator(config: SimulationConfig = None) -> SimulationGenerator:
    """获取模拟生成器实例（单例）"""
    global _simulation_instance
    if _simulation_instance is None:
        _simulation_instance = SimulationGenerator(config)
    return _simulation_instance
