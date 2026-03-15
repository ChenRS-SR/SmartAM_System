"""
ROI区域配置管理
==============
用于管理图像中感兴趣区域(ROI)的配置和特征计算
"""

import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import threading


class ROIConfig:
    """ROI区域配置"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.rois: Dict[str, Any] = {}  # ROI区域定义
        self.features: Dict[str, List[float]] = {}  # 特征历史数据
        self.layer_features: Dict[int, Dict[str, float]] = {}  # 每层特征数据
        self.lock = threading.Lock()
        
        if config_path and Path(config_path).exists():
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> bool:
        """加载ROI配置文件
        
        配置文件格式:
        {
            "rois": {
                "region1": {
                    "name": "熔池中心",
                    "type": "rectangle",  # rectangle, circle, polygon
                    "coords": [x, y, width, height],  # 矩形: [x, y, w, h]
                    "coords": [cx, cy, radius],  # 圆形: [cx, cy, r]
                    "coords": [[x1,y1], [x2,y2], ...],  # 多边形
                    "description": "描述信息"
                },
                ...
            },
            "features": ["mean", "std", "max", "min", "median"],  # 要计算的特征
            "update_mode": "layer"  # layer: 按层更新, frame: 按帧更新
        }
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            with self.lock:
                self.rois = config.get('rois', {})
                self.feature_types = config.get('features', ['mean', 'std'])
                self.update_mode = config.get('update_mode', 'layer')
                self.config_path = config_path
            
            print(f"[ROIConfig] 加载配置成功: {config_path}")
            print(f"[ROIConfig] ROI区域: {list(self.rois.keys())}")
            return True
            
        except Exception as e:
            print(f"[ROIConfig] 加载配置失败: {e}")
            return False
    
    def save_config(self, config_path: str = None) -> bool:
        """保存ROI配置"""
        try:
            path = config_path or self.config_path
            if not path:
                return False
            
            config = {
                'rois': self.rois,
                'features': getattr(self, 'feature_types', ['mean', 'std']),
                'update_mode': getattr(self, 'update_mode', 'layer')
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"[ROIConfig] 保存配置成功: {path}")
            return True
            
        except Exception as e:
            print(f"[ROIConfig] 保存配置失败: {e}")
            return False
    
    def add_roi(self, roi_id: str, roi_data: Dict) -> bool:
        """添加ROI区域"""
        with self.lock:
            self.rois[roi_id] = roi_data
        return True
    
    def remove_roi(self, roi_id: str) -> bool:
        """删除ROI区域"""
        with self.lock:
            if roi_id in self.rois:
                del self.rois[roi_id]
                return True
        return False
    
    def get_rois(self) -> Dict:
        """获取所有ROI区域"""
        with self.lock:
            return self.rois.copy()
    
    def extract_roi_image(self, image: np.ndarray, roi_id: str) -> Optional[np.ndarray]:
        """从图像中提取ROI区域"""
        if roi_id not in self.rois:
            return None
        
        roi = self.rois[roi_id]
        h, w = image.shape[:2]
        
        try:
            roi_type = roi.get('type', 'rectangle')
            coords = roi.get('coords', [])
            
            if roi_type == 'rectangle' and len(coords) >= 4:
                x, y, rw, rh = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
                # 确保坐标在图像范围内
                x = max(0, min(x, w-1))
                y = max(0, min(y, h-1))
                rw = min(rw, w - x)
                rh = min(rh, h - y)
                return image[y:y+rh, x:x+rw]
            
            elif roi_type == 'circle' and len(coords) >= 3:
                cx, cy, r = int(coords[0]), int(coords[1]), int(coords[2])
                # 创建圆形mask
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.circle(mask, (cx, cy), r, 255, -1)
                # 提取圆形区域（使用bounding rect）
                x1, y1 = max(0, cx-r), max(0, cy-r)
                x2, y2 = min(w, cx+r), min(h, cy+r)
                return image[y1:y2, x1:x2]
            
            elif roi_type == 'polygon' and len(coords) >= 3:
                # 多边形
                pts = np.array(coords, dtype=np.int32).reshape((-1, 1, 2))
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.fillPoly(mask, [pts], 255)
                # 提取多边形区域
                x, y, rw, rh = cv2.boundingRect(pts)
                return image[y:y+rh, x:x+rw]
            
        except Exception as e:
            print(f"[ROIConfig] 提取ROI失败 {roi_id}: {e}")
        
        return None
    
    def calculate_features(self, roi_image: np.ndarray) -> Dict[str, float]:
        """计算ROI区域的特征值
        
        支持的特征:
        - mean: 灰度均值
        - std: 标准差
        - max: 最大值
        - min: 最小值
        - median: 中位数
        - area: 区域面积（像素数）
        """
        if roi_image is None or roi_image.size == 0:
            return {}
        
        # 转换为灰度图
        if len(roi_image.shape) == 3:
            gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi_image
        
        features = {}
        feature_types = getattr(self, 'feature_types', ['mean', 'std'])
        
        for feat_type in feature_types:
            try:
                if feat_type == 'mean':
                    features['mean'] = float(np.mean(gray))
                elif feat_type == 'std':
                    features['std'] = float(np.std(gray))
                elif feat_type == 'max':
                    features['max'] = float(np.max(gray))
                elif feat_type == 'min':
                    features['min'] = float(np.min(gray))
                elif feat_type == 'median':
                    features['median'] = float(np.median(gray))
                elif feat_type == 'area':
                    features['area'] = int(gray.size)
            except Exception as e:
                print(f"[ROIConfig] 计算特征失败 {feat_type}: {e}")
        
        return features
    
    def update_layer_features(self, layer: int, image: np.ndarray, is_start: bool = True):
        """更新层的特征数据
        
        Args:
            layer: 层号
            image: 当前帧图像（已畸变矫正）
            is_start: 是否为层开始（True: 层开始, False: 层结束）
        """
        if not self.rois:
            return
        
        suffix = '_start' if is_start else '_end'
        
        with self.lock:
            if layer not in self.layer_features:
                self.layer_features[layer] = {}
            
            for roi_id in self.rois:
                roi_image = self.extract_roi_image(image, roi_id)
                features = self.calculate_features(roi_image)
                
                for feat_name, value in features.items():
                    key = f"{roi_id}_{feat_name}{suffix}"
                    self.layer_features[layer][key] = value
                    
                    # 同时添加到历史数据
                    if roi_id not in self.features:
                        self.features[roi_id] = []
                    self.features[roi_id].append(value)
    
    def get_layer_features(self, layer: int) -> Dict[str, float]:
        """获取指定层的特征数据"""
        with self.lock:
            return self.layer_features.get(layer, {}).copy()
    
    def get_feature_history(self, roi_id: str, feature_name: str = 'mean') -> List[float]:
        """获取特征历史数据"""
        with self.lock:
            return self.features.get(roi_id, []).copy()
    
    def clear_history(self):
        """清除历史数据"""
        with self.lock:
            self.features.clear()
            self.layer_features.clear()


# 全局ROI配置实例
_roi_config_instance: Optional[ROIConfig] = None
_roi_config_lock = threading.Lock()


def get_roi_config(config_path: str = None) -> ROIConfig:
    """获取ROI配置实例（单例）"""
    global _roi_config_instance
    
    with _roi_config_lock:
        if _roi_config_instance is None:
            _roi_config_instance = ROIConfig(config_path)
        elif config_path:
            _roi_config_instance.load_config(config_path)
        
        return _roi_config_instance


def reset_roi_config():
    """重置ROI配置实例"""
    global _roi_config_instance
    
    with _roi_config_lock:
        _roi_config_instance = None
