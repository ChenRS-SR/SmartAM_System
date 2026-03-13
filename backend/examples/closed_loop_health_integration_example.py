"""
闭环控制与SLM设备健康状态集成示例
====================================

演示如何将闭环控制器的诊断结果同步到SLM设备健康状态

使用场景：
1. 启动SLM数据采集
2. 启动闭环控制器
3. 模拟诊断结果（激光功率异常/正常）
4. 观察设备健康状态的变化
"""

import sys
import time
from pathlib import Path

# 添加backend到路径
backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from core.closed_loop_controller import (
    ClosedLoopController, ParameterType, ParameterState,
    create_default_config
)
from core.slm.slm_acquisition import get_slm_acquisition
from core.slm.closed_loop_integration import (
    setup_closed_loop_to_slm_health_bridge,
    update_slm_health_from_diagnosis
)


def example_1_basic_integration():
    """示例1：基本的闭环控制与健康状态集成"""
    print("\n" + "=" * 60)
    print("示例1：基本的闭环控制与健康状态集成")
    print("=" * 60)
    
    # 1. 创建SLM采集实例（模拟模式）
    print("\n[1] 创建SLM采集实例...")
    slm_acquisition = get_slm_acquisition(use_mock=True)
    slm_acquisition.initialize()
    slm_acquisition.start()
    
    # 2. 创建闭环控制器
    print("\n[2] 创建闭环控制器...")
    config = create_default_config()
    controller = ClosedLoopController(config)
    
    # 3. 建立桥接
    print("\n[3] 建立闭环控制与SLM健康状态的桥接...")
    integration = setup_closed_loop_to_slm_health_bridge(controller, slm_acquisition)
    
    # 4. 模拟正常状态
    print("\n[4] 模拟正常状态...")
    for i in range(5):
        predictions = {
            ParameterType.HOTEND_TEMP: (ParameterState.NORMAL, 0.9),
        }
        controller.process_prediction(predictions)
        time.sleep(0.5)
        
        # 查看当前健康状态
        health = slm_acquisition._health_state.to_dict()
        print(f"  第{i+1}次 - 状态码: {health['status_code']}, 标签: {health['status_labels']}")
    
    # 5. 模拟激光功率异常（LOW）
    print("\n[5] 模拟激光功率异常（LOW）...")
    for i in range(5):
        confidence = 0.5 + i * 0.08  # 逐渐增加的置信度
        predictions = {
            ParameterType.HOTEND_TEMP: (ParameterState.LOW, min(confidence, 0.9)),
        }
        controller.process_prediction(predictions)
        time.sleep(0.5)
        
        health = slm_acquisition._health_state.to_dict()
        print(f"  第{i+1}次 - 状态码: {health['status_code']}, 标签: {health['status_labels']}")
    
    # 6. 恢复正常
    print("\n[6] 恢复正常状态...")
    for i in range(5):
        predictions = {
            ParameterType.HOTEND_TEMP: (ParameterState.NORMAL, 0.95),
        }
        controller.process_prediction(predictions)
        time.sleep(0.5)
        
        health = slm_acquisition._health_state.to_dict()
        print(f"  第{i+1}次 - 状态码: {health['status_code']}, 标签: {health['status_labels']}")
    
    # 7. 查看控制器状态
    print("\n[7] 闭环控制器状态:")
    status = controller.get_status()
    print(f"  当前诊断状态码: {status['diagnosis']['current_status_code']}")
    print(f"  诊断历史数: {len(status['diagnosis']['history'])}")
    
    # 清理
    slm_acquisition.stop()
    print("\n示例1完成")


def example_2_direct_update():
    """示例2：直接更新SLM健康状态"""
    print("\n" + "=" * 60)
    print("示例2：直接更新SLM健康状态")
    print("=" * 60)
    
    # 1. 创建SLM采集实例
    print("\n[1] 创建SLM采集实例...")
    slm_acquisition = get_slm_acquisition(use_mock=True)
    slm_acquisition.initialize()
    slm_acquisition.start()
    
    # 2. 模拟各种诊断结果
    test_cases = [
        (False, False, False, 0.0, "正常"),
        (True, False, False, 0.8, "激光异常"),
        (False, True, False, 0.7, "铺粉异常"),
        (False, False, True, 0.75, "气体异常"),
        (True, True, False, 0.85, "激光+铺粉异常"),
        (True, True, True, 0.9, "复合故障"),
        (False, False, False, 0.0, "恢复正常"),
    ]
    
    print("\n[2] 模拟各种诊断结果...")
    for is_laser, is_powder, is_gas, conf, desc in test_cases:
        print(f"\n  场景: {desc}")
        update_slm_health_from_diagnosis(
            slm_acquisition,
            is_laser_fault=is_laser,
            is_powder_fault=is_powder,
            is_gas_fault=is_gas,
            confidence=conf
        )
        
        health = slm_acquisition._health_state.to_dict()
        print(f"  -> 状态码: {health['status_code']}, 状态: {health['status']}")
        time.sleep(1)
    
    # 清理
    slm_acquisition.stop()
    print("\n示例2完成")


def example_3_api_usage():
    """示例3：API使用方式"""
    print("\n" + "=" * 60)
    print("示例3：API使用方式")
    print("=" * 60)
    
    print("""
在实际应用中，可以通过以下方式集成：

1. 在启动采集时，建立桥接：
   
   from core.slm.closed_loop_integration import setup_closed_loop_to_slm_health_bridge
   
   # 获取实例
   slm_acquisition = get_slm_acquisition(use_mock=True)
   controller = ClosedLoopController(config)
   
   # 建立桥接
   integration = setup_closed_loop_to_slm_health_bridge(controller, slm_acquisition)

2. 在诊断回调中更新状态：
   
   def on_diagnosis_result(diagnosis_result):
       # 直接更新SLM健康状态
       update_slm_health_from_diagnosis(
           slm_acquisition,
           is_laser_fault=diagnosis_result.get('is_laser_fault', False),
           confidence=diagnosis_result.get('confidence', 0)
       )

3. 前端获取健康状态：
   
   GET /slm/health/status
   
   返回：
   {
       "success": true,
       "health": {
           "status": "laser_fault",
           "status_code": 2,
           "status_labels": ["激光功率异常"],
           "laser_system": {"status": "fault", "message": "激光功率衰减或波动"},
           ...
       }
   }
""")


if __name__ == "__main__":
    print("=" * 60)
    print("闭环控制与SLM设备健康状态集成示例")
    print("=" * 60)
    
    try:
        example_1_basic_integration()
    except Exception as e:
        print(f"示例1出错: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        example_2_direct_update()
    except Exception as e:
        print(f"示例2出错: {e}")
        import traceback
        traceback.print_exc()
    
    example_3_api_usage()
    
    print("\n" + "=" * 60)
    print("所有示例完成")
    print("=" * 60)
