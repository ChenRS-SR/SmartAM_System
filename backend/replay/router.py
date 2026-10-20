"""案例只读接口：回放游标由客户端工作区共享，不创建全局硬件运行状态。"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from .service import get_case

router = APIRouter(prefix='/slm/replay', tags=['历史案例回放'])


def case(case_id):
    try:
        return get_case(case_id)
    except KeyError:
        raise HTTPException(404, '无此回放案例')
    except (FileNotFoundError, ValueError):
        raise HTTPException(503, '案例尚未完成封存')


@router.get('/cases/{case_id}/manifest')
def manifest(case_id: str):
    return case(case_id).manifest


@router.get('/cases/{case_id}/snapshot')
def snapshot(case_id: str, offset: float = Query(0, ge=0, allow_inf_nan=False)):
    return case(case_id).snapshot(offset)


@router.get('/cases/{case_id}/photo')
def photo(case_id: str):
    return FileResponse(case(case_id).root / 'assets/photo.jpg', media_type='image/jpeg')


@router.get('/cases/{case_id}/media/{layer}/{kind}')
def media(case_id: str, layer: int, kind: str):
    c = case(case_id)
    if kind not in ('before', 'after', 'model_view') or layer not in {r['layer'] for r in c.layers}:
        raise HTTPException(404, '无此案例图像')
    path = c.root / 'assets' / f'{layer}_{kind}.jpg'
    if not path.is_file():
        raise HTTPException(404, '该层没有对应图像')
    return FileResponse(path, media_type='image/jpeg', headers={'Cache-Control': 'max-age=86400'})
