"""
硬件适配层 (Hardware Adapter Layer)
===================================
解决外部模块依赖问题：
1. 优先尝试导入 pacnet_project 的模块
2. 如果失败，提供简化版实现或占位符

这样 SmartAM_System 可以独立运行，
同时也兼容 pacnet_project 的高级功能。
"""

import os
import sys
import time
import logging
from typing import Optional, Dict, Tuple, Any
from pathlib import Path
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# 尝试添加 pacnet_project 到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PACNET_PATH = PROJECT_ROOT / "pacnet_project"

if str(PACNET_PATH) not in sys.path:
    sys.path.insert(0, str(PACNET_PATH))


# ========== Fotric 红外相机适配 ==========

FOTRIC_AVAILABLE = False
FotricEnhancedDevice = None

try:
    from hardware.fotric_driver import FotricEnhancedDevice as _FotricDevice
    FotricEnhancedDevice = _FotricDevice
    FOTRIC_AVAILABLE = True
    logger.info("[Adapter] 使用外部 Fotric 驱动")
except ImportError as e:
    logger.warning(f"[Adapter] 外部 Fotric 驱动不可用: {e}")


class FotricDeviceAdapter:
    """
    Fotric 红外相机适配器
    
    如果外部驱动可用，使用外部驱动；
    否则提供模拟模式。
    """
    
    def __init__(self, ip: str = "192.168.1.100", port: int = 10080, 
                 simulation_mode: bool = False, **kwargs):
        self.ip = ip
        self.port = port
        self.simulation_mode = simulation_mode or not FOTRIC_AVAILABLE
        self.is_connected = False
        self.width = 640
        self.height = 480
        
        self._device = None
        self._latest_frame = None
        
        if FOTRIC_AVAILABLE and not self.simulation_mode:
            try:
                self._device = FotricEnhancedDevice(
                    ip=ip, port=port, 
                    simulation_mode=False, **kwargs
                )
                self.is_connected = self._device.is_connected
                if self.is_connected:
                    self.width = self._device.width
                    self.height = self._device.height
                    logger.info(f"[FotricAdapter] 使用真实设备: {self.width}x{self.height}")
                else:
                    logger.warning("[FotricAdapter] 真实设备连接失败，切换到模拟模式")
                    self.simulation_mode = True
            except Exception as e:
                logger.error(f"[FotricAdapter] 初始化失败: {e}")
                self.simulation_mode = True
        
        if self.simulation_mode:
            self.is_connected = True
            logger.info("[FotricAdapter] 使用模拟模式")
    
    def get_temperature_stats(self) -> Optional[Dict]:
        """获取温度统计"""
        if self._device and self.is_connected and not self.simulation_mode:
            return self._device.get_temperature_stats()
        
        # 模拟数据
        if self.simulation_mode:
            return {
                'min_temp': 25.0 + np.random.randn() * 2,
                'max_temp': 200.0 + np.random.randn() * 10,
                'avg_temp': 100.0 + np.random.randn() * 5,
            }
        return None
    
    def get_thermal_data(self) -> Optional[np.ndarray]:
        """获取温度矩阵"""
        if self._device and self.is_connected and not self.simulation_mode:
            return self._device.get_thermal_data()
        
        # 模拟数据
        if self.simulation_mode:
            base = 100 + 50 * np.sin(time.time())
            data = np.random.randn(self.height, self.width) * 10 + base
            # 添加一个热点模拟熔池
            cy, cx = self.height // 2, self.width // 2
            Y, X = np.ogrid[:self.height, :self.width]
            dist = np.sqrt((X-cx)**2 + (Y-cy)**2)
            data += 100 * np.exp(-dist / 50)
            return data.astype(np.float32)
        return None
    
    def disconnect(self):
        """断开连接"""
        if self._device:
            try:
                self._device.disconnect()
            except:
                pass
        self.is_connected = False


# ========== M114 坐标获取适配 ==========

COORDINATOR_AVAILABLE = False
M114Coordinator = None

try:
    from hardware.coordinator import M114Coordinator as _M114Coord
    M114Coordinator = _M114Coord
    COORDINATOR_AVAILABLE = True
    logger.info("[Adapter] 使用外部 M114Coordinator")
except ImportError as e:
    logger.warning(f"[Adapter] 外部 M114Coordinator 不可用: {e}")


class CoordinatorAdapter:
    """
    坐标获取适配器
    
    如果外部 coordinator 可用，使用它；
    否则提供基于 OctoPrint API 的简化版。
    """
    
    def __init__(self, octoprint_url: str = "http://127.0.0.1:5000", 
                 api_key: str = None):
        self.octoprint_url = octoprint_url
        self.api_key = api_key or "UGjrS2T5n_48GF0YsWADx1EoTILjwn7ZkeWUfgGvW2Q"
        self._external_coord = None
        
        if COORDINATOR_AVAILABLE:
            try:
                self._external_coord = M114Coordinator()
                logger.info("[CoordinatorAdapter] 使用外部 coordinator")
            except Exception as e:
                logger.warning(f"[CoordinatorAdapter] 外部 coordinator 初始化失败: {e}")
    
    def wait_for_m114_response(self, timeout: float = 2.0, caller="Adapter") -> Optional[Dict[str, float]]:
        """获取坐标"""
        # 优先使用外部 coordinator
        if self._external_coord:
            try:
                result = self._external_coord.wait_for_m114_response(timeout, caller=caller)
                if result:
                    return result
            except Exception as e:
                logger.debug(f"[CoordinatorAdapter] 外部 coordinator 失败: {e}")
        
        # 回退：使用 OctoPrint API
        return self._get_position_from_api()
    
    def _get_position_from_api(self) -> Optional[Dict[str, float]]:
        """从 OctoPrint API 获取位置"""
        try:
            import requests
            url = f"{self.octoprint_url}/api/printer"
            headers = {"X-Api-Key": self.api_key}
            response = requests.get(url, headers=headers, timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                state = data.get("state", {})
                if "position" in state and state["position"]:
                    pos = state["position"]
                    return {
                        "X": pos.get("x", 0),
                        "Y": pos.get("y", 0),
                        "Z": pos.get("z", 0)
                    }
        except Exception as e:
            logger.debug(f"[CoordinatorAdapter] API 获取失败: {e}")
        
        return None
    
    def get_current_coordinates(self) -> Dict[str, float]:
        """获取最后已知坐标"""
        if self._external_coord:
            try:
                return self._external_coord.get_current_coordinates()
            except:
                pass
        return {"X": 0, "Y": 0, "Z": 0}


# ========== 统一硬件管理器 ==========

class HardwareManager:
    """
    统一硬件管理器
    
    简化 DAQ 的硬件初始化，自动处理外部依赖。
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.fotric: Optional[FotricDeviceAdapter] = None
        self.coordinator: Optional[CoordinatorAdapter] = None
    
    def initialize(self) -> Dict[str, bool]:
        """初始化所有硬件，返回状态字典"""
        status = {
            "fotric": False,
            "coordinator": False
        }
        
        # 初始化红外相机
        try:
            self.fotric = FotricDeviceAdapter(
                ip=self.config.get("fotric_ip", "192.168.1.100"),
                port=self.config.get("fotric_port", 10080),
                simulation_mode=self.config.get("fotric_simulation", False)
            )
            status["fotric"] = self.fotric.is_connected
            if status["fotric"]:
                logger.info("[HardwareManager] 红外相机就绪")
        except Exception as e:
            logger.error(f"[HardwareManager] 红外相机初始化失败: {e}")
        
        # 初始化坐标获取
        try:
            self.coordinator = CoordinatorAdapter(
                octoprint_url=self.config.get("octoprint_url", "http://127.0.0.1:5000"),
                api_key=self.config.get("api_key")
            )
            status["coordinator"] = True
            logger.info("[HardwareManager] 坐标获取器就绪")
        except Exception as e:
            logger.error(f"[HardwareManager] 坐标获取器初始化失败: {e}")
        
        return status
    
    def shutdown(self):
        """关闭所有硬件"""
        if self.fotric:
            self.fotric.disconnect()
            logger.info("[HardwareManager] 红外相机已关闭")


# ========== 便捷函数 ==========

def create_fotric_device(**kwargs) -> FotricDeviceAdapter:
    """创建 Fotric 设备（适配器）"""
    return FotricDeviceAdapter(**kwargs)


def create_coordinator(**kwargs) -> CoordinatorAdapter:
    """创建坐标获取器（适配器）"""
    return CoordinatorAdapter(**kwargs)


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("硬件适配层测试")
    print("=" * 60)
    
    # 测试 Fotric 适配器
    print("\n1. 测试 Fotric 适配器...")
    fotric = create_fotric_device(simulation_mode=True)
    
    if fotric.is_connected:
        print("✓ Fotric 连接成功")
        time.sleep(1)
        stats = fotric.get_temperature_stats()
        if stats:
            print(f"  温度: {stats['min_temp']:.1f} ~ {stats['max_temp']:.1f}°C")
        fotric.disconnect()
    else:
        print("✗ Fotric 连接失败")
    
    # 测试 Coordinator 适配器
    print("\n2. 测试 Coordinator 适配器...")
    coord = create_coordinator()
    
    coords = coord.wait_for_m114_response(timeout=2)
    if coords:
        print(f"✓ 坐标获取成功: X={coords['X']:.2f}, Y={coords['Y']:.2f}, Z={coords['Z']:.2f}")
    else:
        print("✗ 坐标获取失败（OctoPrint 可能未运行）")
    
    print("\n" + "=" * 60)
    print("测试完成")
