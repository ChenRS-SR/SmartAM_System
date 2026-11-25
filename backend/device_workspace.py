"""设备档案到统一工作区的适配层：只转换已有记录，不合成模型结果。"""
import csv
import math
from collections import deque
from datetime import datetime

from fastapi import APIRouter, HTTPException
from task4.service import ROOT, asset, devices
from replay.service import case_for_device
from core.slm_device_data import get_slm_device_data_store

router = APIRouter(prefix='/slm/workspace', tags=['设备工作区'])


def number(value):
    if value is None or value == '':
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def preview_records(device):
    relative = (device.get('realData') or {}).get('preview_csv')
    if not relative:
        return []
    root = ROOT / 'slm_device_data'
    path = (root / relative).resolve()
    if root.resolve() not in path.parents:
        raise HTTPException(409, '设备记录路径超出数据目录')
    if not path.is_file():
        raise HTTPException(409, '设备登记的采样文件不存在')
    with path.open('r', encoding='utf-8-sig', newline='') as stream:
        return list(deque(csv.DictReader(stream), maxlen=50))


def empty_factor(name):
    return dict(name=name, total=None, upper=None, present=False, prob=None,
                zones=[dict(key=k, name=n, v=None, over=None) for k, n in [('part', '零件区'), ('powder', '粉床区')]])


def record_workspace(device_id):
    device = devices([device_id])[0]
    if case_for_device(device_id):
        raise HTTPException(409, '该设备使用逐层案例数据接口')
    device = get_slm_device_data_store().get_device(device_id)
    fault = asset('fault-demos.json').get(device_id)
    records = preview_records(device)
    parameters = device.get('parameters', [])
    values = {p['id']: p['value'] for p in parameters}
    layer = number(values.get('current_layer'))
    layer = int(layer) if layer is not None and layer >= 1 and layer.is_integer() else None
    sample_time = values.get('data_time')
    sample_time = sample_time if sample_time not in (None, '', '--') else None
    identity = dict(id=device_id, name=device['name'])
    task = dict(id=None, name='未登记成形任务', layers=None)
    context = dict(device=identity, task=task, layer=layer, time=sample_time)
    # 文件标签的诊断属于档案证据，不能宣称与最后一条采样同层或来自识别模型。
    diagnosis = dict(image=fault['image'] if fault else 'power_off.png', state='fault' if fault else 'pending',
                     title=fault['status'] if fault else '诊断结果未接入',
                     conclusion=fault['status'] if fault else '暂无诊断结果',
                     powder='待检查' if fault and fault['control']['side'] == 'dev' else '未确认',
                     process='待检查' if fault and fault['control']['side'] == 'proc' else '未确认',
                     source='设备档案', other='见诊断记录')
    torque = dict(t=[], scraper=[], platform=[], events=[], recoatDur=None)
    # 原始时间轴必须可解析；缺失通道保留 null，不补零、不插值。
    timed = []
    for row in records:
        try:
            stamp = datetime.fromisoformat(row.get('时间', ''))
        except ValueError:
            continue
        timed.append((stamp, row))
    timed.sort(key=lambda pair: pair[0])
    for stamp, row in timed:
        torque['t'].append((stamp - timed[0][0]).total_seconds())
        torque['scraper'].append(number(row.get('刮刀扭矩(%)')))
        torque['platform'].append(number(row.get('加工平台扭矩(%)')))
    # 环境卡使用参数登记值，不能把预览片段的首层读数混入当前层。
    mapping = {'成形室温度':'chamber_temperature', '气源压力':'gas_pressure', '循环气体实时流量':'gas_flow', '风机转速':'fan_speed'}
    env = {name:number(values.get(key)) for name, key in mapping.items()}
    oxygen = next((p for p in parameters if p['id'] == 'oxygen'), None)
    if oxygen and number(oxygen['value']) is not None and oxygen['unit'] in ('%', 'ppm'):
        env['成形室氧含量ppm'] = number(oxygen['value']) * (10000 if oxygen['unit'] == '%' else 1)
    images = {key:dict(url=None, time=None, layer=None, available=False) for key in ('before', 'after')}
    channels = [dict(name=name, spec=kind, rate='未接入', imageKey=key) for name, kind, key in [
        ('铺粉后图像', '图像', 'before'), ('熔化后图像', '图像', 'after'),
        ('刮刀扭矩', '采样', None), ('加工平台扭矩', '采样', None), ('设备状态参数', '采样', None)]]
    # 经用户确认的演示阶段映射，仅引用本设备预矫正代表帧，不作为模型输入。
    stage_demo = asset('monitor-stage-demos.json').get(device_id)
    corrected = (device.get('mockVideo') or {}).get('correctedChannels', {})
    for channel, prefix, suffix in [('camera_ch1', '', '图像'), ('thermal', 'ir_', '红外图像')]:
        sequence = corrected.get(channel, {}).get('frameSequence')
        for stage, label in [('before', '铺粉后'), ('after', '熔化后')]:
            key = prefix + stage
            if prefix:
                images[key] = dict(url=None, time=None, layer=None, available=False)
                channels.append(dict(name=label + suffix, spec='图像', rate='未接入', imageKey=key))
            if stage_demo and sequence and stage_demo[stage] <= sequence['count']:
                index = stage_demo[stage]
                images[key] = dict(url=f"{sequence['baseUrl']}/{index:06d}.jpg", time=None, layer=None,
                                   available=True, distortionCorrected=True,
                                   sourceKind='stage-demo', sourceFrame=index)
                next(c for c in channels if c.get('imageKey') == key)['rate'] = '代表帧'
    alarms = [dict(time='', text=e['text']) for e in (fault or {}).get('diagnosis', {}).get('evidence', [])]
    access = dict(**context, progress=dict(layer=layer, total=None), images=images, env=env, torque=torque,
                  channels=channels, alarms=alarms, records=[], acquisition=dict(running=False, mode='record', layer=layer),
                  rawRecords=records)
    recognition = dict(**context, available=False, model=dict(name='未接入', source=None),
                       params=dict(threshold=None, modalities=[]), image=dict(url=None, w=224, h=224, box=None),
                       prob=dict(def_=None, vis=None, tq=None, proc=None, dev=None), label='未接入',
                       weights=dict(vis=None, tq=None), singles=[], torque=torque, records=[])
    recognition['prob']['def'] = recognition['prob'].pop('def_')
    trace = dict(**context, available=False, mode='dual', refLayer=None, refMode=None, params=dict(bandPx=None),
                 image=dict(url=None, width=224, height=224, content=[0, 0, 1, 1]), partContours=[], bandContours=[],
                 factors=dict(proc=empty_factor('工艺问题'), dev=empty_factor('设备问题')),
                 conclusion=diagnosis['conclusion'], actions=[fault['advice']] if fault else [], recordDiagnosis=diagnosis,
                 curve=dict(upper=dict(proc=None, dev=None), layers=[]), records=[])
    return dict(schemaVersion=1, device=device,
                manifest=dict(deviceId=device_id, task=task, gasPressureLabel='气源压力',
                              capabilities=dict(access=True, recognition=False, trace=False, control=bool(fault))),
                snapshot=dict(caseId=device_id, source='device-record', layer=layer, time=sample_time, phase='档案数据',
                              parameters=parameters, samples={}, access=access, recognition=recognition, trace=trace,
                              slice=fault['slice'] if fault else None, controlSignal=fault['control'] if fault else None))


@router.get('/devices/{device_id}')
def workspace(device_id: str):
    from workspace_demo import complete_workspace
    return complete_workspace(record_workspace(device_id))
