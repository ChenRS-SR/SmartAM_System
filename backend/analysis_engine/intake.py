"""新采集层的标准化接入。模型按设备绑定，任务之间不共享正常参照。"""
from __future__ import annotations
import hashlib
import io
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, field_validator
from .results import format_result
from .service import package
from replay.service import case_for_device

router = APIRouter(prefix='/slm/analysis', tags=['设备模型处理'])
ROOT = Path(__file__).resolve().parents[1] / 'data/live_analysis'
LOCK = threading.Lock()


class LayerInfo(BaseModel):
    task_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    task_name: str = Field(min_length=1, max_length=160)
    layer: int = Field(ge=1)
    total_layers: int = Field(ge=1)
    time: datetime
    roi: Optional[list[int]] = None
    torque_time: Optional[list[float]] = None
    scraper: Optional[list[float]] = None
    platform: Optional[list[float]] = None

    @field_validator('time')
    @classmethod
    def aware_time(cls, value):
        if value.tzinfo is None:
            raise ValueError('时间必须包含时区')
        return value


def prepare(before, after, mask, info, model):
    """不补造缺失模态；视觉模型需要零件掩膜，多模态模型需要两通道铺粉扭矩。"""
    from forming_monitor.engine import preprocess as P
    h, w = before.shape[:2]
    if info.layer > info.total_layers:
        raise ValueError('当前层超出任务总层数')
    torque = None
    if model['architecture'] == 'vis_torque':
        roi = info.roi
        if not roi or len(roi) != 4 or not (0 <= roi[0] < roi[2] <= w and 0 <= roi[1] < roi[3] <= h):
            raise ValueError('需要图像范围内的成形区 ROI [x0,y0,x1,y1]')
        if after is None or after.shape != before.shape:
            raise ValueError('需要同尺寸的铺粉后、熔化后图像')
        series = [info.torque_time, info.scraper, info.platform]
        if any(v is None or len(v) < 2 for v in series) or len({len(v) for v in series}) != 1:
            raise ValueError('需要等长的铺粉段时间、刮刀扭矩、平台扭矩序列')
        t, s, p = [np.asarray(v, dtype=np.float64) for v in series]
        if not all(np.isfinite(v).all() for v in (t, s, p)) or not np.all(np.diff(t) > 0):
            raise ValueError('扭矩数值必须有限，采样时间必须严格递增')
        grid = np.linspace(t[0], t[-1], 224)
        torque = np.stack([np.interp(grid, t, s), np.interp(grid, t, p)]).astype(np.float32)
        part, band, valid = P.part_regions(after, before, roi, 12)
        rgb = P.crop_letterbox(before, roi)
        box = roi
    else:
        if mask is None or mask.shape != (h, w) or not mask.any() or mask.all():
            raise ValueError('需要同尺寸且同时含零件区和背景的二值掩膜')
        background = before[~mask].astype(np.float32)
        sd = background.std(0)
        if np.any(sd <= 0):
            raise ValueError('粉床背景标准差无效')
        norm = model['background_norm']
        normalized = np.clip((before.astype(np.float32)-background.mean(0))/sd*np.array(norm['rgb_std_255'])+np.array(norm['rgb_mean_255']), 0, 255)
        rgb = np.round(cv2.resize(normalized, (224, 224), interpolation=cv2.INTER_AREA)).astype(np.uint8)
        part = cv2.resize(mask.astype(np.uint8), (224, 224), interpolation=cv2.INTER_NEAREST) > 0
        band = cv2.dilate(part.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))) > 0
        valid = np.ones_like(part)
        box = [0, 0, w, h]
    sample = dict(rgb=rgb, part=part, band=band, valid=valid)
    if torque is not None: sample['torque'] = torque
    item = {'layer': info.layer, 'time': info.time.isoformat(), 'image': {'w': w, 'h': h, 'box': box},
            'partContours': P.contours(part), 'bandContours': P.contours(band),
            'torque': {'t': grid.tolist() if torque is not None else [],
                       'scraper': torque[0].tolist() if torque is not None else [],
                       'platform': torque[1].tolist() if torque is not None else []}}
    return sample, item


def read_image(file, mask=False):
    if file is None: return None
    data = file.file.read(25*1024*1024+1)
    if len(data) > 25*1024*1024: raise ValueError('单张图像不得超过 25 MiB')
    with Image.open(io.BytesIO(data)) as im:
        if im.width*im.height > 20_000_000: raise ValueError('图像超过 2000 万像素')
        pixels = np.array(im.convert('L' if mask else 'RGB'))
    return pixels > 0 if mask else pixels


@router.get('/devices/{device_id}/tasks/{task_id}/layers/{layer}')
def saved_result(device_id: str, task_id: str, layer: int):
    """已经计算的任务结果直接读取，供采集端离线展示，不再次加载模型。"""
    import re
    if case_for_device(device_id) is None or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', task_id):
        raise HTTPException(404, '无此采集任务')
    path = ROOT/device_id/task_id/f'{layer}.json'
    if not path.is_file(): raise HTTPException(404, '该层尚无处理结果')
    return json.loads(path.read_text(encoding='utf-8'))


@router.post('/devices/{device_id}/layers')
def process_layer(device_id: str, metadata: str = Form(...), before: UploadFile = File(...),
                  after: UploadFile = File(None), mask: UploadFile = File(None), infrared_before: UploadFile = File(None)):
    config = case_for_device(device_id)
    if config is None: raise HTTPException(404, '设备未绑定模型')
    try:
        info = LayerInfo.model_validate_json(metadata)
        bound = package(config['id'])
        model = json.loads((Path(__file__).resolve().parents[1]/'inference_models/registry.json').read_text(encoding='utf-8'))[bound.meta['modelId']]
        sample, item = prepare(read_image(before), read_image(after), read_image(mask, True), info, model)
        if infrared_before is not None:
            if bound.meta['modelId'] != 'm130-dual':
                raise ValueError('当前设备未绑定红外模型')
            buffer = io.BytesIO()
            Image.fromarray(read_image(infrared_before)).save(buffer,format='PNG')
            sample['infrared'] = np.frombuffer(buffer.getvalue(),dtype=np.uint8)
        identity = hashlib.sha256(metadata.encode()+b''.join(sample[k].tobytes() for k in sorted(sample))).hexdigest()
    except (ValueError, OSError) as e:
        raise HTTPException(422, str(e)) from e
    # 仅本地记录识别与溯源，不初始化硬件、不下发调控指令。
    with LOCK:
        folder = ROOT/device_id/info.task_id
        result_file = folder/f'{info.layer}.json'
        if result_file.is_file():
            saved = json.loads(result_file.read_text(encoding='utf-8'))
            if saved['inputSha256'] != identity: raise HTTPException(409, '同层已有不同输入，请使用新任务编号')
            return saved
        history = [json.loads(p.read_text(encoding='utf-8')) for p in folder.glob('*.json')]
        if history and max(r['layer'] for r in history) >= info.layer:
            raise HTTPException(409, '采集层必须按层号递增提交')
        if history and max(datetime.fromisoformat(r['time']) for r in history) >= info.time:
            raise HTTPException(409, '采集时间必须递增')
        if any(r['modelVersion'] != model['sha256'] for r in history):
            raise HTTPException(409, '模型版本已改变，请使用新任务编号')
        previous = [r for r in history if r['row']['p_proc'] < .5 and r['row']['p_dev'] < .5]
        ref = max(previous, key=lambda r:r['layer'])['layer'] if previous else None
        reference = None
        if ref is not None:
            with np.load(folder/f'{ref}.npz', allow_pickle=False) as saved:
                reference = {k:saved[k] for k in saved.files}
        try:
            from .runtime import Runtime
            runtime = Runtime(bound.meta['modelId'])
            output = runtime.infer(sample, reference)
        except Exception as e:
            # 新采集任务没有对应封存输出，必须明确失败，不能挪用旧案例结果。
            import logging
            logging.getLogger(__name__).exception('新采集层模型处理失败：%s/%s',device_id,info.layer)
            raise HTTPException(503, '当前无法完成模型处理') from e
        if ref is not None: output['ref'] = ref
        base = f'/api/slm/analysis/devices/{device_id}/tasks/{info.task_id}/layers/{info.layer}'
        item['image']['url'] = base+'/image'
        item['modelView'] = base+'/image'
        if 'infrared' in sample:
            item['infraredImage'] = {'url':base+'/image?kind=infrared','time':info.time.isoformat()}
        item['image'].update(w=224, h=224, box=[0, 0, 224, 224])
        meta = {**bound.meta, 'task': {'id':info.task_id, 'name':info.task_name, 'layers':info.total_layers}}
        result = {**format_result(meta, item, output), 'layer':info.layer, 'time':info.time.isoformat(),
                  'inputSha256':identity, 'modelVersion':model['sha256']}
        folder.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(folder/f'{info.layer}.npz', **sample)
        temp = result_file.with_suffix('.tmp')
        temp.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        temp.replace(result_file)
        return result


@router.get('/devices/{device_id}/tasks/{task_id}/layers/{layer}/image')
def input_image(device_id: str, task_id: str, layer: int, kind: str = 'rgb'):
    import re
    from fastapi.responses import Response
    if case_for_device(device_id) is None or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', task_id):
        raise HTTPException(404, '无此采集任务')
    path = ROOT/device_id/task_id/f'{layer}.npz'
    if not path.is_file(): raise HTTPException(404, '无此采集层')
    with np.load(path, allow_pickle=False) as data:
        if kind not in ('rgb', 'infrared') or kind not in data.files:
            raise HTTPException(404, '该层没有此模态图像')
        buffer = io.BytesIO()
        if kind == 'infrared':
            with Image.open(io.BytesIO(data['infrared'].tobytes())) as image:
                image.save(buffer,format='PNG')
        else: Image.fromarray(data['rgb']).save(buffer, format='PNG')
    return Response(buffer.getvalue(), media_type='image/png')
