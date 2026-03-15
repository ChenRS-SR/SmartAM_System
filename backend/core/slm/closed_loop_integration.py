"""
闭环控制与SLM设备健康状态集成模块
====================================

将闭环控制器的诊断结果同步到SLM设备健康状态系统

功能：
1. 监听闭环控制器的诊断结果
2. 将诊断结果转换为设备健康状态码
3. 更新SLM采集系统的健康状态

状态码映射：
- -1: 未开机
-  0: 健康
-  1: 刮刀磨损（铺粉系统异常）
-  2: 激光功率异常
-  3: 保护气体异常
-  4: 复合故障
"""

import time
from typing import Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DiagnosisToHealthMapping:
    """诊断结果到健康状态的映射配置"""
    
    # 参数类型到状态码的映射
    # 目前闭环系统主要诊断激光相关参数
    param_to_status_code: dict = field(default_factory=lambda: {
        'hotend_temp': 2,      # 热端温度异常 -> 激光功率异常
        'flow_rate': 1,        # 流量异常 -> 铺粉系统异常
        'feed_rate': 1,        # 速度异常 -> 铺粉系统异常
        'z_offset': 1,         # Z偏移异常 -> 铺粉系统异常
    })
    
    # 状态码到标签的映射
    status_code_to_label: dict = field(default_factory=lambda: {
        -1: '未开机',
        0: '健康',
        1: '刮刀磨损',
        2: '激光功率异常',
        3: '保护气体异常',
        4: '复合故障',
    })


class ClosedLoopHealthIntegration:
    """
    闭环控制与设备健康状态集成器
    
    负责将闭环控制器的诊断结果同步到SLM设备健康状态
    """
    
    def __init__(self, mapping: Optional[DiagnosisToHealthMapping] = None):
        self.mapping = mapping or DiagnosisToHealthMapping()
        
        # 健康状态更新回调
        self._health_update_callback: Optional[Callable[[int, List[str]], None]] = None
        
        # 当前状态
        self._current_status_code: int = -1
        self._current_labels: List[str] = []
        
        # 状态历史
        self._status_history: List[dict] = []
        self._max_history_size: int = 100
        
        print("[ClosedLoopHealthIntegration] 集成器已初始化")
    
    def set_health_update_callback(self, callback: Callable[[int, List[str]], None]):
        """
        设置健康状态更新回调
        
        Args:
            callback: 回调函数，参数为 (status_code: int, labels: List[str])
        """
        self._health_update_callback = callback
        print("[ClosedLoopHealthIntegration] 健康状态更新回调已设置")
    
    def on_closed_loop_diagnosis(self, param_type: str, param_state: str, confidence: float):
        """
        处理闭环控制器的诊断结果
        
        Args:
            param_type: 参数类型（如 'hotend_temp', 'flow_rate' 等）
            param_state: 参数状态（'LOW', 'NORMAL', 'HIGH'）
            confidence: 置信度（0-1）
        """
        # 如果状态正常，返回健康状态
        if param_state == 'NORMAL':
            self._update_health_status(0, ['系统正常'])
            return
        
        # 根据参数类型获取对应的状态码
        status_code = self.mapping.param_to_status_code.get(param_type, 2)
        
        # 生成状态标签
        label = self.mapping.status_code_to_label.get(status_code, '未知故障')
        detail_label = f"{param_type}_{param_state}"
        labels = [label, detail_label, f"置信度:{confidence:.2f}"]
        
        self._update_health_status(status_code, labels)
    
    def _update_health_status(self, status_code: int, labels: List[str]):
        """
        更新设备健康状态
        
        Args:
            status_code: 状态码（-1, 0, 1, 2, 3, 4）
            labels: 状态标签列表
        """
        # 记录历史
        self._status_history.append({
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'status_code': status_code,
            'labels': labels
        })
        
        # 限制历史记录大小
        if len(self._status_history) > self._max_history_size:
            self._status_history = self._status_history[-self._max_history_size:]
        
        # 如果状态发生变化，触发回调
        if status_code != self._current_status_code or labels != self._current_labels:
            self._current_status_code = status_code
            self._current_labels = labels.copy()
            
            if self._health_update_callback:
                try:
                    self._health_update_callback(status_code, labels)
                    print(f"[ClosedLoopHealthIntegration] 健康状态已更新: 状态码={status_code}, 标签={labels}")
                except Exception as e:
                    print(f"[ClosedLoopHealthIntegration] 更新健康状态失败: {e}")
            else:
                print(f"[ClosedLoopHealthIntegration] 健康状态变化: 状态码={status_code}, 标签={labels} (未设置回调)")
    
    def get_current_status(self) -> dict:
        """获取当前健康状态"""
        return {
            'status_code': self._current_status_code,
            'labels': self._current_labels,
            'status_label': self.mapping.status_code_to_label.get(
                self._current_status_code, '未知'
            )
        }
    
    def get_status_history(self, limit: int = 10) -> List[dict]:
        """获取状态历史记录"""
        return self._status_history[-limit:]
    
    def reset(self):
        """重置状态"""
        self._current_status_code = -1
        self._current_labels = []
        self._status_history.clear()
        print("[ClosedLoopHealthIntegration] 状态已重置")


# 全局集成器实例
_integration_instance: Optional[ClosedLoopHealthIntegration] = None


def get_closed_loop_health_integration() -> ClosedLoopHealthIntegration:
    """获取全局集成器实例（单例）"""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = ClosedLoopHealthIntegration()
    return _integration_instance


def reset_closed_loop_health_integration():
    """重置全局集成器实例"""
    global _integration_instance
    if _integration_instance is not None:
        _integration_instance.reset()
        _integration_instance = None
    print("[ClosedLoopHealthIntegration] 全局实例已重置")


def setup_closed_loop_to_slm_health_bridge(closed_loop_controller, slm_acquisition):
    """
    设置闭环控制器到SLM健康状态的桥接
    
    Args:
        closed_loop_controller: 闭环控制器实例
        slm_acquisition: SLM采集实例
    
    Returns:
        ClosedLoopHealthIntegration: 集成器实例
    """
    integration = get_closed_loop_health_integration()
    
    # 设置健康状态更新回调
    def health_update_callback(status_code: int, labels: List[str]):
        """健康状态更新回调"""
        if slm_acquisition and hasattr(slm_acquisition, 'update_health_status'):
            slm_acquisition.update_health_status(status_code, labels)
    
    integration.set_health_update_callback(health_update_callback)
    
    # 设置闭环控制器的健康状态回调
    if closed_loop_controller and hasattr(closed_loop_controller, 'set_health_status_callback'):
        def closed_loop_callback(status_code: int, labels: List[str]):
            """闭环控制器健康状态回调"""
            integration._update_health_status(status_code, labels)
        
        closed_loop_controller.set_health_status_callback(closed_loop_callback)
    
    print("[ClosedLoopHealthIntegration] 桥接已建立")
    return integration


# 便捷函数：直接根据诊断结果更新SLM健康状态
def update_slm_health_from_diagnosis(
    slm_acquisition,
    is_laser_fault: bool = False,
    is_powder_fault: bool = False,
    is_gas_fault: bool = False,
    confidence: float = 0.0
):
    """
    根据诊断结果直接更新SLM健康状态
    
    Args:
        slm_acquisition: SLM采集实例
        is_laser_fault: 是否激光异常
        is_powder_fault: 是否铺粉异常
        is_gas_fault: 是否气体异常
        confidence: 置信度
    """
    if slm_acquisition is None or not hasattr(slm_acquisition, 'update_health_status'):
        print("[ClosedLoopHealthIntegration] 警告: SLM采集实例不可用")
        return
    
    # 计算状态码
    fault_count = sum([is_laser_fault, is_powder_fault, is_gas_fault])
    
    if fault_count == 0:
        status_code = 0
        labels = ['系统正常']
    elif fault_count >= 2:
        status_code = 4
        labels = ['复合故障']
    elif is_laser_fault:
        status_code = 2
        labels = ['激光功率异常']
    elif is_powder_fault:
        status_code = 1
        labels = ['刮刀磨损']
    else:  # is_gas_fault
        status_code = 3
        labels = ['保护气体异常']
    
    if confidence > 0:
        labels.append(f"置信度:{confidence:.2f}")
    
    slm_acquisition.update_health_status(status_code, labels)
    print(f"[ClosedLoopHealthIntegration] SLM健康状态已更新: 状态码={status_code}, 标签={labels}")


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("闭环控制与SLM健康状态集成测试")
    print("=" * 60)
    
    integration = get_closed_loop_health_integration()
    
    # 模拟诊断结果
    test_cases = [
        ('hotend_temp', 'NORMAL', 0.9),
        ('hotend_temp', 'LOW', 0.8),
        ('hotend_temp', 'HIGH', 0.75),
        ('flow_rate', 'LOW', 0.7),
        ('hotend_temp', 'NORMAL', 0.95),
    ]
    
    print("\n模拟诊断结果:")
    for param, state, conf in test_cases:
        print(f"\n  参数: {param}, 状态: {state}, 置信度: {conf}")
        integration.on_closed_loop_diagnosis(param, state, conf)
        current = integration.get_current_status()
        print(f"  -> 当前状态: {current}")
    
    print("\n状态历史:")
    for record in integration.get_status_history():
        print(f"  {record}")
    
    print("\n" + "=" * 60)
    print("测试完成")
