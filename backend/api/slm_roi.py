"""
SLM ROI区域配置和特征计算API
==============================
"""

from fastapi import APIRouter, UploadFile, File, Form, Query, Body
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import json
import shutil
from pathlib import Path

router = APIRouter(prefix="/slm/roi", tags=["SLM ROI"])

# 全局ROI配置路径
ROI_CONFIG_PATH = Path("config/roi_config.json")


def ensure_config_dir():
    """确保配置目录存在"""
    ROI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


@router.post("/load")
async def load_roi_config(data: Dict[str, Any] = Body(...)):
    """加载ROI配置文件"""
    try:
        config_path = data.get('config_path', '')
        if not config_path:
            return {"success": False, "message": "缺少config_path参数"}
        
        path = Path(config_path)
        if not path.exists():
            return {"success": False, "message": f"配置文件不存在: {config_path}"}
        
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 同时加载到全局配置
        from core.slm.roi_config import get_roi_config
        roi_config = get_roi_config()
        roi_config.load_config(str(path))
        
        return {
            "success": True,
            "config": config,
            "message": "配置加载成功"
        }
        
    except Exception as e:
        return {"success": False, "message": f"加载失败: {str(e)}"}


@router.post("/save")
async def save_roi_config(data: Dict[str, Any] = Body(...)):
    """保存ROI配置"""
    try:
        config = data.get('config', {})
        config_path = data.get('config_path', 'config/roi_config.json')
        
        if not config:
            return {"success": False, "message": "缺少config参数"}
        
        ensure_config_dir()
        
        path = Path(config_path)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 同时更新全局配置
        from core.slm.roi_config import get_roi_config
        roi_config = get_roi_config()
        roi_config.load_config(str(path))
        
        return {
            "success": True,
            "config_path": str(path),
            "message": "配置保存成功"
        }
        
    except Exception as e:
        return {"success": False, "message": f"保存失败: {str(e)}"}


@router.get("/config")
async def get_roi_config():
    """获取当前ROI配置"""
    try:
        from core.slm.roi_config import get_roi_config as get_config
        roi_config = get_config()
        
        return {
            "success": True,
            "config": {
                "rois": roi_config.get_rois(),
                "features": getattr(roi_config, 'feature_types', ['mean', 'std']),
                "update_mode": getattr(roi_config, 'update_mode', 'layer')
            },
            "config_path": str(ROI_CONFIG_PATH) if ROI_CONFIG_PATH.exists() else None
        }
        
    except Exception as e:
        return {"success": False, "message": f"获取配置失败: {str(e)}"}


@router.get("/features")
async def get_roi_features(
    roi_id: str = Query(..., description="ROI区域ID"),
    feature: str = Query("mean", description="特征类型"),
    layer: int = Query(0, description="层号")
):
    """获取ROI区域的特征值"""
    try:
        from core.slm.roi_config import get_roi_config
        roi_config = get_roi_config()
        
        # 获取该层的特征数据
        layer_features = roi_config.get_layer_features(layer)
        
        # 构建特征键名
        feature_key = f"{roi_id}_{feature}"
        
        # 先尝试获取层结束时的特征
        value = layer_features.get(f"{feature_key}_end")
        
        # 如果没有，尝试获取层开始时的特征
        if value is None:
            value = layer_features.get(f"{feature_key}_start")
        
        if value is not None:
            return {
                "success": True,
                "roi_id": roi_id,
                "feature": feature,
                "layer": layer,
                "value": value
            }
        else:
            return {
                "success": False,
                "message": f"未找到层 {layer} 的特征数据"
            }
        
    except Exception as e:
        return {"success": False, "message": f"获取特征失败: {str(e)}"}


@router.get("/features/history")
async def get_feature_history(
    roi_id: str = Query(..., description="ROI区域ID"),
    feature: str = Query("mean", description="特征类型")
):
    """获取特征历史数据"""
    try:
        from core.slm.roi_config import get_roi_config
        roi_config = get_roi_config()
        
        history = roi_config.get_feature_history(roi_id, feature)
        
        return {
            "success": True,
            "roi_id": roi_id,
            "feature": feature,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        return {"success": False, "message": f"获取历史数据失败: {str(e)}"}


@router.post("/update")
async def update_roi_features(
    layer: int = Form(..., description="层号"),
    is_start: bool = Form(True, description="是否为层开始")
):
    """手动触发ROI特征更新（从当前帧）"""
    try:
        from core.slm import get_slm_acquisition
        from core.slm.roi_config import get_roi_config
        
        acquisition = get_slm_acquisition(create_if_none=False)
        if acquisition is None:
            return {"success": False, "message": "采集系统未启动"}
        
        # 获取当前帧
        frame = acquisition.camera_manager.get_frame('CH1')
        if frame is None:
            return {"success": False, "message": "无法获取当前帧"}
        
        # 更新ROI特征
        roi_config = get_roi_config()
        roi_config.update_layer_features(layer, frame, is_start)
        
        return {
            "success": True,
            "layer": layer,
            "is_start": is_start,
            "message": "特征更新成功"
        }
        
    except Exception as e:
        return {"success": False, "message": f"更新失败: {str(e)}"}


@router.post("/clear")
async def clear_roi_history():
    """清除ROI特征历史数据"""
    try:
        from core.slm.roi_config import get_roi_config
        roi_config = get_roi_config()
        roi_config.clear_history()
        
        return {"success": True, "message": "历史数据已清除"}
        
    except Exception as e:
        return {"success": False, "message": f"清除失败: {str(e)}"}


@router.post("/upload")
async def upload_roi_config(file: UploadFile = File(...)):
    """上传ROI配置文件"""
    try:
        ensure_config_dir()
        
        # 保存上传的文件
        config_path = ROI_CONFIG_PATH.parent / file.filename
        with open(config_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 更新全局配置
        from core.slm.roi_config import get_roi_config
        roi_config = get_roi_config()
        roi_config.load_config(str(config_path))
        
        return {
            "success": True,
            "config": config,
            "config_path": str(config_path),
            "message": "配置上传成功"
        }
        
    except Exception as e:
        return {"success": False, "message": f"上传失败: {str(e)}"}
