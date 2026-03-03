"""
SLM 控制模块测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from core.slm_control import PIDController, SLMController, SLMParameters, SensorData


def test_pid_controller():
    """测试 PID 控制器"""
    pid = PIDController(kp=1.0, ki=0.1, kd=0.01)
    
    # 测试阶跃响应
    setpoint = 100.0
    measurement = 80.0
    
    outputs = []
    for _ in range(10):
        output = pid.update(setpoint, measurement)
        outputs.append(output)
        measurement += output * 0.1  # 模拟系统响应
    
    print(f"PID 输出序列: {outputs}")
    print("✓ PID 控制器测试通过")


def test_slm_controller():
    """测试 SLM 控制器"""
    params = SLMParameters(laser_power=200, scan_speed=800)
    controller = SLMController(initial_params=params)
    
    # 测试参数更新
    controller.update_parameters({"laser_power": 250})
    assert controller.params.laser_power == 250
    
    # 测试传感器数据处理
    import time
    sensor_data = SensorData(
        timestamp=time.time(),
        melt_pool_temp=1400
    )
    
    result = controller.process_sensor_data(sensor_data)
    print(f"控制决策: {result}")
    
    # 测试缺陷处理
    defect_result = controller.process_defect_prediction(0.9, "porosity")
    print(f"缺陷处理: {defect_result}")
    
    print("✓ SLM 控制器测试通过")


if __name__ == "__main__":
    test_pid_controller()
    test_slm_controller()
    print("\n所有测试通过！")
