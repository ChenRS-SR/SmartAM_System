"""
SLM (Selective Laser Melting) 调控逻辑模块
第三章/第四章的调控策略实现

功能：
1. 实时工艺参数调控
2. PID 控制算法
3. 基于缺陷预测的反馈控制
4. 激光功率、扫描速度等参数动态调整
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import time


@dataclass
class SLMParameters:
    """SLM 工艺参数数据结构"""
    laser_power: float = 200.0          # 激光功率 (W)
    scan_speed: float = 800.0           # 扫描速度 (mm/s)
    layer_thickness: float = 0.03       # 层厚 (mm)
    hatch_spacing: float = 0.1          # 扫描间距 (mm)
    spot_size: float = 0.1              # 光斑直径 (mm)
    
    # 温度相关
    preheat_temp: float = 80.0          # 预热温度 (°C)
    melt_pool_target: float = 1500.0    # 目标熔池温度 (°C)
    
    # 限制范围
    power_min: float = 50.0
    power_max: float = 400.0
    speed_min: float = 100.0
    speed_max: float = 2000.0


@dataclass
class SensorData:
    """传感器数据结构"""
    timestamp: float
    melt_pool_temp: float               # 熔池温度
    thermal_image: Optional[np.ndarray] = None  # 红外图像
    rgb_image: Optional[np.ndarray] = None      # 可见光图像
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # 打印位置


class PIDController:
    """
    PID 控制器
    用于温度、功率等连续量的闭环控制
    """
    
    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.1,
        kd: float = 0.05,
        output_limits: Tuple[float, float] = (-float('inf'), float('inf')),
        integral_limits: Tuple[float, float] = (-float('inf'), float('inf'))
    ):
        """
        初始化 PID 控制器
        
        Args:
            kp: 比例系数
            ki: 积分系数
            kd: 微分系数
            output_limits: 输出限制 (min, max)
            integral_limits: 积分项限制 (防止积分饱和)
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limits = output_limits
        self.integral_limits = integral_limits
        
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = None
    
    def reset(self):
        """重置控制器状态"""
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = None
    
    def update_params(self, kp: Optional[float] = None, ki: Optional[float] = None, kd: Optional[float] = None):
        """
        更新 PID 参数
        
        Args:
            kp: 新的比例系数（None 表示不变）
            ki: 新的积分系数（None 表示不变）
            kd: 新的微分系数（None 表示不变）
        """
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if kd is not None:
            self.kd = kd
    
    def get_params(self) -> Dict[str, float]:
        """获取当前 PID 参数"""
        return {
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd
        }
    
    def update(self, setpoint: float, measurement: float) -> float:
        """
        更新控制器并返回控制输出
        
        Args:
            setpoint: 目标值
            measurement: 当前测量值
            
        Returns:
            控制输出值
        """
        current_time = time.time()
        error = setpoint - measurement
        
        if self._last_time is None:
            dt = 0.1  # 默认时间间隔
        else:
            dt = current_time - self._last_time
        
        # 比例项
        proportional = self.kp * error
        
        # 积分项
        self._integral += error * dt
        self._integral = np.clip(
            self._integral,
            self.integral_limits[0],
            self.integral_limits[1]
        )
        integral = self.ki * self._integral
        
        # 微分项
        derivative = self.kd * (error - self._last_error) / dt if dt > 0 else 0
        
        # 计算输出
        output = proportional + integral + derivative
        output = np.clip(output, self.output_limits[0], self.output_limits[1])
        
        # 更新状态
        self._last_error = error
        self._last_time = current_time
        
        return output


class SLMController:
    """
    SLM 打印过程主控制器
    整合传感器数据、缺陷预测、PID 调控
    """
    
    def __init__(
        self,
        initial_params: Optional[SLMParameters] = None,
        enable_pid: bool = True,
        enable_defect_feedback: bool = True
    ):
        """
        初始化 SLM 控制器
        
        Args:
            initial_params: 初始工艺参数
            enable_pid: 是否启用 PID 控制
            enable_defect_feedback: 是否启用缺陷反馈控制
        """
        self.params = initial_params or SLMParameters()
        self.enable_pid = enable_pid
        self.enable_defect_feedback = enable_defect_feedback
        
        # 温度 PID 控制器 (控制激光功率)
        self.temp_pid = PIDController(
            kp=0.5,
            ki=0.05,
            kd=0.02,
            output_limits=(-50, 50)  # 功率调整范围 ±50W
        )
        
        # 数据历史 (用于趋势分析)
        self.temp_history: deque = deque(maxlen=100)
        self.power_history: deque = deque(maxlen=100)
        
        # 回调函数 (用于发送控制指令到打印机)
        self.command_callback: Optional[Callable[[str, Dict], None]] = None
        
        # 运行状态
        self.is_running = False
        self.control_loop_count = 0
    
    def set_command_callback(self, callback: Callable[[str, Dict], None]):
        """
        设置命令发送回调函数
        
        Args:
            callback: 函数签名 (command_type: str, params: Dict) -> None
        """
        self.command_callback = callback
    
    def _send_command(self, command_type: str, params: Dict):
        """发送控制指令"""
        if self.command_callback:
            self.command_callback(command_type, params)
        else:
            print(f"[SLM Control] 指令: {command_type}, 参数: {params}")
    
    def update_parameters(self, new_params: Dict):
        """更新工艺参数"""
        for key, value in new_params.items():
            if hasattr(self.params, key):
                setattr(self.params, key, value)
                print(f"[SLM Control] 更新参数: {key} = {value}")
    
    def process_sensor_data(self, data: SensorData) -> Dict:
        """
        处理传感器数据并执行控制逻辑
        
        Args:
            data: 传感器数据
            
        Returns:
            控制决策结果
        """
        result = {
            "timestamp": data.timestamp,
            "control_action": "none",
            "power_adjustment": 0.0,
            "speed_adjustment": 0.0,
            "reason": ""
        }
        
        # 记录历史数据
        self.temp_history.append(data.melt_pool_temp)
        
        # 1. PID 温度控制
        if self.enable_pid:
            power_adjust = self.temp_pid.update(
                self.params.melt_pool_target,
                data.melt_pool_temp
            )
            
            new_power = self.params.laser_power + power_adjust
            new_power = np.clip(
                new_power,
                self.params.power_min,
                self.params.power_max
            )
            
            if abs(power_adjust) > 5:  # 最小调整阈值
                result["control_action"] = "adjust_power"
                result["power_adjustment"] = power_adjust
                result["new_power"] = new_power
                result["reason"] = f"温度偏差: {self.params.melt_pool_target - data.melt_pool_temp:.1f}°C"
                
                self.params.laser_power = new_power
                self.power_history.append(new_power)
                
                # 发送功率调整指令
                self._send_command("SET_POWER", {"power": new_power})
        
        self.control_loop_count += 1
        return result
    
    def process_defect_prediction(
        self,
        defect_prob: float,
        defect_type: Optional[str] = None,
        defect_location: Optional[Tuple[int, int]] = None
    ) -> Dict:
        """
        处理缺陷预测结果并执行反馈控制
        
        Args:
            defect_prob: 缺陷概率 (0-1)
            defect_type: 缺陷类型
            defect_location: 缺陷位置坐标
            
        Returns:
            调控决策结果
        """
        result = {
            "defect_prob": defect_prob,
            "action_taken": False,
            "adjustments": {}
        }
        
        if not self.enable_defect_feedback:
            return result
        
        # 缺陷反馈控制策略
        if defect_prob > 0.8:
            # 高概率缺陷：紧急干预
            # 降低扫描速度，增加功率以改善熔合
            speed_adj = -100  # mm/s
            power_adj = 20    # W
            
            new_speed = np.clip(
                self.params.scan_speed + speed_adj,
                self.params.speed_min,
                self.params.speed_max
            )
            new_power = np.clip(
                self.params.laser_power + power_adj,
                self.params.power_min,
                self.params.power_max
            )
            
            self.params.scan_speed = new_speed
            self.params.laser_power = new_power
            
            result["action_taken"] = True
            result["adjustments"] = {
                "speed_change": speed_adj,
                "power_change": power_adj,
                "reason": "高概率缺陷预警"
            }
            
            self._send_command("EMERGENCY_ADJUST", result["adjustments"])
            
        elif defect_prob > 0.5:
            # 中等概率缺陷：预警，轻微调整
            power_adj = 10
            new_power = np.clip(
                self.params.laser_power + power_adj,
                self.params.power_min,
                self.params.power_max
            )
            
            self.params.laser_power = new_power
            
            result["action_taken"] = True
            result["adjustments"] = {
                "power_change": power_adj,
                "reason": "中等缺陷风险"
            }
            
            self._send_command("ADJUST_POWER", {"power": new_power})
        
        return result
    
    def get_pid_params(self) -> Dict[str, float]:
        """获取 PID 控制器参数"""
        params = self.temp_pid.get_params()
        params["target_temp"] = self.params.melt_pool_target
        return params
    
    def set_pid_params(self, kp: Optional[float] = None, 
                       ki: Optional[float] = None,
                       kd: Optional[float] = None,
                       target_temp: Optional[float] = None):
        """
        设置 PID 控制器参数
        
        Args:
            kp: 比例系数
            ki: 积分系数
            kd: 微分系数
            target_temp: 目标熔池温度
        """
        self.temp_pid.update_params(kp, ki, kd)
        if target_temp is not None:
            self.params.melt_pool_target = target_temp
        print(f"[SLM Control] PID 参数已更新: Kp={kp}, Ki={ki}, Kd={kd}, Target={target_temp}")
    
    def get_status(self) -> Dict:
        """获取控制器状态"""
        return {
            "is_running": self.is_running,
            "current_params": {
                "laser_power": self.params.laser_power,
                "scan_speed": self.params.scan_speed,
                "layer_thickness": self.params.layer_thickness,
            },
            "pid_params": self.get_pid_params(),
            "control_loop_count": self.control_loop_count,
            "temp_history_size": len(self.temp_history),
            "avg_temperature": np.mean(self.temp_history) if self.temp_history else 0
        }
    
    def start(self):
        """启动控制器"""
        self.is_running = True
        self.temp_pid.reset()
        print("[SLM Control] 控制器已启动")
    
    def stop(self):
        """停止控制器"""
        self.is_running = False
        print("[SLM Control] 控制器已停止")
    
    def reset(self):
        """重置控制器状态"""
        self.temp_history.clear()
        self.power_history.clear()
        self.temp_pid.reset()
        self.control_loop_count = 0
        print("[SLM Control] 控制器已重置")


# 单例模式
_controller: Optional[SLMController] = None


def get_slm_controller(**kwargs) -> SLMController:
    """获取 SLM 控制器单例"""
    global _controller
    if _controller is None:
        _controller = SLMController(**kwargs)
    return _controller


if __name__ == "__main__":
    # 测试代码
    print("[Test] SLM 控制器测试")
    
    controller = get_slm_controller()
    
    # 模拟控制循环
    controller.start()
    
    for i in range(10):
        # 模拟传感器数据
        sensor = SensorData(
            timestamp=time.time(),
            melt_pool_temp=1400 + np.random.randn() * 50
        )
        
        result = controller.process_sensor_data(sensor)
        print(f"Loop {i}: {result}")
        
        # 模拟缺陷预测
        if i == 5:
            defect_result = controller.process_defect_prediction(0.85, "porosity")
            print(f"Defect handling: {defect_result}")
        
        time.sleep(0.1)
    
    print(f"\n最终状态: {controller.get_status()}")
    controller.stop()
