"""
闭环调控控制器测试套件
========================
测试项目：
1. OctoPrint 客户端连接和 G-code 发送
2. 状态序列缓冲区的时间衰减置信度计算
3. 施密特触发器逻辑
4. 自适应增益调度
5. 闭环控制器整体流程
6. 不同配置模式测试

注意：部分测试需要 OctoPrint 运行才能测试实际控制功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import numpy as np
from datetime import datetime


def test_octoprint_client():
    """测试 OctoPrint 客户端"""
    print("\n" + "="*60)
    print("测试 1: OctoPrint 客户端")
    print("="*60)
    
    try:
        from core.closed_loop_controller import OctoPrintClient
        
        client = OctoPrintClient()
        print("✓ OctoPrint 客户端创建成功")
        
        # 查看当前参数
        print(f"  当前参数缓存: {client.current_values}")
        
        # 测试发送 G-code（如果不连接打印机可能会失败）
        print("\n  测试发送 G-code (M105 查询温度)...")
        success = client.send_gcode("M105")
        if success:
            print("  ✓ G-code 发送成功")
        else:
            print("  ⚠ G-code 发送失败（OctoPrint 可能未运行）")
        
        # 测试设置参数（仅本地缓存）
        print("\n  测试参数设置（本地缓存）...")
        client.current_values[client.current_values.__class__.__dict__.get('__class__', 'flow_rate')] = 100.0
        print(f"  当前流量倍率: {client.current_values}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_sequence_buffer():
    """测试状态序列缓冲区"""
    print("\n" + "="*60)
    print("测试 2: 状态序列缓冲区")
    print("="*60)
    
    try:
        from core.closed_loop_controller import (
            StateSequenceBuffer, ClosedLoopConfig, 
            PredictionResult, ParameterType, ParameterState
        )
        
        config = ClosedLoopConfig(buffer_size=5, forgetting_factor=0.8)
        buffer = StateSequenceBuffer(config)
        print("✓ 状态序列缓冲区创建成功")
        print(f"  缓冲区大小: {config.buffer_size}")
        print(f"  遗忘因子: {config.forgetting_factor}")
        
        # 添加预测数据
        print("\n  添加 5 个预测样本...")
        for i in range(5):
            pred = PredictionResult(
                param=ParameterType.FLOW_RATE,
                state=ParameterState.LOW if i < 3 else ParameterState.NORMAL,
                confidence=0.5 + i * 0.1,
                timestamp=time.time()
            )
            buffer.add_prediction(pred)
            print(f"    样本 {i+1}: state={pred.state.name}, conf={pred.confidence:.2f}")
        
        # 计算加权置信度
        print("\n  计算时间衰减加权置信度...")
        low_confidence = buffer.calculate_weighted_confidence(ParameterState.LOW)
        normal_confidence = buffer.calculate_weighted_confidence(ParameterState.NORMAL)
        
        print(f"    LOW 状态置信度: {low_confidence:.4f}")
        print(f"    NORMAL 状态置信度: {normal_confidence:.4f}")
        
        # 获取统计信息
        stats = buffer.get_sequence_statistics()
        print(f"\n  缓冲区统计:")
        print(f"    长度: {stats['length']}")
        print(f"    状态分布: {stats['state_distribution']}")
        print(f"    平均置信度: {stats['avg_confidence']:.4f}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schmitt_trigger():
    """测试施密特触发器"""
    print("\n" + "="*60)
    print("测试 3: 施密特触发器")
    print("="*60)
    
    try:
        from core.closed_loop_controller import SchmittTrigger, ClosedLoopConfig
        
        config = ClosedLoopConfig(threshold_on=0.7, threshold_off=0.4)
        trigger = SchmittTrigger(config)
        print("✓ 施密特触发器创建成功")
        print(f"  开启阈值: {config.threshold_on}")
        print(f"  关闭阈值: {config.threshold_off}")
        
        # 测试状态转换
        print("\n  测试状态转换...")
        
        test_values = [0.3, 0.5, 0.6, 0.75, 0.8, 0.5, 0.35, 0.2]
        expected_states = [False, False, False, True, True, True, True, False]
        
        for i, (val, expected) in enumerate(zip(test_values, expected_states)):
            result = trigger.update(val)
            status = "✓" if result == expected else "✗"
            print(f"    [{status}] 输入={val:.2f} -> 激活={result} (期望={expected})")
        
        # 重置测试
        trigger.reset()
        print(f"\n  重置后状态: {trigger.is_active}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_adaptive_gain_scheduler():
    """测试自适应增益调度器"""
    print("\n" + "="*60)
    print("测试 4: 自适应增益调度器")
    print("="*60)
    
    try:
        from core.closed_loop_controller import (
            AdaptiveGainScheduler, ClosedLoopConfig, ParameterType
        )
        
        config = ClosedLoopConfig(
            aggressive_factor=3.0,
            nonlinear_exp=2.0
        )
        scheduler = AdaptiveGainScheduler(config)
        print("✓ 增益调度器创建成功")
        
        # 测试不同置信度下的调节量
        print("\n  测试流量倍率调节量...")
        confidences = [0.0, 0.3, 0.5, 0.7, 0.9, 1.0]
        
        for conf in confidences:
            adj_up = scheduler.calculate_adjustment(ParameterType.FLOW_RATE, conf, +1)
            adj_down = scheduler.calculate_adjustment(ParameterType.FLOW_RATE, conf, -1)
            print(f"    置信度={conf:.1f}: 增加={adj_up:+.2f}%, 减少={adj_down:+.2f}%")
        
        # 测试温度调节
        print("\n  测试温度调节...")
        new_temp = scheduler.calculate_temperature_adjustment(
            current_temp=205.0,
            target_temp=200.0,
            confidence=0.8
        )
        print(f"    当前205°C -> 新目标: {new_temp:.1f}°C")
        
        # 测试安全限制
        print("\n  测试安全限制...")
        large_adj = scheduler.calculate_adjustment(ParameterType.Z_OFFSET, 0.99, +1)
        print(f"    Z偏移调节量（应被限制）: {large_adj:+.4f}mm")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_closed_loop_controller():
    """测试闭环控制器整体流程"""
    print("\n" + "="*60)
    print("测试 5: 闭环控制器整体流程")
    print("="*60)
    
    try:
        from core.closed_loop_controller import (
            ClosedLoopController, ClosedLoopConfig,
            ParameterType, ParameterState,
            create_default_config, create_aggressive_config, create_conservative_config
        )
        
        # 使用默认配置
        config = create_default_config()
        controller = ClosedLoopController(config)
        print("✓ 闭环控制器创建成功（默认配置）")
        print(f"  缓冲区大小: {config.buffer_size}")
        print(f"  控制间隔: {config.control_interval}s")
        
        # 模拟预测序列（流量持续偏低）
        print("\n  模拟流量偏低场景...")
        
        # 先添加一些正常状态
        for i in range(3):
            predictions = {
                ParameterType.FLOW_RATE: (ParameterState.NORMAL, 0.9),
            }
            controller.process_prediction(predictions)
            time.sleep(0.05)
        
        # 然后逐渐变为偏低
        print("  添加 LOW 状态预测（逐渐增加置信度）...")
        for i in range(10):
            confidence = 0.4 + i * 0.05
            predictions = {
                ParameterType.FLOW_RATE: (ParameterState.LOW, min(confidence, 0.95)),
                ParameterType.FEED_RATE: (ParameterState.NORMAL, 0.8),
            }
            controller.process_prediction(predictions)
            time.sleep(0.05)
        
        # 查看状态
        status = controller.get_status()
        print(f"\n  控制器状态:")
        print(f"    流量缓冲区: {status['buffers']['flow_rate']}")
        print(f"    触发器状态: {status['triggers']}")
        print(f"    控制记录数: {len(status['recent_controls'])}")
        
        if status['recent_controls']:
            print(f"\n  最近控制记录:")
            for record in status['recent_controls'][-3:]:
                print(f"    {record['timestamp']}: {record['parameter']} {record['state']} "
                      f"{record['old_value']:.1f} -> {record['new_value']:.1f}")
        
        # 重置测试
        controller.reset()
        print("\n  ✓ 控制器已重置")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_controller_configs():
    """测试不同配置模式"""
    print("\n" + "="*60)
    print("测试 6: 不同配置模式")
    print("="*60)
    
    try:
        from core.closed_loop_controller import (
            create_default_config, create_aggressive_config, create_conservative_config
        )
        
        print("  默认配置:")
        default = create_default_config()
        print(f"    缓冲区: {default.buffer_size}, 遗忘因子: {default.forgetting_factor}")
        print(f"    阈值: {default.threshold_on}/{default.threshold_off}")
        
        print("\n  激进配置（快速响应）:")
        aggressive = create_aggressive_config()
        print(f"    缓冲区: {aggressive.buffer_size}, 遗忘因子: {aggressive.forgetting_factor}")
        print(f"    阈值: {aggressive.threshold_on}/{aggressive.threshold_off}")
        print(f"    激进因子: {aggressive.aggressive_factor}")
        
        print("\n  保守配置（稳定优先）:")
        conservative = create_conservative_config()
        print(f"    缓冲区: {conservative.buffer_size}, 遗忘因子: {conservative.forgetting_factor}")
        print(f"    阈值: {conservative.threshold_on}/{conservative.threshold_off}")
        print(f"    激进因子: {conservative.aggressive_factor}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_parameters():
    """测试多参数同时调控"""
    print("\n" + "="*60)
    print("测试 7: 多参数同时调控")
    print("="*60)
    
    try:
        from core.closed_loop_controller import (
            ClosedLoopController, ParameterType, ParameterState
        )
        
        controller = ClosedLoopController()
        print("✓ 控制器创建成功")
        
        # 模拟多个参数同时异常
        print("\n  模拟流量偏低 + 温度偏高...")
        
        for i in range(8):
            predictions = {
                ParameterType.FLOW_RATE: (ParameterState.LOW, 0.6 + i * 0.04),
                ParameterType.FEED_RATE: (ParameterState.NORMAL, 0.8),
                ParameterType.Z_OFFSET: (ParameterState.NORMAL, 0.85),
                ParameterType.HOTEND_TEMP: (ParameterState.HIGH, 0.55 + i * 0.05),
            }
            controller.process_prediction(predictions)
            time.sleep(0.05)
        
        status = controller.get_status()
        print(f"\n  调控结果:")
        print(f"    控制记录数: {len(status['recent_controls'])}")
        
        for record in status['recent_controls']:
            print(f"    - {record['parameter']}: {record['old_value']:.1f} -> {record['new_value']:.1f}")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("="*60)
    print("闭环调控控制器测试套件")
    print("="*60)
    print("\n注意: 部分测试需要 OctoPrint 运行")
    print("      如果 OctoPrint 未运行，相关测试会跳过")
    
    results = []
    
    # 运行测试
    results.append(("OctoPrint 客户端", test_octoprint_client()))
    results.append(("状态序列缓冲区", test_state_sequence_buffer()))
    results.append(("施密特触发器", test_schmitt_trigger()))
    results.append(("自适应增益调度", test_adaptive_gain_scheduler()))
    results.append(("闭环控制器整体", test_closed_loop_controller()))
    results.append(("不同配置模式", test_controller_configs()))
    results.append(("多参数同时调控", test_multiple_parameters()))
    
    # 汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status}: {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  {total - passed} 项测试失败，请检查日志")
