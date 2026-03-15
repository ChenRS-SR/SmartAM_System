"""
闭环控制系统 - 基于时间衰减置信度和序列一致性的自适应调控
第三章核心算法实现
"""
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import time
import requests
from datetime import datetime

class ParameterType(Enum):
    """工艺参数类型"""
    FLOW_RATE = "flow_rate"      # 流量倍率 (M221)
    FEED_RATE = "feed_rate"      # 打印速度 (M220)
    Z_OFFSET = "z_offset"        # Z轴补偿 (M290)
    HOTEND_TEMP = "hotend_temp"  # 热端温度 (M104)

class ParameterState(Enum):
    """参数状态"""
    LOW = 0      # 偏低
    NORMAL = 1   # 正常
    HIGH = 2     # 偏高

@dataclass
class PredictionResult:
    """预测结果数据结构"""
    param: ParameterType
    state: ParameterState
    confidence: float  # 0-1 之间
    timestamp: float
    
@dataclass
class ParameterAdjustment:
    """参数调整指令"""
    param: ParameterType
    value: float  # 调整量（可为正负）
    confidence: float  # 触发调整的置信度
    timestamp: float
    
@dataclass
class ClosedLoopConfig:
    """闭环控制配置参数"""
    # 状态序列缓冲区配置
    buffer_size: int = 10           # 缓冲区长度 N
    forgetting_factor: float = 0.8  # 遗忘因子 α
    
    # 双阈值施密特触发配置
    threshold_on: float = 0.7       # 开启阈值 θ_on
    threshold_off: float = 0.4      # 关闭阈值 θ_off
    
    # 非线性增益调度配置
    base_gain: Dict[ParameterType, float] = field(default_factory=lambda: {
        ParameterType.FLOW_RATE: 5.0,      # 基础调节 ±5%
        ParameterType.FEED_RATE: 10.0,     # 基础调节 ±10%
        ParameterType.Z_OFFSET: 0.05,      # 基础调节 ±0.05mm
        ParameterType.HOTEND_TEMP: 5.0,    # 基础调节 ±5°C
    })
    aggressive_factor: float = 3.0   # 激进因子 β
    nonlinear_exp: float = 2.0       # 非线性指数 n
    
    # 安全约束
    max_adjustment: Dict[ParameterType, float] = field(default_factory=lambda: {
        ParameterType.FLOW_RATE: 20.0,     # 最大 ±20%
        ParameterType.FEED_RATE: 50.0,     # 最大 ±50%
        ParameterType.Z_OFFSET: 0.2,       # 最大 ±0.2mm
        ParameterType.HOTEND_TEMP: 15.0,   # 最大 ±15°C
    })
    
    # 控制间隔
    control_interval: float = 1.0    # 最短控制间隔（秒）

class StateSequenceBuffer:
    """
    状态序列缓冲区 - 实现时间衰减加权置信度
    
    对应论文3.3.1节：状态序列缓冲区与加权置信度模型
    """
    def __init__(self, config: ClosedLoopConfig):
        self.config = config
        # FIFO队列存储历史预测结果
        self.buffer: deque = deque(maxlen=config.buffer_size)
        self.alpha = config.forgetting_factor
        
    def add_prediction(self, prediction: PredictionResult):
        """添加新的预测结果到缓冲区"""
        self.buffer.append(prediction)
        
    def calculate_weighted_confidence(self, target_state: ParameterState) -> float:
        """
        计算时间衰减加权置信度
        
        公式: W(k) = Σ[α^(N-j) * I(c_j == c_target)] / Σ[α^(N-j)]
        
        Args:
            target_state: 目标状态（LOW/NORMAL/HIGH）
            
        Returns:
            weighted_confidence: 加权置信度 [0, 1]
        """
        if len(self.buffer) == 0:
            return 0.0
            
        N = len(self.buffer)
        numerator = 0.0
        denominator = 0.0
        
        for j, pred in enumerate(self.buffer):
            # 计算时间权重: w_j = α^(N-j)
            weight = self.alpha ** (N - j - 1)
            denominator += weight
            
            # 指示函数: I(c_j == c_target)
            if pred.state == target_state:
                numerator += weight * pred.confidence
                
        if denominator == 0:
            return 0.0
            
        return numerator / denominator
    
    def get_sequence_statistics(self) -> Dict:
        """获取序列统计信息"""
        if len(self.buffer) == 0:
            return {}
            
        states = [p.state for p in self.buffer]
        confidences = [p.confidence for p in self.buffer]
        
        # 统计各状态出现频率
        state_counts = {state: states.count(state) for state in ParameterState}
        
        return {
            "length": len(self.buffer),
            "state_distribution": state_counts,
            "avg_confidence": np.mean(confidences),
            "max_confidence": max(confidences),
            "min_confidence": min(confidences),
        }

class SchmittTrigger:
    """
    双阈值施密特触发器
    
    对应论文3.3.2节：双阈值施密特触发逻辑
    防止控制信号在阈值附近频繁跳变
    """
    def __init__(self, config: ClosedLoopConfig):
        self.config = config
        self.is_active = False  # 当前调控激活状态
        
    def update(self, confidence: float) -> bool:
        """
        更新触发器状态
        
        状态转移方程:
        - 从非激活到激活: 当 confidence >= θ_on
        - 从激活到非激活: 当 confidence <= θ_off
        
        Args:
            confidence: 当前加权置信度
            
        Returns:
            bool: 当前是否处于调控激活状态
        """
        if not self.is_active:
            # 非激活状态: 需要超过开启阈值
            if confidence >= self.config.threshold_on:
                self.is_active = True
                return True
        else:
            # 激活状态: 需要低于关闭阈值才退出
            if confidence <= self.config.threshold_off:
                self.is_active = False
                return False
            return True
            
        return self.is_active
    
    def reset(self):
        """重置触发器状态"""
        self.is_active = False

class AdaptiveGainScheduler:
    """
    自适应非线性增益调度器
    
    对应论文3.4节：基于置信度梯度的非线性增益调度
    """
    def __init__(self, config: ClosedLoopConfig):
        self.config = config
        
    def calculate_adjustment(self, 
                            param: ParameterType,
                            confidence: float,
                            direction: int) -> float:
        """
        计算参数调节量
        
        公式: Δu = direction * K_base * (1 + β * C^n)
        
        Args:
            param: 参数类型
            confidence: 加权置信度 [0, 1]
            direction: 调节方向 (+1 增加, -1 减少)
            
        Returns:
            float: 调节量
        """
        # 基础增益
        K_base = self.config.base_gain.get(param, 1.0)
        
        # 非线性增益函数
        # Δu = direction * K_base * (1 + β * C^n)
        gain_factor = 1.0 + self.config.aggressive_factor * (confidence ** self.config.nonlinear_exp)
        adjustment = direction * K_base * gain_factor
        
        # 安全约束
        max_adj = self.config.max_adjustment.get(param, float('inf'))
        adjustment = np.clip(adjustment, -max_adj, max_adj)
        
        return adjustment
    
    def calculate_temperature_adjustment(self,
                                       current_temp: float,
                                       target_temp: float,
                                       confidence: float) -> float:
        """
        温度专用调节计算（考虑热惯性）
        
        温度控制需要考虑：
        1. 当前与目标温差
        2. 置信度
        3. 热惯性补偿
        
        Args:
            current_temp: 当前温度
            target_temp: 目标温度
            confidence: 置信度
            
        Returns:
            float: 新的目标温度
        """
        temp_error = target_temp - current_temp
        
        # 如果温度偏差已经很小，不进行调节
        if abs(temp_error) < 2.0:
            return target_temp
            
        # 计算调节量
        direction = 1 if temp_error < 0 else -1  # 温度过高则降温，过低则升温
        adjustment = self.calculate_adjustment(
            ParameterType.HOTEND_TEMP,
            confidence,
            direction
        )
        
        new_temp = target_temp + adjustment
        
        # 安全限制
        new_temp = np.clip(new_temp, 180.0, 260.0)
        
        return new_temp

class OctoPrintClient:
    """OctoPrint HTTP客户端 - 发送G-code指令"""
    
    def __init__(self, base_url: str = "http://localhost:5000", api_key: str = ""):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}
        
        # 当前参数值缓存
        self.current_values = {
            ParameterType.FLOW_RATE: 100.0,
            ParameterType.FEED_RATE: 100.0,
            ParameterType.Z_OFFSET: 0.0,
            ParameterType.HOTEND_TEMP: 200.0,
        }
        
        # Z-offset 累积调整量（相对于初始值）
        # 例如：初始-2.55，当前-1.80，则累积调整量为 +0.75
        self.z_offset_cumulative = 0.0
        
        # 上次Z调整时间（防止过于频繁调整）
        self.last_z_adjust_time = 0.0
        self.z_adjust_cooldown = 10.0  # 最小调整间隔（秒）
        
        # 兼容性别名
        self.current_params = self.current_values
        
    def send_gcode(self, command: str) -> bool:
        """发送G-code指令"""
        try:
            url = f"{self.base_url}/api/printer/command"
            response = requests.post(
                url,
                headers=self.headers,
                json={"command": command},
                timeout=5
            )
            return response.status_code == 204
        except Exception as e:
            print(f"发送G-code失败: {e}")
            return False
    
    def set_flow_rate(self, percentage: float) -> bool:
        """设置流量倍率 M221"""
        percentage = np.clip(percentage, 50, 150)
        if self.send_gcode(f"M221 S{int(percentage)}"):
            self.current_values[ParameterType.FLOW_RATE] = percentage
            print(f"流量倍率设置为: {percentage}%")
            return True
        return False
    
    def set_feed_rate(self, percentage: float) -> bool:
        """设置打印速度 M220"""
        percentage = np.clip(percentage, 20, 200)
        if self.send_gcode(f"M220 S{int(percentage)}"):
            self.current_values[ParameterType.FEED_RATE] = percentage
            print(f"打印速度设置为: {percentage}%")
            return True
        return False
    
    def set_z_offset(self, target_cumulative: float) -> bool:
        """
        设置Z轴偏移的累积调整量
        
        Args:
            target_cumulative: 目标累积调整量（相对于初始Z-offset）
                            例如：+0.75 表示比初始值抬高0.75mm
        
        实际发送的M290值 = target_cumulative - 当前累积量
        """
        # 限制累积调整量范围（相对于初始值的最大调整）
        target_cumulative = np.clip(target_cumulative, -0.5, 0.5)
        
        # 计算需要调整的差值
        delta = target_cumulative - self.z_offset_cumulative
        
        # 如果调整量太小，跳过
        if abs(delta) < 0.01:
            return True
        
        # 发送相对调整命令
        if self.send_gcode(f"M290 Z{delta:.3f}"):
            self.z_offset_cumulative = target_cumulative
            self.current_values[ParameterType.Z_OFFSET] = target_cumulative
            print(f"Z轴偏移调整: {delta:+.3f}mm, 累积调整量: {target_cumulative:+.3f}mm")
            return True
        return False
    
    def adjust_z_offset(self, delta: float) -> bool:
        """
        增量调整Z轴偏移（用于闭环控制）
        
        Args:
            delta: 调整量（如 +0.1 表示抬高0.1mm）
        
        Returns:
            bool: 是否成功
        """
        # 检查冷却时间（防止过于频繁调整）
        current_time = time.time()
        if current_time - self.last_z_adjust_time < self.z_adjust_cooldown:
            print(f"Z调整冷却中，还需等待 {self.z_adjust_cooldown - (current_time - self.last_z_adjust_time):.1f}s")
            return False
        
        # 限制单次调整幅度（用户建议不超过0.2mm）
        delta = np.clip(delta, -0.2, 0.2)
        
        # 计算新的累积调整量
        new_cumulative = self.z_offset_cumulative + delta
        
        # 限制总范围
        if not (-0.5 <= new_cumulative <= 0.5):
            print(f"Z调整超出安全范围 [-0.5, +0.5]，拒绝调整")
            return False
        
        # 发送调整
        if self.send_gcode(f"M290 Z{delta:.3f}"):
            self.z_offset_cumulative = new_cumulative
            self.current_values[ParameterType.Z_OFFSET] = new_cumulative
            self.last_z_adjust_time = current_time
            print(f"Z轴增量调整: {delta:+.3f}mm, 新累积量: {new_cumulative:+.3f}mm")
            return True
        return False
    
    def get_z_offset_status(self) -> dict:
        """获取Z-offset当前状态"""
        return {
            "cumulative": self.z_offset_cumulative,  # 累积调整量
            "initial": -2.55,  # 初始值（调平时的基准）
            "estimated_current": -2.55 + self.z_offset_cumulative,  # 估算的当前M851值
            "last_adjust_time": self.last_z_adjust_time,
            "cooldown_remaining": max(0, self.z_adjust_cooldown - (time.time() - self.last_z_adjust_time))
        }
    
    def set_hotend_temp(self, temp: float) -> bool:
        """设置热端温度 M104"""
        temp = np.clip(temp, 180, 260)
        if self.send_gcode(f"M104 S{int(temp)}"):
            self.current_values[ParameterType.HOTEND_TEMP] = temp
            print(f"热端温度设置为: {temp}°C")
            return True
        return False
    
    def get_printer_status(self) -> Optional[Dict]:
        """获取打印机状态"""
        try:
            url = f"{self.base_url}/api/printer"
            response = requests.get(url, headers=self.headers, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"获取打印机状态失败: {e}")
        return None

class ClosedLoopController:
    """
    闭环控制器主类
    
    整合所有算法模块，实现完整的闭环控制流程
    """
    def __init__(self, config: Optional[ClosedLoopConfig] = None):
        self.config = config or ClosedLoopConfig()
        
        # 初始化各模块
        self.buffers: Dict[ParameterType, StateSequenceBuffer] = {
            param: StateSequenceBuffer(self.config) 
            for param in ParameterType
        }
        self.triggers: Dict[ParameterType, SchmittTrigger] = {
            param: SchmittTrigger(self.config) 
            for param in ParameterType
        }
        self.scheduler = AdaptiveGainScheduler(self.config)
        self.octoprint = OctoPrintClient()
        
        # 参数-缺陷映射（表3-1）
        # 注意：Z_OFFSET 使用特殊的增量调整函数 adjust_z_offset
        self.param_adjustment_map = {
            # (诊断参数, 状态) -> (调节方向, G-code函数)
            (ParameterType.FLOW_RATE, ParameterState.LOW): 
                (1, self.octoprint.set_flow_rate),
            (ParameterType.FLOW_RATE, ParameterState.HIGH): 
                (-1, self.octoprint.set_flow_rate),
            (ParameterType.FEED_RATE, ParameterState.LOW): 
                (1, self.octoprint.set_feed_rate),
            (ParameterType.FEED_RATE, ParameterState.HIGH): 
                (-1, self.octoprint.set_feed_rate),
            (ParameterType.Z_OFFSET, ParameterState.LOW): 
                (+0.1, self.octoprint.adjust_z_offset),  # 增加0.1mm（抬高喷嘴）
            (ParameterType.Z_OFFSET, ParameterState.HIGH): 
                (-0.1, self.octoprint.adjust_z_offset),  # 减少0.1mm（降低喷嘴）
            (ParameterType.HOTEND_TEMP, ParameterState.LOW): 
                (1, self.octoprint.set_hotend_temp),
            (ParameterType.HOTEND_TEMP, ParameterState.HIGH): 
                (-1, self.octoprint.set_hotend_temp),
        }
        
        # 上次控制时间
        self.last_control_time = 0.0
        
        # 控制日志
        self.control_log: List[Dict] = []
        
        # 设备健康状态回调（用于更新SLM设备健康状态）
        self._health_status_callback: Optional[Callable[[int, List[str]], None]] = None
        
        # 当前诊断状态码（用于跟踪状态变化）
        self._current_diagnosis_code: int = 0
        self._diagnosis_history: deque = deque(maxlen=10)  # 最近10次诊断结果
    
    def set_health_status_callback(self, callback: Callable[[int, List[str]], None]):
        """
        设置设备健康状态回调函数
        
        Args:
            callback: 回调函数，参数为 (status_code: int, labels: List[str])
                     status_code: -1=未开机, 0=健康, 1=刮刀磨损, 2=激光异常, 3=气体异常, 4=复合故障
        """
        self._health_status_callback = callback
        print(f"[ClosedLoopController] 健康状态回调已设置")
    
    def _update_health_status(self, status_code: int, labels: List[str] = None):
        """
        更新设备健康状态
        
        根据闭环调控的诊断结果，更新SLM设备健康状态码
        目前只诊断激光功率异常（状态码2）和正常（状态码0）
        """
        labels = labels or []
        
        # 记录诊断历史
        self._diagnosis_history.append({
            'status_code': status_code,
            'labels': labels,
            'timestamp': time.time()
        })
        
        # 如果状态发生变化，触发回调
        if status_code != self._current_diagnosis_code:
            self._current_diagnosis_code = status_code
            
            if self._health_status_callback:
                try:
                    self._health_status_callback(status_code, labels)
                    print(f"[ClosedLoopController] 健康状态已更新: 状态码={status_code}, 标签={labels}")
                except Exception as e:
                    print(f"[ClosedLoopController] 更新健康状态失败: {e}")
            else:
                print(f"[ClosedLoopController] 健康状态变化: 状态码={status_code}, 标签={labels} (未设置回调)")
        
    def process_prediction(self, predictions: Dict[ParameterType, Tuple[ParameterState, float]]):
        """
        处理新的预测结果
        
        Args:
            predictions: {参数类型: (状态, 置信度)}
        """
        current_time = time.time()
        
        # 添加到各参数的缓冲区
        for param, (state, confidence) in predictions.items():
            pred = PredictionResult(
                param=param,
                state=state,
                confidence=confidence,
                timestamp=current_time
            )
            self.buffers[param].add_prediction(pred)
        
        # 根据预测结果更新设备健康状态
        self._update_diagnosis_status(predictions)
            
        # 检查是否需要执行控制
        if current_time - self.last_control_time >= self.config.control_interval:
            self._evaluate_and_control()
            self.last_control_time = current_time
    
    def _update_diagnosis_status(self, predictions: Dict[ParameterType, Tuple[ParameterState, float]]):
        """
        根据预测结果更新诊断状态
        
        目前只诊断激光功率异常：
        - 如果激光功率状态为 LOW 或 HIGH，返回状态码 2（激光异常）
        - 如果激光功率状态为 NORMAL，返回状态码 0（健康）
        
        Args:
            predictions: {参数类型: (状态, 置信度)}
        """
        # 检查激光功率状态（这里假设激光功率对应 HOTEND_TEMP 或其他参数）
        # 实际使用时，可能需要根据具体的参数映射关系调整
        
        laser_related_params = [
            ParameterType.HOTEND_TEMP,  # 热端温度与激光功率相关
            # 可以添加其他与激光相关的参数
        ]
        
        has_laser_fault = False
        fault_labels = []
        
        for param in laser_related_params:
            if param in predictions:
                state, confidence = predictions[param]
                if state != ParameterState.NORMAL and confidence >= self.config.threshold_on:
                    has_laser_fault = True
                    fault_labels.append(f"{param.value}_{state.name}")
        
        # 根据诊断结果设置状态码
        if has_laser_fault:
            status_code = 2  # 激光异常
            labels = ["激光功率异常"] + fault_labels
        else:
            status_code = 0  # 健康
            labels = ["系统正常"]
        
        # 更新健康状态
        self._update_health_status(status_code, labels)
    
    def _evaluate_and_control(self):
        """评估状态并执行控制"""
        for param in ParameterType:
            buffer = self.buffers[param]
            trigger = self.triggers[param]
            
            # 跳过NORMAL状态
            # 计算非NORMAL状态的加权置信度
            for state in [ParameterState.LOW, ParameterState.HIGH]:
                confidence = buffer.calculate_weighted_confidence(state)
                
                # 施密特触发判断
                should_regulate = trigger.update(confidence)
                
                if should_regulate:
                    # 执行调控
                    self._execute_regulation(param, state, confidence)
                    break  # 一个参数只处理一个异常状态
                else:
                    # 如果置信度很低，重置触发器
                    if confidence < 0.2:
                        trigger.reset()
    
    def _execute_regulation(self, 
                           param: ParameterType, 
                           state: ParameterState,
                           confidence: float):
        """执行参数调节"""
        # 获取调节方向和执行函数
        key = (param, state)
        if key not in self.param_adjustment_map:
            return
            
        direction, control_func = self.param_adjustment_map[key]
        
        # 计算调节量
        adjustment = self.scheduler.calculate_adjustment(param, confidence, direction)
        
        # 获取当前值
        current_value = self.octoprint.current_values[param]
        
        # Z_OFFSET 特殊处理：使用增量调整（固定步长，不随置信度变化）
        if param == ParameterType.Z_OFFSET:
            # 对于Z偏移，使用adjust_z_offset进行增量调整
            # 使用固定的调整步长（±0.1mm），忽略 confidence 计算的调整量
            fixed_step = 0.1 if direction > 0 else -0.1
            success = self.octoprint.adjust_z_offset(fixed_step)
            new_value = current_value + fixed_step if success else current_value
        elif param == ParameterType.HOTEND_TEMP:
            # 温度使用特殊处理
            new_value = self.scheduler.calculate_temperature_adjustment(
                current_value, current_value + adjustment, confidence
            )
            success = control_func(new_value)
        else:
            new_value = current_value + adjustment
            success = control_func(new_value)
        
        if success:
            # 记录控制日志
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "parameter": param.value,
                "state": state.name,
                "confidence": confidence,
                "adjustment": adjustment,
                "old_value": current_value,
                "new_value": new_value,
            }
            self.control_log.append(log_entry)
            print(f"[闭环控制] {log_entry}")
    
    def get_status(self) -> Dict:
        """获取控制器状态"""
        status = {
            "buffers": {
                param.value: buf.get_sequence_statistics()
                for param, buf in self.buffers.items()
            },
            "triggers": {
                param.value: trig.is_active
                for param, trig in self.triggers.items()
            },
            "current_values": {
                param.value: val
                for param, val in self.octoprint.current_values.items()
            },
            "z_offset_detail": self.octoprint.get_z_offset_status(),  # Z-offset详细状态
            "recent_controls": self.control_log[-10:],  # 最近10条控制记录
            "diagnosis": {
                "current_status_code": self._current_diagnosis_code,
                "status_labels": self._diagnosis_history[-1]['labels'] if self._diagnosis_history else [],
                "history": list(self._diagnosis_history)
            }
        }
        return status
    
    def reset(self):
        """重置控制器状态"""
        for buf in self.buffers.values():
            buf.buffer.clear()
        for trig in self.triggers.values():
            trig.reset()
        self.control_log.clear()
        self._current_diagnosis_code = 0
        self._diagnosis_history.clear()
        # 重置时更新健康状态为正常
        self._update_health_status(0, ["系统重置"])

# 便捷函数：创建默认配置
def create_default_config() -> ClosedLoopConfig:
    """创建默认配置"""
    return ClosedLoopConfig()

def create_aggressive_config() -> ClosedLoopConfig:
    """创建激进配置（快速响应）"""
    return ClosedLoopConfig(
        buffer_size=5,           # 更短的缓冲
        forgetting_factor=0.9,   # 更快的遗忘
        threshold_on=0.6,        # 更低的触发阈值
        threshold_off=0.3,
        aggressive_factor=5.0,   # 更大的增益
        control_interval=0.5,    # 更短的控制间隔
    )

def create_conservative_config() -> ClosedLoopConfig:
    """创建保守配置（稳定优先）"""
    return ClosedLoopConfig(
        buffer_size=20,          # 更长的缓冲
        forgetting_factor=0.7,   # 更慢的遗忘
        threshold_on=0.8,        # 更高的触发阈值
        threshold_off=0.5,
        aggressive_factor=2.0,   # 更小的增益
        control_interval=2.0,    # 更长的控制间隔
    )

# 测试代码
if __name__ == "__main__":
    print("=== 闭环控制器测试 ===")
    
    # 创建配置
    config = create_default_config()
    print(f"\n配置参数:")
    print(f"  缓冲区大小: {config.buffer_size}")
    print(f"  遗忘因子: {config.forgetting_factor}")
    print(f"  开启阈值: {config.threshold_on}")
    print(f"  关闭阈值: {config.threshold_off}")
    
    # 创建控制器
    controller = ClosedLoopController(config)
    
    # 模拟预测序列（流量持续偏低）
    print("\n=== 模拟流量偏低场景 ===")
    
    # 正常状态
    for i in range(3):
        predictions = {
            ParameterType.FLOW_RATE: (ParameterState.NORMAL, 0.9),
        }
        controller.process_prediction(predictions)
        time.sleep(0.1)
    
    # 逐渐变为偏低
    for i in range(10):
        confidence = 0.4 + i * 0.05  # 逐渐增加的置信度
        predictions = {
            ParameterType.FLOW_RATE: (ParameterState.LOW, min(confidence, 0.95)),
        }
        controller.process_prediction(predictions)
        time.sleep(0.1)
    
    # 查看状态
    status = controller.get_status()
    print(f"\n控制器状态:")
    print(f"  流量缓冲区统计: {status['buffers']['flow_rate']}")
    print(f"  触发器状态: {status['triggers']}")
    print(f"  控制记录数: {len(status['recent_controls'])}")
    
    print("\n=== 测试完成 ===")
