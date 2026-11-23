"""课题四业务接口：复用封存分析与设备档案，不加载推理模型直至显式请求 real。"""
import json
import logging
import math
import re
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from analysis_engine.service import package
from core.slm_device_data import get_slm_device_data_store
from replay.service import case_for_device, get_case, replay_devices
from replay.router import manifest
from .schemas import Selection
from .storage import database, remember, stored_plan, active_strategies, activate_plan

ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


@lru_cache(maxsize=16)
def asset(name):
    return json.loads((ROOT / 'frontend/src/assets' / name).read_text(encoding='utf-8'))


def devices(ids=None):
    registry = {d['id']: d for d in get_slm_device_data_store().load_manifest()['devices']}
    registry.update({d['id']: d for d in replay_devices()})
    if ids is not None and len(set(ids)) != len(ids):
        raise HTTPException(400, '设备编号不得重复')
    selected = list(registry) if ids is None else ids
    if any(key not in registry for key in selected):
        raise HTTPException(404, '设备编号不存在')
    return [registry[key] for key in selected]


def recognition(request):
    devices([request.deviceId])
    entry = case_for_device(request.deviceId)
    faults = asset('fault-demos.json')
    base = dict(deviceId=request.deviceId, taskId=request.taskId, layerNo=request.layerNo,
                processingMode=request.processingMode, resultScope=request.resultScope, ready=False, recognition=None, trace=None)
    if not entry:
        if request.processingMode == 'real':
            raise HTTPException(409, '该设备尚未绑定推理模型')
        if request.taskId is not None or request.layerNo is not None or request.offset is not None:
            raise HTTPException(404, '该设备尚无对应的逐层分析任务')
        fault = faults.get(request.deviceId)
        return dict(base, source='device-record', diagnosis=fault['status'] if fault else None,
                    advice=[fault['advice']] if fault else [])
    item = package(entry['id'])
    task_id = item.meta['task']['id']
    if request.taskId and request.taskId != task_id:
        # 新采集任务的结果已由现有接入接口持久化；不能错配到设备的演示案例。
        if request.layerNo is None or request.offset is not None:
            raise HTTPException(400, '查询已接入任务须指定 layerNo，不使用 offset')
        if request.processingMode == 'real':
            raise HTTPException(409, '新采集层请通过 /api/slm/analysis/devices/{deviceId}/layers 处理')
        from analysis_engine.intake import saved_result
        result = saved_result(request.deviceId, request.taskId, request.layerNo)
        return dict(base, ready=True, source='saved-inference', recognition=result['recognition'], trace=result['trace'])
    current = get_case(entry['id'])
    frame = None
    if request.offset is not None or request.layerNo is None:
        offset = request.offset if request.offset is not None else manifest(entry['id'])['defaultOffset']
        if offset > current.manifest['duration']:
            raise HTTPException(400, 'offset 超出案例时长')
        frame = current.snapshot(offset)
        layer = frame['layer']
        if request.layerNo is not None and request.layerNo != layer:
            raise HTTPException(409, 'layerNo 与 offset 对应层不一致')
    else:
        layer = request.layerNo
    row = next((r for r in current.layers if r['layer'] == layer), None)
    if row is None:
        raise HTTPException(404, '该任务没有此层数据')
    if request.resultScope == 'display':
        # 与工作区使用同一快照装配逻辑；每个结果保留其实际层号，不冒充当前采集层。
        displayed = item.apply(frame, current.layers, request.processingMode == 'real')
        if request.processingMode == 'real' and not displayed['processing']['real']:
            raise HTTPException(503, '真实处理不可用，请检查推理环境及模型输入')
        return dict(base, taskId=task_id, layerNo=layer, offset=displayed['offset'], time=displayed['time'],
                    source=displayed['analysisOrigin'], ready=displayed['recognition'] is not None,
                    recognition=displayed['recognition'], trace=displayed['trace'])
    base.update(taskId=task_id, layerNo=layer, source='sealed-model-results')
    if frame and frame['timestamp'] < row['recognitionAt']:
        return base
    if request.processingMode == 'real':
        try:
            with item.lock:
                result = item.compute(layer)
        except Exception as exc:
            logger.exception('课题四真实处理失败：%s / %s', request.deviceId, layer)
            raise HTTPException(503, '真实处理不可用，请检查推理环境及模型输入') from exc
        base['source'] = 'model-runtime'
    else:
        result = item.archived[str(layer)]
    # 游标请求仅发布本层已到达的结果，不把前一层溯源冒充本层诊断。
    trace = result['trace'] if frame is None or frame['timestamp'] >= row['end'] else None
    return dict(base, ready=True, recognition=result['recognition'], trace=trace)


def slice_for(device_id, task_id, layer):
    entry = case_for_device(device_id)
    if entry:
        data = asset('control-regions/' + entry['id'] + '.json')
        if task_id != data['task']['id']:
            raise HTTPException(409, '该新任务尚未登记切片区域，不能套用演示任务区域')
        result = data.get('representative') or data['layers'].get(str(layer))
    else:
        result = asset('fault-demos.json').get(device_id, {}).get('slice')
    if not result:
        raise HTTPException(409, '该设备任务尚未登记切片区域')
    return result


def region_parameters(strategy, automatic, baseline, signal, prob):
    adjusted = baseline.copy()
    status = '保持基准'
    if strategy != 'adjust':
        status = {'remelt': '策略2 · 重熔', 'recoat': '策略3 · 重铺粉', 'stop': '策略4 · 停机调整'}[strategy]
    elif not automatic:
        status = '自动调整已暂停'
    elif signal and signal.get('stop'):
        status = '停机检查，保持当前参数'
    elif not signal and not prob:
        status = '等待本层识别'
    elif signal or max(prob['proc'], prob['dev']) >= .5:
        process_side = signal['side'] == 'proc' if signal else prob['proc'] >= prob['dev']
        strength = 1 if signal else min(1, max(0, ((prob['proc'] if process_side else prob['dev']) - .5) / .5))
        if process_side:
            increase = signal and signal.get('direction') == 'increase'
            ratio = .05 + .05 * strength
            adjusted['laserPower'] = math.floor(baseline['laserPower'] * (1 + (ratio if increase else -ratio)) + .5)
            status = '预计提高输入能量' if increase else '预计降低输入能量'
        else:
            adjusted['layerWaitTime'] = round(baseline['layerWaitTime'] + 1 + strength, 1)
            status = '延长层间等待'
    if not (50 <= adjusted['laserPower'] <= 500 and 0 <= adjusted['layerWaitTime'] <= 600):
        raise HTTPException(409, '调控值超出允许范围，请修订当前参数')
    return adjusted, status


def control(request):
    devices([request.deviceId])
    if request.operation in ('get', 'simulate', 'execute'):
        result = stored_plan(request.deviceId, request.planId)
        if request.operation == 'execute':
            raise HTTPException(409, '尚未绑定真机执行器，方案可保存或模拟')
        if request.operation == 'simulate':
            return activate_plan(request.deviceId, request.planId)
        return result
    fingerprint = json.dumps(request.model_dump(mode='json'), sort_keys=True, ensure_ascii=False)
    if request.operation == 'save':
        with database() as db:
            old = db.execute('SELECT request_json,response_json FROM plans WHERE device=? AND request_id=?',
                             (request.deviceId, request.requestId)).fetchone()
        if old:
            if old[0] != fingerprint:
                raise HTTPException(409, 'requestId 已用于不同的调控方案')
            return json.loads(old[1])
    selected = request.model_dump(include=set(Selection.model_fields))
    selected['resultScope'] = 'layer'
    result = recognition(Selection(**selected))
    drawing = slice_for(request.deviceId, result['taskId'], result['layerNo'])
    regions = drawing['regions']
    ids = request.regionIds or [r['id'] for r in regions]
    if set(ids) - {r['id'] for r in regions}:
        raise HTTPException(400, 'regionIds 必须对应当前切片中的区域编号')
    baseline = request.currentParameters.model_dump()
    active = active_strategies(request.deviceId, result['taskId'])
    signal = asset('fault-demos.json').get(request.deviceId, {}).get('control')
    prob = result['recognition']['prob'] if result['recognition'] else None
    rows = []
    for region in regions:
        if region['id'] not in ids:
            continue
        existing = active.get(region['id'])
        # 预览与导出默认读取各区域当前策略；显式策略或保存操作用于生成新的替换方案。
        use_active = request.operation == 'preview' and 'strategy' not in request.model_fields_set and existing is not None
        strategy = existing['strategy'] if use_active else request.strategy
        automatic = bool(existing['automatic']) if use_active and 'automatic' not in request.model_fields_set else request.automatic
        adjusted, status = region_parameters(strategy, automatic, baseline, signal, prob)
        rows.append(dict(regionId=region['id'], name=region['name'], color=region['color'],
                         currentParameters=baseline, controlParameters=adjusted, status=status,
                         strategy=strategy, automatic=automatic and strategy == 'adjust',
                         activePlanId=existing['plan_id'] if use_active else None))
    strategies = {r['strategy'] for r in rows}
    payload = dict(deviceId=request.deviceId, taskId=result['taskId'], layerNo=result['layerNo'],
                   planId=None, state='preview', executed=False, strategy=next(iter(strategies)) if len(strategies) == 1 else 'mixed',
                   source='configured-region-control-demo', image=drawing['annotatedImage'],
                   parameterSource='request-and-platform-config' if request.currentParameters.model_fields_set else 'platform-config',
                   units=dict(laserPower='W', fillSpeed='mm/s', layerWaitTime='s'),
                   regions=rows)
    if request.operation == 'save':
        payload.update(planId=uuid.uuid4().hex, state='planned')
        with database() as db:
            db.execute('INSERT OR IGNORE INTO plans VALUES (?,?,?,?,?)', (payload['planId'], request.deviceId,
                       request.requestId, fingerprint, json.dumps(payload, ensure_ascii=False)))
            old = db.execute('SELECT request_json,response_json FROM plans WHERE device=? AND request_id=?',
                             (request.deviceId, request.requestId)).fetchone()
            if old[0] != fingerprint:
                raise HTTPException(409, 'requestId 已用于不同的调控方案')
            payload = json.loads(old[1])
    return payload


def equipment(request):
    output = []
    faults = asset('fault-demos.json')
    for device in devices(request.deviceIds):
        key = device['id']
        model = re.sub(r'BLT[-\s]*', '铂力特 ', device['model'], flags=re.I)
        serial = re.search(r'\bB\d+\b', device['name'], re.I)
        name = model + ' ' + serial[0].upper() if model.startswith('铂力特 ') and serial else device['name']
        fault = faults.get(key)
        entry = case_for_device(key)
        if request.resultScope == 'display' and not entry:
            raise HTTPException(409, '该设备没有案例游标，不能将档案参数当作当前画面')
        row = dict(deviceId=key, name=name, source=device['source'], layerNo=None, taskId=None,
                   status='fault' if fault or device['health'] == 'fault' else ('normal' if device['health'] == 'healthy' else 'unknown'),
                   diagnosis=fault['status'] if fault else device['statusText'],
                   advice=[fault['advice']] if fault else [], parameters=device['parameters'],
                   recognition=None, trace=None)
        if entry and request.parameterSource == 'archive':
            result = recognition(Selection(deviceId=key, offset=request.offset, resultScope=request.resultScope, processingMode=request.processingMode))
            row.update({k: result[k] for k in ('source', 'layerNo', 'taskId', 'recognition', 'trace')})
            current = get_case(entry['id'])
            offset = request.offset if request.offset is not None else manifest(entry['id'])['defaultOffset']
            sample = current.snapshot(offset)
            row.update(parameters=sample['parameters'], offset=sample['offset'], time=sample['time'],
                       alarms=sample['access']['alarms'], samples=sample['samples'])
            rec, trace = result['recognition'], result['trace']
            if rec:
                # B17 论文画面保留原始缺陷概率格式，按其实际显示标签判断，不补造双侧概率。
                row['status'] = {'异常':'abnormal', '正常':'normal'}.get(rec['label'], 'unknown')
                row['diagnosis'] = trace['conclusion'] if trace else '等待本层故障诊断'
                row['advice'] = trace['actions'] if trace else []
                if trace and any(f['over'] for factor in trace['factors'].values() for f in factor['zones']):
                    if row['status'] == 'normal':
                        row['status'] = 'review'
        if request.parameterSource == 'live':
            from core.slm_realtime import get_slm_realtime_store
            sample = get_slm_realtime_store().latest(key)
            if not sample['hasData']:
                raise HTTPException(404, '该设备暂无已接入的实时参数')
            # 实时接入与历史分析不混合成同一份当前状态。
            row.update(parameters=sample['parameters'], source='live-acquisition',
                       recognition=None, trace=None, taskId=None, layerNo=None,
                       realtimeSample=sample, time=sample['eventTime'], alarms=sample['alarms'],
                       diagnosis=sample['diagnosis']['statusLabel'], advice=[],
                       status=('unknown' if sample['diagnosis']['statusCode'] < 0 else
                               'normal' if sample['diagnosis']['statusCode'] == 0 else 'fault'))
            for field in ('offset', 'samples'):
                row.pop(field, None)
        output.append(row)
    return dict(devices=output, deviceCount=len(output), faultDeviceCount=sum(d['status'] == 'fault' for d in output))


def maintenance(request):
    if request.operation != 'query':
        devices([request.deviceId])
        if request.operation == 'recordTask':
            remember('tasks', request.deviceId, request.taskId, request.occurredAt.timestamp(), int(request.faulted))
        else:
            remember('maintenance', request.deviceId, request.recordId, request.occurredAt.timestamp(), request.description)
    selected = devices(request.deviceIds if request.operation == 'query' else [request.deviceId])
    ids = [d['id'] for d in selected]
    clause = 'device IN (' + ','.join('?' for _ in ids) + ')'
    args = list(ids)
    if request.startTime:
        clause += ' AND at>=? AND at<?'
        args += [request.startTime.timestamp(), request.endTime.timestamp()]
    with database() as db:
        tasks = [dict(r) for r in db.execute('SELECT * FROM tasks WHERE '+clause+' ORDER BY at,id', args)]
        records = [dict(r) for r in db.execute('SELECT * FROM maintenance WHERE '+clause+' ORDER BY at,id', args)]
    for r in records:
        r['occurredAt'] = datetime.fromtimestamp(r.pop('at'), timezone.utc).isoformat()
        r['deviceId'], r['recordId'] = r.pop('device'), r.pop('id')
    faults = asset('fault-demos.json')
    fault_devices = sum(d['id'] in faults or d['health'] == 'fault' for d in selected)
    fault_tasks = sum(t['faulted'] for t in tasks)
    return dict(deviceCount=len(ids), faultDeviceCount=fault_devices,
                faultDeviceRatio=fault_devices / len(ids) if ids else None,
                totalTasks=len(tasks), faultTasks=fault_tasks,
                taskFaultRate=fault_tasks / len(tasks) if tasks else None,
                maintenanceCount=len(records), records=records,
                advice=[dict(deviceId=d, diagnosis=faults[d]['status'], suggestion=faults[d]['advice']) for d in ids if d in faults],
                startTime=request.startTime, endTime=request.endTime)
