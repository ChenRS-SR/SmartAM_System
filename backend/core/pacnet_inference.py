"""
PacNet 模型推理模块 (PACF-NET)
=============================
多模态融合缺陷检测/参数预测推理引擎

模型输入 (4模态):
- ids: IDS随轴相机 (448×448, RGB)
- computer: 旁轴RGB相机 (224×224, RGB)  
- fotric: 伪彩色热像 (224×224, RGB)
- thermal: 灰度温度矩阵 (224×224, 单通道)
- params: 工艺参数 (10维，标准化)

模型输出 (4任务，每任务3分类):
- flow_rate: 流量 (Low/Normal/High)
- feed_rate: 进给速度 (Low/Normal/High)
- z_offset: Z轴偏移 (Low/Normal/High)
- hot_end: 热端温度 (Low/Normal/High)

作者: 基于 pacnet_project 模型封装
"""

import os
import sys
import time
import pickle
import logging
import cv2
import numpy as np
from typing import Dict, Optional, Tuple, List, Any
from pathlib import Path
from dataclasses import dataclass
from collections import deque
import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
import torchvision.transforms as transforms

# 配置日志
logger = logging.getLogger(__name__)

# ========== 路径配置 ==========
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PACNET_PATH = PROJECT_ROOT / "pacnet_project"

if str(PACNET_PATH) not in sys.path:
    sys.path.insert(0, str(PACNET_PATH))

# 导入模型定义
try:
    from model import PACFNet
    MODEL_AVAILABLE = True
    logger.info("[PacNet] 模型定义加载成功")
except ImportError as e:
    MODEL_AVAILABLE = False
    logger.error(f"[PacNet] 模型定义加载失败: {e}")

# 导入参数标准化器
try:
    from dataset import ParameterScaler
    SCALER_AVAILABLE = True
except ImportError:
    SCALER_AVAILABLE = False
    logger.warning("[PacNet] ParameterScaler 不可用")


# ========== 数据模型 ==========

@dataclass
class PredictionResult:
    """预测结果数据类"""
    # 预测类别 (0=Low, 1=Normal, 2=High)
    flow_rate_class: int = 1
    feed_rate_class: int = 1
    z_offset_class: int = 1
    hot_end_class: int = 1
    
    # 类别名称
    flow_rate_label: str = "Normal"
    feed_rate_label: str = "Normal"
    z_offset_label: str = "Normal"
    hot_end_label: str = "Normal"
    
    # 置信度
    flow_rate_conf: float = 0.0
    feed_rate_conf: float = 0.0
    z_offset_conf: float = 0.0
    hot_end_conf: float = 0.0
    
    # 完整概率分布
    flow_rate_probs: Dict[str, float] = None
    feed_rate_probs: Dict[str, float] = None
    z_offset_probs: Dict[str, float] = None
    hot_end_probs: Dict[str, float] = None
    
    # 推理时间
    inference_time_ms: float = 0.0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.flow_rate_probs is None:
            self.flow_rate_probs = {}
        if self.feed_rate_probs is None:
            self.feed_rate_probs = {}
        if self.z_offset_probs is None:
            self.z_offset_probs = {}
        if self.hot_end_probs is None:
            self.hot_end_probs = {}
    
    def to_dict(self) -> Dict:
        """转换为字典格式（用于JSON序列化）"""
        return {
            "flow_rate": {
                "class": self.flow_rate_class,
                "label": self.flow_rate_label,
                "confidence": self.flow_rate_conf,
                "probabilities": self.flow_rate_probs
            },
            "feed_rate": {
                "class": self.feed_rate_class,
                "label": self.feed_rate_label,
                "confidence": self.feed_rate_conf,
                "probabilities": self.feed_rate_probs
            },
            "z_offset": {
                "class": self.z_offset_class,
                "label": self.z_offset_label,
                "confidence": self.z_offset_conf,
                "probabilities": self.z_offset_probs
            },
            "hot_end": {
                "class": self.hot_end_class,
                "label": self.hot_end_label,
                "confidence": self.hot_end_conf,
                "probabilities": self.hot_end_probs
            },
            "inference_time_ms": self.inference_time_ms,
            "timestamp": self.timestamp
        }
    
    def get_summary(self) -> str:
        """获取预测摘要字符串"""
        lines = [
            "=" * 50,
            f"Flow Rate   : {self.flow_rate_label:6s} (置信度: {self.flow_rate_conf:.1%})",
            f"Feed Rate   : {self.feed_rate_label:6s} (置信度: {self.feed_rate_conf:.1%})",
            f"Z Offset    : {self.z_offset_label:6s} (置信度: {self.z_offset_conf:.1%})",
            f"Hotend Temp : {self.hot_end_label:6s} (置信度: {self.hot_end_conf:.1%})",
            f"推理时间: {self.inference_time_ms:.1f}ms",
            "=" * 50
        ]
        return "\n".join(lines)


# ========== 图像预处理 ==========

class ImagePreprocessor:
    """图像预处理器"""
    
    # 类别名称映射
    CLASS_NAMES = ['Low', 'Normal', 'High']
    
    def __init__(self):
        # Computer 相机 (旁轴RGB, 224x224)
        self.computer_transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # Fotric 伪彩色热像 (224x224)
        self.fotric_transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])
        
        # IDS 相机 (随轴, 448x448)
        self.ids_transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])
    
    def preprocess_computer(self, image: np.ndarray) -> torch.Tensor:
        """预处理旁轴相机图像 (224x224)"""
        # 输入: OpenCV BGR 格式 (H, W, 3)
        # 转换为 PIL RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # Resize 到 224x224
        pil_image = pil_image.resize((224, 224), Image.LANCZOS)
        
        # 应用变换
        tensor = self.computer_transform(pil_image)
        return tensor
    
    def preprocess_fotric(self, image: np.ndarray) -> torch.Tensor:
        """预处理伪彩色热像 (224x224)"""
        # 输入: OpenCV BGR 格式
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        pil_image = pil_image.resize((224, 224), Image.LANCZOS)
        tensor = self.fotric_transform(pil_image)
        return tensor
    
    def preprocess_ids(self, image: np.ndarray) -> torch.Tensor:
        """预处理IDS相机图像 (448x448)"""
        # 输入: OpenCV BGR 格式
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        pil_image = pil_image.resize((448, 448), Image.LANCZOS)
        tensor = self.ids_transform(pil_image)
        return tensor
    
    def preprocess_thermal(self, thermal_matrix: np.ndarray) -> torch.Tensor:
        """
        预处理灰度温度矩阵 (224x224)
        
        Args:
            thermal_matrix: 温度矩阵 (H, W)，float32
        
        Returns:
            tensor: (1, 224, 224)
        """
        # 归一化到 [0, 1]
        temp_min, temp_max = thermal_matrix.min(), thermal_matrix.max()
        if temp_max > temp_min:
            normalized = (thermal_matrix - temp_min) / (temp_max - temp_min)
        else:
            normalized = np.zeros_like(thermal_matrix)
        
        # Resize 到 224x224
        resized = cv2.resize(normalized, (224, 224), interpolation=cv2.INTER_LINEAR)
        
        # 转换为 tensor (1, H, W)
        tensor = torch.from_numpy(resized).float().unsqueeze(0)
        return tensor


# ========== 推理引擎 ==========

class PacNetInference:
    """
    PacNet 推理引擎
    
    支持实时推理，带推理频率控制（避免GPU过载）
    """
    
    def __init__(
        self,
        model_path: str = None,
        device: str = "cuda",
        inference_interval: float = 0.2,  # 默认 200ms (5Hz)
        enable_gpu: bool = True
    ):
        """
        初始化推理引擎
        
        Args:
            model_path: 模型文件路径 (.pt)，默认使用项目中的模型
            device: 运行设备 (cuda/cpu)
            inference_interval: 推理间隔（秒），默认 0.2s = 5Hz
            enable_gpu: 是否启用 GPU
        """
        self.device = torch.device(device if enable_gpu and torch.cuda.is_available() else 'cpu')
        self.inference_interval = inference_interval
        self.model_path = model_path or self._get_default_model_path()
        
        # 预处理器
        self.preprocessor = ImagePreprocessor()
        
        # 参数标准化器
        self.scaler = self._load_scaler()
        
        # 模型
        self.model = None
        self.is_loaded = False
        
        # 推理控制
        self._last_inference_time = 0
        self._latest_result: Optional[PredictionResult] = None
        
        # 历史缓存（用于平滑结果）
        self._history: deque = deque(maxlen=5)
        
        logger.info(f"[PacNet] 推理引擎初始化完成")
        logger.info(f"  设备: {self.device}")
        logger.info(f"  推理间隔: {inference_interval*1000:.0f}ms ({1/inference_interval:.1f}Hz)")
        logger.info(f"  模型路径: {self.model_path}")
    
    def _get_default_model_path(self) -> str:
        """获取默认模型路径"""
        weights_dir = Path(__file__).parent.parent / "weights"
        
        # 1. 优先查找 ParamDriven_CrossAttn 变体8模型（最新训练）
        for subdir in weights_dir.iterdir():
            if subdir.is_dir() and 'ParamDriven' in subdir.name:
                model_file = subdir / "best_model.pth"
                if model_file.exists():
                    logger.info(f"[PacNet] 找到变体8模型: {model_file}")
                    return str(model_file)
        
        # 2. 查找任何子目录中的 best_model.pth
        for subdir in weights_dir.iterdir():
            if subdir.is_dir():
                model_file = subdir / "best_model.pth"
                if model_file.exists():
                    logger.info(f"[PacNet] 找到模型: {model_file}")
                    return str(model_file)
        
        # 3. 优先使用项目内的模型文件
        local_path = weights_dir / "model_full.pt"
        if local_path.exists():
            return str(local_path)
        
        # 4. 回退到外部项目路径（兼容旧配置）
        external_path = PACNET_PATH / "saved_models" / "full" / "model_full.pt"
        if external_path.exists():
            return str(external_path)
        
        # 如果都不存在，返回项目内路径（让后续报错更清晰）
        return str(local_path)
    
    def _load_scaler(self) -> Optional[Any]:
        """加载参数标准化器"""
        # 优先使用项目内的 scaler
        local_scaler = Path(__file__).parent.parent / "weights" / "scaler.pkl"
        if local_scaler.exists():
            scaler_path = local_scaler
        else:
            # 回退到模型同目录
            scaler_path = Path(self.model_path).parent / "scaler.pkl"
        
        if not scaler_path.exists():
            logger.warning(f"[PacNet] 未找到 scaler: {scaler_path}")
            return None
        
        try:
            with open(scaler_path, 'rb') as f:
                loaded_data = pickle.load(f)
            
            # 兼容两种格式：dict 或 ParameterScaler 对象
            if isinstance(loaded_data, dict) and SCALER_AVAILABLE:
                scaler = ParameterScaler()
                scaler.scalers = loaded_data
                logger.info("[PacNet] Scaler 加载成功 (dict格式)")
                return scaler
            else:
                logger.info("[PacNet] Scaler 加载成功")
                return loaded_data
                
        except Exception as e:
            logger.error(f"[PacNet] Scaler 加载失败: {e}")
            return None
    
    def load_model(self) -> bool:
        """加载模型权重"""
        if not MODEL_AVAILABLE:
            logger.error("[PacNet] 模型定义不可用，无法加载")
            return False
        
        if not os.path.exists(self.model_path):
            logger.error(f"[PacNet] 模型文件不存在: {self.model_path}")
            return False
        
        try:
            logger.info(f"[PacNet] 正在加载模型...")
            
            # 检测变体类型
            variant = self._detect_variant()
            logger.info(f"[PacNet] 检测到变体: {variant}")
            
            # 创建模型
            self.model = PACFNet(variant=variant).to(self.device)
            
            # 加载权重
            checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
            
            if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)
            
            self.model.eval()
            self.is_loaded = True
            
            logger.info(f"[PacNet] 模型加载成功: {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"[PacNet] 模型加载失败: {e}")
            self.model = None
            self.is_loaded = False
            return False
    
    def _detect_variant(self) -> str:
        """从模型路径检测变体类型"""
        path_str = str(self.model_path).lower()
        
        # 变体8: 参数驱动Cross-Attention (ParamDriven_CrossAttn)
        # 在模型定义中，'full' 变体已经包含参数驱动的 Cross-Attention
        if 'paramdriven' in path_str or 'param_driven' in path_str:
            logger.info("[PacNet] 检测到变体8: 参数驱动Cross-Attention -> 使用 'full' 变体")
            return 'full'
        
        # 其他变体
        if 'concat' in path_str:
            return 'concat_only'
        elif 'no-mmd' in path_str or 'no_mmd' in path_str:
            return 'no_mmd'
        elif 'rgb-only' in path_str or 'rgb_only' in path_str:
            return 'rgb_only'
        elif 'ids-only' in path_str or 'ids_only' in path_str:
            return 'ids_only'
        
        # 默认使用完整模型
        return 'full'
    
    def should_infer(self) -> bool:
        """判断是否应该执行推理（基于时间间隔）"""
        current_time = time.time()
        time_since_last = current_time - self._last_inference_time
        return time_since_last >= self.inference_interval
    
    def inference(
        self,
        ids_frame: Optional[np.ndarray] = None,
        computer_frame: Optional[np.ndarray] = None,
        fotric_frame: Optional[np.ndarray] = None,
        thermal_matrix: Optional[np.ndarray] = None,
        params: Optional[np.ndarray] = None,
        force: bool = False
    ) -> Optional[PredictionResult]:
        """
        执行推理
        
        Args:
            ids_frame: IDS相机图像 (H, W, 3) BGR
            computer_frame: 旁轴相机图像 (H, W, 3) BGR
            fotric_frame: 伪彩色热像 (H, W, 3) BGR
            thermal_matrix: 灰度温度矩阵 (H, W)
            params: 工艺参数 (10,) - [x, y, z, flow, feed, z_off, hotend, t_min, t_max, t_avg]
            force: 强制推理（忽略时间间隔）
        
        Returns:
            PredictionResult: 预测结果，未到推理时间返回缓存结果
        """
        # 检查是否应该推理
        if not force and not self.should_infer():
            return self._latest_result
        
        # 检查模型是否加载
        if not self.is_loaded or self.model is None:
            logger.warning("[PacNet] 模型未加载，跳过推理")
            return None
        
        # 检查输入是否完整
        if any(x is None for x in [ids_frame, computer_frame, fotric_frame, thermal_matrix]):
            logger.debug("[PacNet] 输入数据不完整，跳过推理")
            return None
        
        try:
            start_time = time.time()
            
            # 预处理图像
            ids_tensor = self.preprocessor.preprocess_ids(ids_frame).unsqueeze(0)
            computer_tensor = self.preprocessor.preprocess_computer(computer_frame).unsqueeze(0)
            fotric_tensor = self.preprocessor.preprocess_fotric(fotric_frame).unsqueeze(0)
            thermal_tensor = self.preprocessor.preprocess_thermal(thermal_matrix).unsqueeze(0)
            
            # 预处理参数
            if params is not None and self.scaler is not None:
                params_normalized = self.scaler.transform(params)
                params_tensor = torch.from_numpy(params_normalized).float().unsqueeze(0)
            else:
                # 使用默认参数
                params_tensor = torch.zeros(1, 10).float()
            
            # 移动到设备
            batch_data = {
                'ids': ids_tensor.to(self.device),
                'computer': computer_tensor.to(self.device),
                'fotric': fotric_tensor.to(self.device),
                'thermal': thermal_tensor.to(self.device),
                'params': params_tensor.to(self.device)
            }
            
            # 推理
            with torch.no_grad():
                outputs = self.model(batch_data, labels=None)
            
            # 解析结果
            result = self._parse_outputs(outputs)
            result.inference_time_ms = (time.time() - start_time) * 1000
            result.timestamp = time.time()
            
            # 更新缓存
            self._latest_result = result
            self._last_inference_time = time.time()
            self._history.append(result)
            
            logger.debug(f"[PacNet] 推理完成，耗时: {result.inference_time_ms:.1f}ms")
            return result
            
        except Exception as e:
            logger.error(f"[PacNet] 推理失败: {e}")
            return None
    
    def _parse_outputs(self, outputs: Dict) -> PredictionResult:
        """解析模型输出"""
        result = PredictionResult()
        
        task_names = ['flow_rate', 'feed_rate', 'z_offset', 'hot_end']
        
        for i, task in enumerate(task_names):
            # 获取概率分布
            probs = torch.softmax(outputs[task], dim=1).cpu().numpy()[0]
            pred_class = int(torch.argmax(outputs[task], dim=1).item())
            confidence = float(probs[pred_class])
            
            # 设置结果
            if i == 0:
                result.flow_rate_class = pred_class
                result.flow_rate_label = self.preprocessor.CLASS_NAMES[pred_class]
                result.flow_rate_conf = confidence
                result.flow_rate_probs = {
                    self.preprocessor.CLASS_NAMES[j]: float(probs[j])
                    for j in range(3)
                }
            elif i == 1:
                result.feed_rate_class = pred_class
                result.feed_rate_label = self.preprocessor.CLASS_NAMES[pred_class]
                result.feed_rate_conf = confidence
                result.feed_rate_probs = {
                    self.preprocessor.CLASS_NAMES[j]: float(probs[j])
                    for j in range(3)
                }
            elif i == 2:
                result.z_offset_class = pred_class
                result.z_offset_label = self.preprocessor.CLASS_NAMES[pred_class]
                result.z_offset_conf = confidence
                result.z_offset_probs = {
                    self.preprocessor.CLASS_NAMES[j]: float(probs[j])
                    for j in range(3)
                }
            elif i == 3:
                result.hot_end_class = pred_class
                result.hot_end_label = self.preprocessor.CLASS_NAMES[pred_class]
                result.hot_end_conf = confidence
                result.hot_end_probs = {
                    self.preprocessor.CLASS_NAMES[j]: float(probs[j])
                    for j in range(3)
                }
        
        return result
    
    def get_latest_result(self) -> Optional[PredictionResult]:
        """获取最新推理结果"""
        return self._latest_result
    
    def get_smoothed_result(self) -> Optional[PredictionResult]:
        """
        获取平滑后的结果（历史平均）
        用于减少单帧波动
        """
        if len(self._history) < 3:
            return self._latest_result
        
        # 简单多数投票
        from collections import Counter
        
        result = PredictionResult()
        
        # 对各任务分别投票
        for task_idx, task_name in enumerate(['flow_rate', 'feed_rate', 'z_offset', 'hot_end']):
            classes = [getattr(r, f'{task_name}_class') for r in self._history]
            most_common = Counter(classes).most_common(1)[0][0]
            
            if task_idx == 0:
                result.flow_rate_class = most_common
                result.flow_rate_label = self.preprocessor.CLASS_NAMES[most_common]
            elif task_idx == 1:
                result.feed_rate_class = most_common
                result.feed_rate_label = self.preprocessor.CLASS_NAMES[most_common]
            elif task_idx == 2:
                result.z_offset_class = most_common
                result.z_offset_label = self.preprocessor.CLASS_NAMES[most_common]
            elif task_idx == 3:
                result.hot_end_class = most_common
                result.hot_end_label = self.preprocessor.CLASS_NAMES[most_common]
        
        return result
    
    def set_inference_interval(self, interval: float):
        """设置推理间隔"""
        self.inference_interval = interval
        logger.info(f"[PacNet] 推理间隔设置为: {interval*1000:.0f}ms")


# ========== 单例模式 ==========

_inference_engine: Optional[PacNetInference] = None


def get_inference_engine(
    model_path: Optional[str] = None,
    device: str = "cuda",
    inference_interval: float = 0.2,
    **kwargs
) -> PacNetInference:
    """获取推理引擎单例"""
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = PacNetInference(
            model_path=model_path,
            device=device,
            inference_interval=inference_interval,
            **kwargs
        )
        _inference_engine.load_model()
    return _inference_engine


def reset_inference_engine():
    """重置推理引擎"""
    global _inference_engine
    _inference_engine = None


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("PacNet 推理模块测试")
    print("=" * 60)
    
    # 创建推理引擎
    engine = PacNetInference(
        inference_interval=0.2,  # 5Hz
        device="cuda"
    )
    
    # 加载模型
    if engine.load_model():
        print("\n[测试] 模型加载成功")
        
        # 创建模拟数据
        ids_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        computer_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        fotric_frame = np.random.randint(0, 255, (360, 640, 3), dtype=np.uint8)
        thermal_matrix = np.random.randn(480, 640).astype(np.float32) * 50 + 200
        params = np.array([100, 100, 5, 100, 100, 0, 200, 25, 200, 100], dtype=np.float32)
        
        print("\n[测试] 执行推理...")
        result = engine.inference(
            ids_frame=ids_frame,
            computer_frame=computer_frame,
            fotric_frame=fotric_frame,
            thermal_matrix=thermal_matrix,
            params=params,
            force=True
        )
        
        if result:
            print("\n" + result.get_summary())
        else:
            print("\n[测试] 推理失败")
    else:
        print("\n[测试] 模型加载失败")
    
    print("\n[测试] 已完成")
