"""按历史时间生成一致快照。全部页面使用同一游标，不接触硬件运行状态。"""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import tempfile
import zipfile
import threading
from bisect import bisect_right
from contextlib import closing
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from pathlib import Path
from trace_results import DualTraceResults

CASE_ID = 'blt-s430-20240828'
DEVICE_ID = 'slm-b17-replay'
PACK_ROOT = Path(__file__).resolve().parents[1] / 'replay_cases'
RUNTIME_ROOT = Path(__file__).resolve().parents[1] / 'data/replay_runtime'
EXTRACT_LOCK = threading.Lock()
TZ = timezone(timedelta(hours=8))


def display_time(value):
    return datetime.fromtimestamp(value, TZ).strftime('%Y-%m-%d %H:%M:%S')


class ReplayCase:
    def __init__(self, root: Path, dual_path: Path | None = None):
        self.root = root
        self.manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
        self.layers = self.manifest['layers']
        self.alarms = json.loads((root / 'alarms.json').read_text(encoding='utf-8'))
        # 新分析版本单独保存，原始案例封存文件与校验值保持可追溯。
        self.dual = DualTraceResults(dual_path) if dual_path is not None else None
        if self.dual is not None:
            if set(self.dual.rows) != {r['layer'] for r in self.layers}:
                raise ValueError('双输出结果层号与回放案例不一致')
            self.manifest['analysis'].update(
                processModelAvailable=True, traceSource=self.dual.pack['source'],
                traceResultSha256=hashlib.sha256(dual_path.read_bytes()).hexdigest())

    @lru_cache(maxsize=420)
    def layer_data(self, layer):
        data = json.loads((self.root / 'layers' / f'{layer}.json').read_text(encoding='utf-8'))
        if self.dual is not None and data['trace'] is not None:
            self.dual.apply(data['trace'], layer)
        return data

    def position(self, offset):
        offset = max(0, min(float(offset), self.manifest['duration']))
        segments = self.manifest['segments']
        index = min(bisect_right([s['offset'] for s in segments], offset) - 1, len(segments) - 1)
        segment = segments[index]
        at = min(segment['start'] + offset - segment['offset'], segment['end'])
        rows = [r for r in self.layers if segment['firstLayer'] <= r['layer'] <= segment['lastLayer']]
        row = rows[max(0, bisect_right([r['start'] for r in rows], at) - 1)]
        return offset, at, index, segment, rows, row

    def media_url(self, layer, kind):
        return f'/api/slm/replay/cases/{self.manifest["id"]}/media/{layer}/{kind}'

    def snapshot(self, offset):
        offset, at, index, segment, rows, row = self.position(offset)
        current = row['layer']
        if self.manifest.get('imageOnly'):
            # 图像窗口之间保留上一帧，不能因每层单独分段而一直看不到熔化后图像。
            rows = self.layers
        access = copy.deepcopy(self.layer_data(current)['access'])
        # 每个通道取不晚于游标的最后一个原始采样，0 是真实读数，不替换为之前非零值。
        samples = {}
        with closing(sqlite3.connect(f'file:{self.root / "samples.sqlite"}?mode=ro', uri=True)) as db:
            db.row_factory = sqlite3.Row
            for table in ('torque', 'env_a', 'env_b', 'env_c'):
                record = db.execute(f'SELECT * FROM {table} WHERE time >= ? AND time <= ? ORDER BY time DESC, sequence DESC LIMIT 1',
                                    (segment['start'], at)).fetchone()
                samples[table] = dict(record) if record else None
            torque = [dict(r) for r in db.execute(
                'SELECT * FROM torque WHERE time >= ? AND time <= ? ORDER BY time, sequence',
                (max(row['recoat'] - 3, segment['start']), min(at, row['melt'] + 15)))]
            # 连续监测曲线独立于单层模型输入：熔化期间继续接入，最多返回最近 50 秒的 50 个原始点。
            live_torque = [dict(r) for r in db.execute(
                'SELECT * FROM torque WHERE time >= ? AND time <= ? ORDER BY time DESC, sequence DESC LIMIT 50',
                (max(segment['start'], at - 50), at))][::-1]

        def value(table, key, scale=1):
            sample = samples[table]
            return None if sample is None or sample[key] is None else sample[key] * scale

        access['env'] = {
            '成形室压力': value('env_a', 'chamber_pressure'), '成形室温度': value('env_a', 'chamber_temperature'),
            '加热板温度': value('env_a', 'heater_temperature'), self.manifest.get('gasPressureLabel', '氩气压力'): value('env_a', 'argon_pressure'),
            '储粉桶物位计': value('env_b', 'powder_level'), '成形室氧含量ppm': value('env_b', 'oxygen', 10000),
            '循环气体实时流量': value('env_c', 'gas_flow'), '风机转速': value('env_c', 'fan_speed'),
        }
        access['torque'] = {
            't': [r['time'] - row['recoat'] for r in torque],
            'scraper': [r['scraper'] for r in torque], 'platform': [r['platform'] for r in torque],
            'events': [{'s': row['melt'] - row['recoat'], 'name': '熔化开始'}] if at >= row['melt'] else [],
            'recoatDur': row['melt'] - row['recoat'],
        }
        # 同一时刻两种图像可能属于不同层：保留各通道最后到达的帧并显式返回帧层号。
        # 否则层结束恰等于下一层开始时，熔化后图像会被立即清空，永远无法观看。
        def image_time(r, kind):
            return r['imageTimes'][kind] if self.manifest.get('imageOnly') else r[{'before':'melt','after':'end'}[kind]]
        for kind in access['images']:
            arrived = [r for r in rows if image_time(r,kind) <= at]
            image_row = arrived[-1] if arrived else None
            access['images'][kind].update(
                url=self.media_url(image_row['layer'], kind) if image_row else None,
                layer=image_row['layer'] if image_row else None,
                time=display_time(image_time(image_row,kind)) if image_row else '',
                available=bool(image_row))
        access['records'] = []
        for r in [r for r in rows if r['start'] <= at][-6:][::-1]:
            record = copy.deepcopy(self.layer_data(r['layer'])['access']['records'][0])
            complete = at >= r['end']
            record.update(complete=complete, images=sum(at >= image_time(r,kind) for kind in access['images']),
                          state='完整' if complete else '接入中')
            if not complete:
                record.update(dur=None, recoat=None, torqueN=None)
            access['records'].append(record)
        alarms = [{'time': display_time(a['time']), 'text': a['text']} for a in self.alarms if a['time'] <= at]
        access['alarms'] = alarms[::-1][:8]
        access['acquisition'] = {'running': False, 'mode': 'replay', 'layer': current}

        recognized = [r for r in rows if r['recognitionAt'] <= at and self.layer_data(r['layer'])['recognition'] is not None]
        recognition = None
        if recognized:
            target = recognized[-1]['layer']
            recognition = copy.deepcopy(self.layer_data(target)['recognition'])
            recognition['image']['url'] = self.media_url(target, 'before')
            recognition['records'] = [
                {'layer': r['layer'], 'p': self.layer_data(r['layer'])['recognition']['prob']['def'],
                 'label': self.layer_data(r['layer'])['recognition']['label']} for r in recognized[-6:][::-1]]

        traced = [r for r in rows if r['end'] <= at and self.layer_data(r['layer'])['trace'] is not None]
        trace = None
        if traced:
            target = traced[-1]['layer']
            trace = copy.deepcopy(self.layer_data(target)['trace'])
            trace['image']['url'] = self.media_url(target, 'model_view')
            history = []
            for r in traced[-50:]:
                if self.dual is not None:
                    history.append(self.dual.rows[r['layer']])
                    continue
                tr = self.layer_data(r['layer'])['trace']
                f = tr['factors']['dev']
                part, powder = [z['v'] for z in f['zones']]
                history.append({'layer': r['layer'], 'ref': tr['refLayer'], 'part': part, 'powder': powder,
                                'total': f['total'], 'p': f['prob'], 'support': f['support'], 'conclusion': tr['conclusion']})
            trace['curve'].update(layers=history, **{'from': history[0]['layer'], 'to': target})
            trace['records'] = history[-5:][::-1]

        parameters = [
            {'name': '当前层', 'value': current, 'unit': '层'},
            {'name': '刮刀扭矩', 'value': value('torque', 'scraper'), 'unit': '%'},
            {'name': '加工平台扭矩', 'value': value('torque', 'platform'), 'unit': '%'},
            *[{'name': name, 'value': access['env'][key], 'unit': unit} for name, key, unit in [
                ('成形室氧含量', '成形室氧含量ppm', 'ppm'), ('成形室压力', '成形室压力', 'mbar'),
                ('成形室温度', '成形室温度', '℃'), ('加热板温度', '加热板温度', '℃'),
                (self.manifest.get('gasPressureLabel', '氩气压力'), self.manifest.get('gasPressureLabel', '氩气压力'), 'bar'), ('循环气体流量', '循环气体实时流量', 'm³/h'),
                ('风机转速', '风机转速', '%'), ('储粉桶物位', '储粉桶物位计', 'mm')]],
        ]
        if self.manifest.get('imageOnly'):
            parameters = [parameters[0]]
        return {
            'caseId': self.manifest['id'], 'offset': offset, 'time': display_time(at), 'timestamp': at,
            'layer': current, 'segment': index, 'phase': ('熔化图像已到达' if at >= row['end'] else '铺粉图像已到达') if self.manifest.get('imageOnly') else ('层结束' if at >= row['end'] else ('熔化' if at >= row['melt'] else '铺粉')),
            'access': access, 'recognition': recognition, 'trace': trace, 'parameters': parameters,
            'liveTorque': {
                't': [r['time'] for r in live_torque],
                'scraper': [r['scraper'] for r in live_torque],
                'platform': [r['platform'] for r in live_torque],
                'cursor': at, 'layer': current, 'recoatStart': row['recoat'], 'recoatEnd': row['melt'],
            },
            'samples': {k: {'time': display_time(v['time']), 'age': round(at - v['time'], 2)} if v else None for k, v in samples.items()},
            'analysisOrigin': self.manifest.get('analysis', {}).get('origin'), 'controlHistory': [],
            'tracePending': self.layer_data(current)['traceReason'],
        }


@lru_cache(maxsize=1)
def catalog():
    return json.loads((PACK_ROOT / 'catalog.json').read_text(encoding='utf-8'))['cases']


def case_for_device(device_id):
    return next((item for item in catalog() if item['deviceId'] == device_id), None)


def unpack_case(item):
    """校验仓库随附包并原子解包；运行目录可删除后重建，不依赖本机论文目录。"""
    for part in item['archives']:
        if hashlib.sha256((PACK_ROOT / part['file']).read_bytes()).hexdigest() != part['sha256']:
            raise ValueError(f"案例包校验失败：{part['file']}")
    root = RUNTIME_ROOT / item['sha256']
    with EXTRACT_LOCK:
        if not root.is_dir():
            RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=RUNTIME_ROOT) as tmp:
                stage = Path(tmp) / 'case'
                stage.mkdir()
                for part in item['archives']:
                    with zipfile.ZipFile(PACK_ROOT / part['file']) as z:
                        for info in z.infolist():
                            target = (stage / info.filename).resolve()
                            if not target.is_relative_to(stage.resolve()):
                                raise ValueError('案例包包含非法相对路径')
                        z.extractall(stage)
                checksums = json.loads((stage / 'checksums.json').read_text(encoding='utf-8'))
                for name, info in checksums.items():
                    if hashlib.sha256((stage / name).read_bytes()).hexdigest() != info['sha256']:
                        raise ValueError(f'案例文件校验失败：{name}')
                stage.rename(root)
    return root


@lru_cache(maxsize=16)
def get_case(case_id=CASE_ID):
    item = next((c for c in catalog() if c['id'] == case_id), None)
    if item is None:
        raise KeyError(case_id)
    root = unpack_case(item)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    dual = root / manifest['dualPack'] if 'dualPack' in manifest else None
    return ReplayCase(root, dual)


def device_descriptor(device_id=DEVICE_ID):
    item = case_for_device(device_id)
    if item is None:
        raise KeyError(device_id)
    return {
        'id': device_id, 'name': item['name'], 'model': item['model'], 'owner': item.get('owner', '铂力特'),
        'serial': device_id.removeprefix('slm-').removesuffix('-replay').upper(),
        'dataTag': '', 'location': item.get('location', '7103 现场数据设备群'),
        'source': 'replay', 'replayCase': item['id'], 'online': False, 'health': 'unknown',
        'statusText': '等待数据', 'thumbnail': item['thumbnail'],
        'healthData': {'status': 'unknown'}, 'parameters': [],
    }


def replay_devices():
    return [device_descriptor(item['deviceId']) for item in catalog()]
