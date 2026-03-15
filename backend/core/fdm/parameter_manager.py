"""
参数管理模块
============
管理打印参数的生成、切换和同步缓冲策略

功能:
1. 随机参数组合生成
2. 9组标准数据集参数管理
3. 高度区间参数变化
4. 时空同步缓冲控制
"""
import random
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Callable
from enum import Enum


# 参数选项配置
RATE_OPTIONS = [20, 30, 40, 50, 60, 70, 80, 90, 100,
                110, 120, 130, 140, 150, 160, 170, 180, 190, 200]

Z_OFFSET_OPTIONS = [-0.32, -0.28, -0.24, -0.20, -0.16, -0.08, -0.04, 0, 
                    0.04, 0.08, 0.16, 0.20, 0.24, 0.28, 0.32]

# 温度范围 150-250，每隔5度
HOTEND_OPTIONS = list(range(150, 251, 5))


class ParameterMode(Enum):
    """参数生成模式"""
    FIXED = "fixed"           # 固定参数
    RANDOM = "random"         # 随机参数
    STANDARD_TOWER = "tower"  # 9组标准塔


@dataclass
class ParameterSet:
    """参数组合"""
    flow_rate: float = 100.0
    feed_rate: float = 100.0
    z_offset: float = 0.0
    target_hotend: float = 200.0
    
    def to_dict(self) -> Dict:
        return {
            "flow_rate": self.flow_rate,
            "feed_rate": self.feed_rate,
            "z_offset": self.z_offset,
            "target_hotend": self.target_hotend
        }


@dataclass
class TowerConfig:
    """单塔配置 (9组标准数据集之一)"""
    tower_id: int
    name: str
    hotend_temp: float  # 固定温度
    z_offset_fixed: float  # 固定Z补偿
    description: str = ""


# 9组标准塔配置 (外参：温度和Z轴补偿)
# 温度: 185°C(低温L) / 215°C(正常N) / 245°C(高温H)
# Z补偿: -0.15mm(压紧L) / 0.00mm(正常N) / +0.25mm(远离H)
STANDARD_TOWERS = [
    TowerConfig(1, "Tower 1", 185, -0.15, "低温+压头，高风险易堵头"),
    TowerConfig(2, "Tower 2", 185, 0.00, "低温，层间结合差"),
    TowerConfig(3, "Tower 3", 185, 0.25, "低温+远离，易脱落"),
    TowerConfig(4, "Tower 4", 215, -0.15, "正常温+压头，表面波浪纹"),
    TowerConfig(5, "Tower 5", 215, 0.00, "黄金样本（标准态）"),
    TowerConfig(6, "Tower 6", 215, 0.25, "正常温+远离，层间缝隙"),
    TowerConfig(7, "Tower 7", 245, -0.15, "高温+压紧，严重溢料"),
    TowerConfig(8, "Tower 8", 245, 0.00, "高温，拉丝多"),
    TowerConfig(9, "Tower 9", 245, 0.25, "高温+远离，结构松散"),
]


# 高度区间参数表 (内参：速度和流量)
# 总高度50mm = 0-5mm(初始化，不采集) + 5-50mm(9段采集区间)
# 每段5mm，实际采集4mm (0.5静默 + 4.0采集 + 0.5过渡)
# 例如5-10mm段：5.0-5.5静默，5.5-9.5采集，9.5-10.0过渡
HEIGHT_SEGMENTS = [
    # (start_mm, end_mm, feed_rate%, flow_rate%, description)
    # 第1段：0-5mm 初始化区间（正常参数，不采集）
    (0, 5, 100, 100, "初始化区间-正常参数"),
    # 第2-10段：9个采集区间
    (5, 10, 50, 75, "慢速缺料"),      # Seg2: 5.5-9.5采集
    (10, 15, 50, 100, "慢速正常"),     # Seg3: 10.5-14.5采集
    (15, 20, 50, 125, "慢速过挤"),     # Seg4: 15.5-19.5采集
    (20, 25, 100, 75, "正常速缺料"),   # Seg5: 20.5-24.5采集
    (25, 30, 100, 100, "完全标准态"),  # Seg6: 25.5-29.5采集 (Ground Truth)
    (30, 35, 100, 125, "正常速过挤"),  # Seg7: 30.5-34.5采集
    (35, 40, 160, 75, "高速缺料"),     # Seg8: 35.5-39.5采集
    (40, 45, 160, 100, "高速正常"),    # Seg9: 40.5-44.5采集
    (45, 50, 160, 125, "高速过挤"),    # Seg10: 45.5-49.5采集
]


@dataclass
class SyncBufferConfig:
    """时空同步缓冲配置 (适配5mm段高)"""
    # 5mm段高 = 0.5mm静默 + 4.0mm采集 + 0.5mm过渡
    silent_height_mm: float = 0.5      # 静默区高度 (参数变化后不采集，等待稳定)
    stable_capture_height_mm: float = 4.0  # 稳定采集区高度 (主要采集区域)
    transition_height_mm: float = 0.5  # 过渡区高度 (准备进入下一段，不采集)
    capture_fps: float = 2.0           # 采样频率 Hz
    
    # 参数变化后的稳定判断
    stability_z_diff_mm: float = 0.6   # Z轴变化多少后认为稳定 (建议在0.4-0.6mm，即2-3层高度)


class ParameterManager:
    """
    参数管理器
    管理参数生成、切换和时空同步
    """
    
    def __init__(self):
        self.mode = ParameterMode.FIXED
        self.current_params = ParameterSet()
        
        # 随机模式配置
        self.random_interval_sec = 120  # 默认120秒随机变化一次
        self.last_random_change_time = 0
        
        # 标准塔模式配置
        self.current_tower_id = 0  # 0-8 (对应Tower 1-9)
        self.current_segment_idx = 0  # 当前高度区间索引
        
        # 时空同步缓冲配置
        self.sync_config = SyncBufferConfig()
        
        # 状态追踪
        self.last_param_change_z: Optional[float] = None  # 上次参数变化时的Z高度
        self.is_in_silent_zone = False  # 是否在静默区
        self.current_z = 0.0
        
        # 回调函数
        self.on_param_change: Optional[Callable[[ParameterSet], None]] = None
        
        logging.info("[ParameterManager] 初始化完成")
    
    def generate_random_params(self) -> ParameterSet:
        """
        生成随机参数组合
        
        Returns:
            ParameterSet: 随机参数组合
        """
        return ParameterSet(
            flow_rate=random.choice(RATE_OPTIONS),
            feed_rate=random.choice(RATE_OPTIONS),
            z_offset=random.choice(Z_OFFSET_OPTIONS),
            target_hotend=random.choice(HOTEND_OPTIONS)
        )
    
    def get_tower_params(self, tower_id: int, current_z_mm: float) -> Tuple[ParameterSet, int]:
        """
        获取标准塔参数
        
        Args:
            tower_id: 塔编号 1-9
            current_z_mm: 当前Z高度
            
        Returns:
            (ParameterSet, segment_idx): 参数组合和当前区间索引
        """
        tower = STANDARD_TOWERS[tower_id - 1]
        
        # 确定当前高度区间
        segment_idx = 0
        for idx, (start, end, _, _, _) in enumerate(HEIGHT_SEGMENTS):
            if start <= current_z_mm < end:
                segment_idx = idx
                break
        
        # 获取该区间的速度和流量
        _, _, feed_rate, flow_rate, _ = HEIGHT_SEGMENTS[segment_idx]
        
        params = ParameterSet(
            flow_rate=float(flow_rate),
            feed_rate=float(feed_rate),
            z_offset=tower.z_offset_fixed,
            target_hotend=float(tower.hotend_temp)
        )
        
        return params, segment_idx
    
    def check_should_change_random(self, current_time: float) -> bool:
        """
        检查是否应该进行随机参数变化
        
        Args:
            current_time: 当前时间戳
            
        Returns:
            bool: 是否应该变化
        """
        if self.mode != ParameterMode.RANDOM:
            return False
        
        elapsed = current_time - self.last_random_change_time
        return elapsed >= self.random_interval_sec
    
    def should_capture(self, current_z_mm: float) -> Tuple[bool, str]:
        """
        根据时空同步缓冲策略判断是否应采图
        
        不同模式采用不同策略:
        - STANDARD_TOWER(标准9塔): 使用静默区/稳定采集区/过渡区三段式
          * 第1段(0-5mm): 初始化区间，正常参数，不采集
          * 第2-10段(5-50mm): 9个采集区间，每段5mm，实际采4mm
        - RANDOM/FIXED(通用模式): 使用 stability_z_diff_mm 判断稳定
        
        Args:
            current_z_mm: 当前Z高度
            
        Returns:
            (should_capture, reason): 是否应该采图及原因
        """
        self.current_z = current_z_mm
        
        # ========== 标准9塔模式：三段式缓冲 ==========
        if self.mode == ParameterMode.STANDARD_TOWER:
            # 第1段(0-5mm): 初始化区间，不采集
            if 0 <= current_z_mm < 5:
                return False, f"初始化区间 (Z={current_z_mm:.2f}mm, 0-5mm不采集)"
            
            # 如果没有记录过参数变化位置，说明是第一次进入采集区间
            # 根据当前Z值计算所在的段起始位置
            if self.last_param_change_z is None:
                # 计算当前所在的段 (5-10, 10-15, 15-20...)
                segment_start = 5 + int((current_z_mm - 5) / 5) * 5
                self.last_param_change_z = float(segment_start)
                self.is_in_silent_zone = True
                logging.info(f"[ParameterManager] 首次进入采集区间，段起始Z={segment_start}mm，当前Z={current_z_mm:.2f}mm")
            
            z_diff = current_z_mm - self.last_param_change_z
            cfg = self.sync_config
            
            # 静默区: 段起始后0.5mm内不采集 (如5.0-5.5, 10.0-10.5)
            if z_diff < cfg.silent_height_mm:
                self.is_in_silent_zone = True
                return False, f"静默区 (Z变化{z_diff:.2f}mm < {cfg.silent_height_mm}mm)"
            
            # 稳定采集区: 采集4.0mm (如5.5-9.5, 10.5-14.5等)
            if z_diff < (cfg.silent_height_mm + cfg.stable_capture_height_mm):
                self.is_in_silent_zone = False
                return True, f"稳定采集区 (Z变化{z_diff:.2f}mm)"
            
            # 过渡区: 最后0.5mm不采集，准备进入下一段 (如9.5-10.0, 14.5-15.0)
            if z_diff < (cfg.silent_height_mm + cfg.stable_capture_height_mm + cfg.transition_height_mm):
                return False, f"过渡区 (准备下一段)"
            
            # 超过区间，应该进入下一段了
            return False, "等待进入下一段"
        
        # ========== 通用模式(RANDOM/FIXED)：使用 stability_z_diff_mm ==========
        else:
            # 如果没有记录过参数变化位置，允许采集
            if self.last_param_change_z is None:
                return True, "正常采集"
            
            z_diff = current_z_mm - self.last_param_change_z
            cfg = self.sync_config
            
            # 检查是否达到稳定高度
            is_stable, _ = self.check_stability(current_z_mm)
            
            if not is_stable:
                self.is_in_silent_zone = True
                return False, f"等待稳定 (Z变化{z_diff:.2f}mm < {cfg.stability_z_diff_mm}mm)"
            
            self.is_in_silent_zone = False
            return True, f"稳定采集 (Z变化{z_diff:.2f}mm >= {cfg.stability_z_diff_mm}mm)"
    
    def apply_param_change(self, new_params: ParameterSet, current_z_mm: float) -> bool:
        """
        应用新参数，记录变化位置
        
        Args:
            new_params: 新参数
            current_z_mm: 当前Z高度
            
        Returns:
            bool: 是否成功应用
        """
        self.current_params = new_params
        self.last_param_change_z = current_z_mm
        self.is_in_silent_zone = True
        
        # 触发回调
        if self.on_param_change:
            try:
                self.on_param_change(new_params)
            except Exception as e:
                logging.error(f"[ParameterManager] 参数变化回调失败: {e}")
        
        logging.info(f"[ParameterManager] 参数已变化 @ Z={current_z_mm:.2f}mm: "
                    f"F={new_params.feed_rate}, E={new_params.flow_rate}, "
                    f"Z={new_params.z_offset}, T={new_params.target_hotend}")
        
        return True
    
    def set_mode(self, mode: ParameterMode, **kwargs):
        """
        设置参数生成模式
        
        Args:
            mode: 模式
            **kwargs: 模式特定参数
                - random_interval_sec: 随机模式间隔(秒)
                - tower_id: 塔模式塔编号(1-9)
        """
        self.mode = mode
        
        if mode == ParameterMode.RANDOM:
            self.random_interval_sec = kwargs.get('random_interval_sec', 120)
            self.last_random_change_time = time.time()
            logging.info(f"[ParameterManager] 切换到随机模式，间隔{self.random_interval_sec}秒")
            
        elif mode == ParameterMode.STANDARD_TOWER:
            self.current_tower_id = kwargs.get('tower_id', 1) - 1
            self.current_segment_idx = 0
            self.last_param_change_z = None  # 重置上次参数变化位置
            logging.info(f"[ParameterManager] 切换到标准塔模式，当前Tower {self.current_tower_id + 1}")
            
        elif mode == ParameterMode.FIXED:
            self.last_param_change_z = None
            logging.info("[ParameterManager] 切换到固定参数模式")
    
    def get_next_standard_params(self, current_z_mm: float) -> Optional[ParameterSet]:
        """
        获取标准塔模式的下一组参数
        根据当前Z高度自动判断是否需要切换区间
        
        Args:
            current_z_mm: 当前Z高度
            
        Returns:
            ParameterSet or None: 新参数(如果需要变化)或None(保持当前)
        """
        if self.mode != ParameterMode.STANDARD_TOWER:
            return None
        
        params, segment_idx = self.get_tower_params(
            self.current_tower_id + 1, 
            current_z_mm
        )
        
        # 检查是否需要更新参数
        logging.debug(f"[ParameterManager] Z={current_z_mm:.2f}mm -> segment_idx={segment_idx}, "
                    f"current_segment_idx={self.current_segment_idx}")
        
        if segment_idx != self.current_segment_idx:
            self.current_segment_idx = segment_idx
            logging.info(f"[ParameterManager] Tower {self.current_tower_id + 1} "
                        f"进入区间 {segment_idx + 1}/9 "
                        f"({HEIGHT_SEGMENTS[segment_idx][0]}-{HEIGHT_SEGMENTS[segment_idx][1]}mm), "
                        f"参数: T={params.target_hotend}°C, Z={params.z_offset}mm, F={params.feed_rate}, E={params.flow_rate}")
            return params
        
        # 检查参数是否一致（温度或Z偏移变化也需要返回）
        if (params.flow_rate != self.current_params.flow_rate or
            params.feed_rate != self.current_params.feed_rate or
            params.target_hotend != self.current_params.target_hotend or
            params.z_offset != self.current_params.z_offset):
            logging.info(f"[ParameterManager] 同一区间内参数变化: "
                       f"T={self.current_params.target_hotend}->{params.target_hotend}, "
                       f"Z={self.current_params.z_offset}->{params.z_offset}")
            return params
        
        logging.debug(f"[ParameterManager] 参数无变化，不返回新参数")
        return None
    
    def check_stability(self, current_z_mm: float) -> Tuple[bool, float]:
        """
        检查参数变化后是否达到稳定状态
        
        Args:
            current_z_mm: 当前Z高度
            
        Returns:
            (is_stable, z_diff): 是否稳定及Z轴变化量
        """
        if self.last_param_change_z is None:
            return True, 0.0
        
        z_diff = abs(current_z_mm - self.last_param_change_z)
        is_stable = z_diff >= self.sync_config.stability_z_diff_mm
        
        return is_stable, z_diff
    
    def get_current_segment_info(self) -> Optional[Dict]:
        """
        获取当前区间信息
        
        Returns:
            Dict or None: 当前区间信息
        """
        if self.mode != ParameterMode.STANDARD_TOWER:
            return None
        
        start, end, feed, flow, desc = HEIGHT_SEGMENTS[self.current_segment_idx]
        tower = STANDARD_TOWERS[self.current_tower_id]
        
        return {
            "tower_id": tower.tower_id,
            "tower_name": tower.name,
            "segment_idx": self.current_segment_idx + 1,
            "segment_total": len(HEIGHT_SEGMENTS),
            "height_range": f"{start}-{end}mm",
            "feed_rate": feed,
            "flow_rate": flow,
            "hotend_temp": tower.hotend_temp,
            "z_offset": tower.z_offset_fixed,
            "description": desc
        }
    
    def get_status(self) -> Dict:
        """获取当前状态"""
        return {
            "mode": self.mode.value,
            "current_params": self.current_params.to_dict(),
            "last_param_change_z": self.last_param_change_z,
            "current_z": self.current_z,
            "is_in_silent_zone": self.is_in_silent_zone,
            "sync_config": {
                "silent_height_mm": self.sync_config.silent_height_mm,
                "stable_capture_height_mm": self.sync_config.stable_capture_height_mm,
                "stability_z_diff_mm": self.sync_config.stability_z_diff_mm,
                "capture_fps": self.sync_config.capture_fps
            }
        }


def generate_random_param_combinations(
    count: int = 10,
    ensure_normal: bool = True
) -> List[ParameterSet]:
    """
    生成多组随机参数组合
    
    Args:
        count: 生成数量
        ensure_normal: 确保包含一组标准参数(100,100,0,200)
        
    Returns:
        List[ParameterSet]: 参数组合列表
    """
    combinations = []
    
    for _ in range(count):
        combinations.append(ParameterManager().generate_random_params())
    
    if ensure_normal and count > 0:
        combinations[0] = ParameterSet(100, 100, 0, 200)
    
    return combinations


# 单例实例
_parameter_manager: Optional[ParameterManager] = None

def get_parameter_manager() -> ParameterManager:
    """获取参数管理器单例"""
    global _parameter_manager
    if _parameter_manager is None:
        _parameter_manager = ParameterManager()
    return _parameter_manager
