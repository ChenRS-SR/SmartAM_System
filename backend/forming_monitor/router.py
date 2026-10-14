"""成形监测接口，前缀 /slm/forming（挂到 SmartAM 的 /api 下即 /api/slm/forming/*）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, JSONResponse

from .schemas import AcquisitionStart, RecognizeRequest, TraceRequest
from .service import ApiError, get_service

router = APIRouter(prefix='/slm/forming', tags=['成形监测'])


def _run(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except ApiError as e:
        return JSONResponse(status_code=e.status, content={'detail': e.msg})
    except KeyError as e:
        return JSONResponse(status_code=404, content={'detail': str(e).strip("'")})


@router.get('/status', summary='系统状态与数据模式')
def status():
    return get_service().status()


@router.get('/devices', summary='设备清单')
def devices():
    return [d.public() for d in get_service().devices.values()]


@router.get('/devices/{device_id}/overview', summary='设备总览：当前层、最新结果、最近事件')
def overview(device_id: str):
    return _run(lambda: get_service().get(device_id).overview())


@router.get('/devices/{device_id}/tasks', summary='成形任务')
def tasks(device_id: str):
    return _run(lambda: get_service().get(device_id).tasks())


@router.get('/devices/{device_id}/tasks/{task_id}/layers', summary='数据完整的层号')
def layers(device_id: str, task_id: str):
    return _run(lambda: get_service().get(device_id).layers(task_id))


@router.get('/devices/{device_id}/photo', summary='设备照片')
def photo(device_id: str):
    r = _run(lambda: get_service().get(device_id).photo())
    return r if isinstance(r, JSONResponse) else FileResponse(r, media_type='image/jpeg')


@router.get('/devices/{device_id}/acquisition', summary='逐层接入状态')
def acq_status(device_id: str):
    return _run(lambda: get_service().get(device_id).acq_status())


@router.post('/devices/{device_id}/acquisition/start', summary='开始逐层接入（离线模式为按间隔回放）')
def acq_start(device_id: str, body: AcquisitionStart):
    return _run(lambda: get_service().get(device_id).acq_start(body.task_id, body.from_layer, body.interval))


@router.post('/devices/{device_id}/acquisition/stop', summary='暂停逐层接入')
def acq_stop(device_id: str):
    return _run(lambda: get_service().get(device_id).acq_stop())


@router.get('/devices/{device_id}/access', summary='数据接入：单层图像、扭矩、设备状态参数与逐层接入记录')
def access(device_id: str, layer: Optional[int] = None, task_id: Optional[str] = None, n_records: int = Query(7, ge=1, le=50)):
    return _run(lambda: get_service().get(device_id).access(layer, task_id, n_records))


@router.post('/recognition/infer', summary='异常识别（单层），附最近若干层记录')
def recognize(body: RecognizeRequest):
    return _run(lambda: get_service().get(body.device_id).recognize(body.layer, body.threshold, body.modalities, body.task_id, body.n_records))


@router.post('/trace/analyze', summary='异常溯源（单层），附逐层贡献曲线与记录')
def trace(body: TraceRequest):
    return _run(lambda: get_service().get(body.device_id).trace(body.layer, body.band_px, body.ref_mode, body.ref_layer,
                                                                 body.task_id, body.n_curve, body.n_records))


@router.get('/media/{device_id}/{task_id}/{layer}/{kind}', summary='图像（before 铺粉后 / after 烧结后 / model_view 模型输入视图）')
def media(device_id: str, task_id: str, layer: int, kind: str, w: int = Query(1200, ge=64, le=2592)):
    def go():
        d = get_service().get(device_id)
        d.check_task(task_id)
        return d.media(layer, kind, w)
    r = _run(go)
    return r if isinstance(r, JSONResponse) else FileResponse(r, media_type='image/jpeg', headers={'Cache-Control': 'max-age=3600'})
