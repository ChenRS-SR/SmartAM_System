"""
调控策略 API
============
提供闭环控制相关的接口：
- PID 参数设置
- 手动控制
- 启停自动控制
- 查看调控历史
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()


class PIDParams(BaseModel):
    """PID 参数模型"""
    kp: float
    ki: float
    kd: float
    target_temp: float


class ManualControlRequest(BaseModel):
    """手动控制请求"""
    flow_rate_delta: Optional[int] = 0  # 流量调整值
    feed_rate_delta: Optional[int] = 0  # 速度调整值
    z_offset_delta: Optional[float] = 0.0  # Z偏移调整值
    hotend_delta: Optional[int] = 0  # 温度调整值


class RegulationThresholdRequest(BaseModel):
    """调控阈值设置"""
    threshold: float  # 0.0 - 1.0


@router.get("/status")
async def get_control_status():
    """获取闭环控制状态"""
    from main import daq
    
    if not daq or not hasattr(daq, 'closed_loop') or not daq.closed_loop:
        return {
            "available": False,
            "message": "闭环控制器不可用"
        }
    
    return daq.closed_loop.get_status()


@router.post("/start")
async def start_closed_loop():
    """启动闭环调控"""
    from main import daq
    
    if not daq or not hasattr(daq, 'closed_loop') or not daq.closed_loop:
        raise HTTPException(status_code=503, detail="闭环控制器不可用")
    
    daq.closed_loop.start()
    return {"message": "闭环调控已启动", "status": "monitoring"}


@router.post("/stop")
async def stop_closed_loop():
    """停止闭环调控"""
    from main import daq
    
    if not daq or not hasattr(daq, 'closed_loop') or not daq.closed_loop:
        raise HTTPException(status_code=503, detail="闭环控制器不可用")
    
    daq.closed_loop.stop()
    return {"message": "闭环调控已停止", "status": "idle"}


@router.post("/pause")
async def pause_closed_loop():
    """暂停闭环调控（继续收集数据但不执行调控）"""
    from main import daq
    
    if not daq or not hasattr(daq, 'closed_loop') or not daq.closed_loop:
        raise HTTPException(status_code=503, detail="闭环控制器不可用")
    
    daq.closed_loop.pause()
    return {"message": "闭环调控已暂停", "status": "paused"}


@router.get("/pid_params")
async def get_pid_params():
    """获取当前 PID 参数"""
    from main import daq
    
    # 优先从 SLMController 获取
    if daq and hasattr(daq, 'slm_controller') and daq.slm_controller:
        params = daq.slm_controller.get_pid_params()
        return {
            "source": "slm_controller",
            "kp": params["kp"],
            "ki": params["ki"],
            "kd": params["kd"],
            "target_temp": params["target_temp"]
        }
    
    # 回退到默认值
    return {
        "source": "default",
        "kp": 0.5,
        "ki": 0.05,
        "kd": 0.02,
        "target_temp": 200.0
    }


@router.post("/pid_params")
async def set_pid_params(params: PIDParams):
    """设置 PID 参数"""
    from main import daq
    
    # 更新到 SLMController
    if daq and hasattr(daq, 'slm_controller') and daq.slm_controller:
        daq.slm_controller.set_pid_params(
            kp=params.kp,
            ki=params.ki,
            kd=params.kd,
            target_temp=params.target_temp
        )
        return {
            "message": "PID 参数已更新到 SLMController",
            "params": params.dict(),
            "source": "slm_controller"
        }
    
    # 如果没有 SLMController，仅返回参数
    return {
        "message": "PID 参数已接收（SLMController 未启动）",
        "params": params.dict(),
        "source": "default"
    }


@router.post("/threshold")
async def set_regulation_threshold(req: RegulationThresholdRequest):
    """设置调控置信度阈值"""
    from main import daq
    
    if not daq or not hasattr(daq, 'closed_loop') or not daq.closed_loop:
        raise HTTPException(status_code=503, detail="闭环控制器不可用")
    
    if req.threshold < 0 or req.threshold > 1:
        raise HTTPException(status_code=400, detail="阈值必须在 0-1 之间")
    
    daq.closed_loop.set_threshold(req.threshold)
    return {
        "message": "调控阈值已更新",
        "threshold": req.threshold
    }


@router.post("/manual")
async def manual_control(req: ManualControlRequest):
    """手动控制打印参数"""
    from main import daq
    
    if not daq or not hasattr(daq, 'closed_loop') or not daq.closed_loop:
        raise HTTPException(status_code=503, detail="闭环控制器不可用")
    
    octoprint = daq.closed_loop.octoprint
    results = []
    
    # 流量调整
    if req.flow_rate_delta != 0:
        current = octoprint.current_params.get("flow_rate", 100)
        new_value = current + req.flow_rate_delta
        new_value = max(20, min(200, new_value))
        success = octoprint.set_flow_rate(int(new_value))
        results.append({
            "parameter": "flow_rate",
            "old_value": current,
            "new_value": new_value,
            "success": success
        })
    
    # 速度调整
    if req.feed_rate_delta != 0:
        current = octoprint.current_params.get("feed_rate", 100)
        new_value = current + req.feed_rate_delta
        new_value = max(20, min(200, new_value))
        success = octoprint.set_feed_rate(int(new_value))
        results.append({
            "parameter": "feed_rate",
            "old_value": current,
            "new_value": new_value,
            "success": success
        })
    
    # Z偏移调整
    if req.z_offset_delta != 0:
        success = octoprint.adjust_z_offset(req.z_offset_delta)
        results.append({
            "parameter": "z_offset",
            "delta": req.z_offset_delta,
            "cumulative": octoprint.z_offset_cumulative,
            "success": success
        })
    
    # 温度调整
    if req.hotend_delta != 0:
        current = octoprint.current_params.get("hotend_temp", 200)
        new_value = current + req.hotend_delta
        new_value = max(150, min(260, new_value))
        success = octoprint.set_hotend_temp(int(new_value))
        results.append({
            "parameter": "hotend_temp",
            "old_value": current,
            "new_value": new_value,
            "success": success
        })
    
    return {
        "message": "手动控制指令已执行",
        "adjustments": results
    }


@router.get("/history")
async def get_regulation_history(limit: int = 100):
    """获取调控历史记录"""
    from main import daq
    
    if not daq or not hasattr(daq, 'closed_loop') or not daq.closed_loop:
        raise HTTPException(status_code=503, detail="闭环控制器不可用")
    
    history = daq.closed_loop.get_regulation_history(limit)
    
    return {
        "count": len(history),
        "records": [
            {
                "timestamp": r.timestamp,
                "datetime": datetime.fromtimestamp(r.timestamp).isoformat(),
                "parameter": r.parameter.value,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "adjustment": r.adjustment,
                "confidence": r.confidence,
                "gcode": r.gcode_sent,
                "success": r.success
            }
            for r in history
        ]
    }


@router.post("/export")
async def export_regulation_history(filepath: Optional[str] = None):
    """导出调控历史到文件"""
    from main import daq
    from datetime import datetime
    
    if not daq or not hasattr(daq, 'closed_loop') or not daq.closed_loop:
        raise HTTPException(status_code=503, detail="闭环控制器不可用")
    
    if filepath is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"data/regulation_history_{timestamp}.json"
    
    daq.closed_loop.export_history(filepath)
    
    return {
        "message": "调控历史已导出",
        "filepath": filepath
    }
