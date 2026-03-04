"""
打印机控制 API
- 连接/断开打印机
- 获取打印状态
- 发送 G-code 指令
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class PrinterCommand(BaseModel):
    """G-code 指令模型"""
    command: str
    parameters: Optional[dict] = None


class PrinterStatus(BaseModel):
    """打印机状态模型"""
    connected: bool
    printing: bool
    progress: float  # 0-100%
    nozzle_temp: float
    bed_temp: float
    position: dict  # x, y, z


@router.post("/connect")
async def connect_printer(port: str = "/dev/ttyUSB0", baudrate: int = 115200):
    """连接打印机串口"""
    # TODO: 实现串口连接逻辑
    return {"message": f"尝试连接打印机: {port}@{baudrate}"}


@router.post("/disconnect")
async def disconnect_printer():
    """断开打印机连接"""
    # TODO: 实现断开连接逻辑
    return {"message": "打印机已断开"}


@router.get("/status", response_model=PrinterStatus)
async def get_printer_status():
    """获取打印机当前状态（从 OctoPrint）"""
    from main import daq
    
    if not daq:
        return PrinterStatus(
            connected=False,
            printing=False,
            progress=0.0,
            nozzle_temp=0.0,
            bed_temp=0.0,
            position={"x": 0, "y": 0, "z": 0}
        )
    
    # 从 DAQ 获取打印机状态
    try:
        printer_status = daq.get_printer_status()
        return PrinterStatus(
            connected=printer_status.get("connected", False),
            printing=printer_status.get("state") == "Printing",
            progress=printer_status.get("progress", 0.0),
            nozzle_temp=printer_status.get("hotend_actual", 0.0),
            bed_temp=printer_status.get("bed_actual", 0.0),
            position=printer_status.get("position", {"x": 0, "y": 0, "z": 0})
        )
    except Exception as e:
        return PrinterStatus(
            connected=False,
            printing=False,
            progress=0.0,
            nozzle_temp=0.0,
            bed_temp=0.0,
            position={"x": 0, "y": 0, "z": 0}
        )


def _get_api_key_from_env():
    """备用方案：从 .env 文件读取 API Key"""
    try:
        import os
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('OCTOPRINT_API_KEY='):
                        return line.split('=', 1)[1].strip()
    except Exception as e:
        print(f"[API Key] 读取 .env 失败: {e}")
    return None


@router.get("/temperature")
async def get_printer_temperature():
    """获取打印机当前温度（实时从 OctoPrint 获取，支持模拟模式）"""
    from main import daq
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    # 检查 OctoPrint 模拟模式
    if getattr(daq, '_octoprint_simulation_active', False) and daq._octoprint_simulator:
        status = daq._octoprint_simulator.get_printer_status()
        temp = status.get("temperature", {})
        return {
            "success": True,
            "simulation": True,
            "timestamp": datetime.now().isoformat(),
            "nozzle": {
                "actual": temp.get("tool0", {}).get("actual", 0),
                "target": temp.get("tool0", {}).get("target", 0)
            },
            "bed": {
                "actual": temp.get("bed", {}).get("actual", 0),
                "target": temp.get("bed", {}).get("target", 0)
            }
        }
    
    # 获取 API Key
    api_key = daq.config.octoprint_api_key
    print(f"[Temp] DAQ API Key: '{api_key[:20]}...' (len={len(api_key) if api_key else 0})")
    
    if not api_key or len(api_key) < 20:
        env_key = _get_api_key_from_env()
        print(f"[Temp] 从 .env 读取 Key: '{env_key[:20] if env_key else 'None'}...'")
        if env_key:
            api_key = env_key
    
    try:
        import requests
        url = f"{daq.config.octoprint_url}/api/printer"
        headers = {"X-Api-Key": api_key}
        
        print(f"[Temp] 请求 URL: {url}")
        print(f"[Temp] 使用 Key: {api_key[:30]}... (长度: {len(api_key)})")
        
        response = requests.get(url, headers=headers, timeout=5)
        
        print(f"[Temp] 响应状态: {response.status_code}")
        
        # 如果 403，打印详细错误信息
        if response.status_code == 403:
            print(f"[Temp] 403 响应内容: {response.text[:500]}")
            print(f"[Temp] 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            temp_data = data.get("temperature", {})
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "nozzle": {
                    "actual": temp_data.get("tool0", {}).get("actual", 0),
                    "target": temp_data.get("tool0", {}).get("target", 0)
                },
                "bed": {
                    "actual": temp_data.get("bed", {}).get("actual", 0),
                    "target": temp_data.get("bed", {}).get("target", 0)
                },
                "chamber": {
                    "actual": temp_data.get("chamber", {}).get("actual", 0),
                    "target": temp_data.get("chamber", {}).get("target", 0)
                } if temp_data.get("chamber") else None
            }
        elif response.status_code == 403:
            return {
                "success": False,
                "error": f"OctoPrint 403 禁止访问 - API Key 无效或权限不足。请检查: 1) API Key 是否正确 2) OctoPrint 是否启用了访问控制 3) 尝试重启 OctoPrint",
                "details": f"使用的 API Key: {daq.config.octoprint_api_key[:20]}...",
                "nozzle": {"actual": 0, "target": 0},
                "bed": {"actual": 0, "target": 0}
            }
        else:
            return {
                "success": False,
                "error": f"OctoPrint 返回错误: {response.status_code} - {response.text[:100]}",
                "nozzle": {"actual": 0, "target": 0},
                "bed": {"actual": 0, "target": 0}
            }
    except requests.exceptions.ConnectionError:
        # 连接失败且启用了自动回退
        if getattr(daq, 'config', None) and getattr(daq.config, 'octoprint_simulation_auto_fallback', False):
            logging.warning("[Temperature] OctoPrint 连接失败，自动启用模拟模式")
            daq._enable_octoprint_simulation()
            status = daq._octoprint_simulator.get_printer_status()
            temp = status.get("temperature", {})
            return {
                "success": True,
                "simulation": True,
                "auto_fallback": True,
                "timestamp": datetime.now().isoformat(),
                "nozzle": {
                    "actual": temp.get("tool0", {}).get("actual", 0),
                    "target": temp.get("tool0", {}).get("target", 0)
                },
                "bed": {
                    "actual": temp.get("bed", {}).get("actual", 0),
                    "target": temp.get("bed", {}).get("target", 0)
                }
            }
        
        return {
            "success": False,
            "error": f"无法连接到 OctoPrint ({daq.config.octoprint_url})，请检查 OctoPrint 是否运行",
            "nozzle": {"actual": 0, "target": 0},
            "bed": {"actual": 0, "target": 0}
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "nozzle": {"actual": 0, "target": 0},
            "bed": {"actual": 0, "target": 0}
        }


@router.post("/command")
async def send_command(cmd: PrinterCommand):
    """发送 G-code 指令"""
    # TODO: 实现 G-code 发送逻辑
    return {"message": f"发送指令: {cmd.command}", "status": "pending"}


@router.post("/pause")
async def pause_print():
    """暂停打印"""
    return {"message": "打印已暂停"}


@router.post("/resume")
async def resume_print():
    """恢复打印"""
    from main import daq
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    api_key = daq.config.octoprint_api_key
    if not api_key or len(api_key) < 20:
        api_key = _get_api_key_from_env()
    
    try:
        import requests
        url = f"{daq.config.octoprint_url}/api/job"
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json={"command": "pause", "action": "resume"}, timeout=5)
        
        if response.status_code == 204:
            return {"success": True, "message": "打印已恢复"}
        else:
            return {"success": False, "error": f"返回 {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/stop")
async def stop_print():
    """停止打印"""
    return {"message": "打印已停止"}


@router.get("/test")
async def test_printer_connection():
    """测试 OctoPrint 连接（支持模拟模式）"""
    from main import daq
    
    if not daq:
        return {
            "success": False,
            "error": "DAQ 系统未初始化"
        }
    
    # 检查 OctoPrint 模拟模式
    if getattr(daq, '_octoprint_simulation_active', False) and daq._octoprint_simulator:
        return {
            "success": True,
            "simulation": True,
            "message": "OctoPrint 模拟模式运行中",
            "octoprint_url": "simulation",
            "temperature": {
                "nozzle_actual": daq._octoprint_simulator._current_temps.get("hotend", 200),
                "bed_actual": daq._octoprint_simulator._current_temps.get("bed", 60)
            }
        }
    
    # 获取 API Key
    api_key = daq.config.octoprint_api_key
    print(f"[Test] DAQ API Key: '{api_key[:20]}...' (len={len(api_key) if api_key else 0})")
    
    if not api_key or len(api_key) < 20:
        env_key = _get_api_key_from_env()
        print(f"[Test] 从 .env 读取 Key: '{env_key[:20] if env_key else 'None'}...'")
        if env_key:
            api_key = env_key
    
    try:
        import requests
        url = f"{daq.config.octoprint_url}/api/printer"
        headers = {"X-Api-Key": api_key}
        
        print(f"[Test] 请求 URL: {url}")
        print(f"[Test] 使用 Key: {api_key[:30]}... (长度: {len(api_key)})")
        
        response = requests.get(url, headers=headers, timeout=5)
        
        print(f"[Test] 响应状态: {response.status_code}")
        
        # 如果 403，打印详细错误信息
        if response.status_code == 403:
            print(f"[Test] 403 响应内容: {response.text[:500]}")
            print(f"[Test] 响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            temp = data.get("temperature", {})
            return {
                "success": True,
                "message": "OctoPrint 连接成功",
                "octoprint_url": daq.config.octoprint_url,
                "api_key_preview": daq.config.octoprint_api_key[:10] + "...",
                "temperature": {
                    "nozzle_actual": temp.get("tool0", {}).get("actual", 0),
                    "bed_actual": temp.get("bed", {}).get("actual", 0)
                }
            }
        elif response.status_code == 403:
            return {
                "success": False,
                "error": "403 Forbidden - API Key 无效或权限不足",
                "details": {
                    "octoprint_url": daq.config.octoprint_url,
                    "api_key_preview": api_key[:10] + "..." if api_key else "None",
                    "suggestion": [
                        "1. 检查 OctoPrint 设置 → API → 启用 API 和 CORS",
                        "2. 重新生成 Application Key:",
                        "   - OctoPrint 设置 → API → Application Keys",
                        "   - 删除旧的 user1 key，创建新 key",
                        "   - 更新 backend/.env 中的 OCTOPRINT_API_KEY",
                        "3. 重启 OctoPrint 和后端服务"
                    ]
                }
            }
        else:
            return {
                "success": False,
                "error": f"OctoPrint 返回 {response.status_code}",
                "response": response.text[:200]
            }
    except requests.exceptions.ConnectionError:
        # 连接失败且启用了自动回退
        if getattr(daq, 'config', None) and getattr(daq.config, 'octoprint_simulation_auto_fallback', False):
            logging.warning("[Test] OctoPrint 连接失败，自动启用模拟模式")
            daq._enable_octoprint_simulation()
            return {
                "success": True,
                "simulation": True,
                "auto_fallback": True,
                "message": "OctoPrint 连接失败，已自动切换到模拟模式",
                "octoprint_url": "simulation",
                "temperature": {
                    "nozzle_actual": 200,
                    "bed_actual": 60
                }
            }
        
        return {
            "success": False,
            "error": f"无法连接到 OctoPrint ({daq.config.octoprint_url})",
            "suggestion": "请检查 OctoPrint 是否运行，以及 URL 是否正确"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/files")
async def get_printer_files():
    """获取打印机文件列表（本地和 SD 卡）"""
    from main import daq
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    api_key = daq.config.octoprint_api_key
    if not api_key or len(api_key) < 20:
        api_key = _get_api_key_from_env()
    
    try:
        import requests
        
        # 获取本地文件（包含详细信息）
        local_files = []
        try:
            url = f"{daq.config.octoprint_url}/api/files?location=local&recursive=true"
            headers = {"X-Api-Key": api_key}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                local_files = [
                    {
                        "name": f["name"],
                        "path": f["path"],
                        "size": f.get("size", 0),
                        "date": f.get("date", 0),
                        "type": f.get("type", "unknown"),
                        "location": "local",
                        "estimatedPrintTime": f.get("gcodeAnalysis", {}).get("estimatedPrintTime", 0) if f.get("gcodeAnalysis") else 0
                    }
                    for f in files
                ]
                print(f"[Files] 获取到 {len(local_files)} 个本地文件")
        except Exception as e:
            print(f"[Files] 获取本地文件失败: {e}")
        
        # 获取 SD 卡文件（包含详细信息）
        sdcard_files = []
        try:
            url = f"{daq.config.octoprint_url}/api/files?location=sdcard&recursive=true"
            headers = {"X-Api-Key": api_key}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                sdcard_files = [
                    {
                        "name": f["name"],
                        "path": f["path"],
                        "size": f.get("size", 0),
                        "date": f.get("date", 0),
                        "type": f.get("type", "unknown"),
                        "location": "sdcard",
                        "estimatedPrintTime": f.get("gcodeAnalysis", {}).get("estimatedPrintTime", 0) if f.get("gcodeAnalysis") else 0
                    }
                    for f in files
                ]
                print(f"[Files] 获取到 {len(sdcard_files)} 个 SD 卡文件")
        except Exception as e:
            print(f"[Files] 获取 SD 卡文件失败: {e}")
        
        return {
            "success": True,
            "files": {
                "local": local_files,
                "sdcard": sdcard_files
            },
            "total": len(local_files) + len(sdcard_files)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/print")
async def start_print_file(
    filename: str = Query(..., description="文件名路径"),
    location: str = Query("local", description="文件位置: local 或 sdcard")
):
    """选择文件并开始打印
    
    Args:
        filename: 文件名（包含路径）
        location: 文件位置，'local' 或 'sdcard'
    """
    from main import daq
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    api_key = daq.config.octoprint_api_key
    if not api_key or len(api_key) < 20:
        api_key = _get_api_key_from_env()
    
    try:
        import requests
        
        # 先选择文件
        url = f"{daq.config.octoprint_url}/api/job"
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        # 构建文件路径
        if location == "sdcard":
            full_path = f"sdcard/{filename}"
        else:
            full_path = filename
        
        print(f"[Print] 选择文件: {full_path}")
        print(f"[Print] location: {location}")
        
        # 发送选择并打印命令
        # OctoPrint API 对于 SD 卡文件需要使用 origin 参数
        if location == "sdcard":
            payload = {
                "command": "select",
                "path": filename,  # 去掉 sdcard/ 前缀
                "origin": "sdcard",
                "print": True
            }
        else:
            payload = {
                "command": "select",
                "path": filename,
                "origin": "local",
                "print": True
            }
        
        print(f"[Print] payload: {payload}")
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        print(f"[Print] 响应状态: {response.status_code}")
        
        if response.status_code == 204:
            return {
                "success": True,
                "message": f"已开始打印: {filename}",
                "filename": filename,
                "location": location
            }
        else:
            return {
                "success": False,
                "error": f"OctoPrint 返回错误: {response.status_code}",
                "details": response.text[:200]
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/job/pause")
async def pause_job():
    """暂停当前打印任务"""
    from main import daq
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    api_key = daq.config.octoprint_api_key
    if not api_key or len(api_key) < 20:
        api_key = _get_api_key_from_env()
    
    try:
        import requests
        url = f"{daq.config.octoprint_url}/api/job"
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json={"command": "pause"}, timeout=5)
        
        if response.status_code == 204:
            return {"success": True, "message": "打印已暂停"}
        else:
            return {"success": False, "error": f"返回 {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/job/cancel")
async def cancel_job():
    """取消当前打印任务"""
    from main import daq
    
    if not daq:
        raise HTTPException(status_code=503, detail="DAQ 系统未初始化")
    
    api_key = daq.config.octoprint_api_key
    if not api_key or len(api_key) < 20:
        api_key = _get_api_key_from_env()
    
    try:
        import requests
        url = f"{daq.config.octoprint_url}/api/job"
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, headers=headers, json={"command": "cancel"}, timeout=5)
        
        if response.status_code == 204:
            return {"success": True, "message": "打印已取消"}
        else:
            return {"success": False, "error": f"返回 {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
