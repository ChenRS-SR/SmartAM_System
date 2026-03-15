"""
振动传感器优化器
===============
参考SLS项目中的vibration_optimizer.py实现
提供高级振动计算算法和灵敏度调整
"""

import time
import math
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

from .vibration_sensor import VibrationSensor, MockVibrationSensor


@dataclass
class OptimizerConfig:
    """优化器配置"""
    algorithm: str = "composite"
    sensitivity_level: int = 3
    baseline_samples: int = 10
    calibration_time: float = 5.0
    auto_calibrate: bool = True


class VibrationOptimizer:
    """振动优化器 - 提供高级振动分析算法"""
    
    # 灵敏度算法映射
    SENSITIVITY_ALGORITHMS = {
        "composite": "综合优化",
        "velocity_based": "速度优先",
        "displacement_based": "位移优先",
        "frequency_based": "频率优先",
        "rms": "均方根值",
        "peak": "峰值检测",
        "energy": "能量计算"
    }
    
    def __init__(self, sensor: VibrationSensor = None):
        """
        初始化振动优化器
        
        Args:
            sensor: 振动传感器实例
        """
        self.sensor = sensor
        
        # 配置
        self.config = OptimizerConfig()
        
        # 当前算法
        self.current_algorithm = "composite"
        
        # 灵敏度级别 (1-5)
        self.sensitivity_level = 3
        
        # 基线数据
        self.baseline_data = {
            'velocity_x': 0.0,
            'velocity_y': 0.0,
            'velocity_z': 0.0,
            'displacement_x': 0.0,
            'displacement_y': 0.0,
            'displacement_z': 0.0,
            'frequency_x': 0.0,
            'frequency_y': 0.0,
            'frequency_z': 0.0
        }
        
        # 历史数据（用于RMS计算）
        self.history_buffer = []
        self.max_history_size = 100
        
        # 校准状态
        self.is_calibrated = False
        self.calibration_data = []
        
        # 统计信息
        self.stats = {
            'total_readings': 0,
            'trigger_count': 0,
            'max_magnitude': 0.0,
            'avg_magnitude': 0.0,
            'calibration_time': None
        }
        
        print(f"ℹ️ 初始化振动优化器 (算法: {self.SENSITIVITY_ALGORITHMS[self.current_algorithm]})")
    
    def set_sensor(self, sensor: VibrationSensor):
        """设置传感器"""
        self.sensor = sensor
    
    def set_algorithm(self, algorithm: str) -> bool:
        """设置灵敏度算法"""
        if algorithm in self.SENSITIVITY_ALGORITHMS:
            self.current_algorithm = algorithm
            print(f"✅ 切换到算法: {self.SENSITIVITY_ALGORITHMS[algorithm]}")
            return True
        else:
            print(f"❌ 未知算法: {algorithm}")
            return False
    
    def set_sensitivity(self, level: int):
        """设置灵敏度级别 (1-5)"""
        self.sensitivity_level = max(1, min(5, level))
        print(f"✅ 灵敏度级别设置为: {self.sensitivity_level}")
    
    def calibrate(self, duration: float = 5.0) -> bool:
        """校准基线振动水平"""
        if self.sensor is None or not self.sensor.isOpen:
            print("❌ 传感器未连接，无法校准")
            return False
        
        print(f"⏳ 开始校准，持续 {duration} 秒...")
        self.calibration_data = []
        
        start_time = time.time()
        while time.time() - start_time < duration:
            data = self.sensor.read_data()
            if data:
                self.calibration_data.append({
                    'vx': data.vx, 'vy': data.vy, 'vz': data.vz,
                    'dx': data.dx, 'dy': data.dy, 'dz': data.dz,
                    'fx': data.fx, 'fy': data.fy, 'fz': data.fz
                })
            time.sleep(0.1)
        
        if len(self.calibration_data) > 0:
            # 计算平均值作为基线
            for key in self.baseline_data:
                values = [d[key.replace('_', '')] for d in self.calibration_data]
                self.baseline_data[key] = sum(values) / len(values)
            
            self.is_calibrated = True
            self.stats['calibration_time'] = datetime.now().isoformat()
            print(f"✅ 校准完成，基线: V=({self.baseline_data['velocity_x']:.4f}, "
                  f"{self.baseline_data['velocity_y']:.4f}, {self.baseline_data['velocity_z']:.4f})")
            return True
        else:
            print("❌ 校准失败，未获取到数据")
            return False
    
    def read_all_sensor_data(self) -> Optional[Dict]:
        """读取所有传感器数据"""
        if self.sensor is None:
            return None
        
        data = self.sensor.read_data()
        if data is None:
            return None
        
        return {
            'velocity_x': data.vx,
            'velocity_y': data.vy,
            'velocity_z': data.vz,
            'displacement_x': data.dx,
            'displacement_y': data.dy,
            'displacement_z': data.dz,
            'frequency_x': data.fx,
            'frequency_y': data.fy,
            'frequency_z': data.fz,
            'temperature': data.temperature,
            'timestamp': data.timestamp
        }
    
    def calculate_vibration_magnitude(self, data: Dict = None) -> float:
        """计算振动幅度（使用当前算法）"""
        if data is None:
            data = self.read_all_sensor_data()
        
        if data is None:
            return 0.0
        
        # 调用对应的算法
        algorithm_func = getattr(self, f"_algorithm_{self.current_algorithm}", self._algorithm_composite)
        return algorithm_func(data)
    
    def _algorithm_composite(self, data: Dict) -> float:
        """综合优化算法 - 加权组合"""
        # 减去基线
        vx = abs(data['velocity_x'] - self.baseline_data['velocity_x'])
        vy = abs(data['velocity_y'] - self.baseline_data['velocity_y'])
        vz = abs(data['velocity_z'] - self.baseline_data['velocity_z'])
        
        dx = abs(data['displacement_x'] - self.baseline_data['displacement_x'])
        dy = abs(data['displacement_y'] - self.baseline_data['displacement_y'])
        dz = abs(data['displacement_z'] - self.baseline_data['displacement_z'])
        
        fx = abs(data['frequency_x'] - self.baseline_data['frequency_x'])
        fy = abs(data['frequency_y'] - self.baseline_data['frequency_y'])
        fz = abs(data['frequency_z'] - self.baseline_data['frequency_z'])
        
        vel_mag = math.sqrt(vx**2 + vy**2 + vz**2)
        disp_mag = math.sqrt(dx**2 + dy**2 + dz**2)
        freq_mag = math.sqrt(fx**2 + fy**2 + fz**2)
        
        # 加权组合: 速度30% + 位移50% + 频率20%
        magnitude = vel_mag * 0.3 + disp_mag * 0.5 + freq_mag * 0.2
        
        # 应用灵敏度系数
        sensitivity_factor = self.sensitivity_level / 3.0
        return magnitude * sensitivity_factor
    
    def _algorithm_velocity_based(self, data: Dict) -> float:
        """速度优先算法"""
        vx = abs(data['velocity_x'] - self.baseline_data['velocity_x'])
        vy = abs(data['velocity_y'] - self.baseline_data['velocity_y'])
        vz = abs(data['velocity_z'] - self.baseline_data['velocity_z'])
        
        magnitude = math.sqrt(vx**2 + vy**2 + vz**2)
        sensitivity_factor = self.sensitivity_level / 3.0
        return magnitude * sensitivity_factor * 1.5  # 速度权重更高
    
    def _algorithm_displacement_based(self, data: Dict) -> float:
        """位移优先算法 - 更灵敏"""
        dx = abs(data['displacement_x'] - self.baseline_data['displacement_x'])
        dy = abs(data['displacement_y'] - self.baseline_data['displacement_y'])
        dz = abs(data['displacement_z'] - self.baseline_data['displacement_z'])
        
        magnitude = math.sqrt(dx**2 + dy**2 + dz**2)
        sensitivity_factor = self.sensitivity_level / 3.0
        return magnitude * sensitivity_factor * 2.0  # 位移权重更高
    
    def _algorithm_frequency_based(self, data: Dict) -> float:
        """频率优先算法"""
        fx = abs(data['frequency_x'] - self.baseline_data['frequency_x'])
        fy = abs(data['frequency_y'] - self.baseline_data['frequency_y'])
        fz = abs(data['frequency_z'] - self.baseline_data['frequency_z'])
        
        magnitude = math.sqrt(fx**2 + fy**2 + fz**2)
        sensitivity_factor = self.sensitivity_level / 3.0
        return magnitude * sensitivity_factor * 1.3
    
    def _algorithm_rms(self, data: Dict) -> float:
        """均方根值算法"""
        # 添加到历史缓冲区
        self.history_buffer.append(data)
        if len(self.history_buffer) > self.max_history_size:
            self.history_buffer.pop(0)
        
        if len(self.history_buffer) < 2:
            return 0.0
        
        # 计算RMS
        sum_squares = 0.0
        count = 0
        for hist_data in self.history_buffer:
            vx = hist_data['velocity_x'] - self.baseline_data['velocity_x']
            vy = hist_data['velocity_y'] - self.baseline_data['velocity_y']
            vz = hist_data['velocity_z'] - self.baseline_data['velocity_z']
            sum_squares += vx**2 + vy**2 + vz**2
            count += 3
        
        rms = math.sqrt(sum_squares / count) if count > 0 else 0.0
        sensitivity_factor = self.sensitivity_level / 3.0
        return rms * sensitivity_factor
    
    def _algorithm_peak(self, data: Dict) -> float:
        """峰值检测算法"""
        vx = abs(data['velocity_x'] - self.baseline_data['velocity_x'])
        vy = abs(data['velocity_y'] - self.baseline_data['velocity_y'])
        vz = abs(data['velocity_z'] - self.baseline_data['velocity_z'])
        
        # 返回最大分量
        magnitude = max(vx, vy, vz)
        sensitivity_factor = self.sensitivity_level / 3.0
        return magnitude * sensitivity_factor
    
    def _algorithm_energy(self, data: Dict) -> float:
        """能量计算算法"""
        vx = abs(data['velocity_x'] - self.baseline_data['velocity_x'])
        vy = abs(data['velocity_y'] - self.baseline_data['velocity_y'])
        vz = abs(data['velocity_z'] - self.baseline_data['velocity_z'])
        
        # 动能正比于速度平方
        energy = vx**2 + vy**2 + vz**2
        sensitivity_factor = self.sensitivity_level / 3.0
        return math.sqrt(energy) * sensitivity_factor
    
    def check_vibration_trigger(self, threshold: float) -> Tuple[bool, float]:
        """检查振动触发"""
        magnitude = self.calculate_vibration_magnitude()
        
        self.stats['total_readings'] += 1
        self.stats['max_magnitude'] = max(self.stats['max_magnitude'], magnitude)
        self.stats['avg_magnitude'] = (
            (self.stats['avg_magnitude'] * (self.stats['total_readings'] - 1) + magnitude)
            / self.stats['total_readings']
        )
        
        triggered = magnitude > threshold
        if triggered:
            self.stats['trigger_count'] += 1
        
        return triggered, magnitude
    
    def get_recommended_threshold(self) -> float:
        """获取推荐的阈值"""
        if not self.is_calibrated or not self.calibration_data:
            return 0.1
        
        # 基于校准数据的标准差
        velocities = []
        for d in self.calibration_data:
            velocities.append(math.sqrt(d['vx']**2 + d['vy']**2 + d['vz']**2))
        
        if len(velocities) > 1:
            mean = sum(velocities) / len(velocities)
            variance = sum((v - mean)**2 for v in velocities) / len(velocities)
            std_dev = math.sqrt(variance)
            
            # 阈值 = 平均值 + 3倍标准差
            base_threshold = mean + 3 * std_dev
            
            # 根据灵敏度调整
            sensitivity_multipliers = {1: 2.0, 2: 1.5, 3: 1.0, 4: 0.7, 5: 0.5}
            return base_threshold * sensitivity_multipliers.get(self.sensitivity_level, 1.0)
        
        return 0.1
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'algorithm': self.current_algorithm,
            'algorithm_name': self.SENSITIVITY_ALGORITHMS[self.current_algorithm],
            'sensitivity_level': self.sensitivity_level,
            'is_calibrated': self.is_calibrated,
            'calibration_time': self.stats['calibration_time'],
            'total_readings': self.stats['total_readings'],
            'trigger_count': self.stats['trigger_count'],
            'max_magnitude': self.stats['max_magnitude'],
            'avg_magnitude': self.stats['avg_magnitude'],
            'recommended_threshold': self.get_recommended_threshold(),
            'baseline': self.baseline_data.copy()
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.stats = {
            'total_readings': 0,
            'trigger_count': 0,
            'max_magnitude': 0.0,
            'avg_magnitude': 0.0,
            'calibration_time': self.stats['calibration_time']
        }
        self.history_buffer = []
        print("✅ 统计信息已重置")


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("振动优化器测试")
    print("=" * 60)
    
    # 创建模拟传感器
    sensor = MockVibrationSensor()
    sensor.connect()
    
    # 创建优化器
    optimizer = VibrationOptimizer(sensor)
    
    # 校准
    optimizer.calibrate(duration=2.0)
    
    # 测试不同算法
    print("\n测试不同算法:")
    for algo in optimizer.SENSITIVITY_ALGORITHMS.keys():
        optimizer.set_algorithm(algo)
        magnitude = optimizer.calculate_vibration_magnitude()
        print(f"  {optimizer.SENSITIVITY_ALGORITHMS[algo]}: {magnitude:.6f}")
    
    # 测试触发检测
    print("\n测试触发检测:")
    optimizer.set_algorithm("composite")
    for i in range(10):
        triggered, magnitude = optimizer.check_vibration_trigger(threshold=0.05)
        status = "🔴 触发" if triggered else "🟢 正常"
        print(f"  检测 {i+1}: {status}, 幅度={magnitude:.6f}")
        time.sleep(0.1)
    
    # 显示统计
    print("\n统计信息:")
    stats = optimizer.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    sensor.disconnect()
