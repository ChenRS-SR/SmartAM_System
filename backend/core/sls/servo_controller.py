"""
SLS舵机控制模块
===============
ROBOIDE舵机控制板控制模块
通讯协议：ROBOIDE文本命令格式
波特率：9600
数据位：8
校验位：无
停止位：1

命令格式示例：
  #1P1500T100\r\n    - 舵机1移动到1500位置，耗时100ms
  #1P2500T500\r\n    - 舵机1移动到2500位置，耗时500ms

用于控制红外摄像头挡板：
  - 1500: 中间位置 - 挡板挡住红外摄像头（保护状态）
  - 2500: 开启位置 - 挡板移开，红外摄像头可以拍摄
"""

import serial
import time
import json
import os
import gc
import atexit
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class ServoPosition(Enum):
    """舵机预设位置"""
    CLOSED = 1500   # 关闭位置 - 挡板遮挡
    HALF = 2000     # 半开位置
    OPEN = 2500     # 开启位置 - 挡板移开


@dataclass
class ServoStatus:
    """舵机状态"""
    position: int = 1500
    target: int = 1500
    is_open: bool = False
    is_moving: bool = False
    is_connected: bool = False


# 全局串口实例列表，用于程序退出时强制清理
_global_servo_controllers = []


def _cleanup_all_servos():
    """程序退出时强制清理所有串口"""
    print("\n[Servo] 程序退出，强制清理所有舵机串口...")
    for controller in _global_servo_controllers:
        try:
            controller.force_disconnect()
        except:
            pass
    gc.collect()
    time.sleep(0.5)
    print("[Servo] 清理完成")


# 注册程序退出时的清理函数
atexit.register(_cleanup_all_servos)


class ServoController:
    """ROBOIDE舵机控制类"""
    
    def __init__(self, port: str = 'COM16', baudrate: int = 9600, servo_id: int = 1):
        """
        初始化舵机控制器
        
        Args:
            port: 串口名称 (默认COM16)
            baudrate: 波特率 (ROBOIDE默认9600)
            servo_id: 舵机ID (默认1)
        """
        self.port = port
        self.baudrate = baudrate
        self.servo_id = servo_id
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        self.status = ServoStatus()
        
        # 注册到全局列表
        _global_servo_controllers.append(self)
    
    def connect(self, max_retries: int = 3) -> bool:
        """
        建立串口连接（带重试机制）
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            bool: 连接是否成功
        """
        # 如果已经连接，先断开
        if self.is_connected and self.ser:
            print(f"[Servo] 已经连接，先断开再重新连接...")
            self.disconnect()
            time.sleep(1.0)
        
        for attempt in range(max_retries):
            try:
                print(f"[Servo] 连接尝试 {attempt + 1}/{max_retries}...")
                
                if attempt > 0:
                    wait_time = 2.0 + attempt
                    print(f"[Servo] 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    time.sleep(0.5)
                
                gc.collect()
                
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                    write_timeout=1
                )
                self.is_connected = True
                self.status.is_connected = True
                print(f"[Servo] 成功连接到 {self.port}，波特率: {self.baudrate}")
                
                # 初始化舵机位置
                self.move_to_position(ServoPosition.CLOSED.value, duration=100)
                return True
                
            except PermissionError as e:
                print(f"[Servo] 连接失败 (尝试 {attempt + 1}): 拒绝访问 - COM口被占用")
                self.is_connected = False
                self.status.is_connected = False
                
            except serial.SerialException as e:
                error_msg = str(e)
                if "系统资源不足" in error_msg:
                    print(f"[Servo] 连接失败 (尝试 {attempt + 1}): 系统资源不足")
                else:
                    print(f"[Servo] 连接失败 (尝试 {attempt + 1}): {e}")
                self.is_connected = False
                self.status.is_connected = False
                
            except Exception as e:
                print(f"[Servo] 连接失败 (尝试 {attempt + 1}): 未知错误 - {e}")
                self.is_connected = False
                self.status.is_connected = False
        
        return False
    
    def disconnect(self) -> None:
        """断开串口连接"""
        if not self.ser:
            return
        
        port_name = self.port
        
        try:
            if self.ser.is_open:
                # 清空缓冲区
                try:
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                except:
                    pass
                
                time.sleep(0.1)
                
                # 关闭串口
                try:
                    self.ser.close()
                    print(f"[Servo] 串口已关闭 {port_name}")
                except Exception as e:
                    print(f"[Servo] 关闭串口时出错: {e}")
        except Exception as e:
            print(f"[Servo] 断开连接时出错: {e}")
        finally:
            self.ser = None
            self.is_connected = False
            self.status.is_connected = False
            gc.collect()
        
        time.sleep(1.0)
    
    def force_disconnect(self) -> None:
        """强制断开连接 - 用于异常情况"""
        print(f"[Servo] 强制断开串口 {self.port}")
        try:
            if self.ser:
                if hasattr(self.ser, 'close'):
                    self.ser.close()
        except:
            pass
        finally:
            self.ser = None
            self.is_connected = False
            self.status.is_connected = False
            gc.collect()
    
    def send_command(self, command: str) -> bool:
        """
        发送命令到舵机
        
        Args:
            command: 要发送的命令字符串 (会自动添加\r\n)
            
        Returns:
            bool: 发送是否成功
        """
        if not self.is_connected or not self.ser:
            print("[Servo] 串口未连接")
            return False
        
        try:
            # ROBOIDE命令格式，例如：#1P1500T100
            if not command.endswith('\r\n'):
                command += '\r\n'
            
            self.ser.write(command.encode())
            print(f"[Servo] 发送命令: {command.strip()}")
            return True
        except Exception as e:
            print(f"[Servo] 发送失败: {e}")
            return False
    
    def set_servo_position(self, position: int, duration: int = 100) -> bool:
        """
        设置舵机位置 (ROBOIDE命令格式)
        
        命令格式: #<ID>P<POSITION>T<DURATION>\r\n
        Args:
            position: 目标位置 (500-2500)，1500为中间位置
            duration: 动作耗时(毫秒), 默认100ms
            
        Returns:
            bool: 设置是否成功
        """
        # 限制位置范围
        position = max(500, min(2500, position))
        duration = max(1, duration)
        
        # 更新状态
        self.status.target = position
        self.status.is_moving = True
        self.status.is_open = position > 2000
        
        # 构建ROBOIDE命令
        command = f"#{self.servo_id}P{position}T{duration}"
        
        success = self.send_command(command)
        
        if success:
            # 模拟位置更新（实际应该读取反馈）
            self.status.position = position
            self.status.is_moving = False
        
        return success
    
    def move_to_position(self, position: int, duration: int = 500, wait: bool = False) -> bool:
        """
        让舵机移动到指定位置
        
        Args:
            position: 目标位置 (500-2500，1500为中间)
            duration: 动作耗时(毫秒), 默认500ms
            wait: 是否等待运动完成
            
        Returns:
            bool: 是否成功
        """
        print(f"[Servo] 舵机{self.servo_id}移动到位置: {position} (耗时{duration}ms)")
        success = self.set_servo_position(position, duration)
        
        if success and wait:
            time.sleep(duration / 1000.0)
        
        return success
    
    def open_shutter(self, duration: int = 500) -> bool:
        """
        开启挡板（移开，可拍摄）
        
        Args:
            duration: 动作耗时(毫秒)
            
        Returns:
            bool: 是否成功
        """
        print("[Servo] 开启挡板")
        success = self.move_to_position(ServoPosition.OPEN.value, duration)
        if success:
            self.status.is_open = True
        return success
    
    def close_shutter(self, duration: int = 500) -> bool:
        """
        关闭挡板（遮挡，保护红外摄像头）
        
        Args:
            duration: 动作耗时(毫秒)
            
        Returns:
            bool: 是否成功
        """
        print("[Servo] 关闭挡板")
        success = self.move_to_position(ServoPosition.CLOSED.value, duration)
        if success:
            self.status.is_open = False
        return success
    
    def toggle_shutter(self, duration: int = 500) -> bool:
        """
        切换挡板状态
        
        Args:
            duration: 动作耗时(毫秒)
            
        Returns:
            bool: 是否成功
        """
        if self.status.is_open:
            return self.close_shutter(duration)
        else:
            return self.open_shutter(duration)
    
    def get_status(self) -> dict:
        """获取舵机状态"""
        return {
            'position': self.status.position,
            'target': self.status.target,
            'is_open': self.status.is_open,
            'is_moving': self.status.is_moving,
            'is_connected': self.status.is_connected,
            'port': self.port,
            'servo_id': self.servo_id
        }


# 单例实例
_servo_controller_instance: Optional[ServoController] = None


def get_servo_controller(port: str = 'COM16', servo_id: int = 1) -> ServoController:
    """获取舵机控制器单例"""
    global _servo_controller_instance
    if _servo_controller_instance is None:
        _servo_controller_instance = ServoController(port=port, servo_id=servo_id)
    return _servo_controller_instance


def reset_servo_controller():
    """重置舵机控制器单例"""
    global _servo_controller_instance
    if _servo_controller_instance is not None:
        _servo_controller_instance.disconnect()
        _servo_controller_instance = None
    print("[Servo] 控制器已重置")


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("舵机控制测试")
    print("=" * 60)
    
    controller = ServoController(port='COM16')
    
    if controller.connect():
        print("\n测试舵机运动:")
        
        # 关闭挡板
        controller.close_shutter(duration=300)
        time.sleep(1)
        
        # 开启挡板
        controller.open_shutter(duration=300)
        time.sleep(1)
        
        # 回到关闭位置
        controller.close_shutter(duration=300)
        
        print(f"\n最终状态: {controller.get_status()}")
        
        controller.disconnect()
    else:
        print("连接失败，请检查串口设置")
