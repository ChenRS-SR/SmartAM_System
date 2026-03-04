"""
OctoPrint API 模拟器
====================
用于在没有真实 OctoPrint 和打印机的情况下调试系统

模拟功能：
- 打印机状态查询 (/api/printer)
- 打印任务状态查询 (/api/job)
- G-code 命令发送 (/api/printer/command)
- 温度数据模拟
- 位置数据模拟
- 打印进度模拟
"""

import time
import random
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class OctoPrintSimulationConfig:
    """OctoPrint 模拟配置"""
    # 基础配置
    printer_state: str = "Printing"  # Operational, Printing, Paused, Error, etc.
    
    # 温度配置
    hotend_target: float = 200.0
    bed_target: float = 60.0
    hotend_actual: float = 200.0
    bed_actual: float = 60.0
    
    # 位置配置
    x: float = 100.0
    y: float = 100.0
    z: float = 5.0
    e: float = 0.0
    
    # 打印任务配置
    filename: str = "simulation_test.gcode"
    total_print_time: int = 3600  # 秒
    
    # 行为配置
    enable_temperature_fluctuation: bool = True
    enable_position_movement: bool = True
    enable_progress: bool = True
    
    # 随机波动范围
    temp_noise: float = 2.0
    position_noise: float = 0.1


class OctoPrintSimulator:
    """
    OctoPrint API 模拟器
    
    模拟 OctoPrint REST API 的行为，提供与真实 OctoPrint 兼容的响应格式
    """
    
    def __init__(self, config: OctoPrintSimulationConfig = None):
        self.config = config or OctoPrintSimulationConfig()
        self.start_time = time.time()
        self.command_history = []
        self._current_position = {
            "x": self.config.x,
            "y": self.config.y,
            "z": self.config.z,
            "e": self.config.e
        }
        self._current_temps = {
            "hotend": self.config.hotend_actual,
            "bed": self.config.bed_actual
        }
        self._flow_rate = 100
        self._feed_rate = 100
        self._z_offset = 0.0
        
        logger.info("[OctoPrint模拟器] 初始化完成")
    
    def get_printer_status(self) -> Dict[str, Any]:
        """
        模拟 GET /api/printer
        
        返回打印机状态，包括温度、位置、状态标志等
        """
        self._update_simulation_data()
        
        return {
            "temperature": {
                "tool0": {
                    "actual": round(self._current_temps["hotend"], 2),
                    "target": self.config.hotend_target,
                    "offset": 0
                },
                "bed": {
                    "actual": round(self._current_temps["bed"], 2),
                    "target": self.config.bed_target,
                    "offset": 0
                }
            },
            "state": {
                "text": self.config.printer_state,
                "flags": {
                    "operational": True,
                    "paused": self.config.printer_state == "Paused",
                    "printing": self.config.printer_state == "Printing",
                    "cancelling": False,
                    "pausing": False,
                    "sdReady": False,
                    "error": False,
                    "ready": self.config.printer_state == "Operational",
                    "closedOrError": False
                }
            },
            "position": self._current_position.copy()
        }
    
    def get_job_status(self) -> Dict[str, Any]:
        """
        模拟 GET /api/job
        
        返回当前打印任务状态
        """
        elapsed = time.time() - self.start_time
        progress = 0.0
        
        if self.config.enable_progress and self.config.total_print_time > 0:
            progress = min(100.0, (elapsed / self.config.total_print_time) * 100)
        
        return {
            "job": {
                "file": {
                    "name": self.config.filename,
                    "origin": "local",
                    "size": 1234567,
                    "date": int(self.start_time)
                },
                "estimatedPrintTime": self.config.total_print_time,
                "filament": {
                    "tool0": {
                        "length": 1000.0,
                        "volume": 2.4
                    }
                },
                "user": "simulation"
            },
            "progress": {
                "completion": round(progress, 2),
                "filepos": int(1234567 * progress / 100),
                "printTime": int(elapsed),
                "printTimeLeft": int(max(0, self.config.total_print_time - elapsed)),
                "printTimeLeftOrigin": "estimate"
            },
            "state": self.config.printer_state
        }
    
    def send_command(self, command: str) -> bool:
        """
        模拟 POST /api/printer/command
        
        处理 G-code 命令，记录历史，更新模拟状态
        """
        self.command_history.append({
            "timestamp": datetime.now().isoformat(),
            "command": command
        })
        
        logger.info(f"[OctoPrint模拟器] 收到 G-code: {command}")
        
        # 解析常见 G-code 命令
        cmd = command.strip().upper()
        
        # M104 - 设置热端温度
        if cmd.startswith("M104"):
            try:
                temp = float(cmd.split("S")[1].split()[0])
                self.config.hotend_target = temp
                logger.info(f"[OctoPrint模拟器] 设置热端温度: {temp}°C")
            except:
                pass
        
        # M140 - 设置热床温度
        elif cmd.startswith("M140"):
            try:
                temp = float(cmd.split("S")[1].split()[0])
                self.config.bed_target = temp
                logger.info(f"[OctoPrint模拟器] 设置热床温度: {temp}°C")
            except:
                pass
        
        # M220 - 设置速度倍率
        elif cmd.startswith("M220"):
            try:
                rate = float(cmd.split("S")[1].split()[0])
                self._feed_rate = rate
                logger.info(f"[OctoPrint模拟器] 设置速度倍率: {rate}%")
            except:
                pass
        
        # M221 - 设置流量倍率
        elif cmd.startswith("M221"):
            try:
                rate = float(cmd.split("S")[1].split()[0])
                self._flow_rate = rate
                logger.info(f"[OctoPrint模拟器] 设置流量倍率: {rate}%")
            except:
                pass
        
        # M290 - 设置 Z 偏移
        elif cmd.startswith("M290"):
            try:
                z = float(cmd.split("Z")[1].split()[0])
                self._z_offset += z
                logger.info(f"[OctoPrint模拟器] 调整 Z 偏移: {z}mm, 当前: {self._z_offset}mm")
            except:
                pass
        
        # M114 - 查询位置（实际位置数据在 get_printer_status 中返回）
        elif cmd.startswith("M114"):
            logger.debug(f"[OctoPrint模拟器] 查询位置: {self._current_position}")
        
        # M105 - 查询温度
        elif cmd.startswith("M105"):
            logger.debug(f"[OctoPrint模拟器] 查询温度")
        
        return True
    
    def _update_simulation_data(self):
        """更新模拟数据（温度波动、位置移动等）"""
        elapsed = time.time() - self.start_time
        
        # 模拟温度波动
        if self.config.enable_temperature_fluctuation:
            noise = random.uniform(-self.config.temp_noise, self.config.temp_noise)
            self._current_temps["hotend"] = self.config.hotend_target + noise
            
            noise = random.uniform(-self.config.temp_noise, self.config.temp_noise)
            self._current_temps["bed"] = self.config.bed_target + noise
        
        # 模拟位置移动（打印一个方形路径）
        if self.config.enable_position_movement:
            cycle = 20  # 20秒一个周期
            phase = (elapsed % cycle) / cycle
            
            # 模拟打印一个 100x100mm 的方形，Z 缓慢上升
            if phase < 0.25:
                # 从左到右
                self._current_position["x"] = 50 + phase * 4 * 100
                self._current_position["y"] = 50
            elif phase < 0.5:
                # 从下到上
                self._current_position["x"] = 150
                self._current_position["y"] = 50 + (phase - 0.25) * 4 * 100
            elif phase < 0.75:
                # 从右到左
                self._current_position["x"] = 150 - (phase - 0.5) * 4 * 100
                self._current_position["y"] = 150
            else:
                # 从上到下
                self._current_position["x"] = 50
                self._current_position["y"] = 150 - (phase - 0.75) * 4 * 100
            
            # Z 轴缓慢上升（模拟打印过程）
            self._current_position["z"] = self.config.z + elapsed * 0.05  # 每秒上升 0.05mm
            
            # 挤出量
            self._current_position["e"] = elapsed * 0.5
            
            # 添加微小噪声
            for key in ["x", "y", "z", "e"]:
                noise = random.uniform(-self.config.position_noise, self.config.position_noise)
                self._current_position[key] += noise
    
    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        return {
            "connected": True,
            "simulation": True,
            "start_time": self.start_time,
            "uptime": time.time() - self.start_time
        }
    
    def get_command_history(self, limit: int = 100) -> list:
        """获取命令历史"""
        return self.command_history[-limit:]


# 全局模拟器实例
_simulator_instance: Optional[OctoPrintSimulator] = None


def get_octoprint_simulator(config: OctoPrintSimulationConfig = None) -> OctoPrintSimulator:
    """获取 OctoPrint 模拟器单例"""
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = OctoPrintSimulator(config)
    return _simulator_instance


def reset_simulator():
    """重置模拟器（用于测试）"""
    global _simulator_instance
    _simulator_instance = None
