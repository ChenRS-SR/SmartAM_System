"""
SLS状态API
"""

from fastapi import APIRouter

from core.sls import get_sls_acquisition

router = APIRouter()


@router.get("/vibration")
async def get_vibration_status():
    """获取振动传感器状态"""
    try:
        sls = get_sls_acquisition()
        return {
            'connected': sls.vibration_sensor.connected if sls.vibration_sensor else False,
            'magnitude': sls.vibration_sensor.vibration_magnitude if sls.vibration_sensor else 0,
            'data': sls.vibration_sensor.get_current_data().__dict__ if sls.vibration_sensor else None
        }
    except Exception as e:
        return {'error': str(e)}


@router.get("/powder")
async def get_powder_status():
    """获取扑粉检测状态"""
    try:
        sls = get_sls_acquisition()
        if sls.powder_detector:
            return sls.powder_detector.get_status()
        return {'error': '扑粉检测器未初始化'}
    except Exception as e:
        return {'error': str(e)}


@router.get("/devices")
async def get_device_status():
    """获取所有设备状态"""
    try:
        sls = get_sls_acquisition()
        
        devices = {
            'vibration': {
                'connected': sls.vibration_sensor.connected if sls.vibration_sensor else False,
                'magnitude': sls.vibration_sensor.vibration_magnitude if sls.vibration_sensor else 0
            },
            'main_camera': {
                'connected': sls.main_camera.isOpened() if sls.main_camera else False
            },
            'secondary_camera': {
                'connected': sls.secondary_camera.isOpened() if sls.secondary_camera else False
            },
            'thermal': {
                'connected': sls.thermal_camera is not None
            }
        }
        
        return devices
    except Exception as e:
        return {'error': str(e)}
