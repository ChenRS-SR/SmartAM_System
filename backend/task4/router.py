"""四个独立 HTTP 入口，共用与项目接口协议一致的 status/message/data 信封。"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from . import schemas, service


class ProtocolRoute(APIRoute):
    def get_route_handler(self):
        handle = super().get_route_handler()

        async def protocol(request):
            try:
                return await handle(request)
            except RequestValidationError as exc:
                messages = ['.'.join(map(str, e['loc'][1:])) + ': ' + e['msg'] for e in exc.errors()]
                code, message = 400, '; '.join(messages)
            except HTTPException as exc:
                code, message = exc.status_code, str(exc.detail)
            except Exception:
                logging.getLogger(__name__).exception('课题四接口处理失败')
                code, message = 500, '接口处理失败，请检查服务日志'
            return JSONResponse(status_code=code, content=dict(status=code, message=message, data=None))
        return protocol


router = APIRouter(prefix='/task4', tags=['课题四开放接口'], route_class=ProtocolRoute)


def success(data):
    return dict(status=200, message='操作成功', data=data)


@router.post('/defect-recognition', summary='增材制造制件缺陷关联异常识别')
def defect_recognition(request: schemas.Selection):
    return success(service.recognition(request))


@router.post('/quality-control', summary='增材制造制件质量闭环调控与修复')
def quality_control(request: schemas.Control):
    return success(service.control(request))


@router.post('/equipment-diagnosis', summary='增材制造装备群运行监测与故障诊断')
def equipment_diagnosis(request: schemas.Equipment):
    return success(service.equipment(request))


@router.post('/maintenance-statistics', summary='增材制造装备群智能运维及故障率统计')
def maintenance_statistics(request: schemas.Maintenance):
    return success(service.maintenance(request))
