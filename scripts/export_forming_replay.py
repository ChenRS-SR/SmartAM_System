"""将当前 BLT-S430 数据、模型和分析结果封存为可独立读取的回放案例。"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

import pandas as pd
import torch
from forming_monitor import config
from forming_monitor.service import Device

CASE_ID = 'blt-s430-20240828'
OUT = ROOT / 'backend/data/replay_cases' / CASE_ID
TZ = timezone(timedelta(hours=8))


def epoch(value):
    return pd.Timestamp(value).tz_localize('Asia/Shanghai').timestamp()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    if (OUT / 'manifest.json').exists():
        raise SystemExit('该案例已封存。请使用新的案例编号创建版本，不覆盖正在使用的案例。')
    torch.set_num_threads(2)
    cfg = next(d for d in json.loads((config.PACK_DIR / 'devices.json').read_text())['devices'] if d['id'] == 'blt-s430')
    # 导出使用独立缓存，避免和运行中的服务同时改写原分析缓存。
    cache = OUT / 'analysis_cache'
    cache.mkdir(parents=True, exist_ok=True)
    for file in (config.CACHE_DIR / 'blt-s430').glob('*.json'):
        target = cache / 'blt-s430' / file.name
        target.parent.mkdir(exist_ok=True)
        if not target.exists():
            shutil.copy2(file, target)
    config.CACHE_DIR = cache
    d = Device(cfg, {})
    src = d.source
    layers = d.layers()
    for folder in ('assets', 'layers', 'source', 'torque_inputs'):
        (OUT / folder).mkdir(exist_ok=True)
    shutil.copy2(config.MODEL_DIR / cfg['recognizer']['bundle'], OUT / 'source/model.pt')
    shutil.copy2(config.PACK_DIR / cfg['photo'], OUT / 'assets/photo.jpg')
    write_json(OUT / 'source/device.json', cfg)
    shutil.copy2(src.pre / '层样本索引.csv', OUT / 'source/layer_index.csv')
    shutil.copy2(src.raw_root / 'manifests/review_all.csv', OUT / 'source/review_all.csv')
    # 原始 CSV 原样保存，回放索引仅为加速读取，不改写传感器读数或时间。
    for file in sorted(src.csv.glob('*.csv')):
        shutil.copy2(file, OUT / 'source' / file.name)
    segments = []
    for layer in layers:
        row = src._row(layer)
        start, end = epoch(row.event_start), epoch(row.event_end)
        if not segments or layer != segments[-1]['lastLayer'] + 1:
            segments.append({'firstLayer': layer, 'lastLayer': layer, 'start': start, 'end': end})
        else:
            segments[-1].update(lastLayer=layer, end=end)
    offset = 0
    for segment in segments:
        segment['offset'] = offset
        offset += segment['end'] - segment['start']
        segment['duration'] = segment['end'] - segment['start']

    # SQLite 保留同秒采样的原始顺序；不捏造毫秒时间，不使用未来采样填充当前值。
    db = sqlite3.connect(OUT / 'samples.sqlite')
    sources = [
        ('torque', '刮刀位置_刮刀扭矩_加工平台位置_加工平台扭矩.csv', [1, 3, 5], ['time', 'scraper', 'platform']),
        ('env_a', '成形室压力_成形室温度_加热板温度_氩气压力.csv', [1, 2, 3, 4, 5], ['time', 'chamber_pressure', 'chamber_temperature', 'heater_temperature', 'argon_pressure']),
        ('env_b', '落粉轴角度_落粉轴扭矩_储粉桶物位计_成形室氧含量.csv', [1, 4, 5], ['time', 'powder_level', 'oxygen']),
        ('env_c', '气动蝶阀压力_循环气体实时流量_风机转速_净气室压力.csv', [1, 3, 4], ['time', 'gas_flow', 'fan_speed']),
    ]
    for table, filename, cols, names in sources:
        df = pd.read_csv(src.csv / filename, encoding='utf-16', usecols=cols)
        df.columns = names
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize('Asia/Shanghai').astype('int64') / 1e9
        df['sequence'] = range(len(df))
        df = df.sort_values(['time', 'sequence'])
        keep = pd.Series(False, index=df.index)
        for segment in segments:
            keep |= (df.time >= segment['start']) & (df.time <= segment['end'])
        df[keep].to_sql(table, db, if_exists='replace', index=False)
        db.execute(f'CREATE INDEX "{table}_time" ON "{table}" (time, sequence)')
    db.commit()
    db.close()

    rows = []
    for i, layer in enumerate(layers):
        r = src._row(layer)
        segment = next(s for s in segments if s['firstLayer'] <= layer <= s['lastLayer'])
        entry = {
            'layer': layer, 'start': epoch(r.event_start), 'end': epoch(r.event_end),
            'recoat': epoch(r.recoating_start), 'melt': epoch(r.sintering_start),
            'offset': segment['offset'] + epoch(r.event_start) - segment['start'],
        }
        for kind in ('before', 'after'):
            shutil.copy2(src.image_path(d.task_cfg['id'], layer, kind), OUT / 'assets' / f'{layer}_{kind}.jpg')
        inp = src.inputs(d.task_cfg['id'], layer)
        entry['recognitionAt'] = max(entry['melt'], max(epoch(t) for t in inp.torque_times))
        shutil.copy2(src.pre / r.tq_file, OUT / 'torque_inputs' / f'{layer}.csv')
        target = OUT / 'layers' / f'{layer}.json'
        if not target.exists():
            recognition = d.recognize(layer, cfg['recognizer']['threshold'], ['vis', 'tq'], n_records=1)
            trace = None
            trace_reason = None
            if d.ref_layer(layer) is not None:
                trace = d.trace(layer, cfg['trace']['band_px'], n_curve=5, n_records=1)
                # 仅删除旧配置中的示意因子；双输出模型的真实工艺侧结果必须保留。
                if trace['mode'] == 'single':
                    trace['factors'].pop('proc')
                    trace['notes'].pop('proc')
                trace['replay'] = True
                shutil.copy2(d.media(layer, 'model_view', 1200), OUT / 'assets' / f'{layer}_model_view.jpg')
            else:
                trace_reason = '此前没有可用正常参照层，未计算溯源结果'
            recognition['records'] = []
            if trace:
                trace['records'] = []
                trace['curve']['layers'] = []
            write_json(target, {'access': d.access(layer, n_records=1), 'recognition': recognition, 'trace': trace, 'traceReason': trace_reason})
        rows.append(entry)
        if i % 10 == 0 or i == len(layers) - 1:
            print(f'已封存 {i + 1}/{len(layers)} 层（当前 {layer}）', flush=True)

    alarms = src._tables()['alarm']
    alarm_rows = [{'time': epoch(r.t), 'text': str(r.text).replace('$', '；')} for r in alarms.itertuples()]
    write_json(OUT / 'alarms.json', alarm_rows)
    manifest = {
        'schemaVersion': 1, 'id': CASE_ID, 'deviceId': 'slm-b17-replay',
        'name': 'BLT-S430 历史回放', 'model': 'BLT-S430', 'task': d.task_public(),
        'timezone': 'Asia/Shanghai', 'sourceDevice': d.id, 'segments': segments, 'layers': rows,
        'duration': offset, 'defaultOffset': next(r['offset'] for r in rows if r['layer'] == 2540),
        'analysis': {'origin': '离线模型分析', 'threshold': cfg['recognizer']['threshold'], 'modalities': ['vis', 'tq'],
                     'bandPx': cfg['trace']['band_px'], 'modelSha256': digest(OUT / 'source/model.pt'),
                     'processModelAvailable': bool(cfg['trace'].get('dual_pack')), 'controlHistoryAvailable': False},
        'timeNotes': '采样时间精度为秒，同秒记录保留原始顺序；图像文件只精确到分钟，按铺粉完成、层结束事件对齐。',
        'createdAt': datetime.now(TZ).isoformat(),
    }
    # 最后原子发布清单，半成品不会被设备群当成可用案例。
    files = {}
    for folder in ('assets', 'layers', 'source', 'torque_inputs'):
        for file in sorted((OUT / folder).rglob('*')):
            if file.is_file():
                files[str(file.relative_to(OUT))] = {'bytes': file.stat().st_size, 'sha256': digest(file)}
    for name in ('samples.sqlite', 'alarms.json'):
        file = OUT / name
        files[name] = {'bytes': file.stat().st_size, 'sha256': digest(file)}
    write_json(OUT / 'checksums.json', files)
    write_json(OUT / 'manifest.tmp', manifest)
    os.replace(OUT / 'manifest.tmp', OUT / 'manifest.json')
    print(f'案例发布完成：{OUT}', flush=True)


if __name__ == '__main__':
    main()
