"""
数据采集系统测试脚本
=====================
测试 DAQ (Data Acquisition) 系统的完整功能

使用方法:
    python test_daq.py [选项]

选项:
    --simulation, -s    使用模拟模式（不需要真实硬件）
    --duration, -d      采集持续时间（秒），默认 30 秒
    --save-dir          数据保存目录，默认 ./test_data
    --no-save          不保存数据，仅显示

示例:
    python test_daq.py --simulation --duration 60
    python test_daq.py -s -d 10 --no-save
"""

import os
import sys
import time
import signal
import argparse
from datetime import datetime
from typing import Optional

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class DAQTester:
    """DAQ 测试器"""
    
    def __init__(self, simulation_mode: bool = False, save_dir: str = "./test_data"):
        """
        初始化测试器
        
        Args:
            simulation_mode: 是否使用模拟模式
            save_dir: 数据保存目录
        """
        self.simulation_mode = simulation_mode
        self.save_dir = save_dir
        self.daq = None
        self.running = False
        self.frame_count = 0
        self.start_time = None
        
        # 创建保存目录
        if not simulation_mode:
            os.makedirs(save_dir, exist_ok=True)
            print(f"[信息] 数据将保存到: {os.path.abspath(save_dir)}")
    
    def setup_daq(self) -> bool:
        """
        设置 DAQ 系统
        
        Returns:
            bool: 设置是否成功
        """
        print("\n" + "="*60)
        print("步骤 1: 初始化 DAQ 系统")
        print("="*60)
        
        try:
            from core.data_acquisition import get_acquisition, AcquisitionConfig
            
            # 创建配置
            config = AcquisitionConfig(
                save_directory=self.save_dir,
                capture_fps=5.0,  # 5fps 用于测试
                enable_ids=not self.simulation_mode,
                enable_side_camera=not self.simulation_mode,
                enable_fotric=not self.simulation_mode,
                enable_vibration=False  # 振动传感器通常不需要
            )
            
            # 获取 DAQ 实例
            self.daq = get_acquisition(config)
            print("[OK] DAQ 实例创建成功")
            
            # 初始化（软初始化，不连接设备）
            if self.daq.initialize():
                print("[OK] DAQ 初始化成功")
            else:
                print("[ERROR] DAQ 初始化失败")
                return False
            
            # 如果是模拟模式，修改配置模拟数据
            if self.simulation_mode:
                print("\n[模拟模式] 启用模拟数据生成")
                self._setup_simulation()
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 设置失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _setup_simulation(self):
        """设置模拟数据生成"""
        # 在模拟模式下，我们手动设置一些参数来模拟真实数据
        self.daq.config.flow_rate = 100
        self.daq.config.feed_rate = 100
        self.daq.config.z_offset = 0.0
        self.daq.config.target_hotend = 200
    
    def connect_devices(self) -> bool:
        """
        连接所有设备
        
        Returns:
            bool: 连接是否成功
        """
        print("\n" + "="*60)
        print("步骤 2: 连接传感器设备")
        print("="*60)
        
        if self.simulation_mode:
            print("[模拟模式] 跳过设备连接，使用模拟数据")
            # 在模拟模式下，手动创建一些模拟状态
            self.daq._current_position = {"X": 100.0, "Y": 100.0, "Z": 5.0, "E": 0.0}
            return True
        
        print("正在连接设备...")
        print("  - 旁轴摄像头 (Side Camera)")
        print("  - IDS 工业相机 (IDS Camera)")
        print("  - Fotric 红外相机 (Thermal Camera)")
        print("  - M114 坐标获取 (Printer Position)")
        print()
        
        try:
            # 初始化设备
            results = self.daq.initialize_devices()
            
            # 显示结果
            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)
            
            print(f"\n连接结果: {success_count}/{total_count} 个设备成功")
            print("-" * 40)
            for device, status in results.items():
                icon = "[OK]" if status else "[ERROR]"
                print(f"  {icon} {device}: {'已连接' if status else '未连接'}")
            
            # 只要有一个设备成功就继续
            if success_count > 0:
                print("\n[OK] 设备连接完成")
                return True
            else:
                print("\n[ERROR] 没有可用设备")
                print("\n[建议]")
                print("  1. 检查设备是否正确连接")
                print("  2. 检查设备电源是否开启")
                print("  3. 使用 --simulation 参数运行模拟模式")
                return False
                
        except Exception as e:
            print(f"[ERROR] 连接失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_acquisition(self) -> bool:
        """
        启动数据采集
        
        Returns:
            bool: 启动是否成功
        """
        print("\n" + "="*60)
        print("步骤 3: 启动数据采集")
        print("="*60)
        
        try:
            # 启动采集
            if self.daq.start():
                print("[OK] 数据采集已启动")
                self.running = True
                self.start_time = time.time()
                return True
            else:
                print("[ERROR] 启动失败")
                return False
                
        except Exception as e:
            print(f"[ERROR] 启动异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def monitor_loop(self, duration: int = 30, no_save: bool = False):
        """
        监控循环
        
        Args:
            duration: 采集持续时间（秒）
            no_save: 是否不保存数据
        """
        print("\n" + "="*60)
        print(f"步骤 4: 数据采集监控 ({duration}秒)")
        print("="*60)
        print("[提示] 按 Ctrl+C 可随时停止\n")
        
        # 信号处理，支持 Ctrl+C 优雅退出
        def signal_handler(sig, frame):
            print("\n[用户中断] 正在停止...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            last_frame_count = 0
            last_print_time = time.time()
            print_count = 0
            
            while self.running and (time.time() - self.start_time) < duration:
                # 获取当前状态
                status = self.daq.get_status()
                current_time = time.time()
                elapsed = current_time - self.start_time
                
                # 每 5 秒打印一次状态（减少日志输出）
                if current_time - last_print_time >= 5.0:
                    fps = (status['frame_count'] - last_frame_count) / (current_time - last_print_time)
                    print_count += 1
                    
                    # 打印状态行
                    print(f"[{elapsed:5.1f}s] Frame:{status['frame_count']:4d} FPS:{fps:4.1f}")
                    
                    # 每 10 秒打印一次传感器数据（更少）
                    if print_count % 2 == 1:
                        self._print_sensor_data()
                    
                    last_frame_count = status['frame_count']
                    last_print_time = current_time
                
                # 模拟模式下，手动生成一些数据
                if self.simulation_mode:
                    self._generate_simulation_data()
                
                time.sleep(0.1)
            
            # 正常结束
            if time.time() - self.start_time >= duration:
                print(f"\n[OK] 采集完成，共运行 {duration} 秒")
            
        except KeyboardInterrupt:
            print("\n[中断] 用户取消采集")
        
        except Exception as e:
            print(f"\n[ERROR] 采集异常: {e}")
            import traceback
            traceback.print_exc()
    
    def _print_sensor_data(self):
        """打印传感器数据（精简版）"""
        try:
            # 获取位置信息（从缓存的最新位置）
            if hasattr(self.daq, '_current_position'):
                pos = self.daq._current_position
                x = pos.get('X', 0)
                y = pos.get('Y', 0)
                z = pos.get('Z', 0)
            else:
                x = y = z = 0
            
            # 获取实际温度（通过 API）
            printer_status = self.daq._get_printer_status()
            actual_hotend = printer_status.get('hotend', 0)
            actual_bed = printer_status.get('bed', 0)
            
            # 单行输出所有关键信息
            print(f"  [POS] X={x:.1f} Y={y:.1f} Z={z:.1f} | "
                  f"[PARAM] F={self.daq.config.flow_rate}% S={self.daq.config.feed_rate}% Z={self.daq.config.z_offset:.2f} | "
                  f"[TEMP] {actual_hotend:.0f}°C/{self.daq.config.target_hotend}°C")
            
        except Exception as e:
            pass  # 忽略打印错误
    
    def _generate_simulation_data(self):
        """生成模拟数据"""
        import numpy as np
        
        # 模拟位置变化
        if hasattr(self.daq, '_current_position'):
            import random
            self.daq._current_position['X'] += random.uniform(-0.5, 0.5)
            self.daq._current_position['Y'] += random.uniform(-0.5, 0.5)
        
        # 模拟帧计数增加
        self.daq.frame_count += 1
    
    def stop_acquisition(self):
        """停止数据采集"""
        print("\n" + "="*60)
        print("步骤 5: 停止数据采集")
        print("="*60)
        
        try:
            if self.daq:
                self.daq.stop()
                print("[OK] 数据采集已停止")
                
                # 打印最终统计
                status = self.daq.get_status()
                duration = status['duration']
                frame_count = status['frame_count']
                avg_fps = frame_count / duration if duration > 0 else 0
                
                print("\n采集统计:")
                print(f"  持续时间: {duration:.1f} 秒")
                print(f"  总帧数: {frame_count}")
                print(f"  平均帧率: {avg_fps:.2f} FPS")
                
                if not self.simulation_mode and self.save_dir:
                    print(f"\n  数据保存位置: {os.path.abspath(self.save_dir)}")
        
        except Exception as e:
            print(f"[ERROR] 停止失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        print("\n" + "="*60)
        print("步骤 6: 清理资源")
        print("="*60)
        
        try:
            if self.daq:
                # 关闭设备
                self.daq._close_devices()
                print("[OK] 设备已关闭")
        
        except Exception as e:
            print(f"[ERROR] 清理失败: {e}")
    
    def run(self, duration: int = 30, no_save: bool = False) -> bool:
        """
        运行完整测试
        
        Args:
            duration: 采集持续时间
            no_save: 是否不保存数据
            
        Returns:
            bool: 测试是否成功
        """
        # 参数校验
        if duration <= 0:
            print(f"[ERROR] 持续时间必须大于 0，当前值: {duration}")
            print("[提示] 示例: python test_daq.py --duration 30")
            return False
        
        print("="*60)
        print("SmartAM 数据采集系统测试")
        print("="*60)
        print(f"模式: {'模拟' if self.simulation_mode else '真实设备'}")
        print(f"持续时间: {duration} 秒")
        print(f"保存数据: {'否' if no_save else '是'}")
        if not no_save and not self.simulation_mode:
            print(f"保存目录: {self.save_dir}")
        print()
        
        # 步骤 1: 设置 DAQ
        if not self.setup_daq():
            return False
        
        # 步骤 2: 连接设备
        if not self.connect_devices():
            return False
        
        # 步骤 3: 启动采集
        if not self.start_acquisition():
            return False
        
        # 步骤 4: 监控循环
        self.monitor_loop(duration, no_save)
        
        # 步骤 5: 停止采集
        self.stop_acquisition()
        
        # 步骤 6: 清理
        self.cleanup()
        
        print("\n" + "="*60)
        print("测试完成！")
        print("="*60)
        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='SmartAM 数据采集系统测试工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用模拟模式测试 30 秒
  python test_daq.py --simulation
  
  # 使用真实设备测试 60 秒
  python test_daq.py --duration 60
  
  # 模拟模式，不保存数据，测试 10 秒
  python test_daq.py -s -d 10 --no-save
        """
    )
    
    parser.add_argument('--simulation', '-s', 
                        action='store_true',
                        help='使用模拟模式（不需要真实硬件）')
    
    parser.add_argument('--duration', '-d', 
                        type=int, 
                        default=30,
                        metavar='SEC',
                        help='采集持续时间（秒），必须大于 0，默认 30 秒')
    
    parser.add_argument('--save-dir', 
                        type=str, 
                        default='./test_data',
                        help='数据保存目录，默认 ./test_data')
    
    parser.add_argument('--no-save', 
                        action='store_true',
                        help='不保存数据，仅显示')
    
    args = parser.parse_args()
    
    # 运行测试
    tester = DAQTester(
        simulation_mode=args.simulation,
        save_dir=args.save_dir
    )
    
    success = tester.run(
        duration=args.duration,
        no_save=args.no_save
    )
    
    # 退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
