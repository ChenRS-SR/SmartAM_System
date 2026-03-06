"""
设备管理器 - 根据设备类型动态管理驱动
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum


class DeviceType(Enum):
    """设备类型枚举"""
    NONE = "none"      # 未选择
    FDM = "fdm"        # 熔融沉积
    SLS = "sls"        # 选择性激光烧结
    SLM = "slm"        # 选择性激光熔化


class DeviceManager:
    """
    设备管理器
    
    功能：
    1. 管理当前设备类型
    2. 延迟初始化设备驱动
    3. 提供统一的设备状态接口
    """
    
    def __init__(self):
        self._current_type = DeviceType.NONE
        self._fdm_acquisition = None
        self._sls_acquisition = None
        self._initialized = False
        
        logging.info("[DeviceManager] 初始化完成")
    
    def set_device_type(self, device_type: str) -> bool:
        """
        设置设备类型并初始化对应驱动
        
        Args:
            device_type: 'fdm', 'sls', 'slm'
        
        Returns:
            是否成功
        """
        try:
            # 如果已经有设备在运行，先停止
            if self._initialized:
                self.stop_current_device()
            
            # 设置新设备类型
            if device_type == "fdm":
                self._current_type = DeviceType.FDM
                self._init_fdm()
            elif device_type == "sls":
                self._current_type = DeviceType.SLS
                self._init_sls()
            elif device_type == "slm":
                self._current_type = DeviceType.SLM
                self._init_slm()
            else:
                logging.error(f"[DeviceManager] 未知设备类型: {device_type}")
                return False
            
            self._initialized = True
            logging.info(f"[DeviceManager] 已切换到 {device_type.upper()} 模式")
            return True
            
        except Exception as e:
            logging.error(f"[DeviceManager] 切换设备类型失败: {e}")
            return False
    
    def _init_fdm(self):
        """初始化 FDM 设备"""
        logging.info("[DeviceManager] 正在初始化 FDM 设备...")
        from core.data_acquisition import get_acquisition
        self._fdm_acquisition = get_acquisition()
        # FDM 不在这里初始化设备，等待前端调用 connect
        
    def _init_sls(self):
        """初始化 SLS 设备"""
        logging.info("[DeviceManager] 正在初始化 SLS 设备...")
        from core.sls import get_sls_acquisition
        self._sls_acquisition = get_sls_acquisition()
        # 初始化 SLS 设备（振动传感器、摄像头）
        self._sls_acquisition.initialize_devices()
        
    def _init_slm(self):
        """初始化 SLM 设备"""
        logging.info("[DeviceManager] SLM 模式尚未实现")
        # TODO: 实现 SLM 初始化
    
    def stop_current_device(self):
        """停止当前设备"""
        if self._current_type == DeviceType.FDM and self._fdm_acquisition:
            self._fdm_acquisition.stop()
            self._fdm_acquisition.disconnect_all_devices()
        elif self._current_type == DeviceType.SLS and self._sls_acquisition:
            self._sls_acquisition.disconnect_all()
        
        self._initialized = False
        logging.info(f"[DeviceManager] {self._current_type.value} 设备已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前设备状态"""
        status = {
            "device_type": self._current_type.value,
            "initialized": self._initialized
        }
        
        if self._current_type == DeviceType.FDM and self._fdm_acquisition:
            status["fdm"] = self._fdm_acquisition.get_device_status()
        elif self._current_type == DeviceType.SLS and self._sls_acquisition:
            status["sls"] = self._sls_acquisition.get_device_status()
        
        return status
    
    @property
    def current_type(self) -> DeviceType:
        return self._current_type
    
    @property
    def fdm_acquisition(self):
        return self._fdm_acquisition
    
    @property
    def sls_acquisition(self):
        return self._sls_acquisition


# 全局设备管理器实例
_device_manager: Optional[DeviceManager] = None


def get_device_manager() -> DeviceManager:
    """获取设备管理器单例"""
    global _device_manager
    if _device_manager is None:
        _device_manager = DeviceManager()
    return _device_manager
