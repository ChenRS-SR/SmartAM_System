"""成形监测服务层：设备清单、逐层接入（离线回放游标）、异常识别、异常溯源与事件记录。

接口响应中只出现设备型号、任务名称、层号与结果，不出现设备内部编号、现场代号与文件路径。
"""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from . import config
from .engine import Recognizer
from .engine import preprocess as P
from .sources.site_replay import SiteReplaySource
from trace_results import DualTraceResults

MOD_NAMES = {'vis': '铺粉后图像', 'tq': '刮刀与平台扭矩'}
ACTIONS = {'dev': '检修刮刀与供粉机构', 'proc': '调整工艺参数'}


def conclusion_of(dev_on: bool, proc_on: bool) -> str:
    if dev_on and proc_on:
        return '由二者共同诱发'
    if dev_on:
        return '由设备因素诱发'
    if proc_on:
        return '由工艺因素诱发'
    return '未见异常'


class JsonCache:
    """键值缓存，按文件落盘，删除缓存目录后自动重算。"""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        try:
            self._d = json.loads(path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            self._d = {}

    def get(self, key):
        return self._d.get(key)

    def set(self, key, value):
        with self._lock:
            self._d[key] = value
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix('.tmp')
            tmp.write_text(json.dumps(self._d, ensure_ascii=False), encoding='utf-8')
            tmp.replace(self.path)


class ApiError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status, self.msg = status, msg


class Device:
    """一台设备的运行时：配置、数据源、模型、接入游标、事件。"""

    def __init__(self, cfg: dict, recognizers: dict):
        self.cfg = cfg
        self.id = cfg['id']
        src = cfg['source']
        self.task_cfg = src['task']
        self.source = None
        self.pack = None
        if src['type'] == 'site_replay':
            self.source = SiteReplaySource(config.SITE_RAW_ROOT, config.SITE_PRE_ROOT, src['device_code'], src['build'], src['part'], src['task'])
        elif src['type'] == 'result_replay':
            self.pack = json.loads((config.PACK_DIR / src['pack']).read_text(encoding='utf-8'))
        self.rec = None
        if cfg.get('recognizer'):
            b = cfg['recognizer']['bundle']
            if b not in recognizers:
                dev = config.TORCH_DEVICE
                if dev == 'auto':
                    import torch
                    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
                recognizers[b] = Recognizer(config.MODEL_DIR / b, dev)
            self.rec = recognizers[b]
        cdir = config.CACHE_DIR / self.id
        self.c_prob = JsonCache(cdir / 'recognition.json')
        self.c_shap = JsonCache(cdir / 'shapley.json')
        self.events = deque(maxlen=50)
        self.acq = {'running': False, 'task': self.task_cfg['id'], 'layer': cfg['default_layer'], 't0': 0.0, 'i0': 0,
                    'interval': config.REPLAY_INTERVAL}
        self._mask_cache = {}

    # ------------------------------------------------------------------ 公共信息
    def public(self) -> dict:
        c = self.cfg
        return {'id': c['id'], 'name': c['name'], 'kind': c['kind'], 'laser': c['laser'], 'modalGroups': c['modalGroups'],
                'modules': c['modules'], 'aliases': c.get('aliases', []),
                'photo': f'devices/{c["id"]}/photo' if c.get('photo') else None}

    def task_public(self) -> dict:
        return {'id': self.task_cfg['id'], 'name': self.task_cfg['name']}

    def tasks(self) -> list[dict]:
        if self.source:
            return self.source.tasks()
        return [{**self.task_cfg, 'layers': None}]

    def check_task(self, task_id: str | None) -> str:
        task_id = task_id or self.task_cfg['id']
        if task_id != self.task_cfg['id']:
            raise ApiError(404, f'无成形任务 {task_id}')
        return task_id

    def layers(self, task_id: str | None = None) -> list[int]:
        self.check_task(task_id)
        if self.source:
            return self.source.layers(self.task_cfg['id'])
        return [int(self.pack['layer'])]

    def need(self, module: str):
        if module not in self.cfg['modules']:
            raise ApiError(409, f'{self.cfg["name"]} 未配置{ {"access": "数据接入", "recognition": "异常识别", "trace": "异常溯源"}[module] }模块')

    def check_layer(self, layer: int, task_id=None) -> int:
        if int(layer) not in self.layers(task_id):
            raise ApiError(404, f'第{layer}层无完整数据')
        return int(layer)

    # ------------------------------------------------------------------ 接入游标（离线回放）
    def cursor(self) -> int:
        a = self.acq
        if a['running']:
            L = self.layers()
            i = min(a['i0'] + int((time.time() - a['t0']) / a['interval']), len(L) - 1)
            a['layer'] = L[i]
            if i == len(L) - 1:
                a['running'] = False
        return a['layer']

    def acq_status(self) -> dict:
        layer = self.cursor()
        return {'mode': 'replay', 'running': self.acq['running'], 'task': self.task_public(), 'layer': layer,
                'interval': self.acq['interval'], 'time': self.layer_time(layer)}

    def acq_start(self, task_id=None, from_layer=None, interval=None) -> dict:
        self.need('access')
        self.check_task(task_id)
        L = self.layers()
        start = self.check_layer(from_layer) if from_layer is not None else self.cursor()
        i0 = L.index(start)
        if i0 == len(L) - 1 and from_layer is None:
            i0 = 0
        self.acq.update(running=True, t0=time.time(), i0=i0, layer=L[i0], interval=float(interval or self.acq['interval']))
        return self.acq_status()

    def acq_stop(self) -> dict:
        self.cursor()
        self.acq['running'] = False
        return self.acq_status()

    def layer_time(self, layer: int) -> str | None:
        if self.source:
            try:
                return self.source.layer_time(self.task_cfg['id'], layer)
            except KeyError:
                return None
        return None

    # ------------------------------------------------------------------ 识别
    def _tensors(self, layer: int):
        x = self.source.inputs(self.task_cfg['id'], layer)
        before = P.read_rgb(x.before)
        tq224, grid = P.resample_torque(x.torque_times, x.scraper, x.platform)
        return x, before, P.to_tensor(P.crop_letterbox(before, self.rec.crop)), self.rec.norm_torque(tq224), tq224, grid

    def probs(self, layer: int) -> dict:
        """融合与单模态异常概率（与阈值、所选模态无关，可缓存）。"""
        key = str(layer)
        hit = self.c_prob.get(key)
        if hit:
            return hit
        _, _, v, t, _, _ = self._tensors(layer)
        p = self.rec.recognize(v, t)
        self.c_prob.set(key, p)
        return p

    @staticmethod
    def apply(p: dict, threshold: float, mods: list[str], weights: dict) -> dict:
        if mods == ['vis']:
            q = p['vis']
        elif mods == ['tq']:
            q = p['tq']
        else:
            q = p['fused']
        w = {m: (weights[m] if m in mods else 0.0) for m in ('vis', 'tq')}
        s = sum(w.values()) or 1.0
        return {'p': q, 'label': '异常' if q >= threshold else '正常', 'weights': {m: v / s for m, v in w.items()}}

    def recognize(self, layer: int | None, threshold: float, mods: list[str], task_id=None, n_records: int = 5) -> dict:
        self.need('recognition')
        self.check_task(task_id)
        layer = self.check_layer(layer if layer is not None else self.cursor())
        mods = [m for m in ('vis', 'tq') if m in mods]
        if not mods:
            raise ApiError(422, '至少选择一种输入模态')
        if not 0 < threshold < 1:
            raise ApiError(422, '判定阈值应在 0～100% 之间')
        x, before, _, _, tq224, grid = self._tensors(layer)
        p = self.probs(layer)
        r = self.apply(p, threshold, mods, self.rec.weights)
        h, w = before.shape[:2]
        L = self.layers()
        prev = [v for v in L if v <= layer][-n_records:][::-1]
        records = []
        for v in prev:
            q = self.apply(self.probs(v), threshold, mods, self.rec.weights)
            records.append({'layer': v, 'p': q['p'], 'label': q['label']})
        out = {
            'device': {'id': self.id, 'name': self.cfg['name']}, 'task': self.task_public(), 'layer': layer, 'time': self.layer_time(layer),
            'model': {'name': self.rec.meta['name'], 'source': self.rec.meta['source_device']},
            'params': {'threshold': threshold, 'modalities': mods},
            'image': {'url': f'media/{self.id}/{self.task_cfg["id"]}/{layer}/before', 'w': w, 'h': h, 'box': self.rec.crop},
            'prob': {'def': r['p'], 'vis': p['vis'], 'tq': p['tq']}, 'label': r['label'], 'weights': r['weights'],
            'singles': [{'key': m, 'name': MOD_NAMES[m], 'p': p[m], 'label': '异常' if p[m] >= threshold else '正常', 'used': m in mods}
                        for m in ('vis', 'tq')],
            'torque': {'t': [round(float(v), 3) for v in grid], 'scraper': [round(float(v), 3) for v in tq224[0]],
                       'platform': [round(float(v), 3) for v in tq224[1]]},
            'records': records,
        }
        self.log('异常识别', layer, f'第{layer}层 {r["label"]}（异常概率 {r["p"] * 100:.2f}%）')
        return out

    # ------------------------------------------------------------------ 溯源
    def _masks(self, layer: int, band_px: int):
        key = (layer, band_px)
        if key not in self._mask_cache:
            x = self.source.inputs(self.task_cfg['id'], layer)
            self._mask_cache[key] = P.part_mask(P.read_rgb(x.after), P.read_rgb(x.before), self.rec.crop, band_px)
            if len(self._mask_cache) > 256:
                self._mask_cache.pop(next(iter(self._mask_cache)))
        return self._mask_cache[key]

    def ref_layer(self, layer: int) -> int | None:
        """前序最近正常层：当前层之前最近的、被同一识别模型判为正常（融合异常概率 < 0.5）的层，不使用标签。"""
        L = self.layers()
        for v in reversed([q for q in L if q < layer]):
            if self.probs(v)['fused'] < 0.5:
                return v
        return None

    def shapley(self, layer: int, band_px: int, ref: int) -> dict:
        key = f'{layer}|{band_px}|{ref}'
        hit = self.c_shap.get(key)
        if hit:
            return hit
        _, _, cur, tq, _, _ = self._tensors(layer)
        _, _, rv, _, _, _ = self._tensors(ref)
        _, band = self._masks(layer, band_px)
        s = self.rec.shapley(cur, rv, band, tq)
        self.c_shap.set(key, s)
        return s

    @staticmethod
    def factor(name: str, part: float, powder: float, upper: float, prob: float, illustrative: bool = False) -> dict:
        """分区判据（第五章）：任一区的贡献超过上限水平，即判定该类诱发异常得到体现，超过的区为支撑区域。
        两区之和为总改变量（等于当前层与参照层的 logit 差），只显示、不作判断依据。"""
        zones = [{'key': 'part', 'name': '零件区', 'v': part, 'over': part >= upper},
                 {'key': 'powder', 'name': '粉床区', 'v': powder, 'over': powder >= upper}]
        support = [z['name'] for z in zones if z['over']]
        return {'name': name, 'zones': zones, 'total': part + powder, 'upper': upper, 'present': bool(support),
                'support': support, 'prob': prob, 'illustrative': illustrative}

    def _result(self, f: dict) -> dict:
        concl = conclusion_of(f['dev']['present'], f['proc']['present'])
        support = [z for z in ('零件区', '粉床区') if z in f['dev']['support'] + f['proc']['support']]
        return {'conclusion': concl, 'support': support, 'actions': [ACTIONS[k] for k in ('proc', 'dev') if f[k]['present']]}

    def trace(self, layer: int | None, band_px: int | None, ref_mode: str = 'prev_normal', ref_layer: int | None = None,
              task_id=None, n_curve: int = 41, n_records: int = 4) -> dict:
        self.need('trace')
        self.check_task(task_id)
        if self.pack is not None:
            return self._trace_pack(layer, n_curve, n_records)
        layer = self.check_layer(layer if layer is not None else self.cursor())
        tc = self.cfg['trace']
        if tc.get('dual_pack'):
            if band_px not in (None, tc['band_px']) or ref_mode != 'prev_normal':
                raise ApiError(422, '已归档双输出结果采用固定边缘邻域及前序最近正常层')
            return self._trace_dual(layer, n_curve, n_records)
        band_px = int(tc['band_px'] if band_px is None else band_px)
        if not 0 <= band_px <= 40:
            raise ApiError(422, '边缘邻域应在 0～40 像素之间')
        if ref_mode == 'manual':
            if ref_layer is None or int(ref_layer) >= layer:
                raise ApiError(422, '指定参照层应早于当前层')
            ref = self.check_layer(ref_layer)
        else:
            ref = self.ref_layer(layer)
            if ref is None:
                raise ApiError(409, '当前层之前没有被判为正常的层，无法选取参照层')
        s = self.shapley(layer, band_px, ref)
        pf = tc['process_factor']
        f = {'dev': self.factor('设备诱发异常概率', s['part'], s['powder'], tc['upper_dev'], self.probs(layer)['fused']),
             'proc': self.factor('工艺诱发异常概率', pf['part'], pf['powder'], pf['upper'], pf['prob'], True)}
        res = self._result(f)
        part, band = self._masks(layer, band_px)
        x0, y0, x1, y1 = self.rec.crop
        ch, cw = y1 - y0, x1 - x0
        sc = min(224 / ch, 224 / cw)
        nh, nw = round(ch * sc), round(cw * sc)
        curve = self.trace_curve(layer, band_px, n_curve)
        out = {
            'device': {'id': self.id, 'name': self.cfg['name']}, 'task': self.task_public(), 'layer': layer, 'time': self.layer_time(layer),
            'refLayer': ref, 'refMode': ref_mode, 'params': {'bandPx': band_px}, 'mode': 'single',
            'image': {'url': f'media/{self.id}/{self.task_cfg["id"]}/{layer}/model_view', 'width': 896, 'height': 896,
                      'content': [(224 - nw) // 2 / 224, (224 - nh) // 2 / 224, nw / 224, nh / 224]},
            'partContours': P.contours(part), 'bandContours': P.contours(band),
            'factors': f, 'synergy': {'dev': s['synergy']}, **res,
            'curve': curve, 'records': [r for r in curve['layers'][::-1] if r['layer'] <= layer][:n_records],
            'notes': {'proc': pf['note'], 'upper': tc['upper_rule']},
        }
        self.log('异常溯源', layer, f'第{layer}层 {res["conclusion"]}' + (f'，处置对象：{"、".join(res["actions"])}' if res['actions'] else ''))
        return out

    def _trace_dual(self, layer: int, n_curve: int, n_records: int) -> dict:
        """接入同设备同任务双输出结果，避免将旧单输出模型当作两侧输出。"""
        if not hasattr(self, '_dual'):
            self._dual = DualTraceResults(config.PACK_DIR / self.cfg['trace']['dual_pack'])
        row = self._dual.rows[layer]
        if 'ref' not in row:
            raise ApiError(409, '当前层之前没有被判为正常的层，无法选取参照层')
        part, band = self._masks(layer, self._dual.pack['bandPx'])
        x0, y0, x1, y1 = self.rec.crop
        scale = min(224 / (y1 - y0), 224 / (x1 - x0))
        nh, nw = round((y1 - y0) * scale), round((x1 - x0) * scale)
        history = [r for r in self._dual.pack['layers'] if 'ref' in r and layer - n_curve < r['layer'] <= layer]
        result = self._dual.apply({
            'device': {'id': self.id, 'name': self.cfg['name']}, 'task': self.task_public(),
            'layer': layer, 'time': self.layer_time(layer),
            'image': {'url': f'media/{self.id}/{self.task_cfg["id"]}/{layer}/model_view', 'width': 896, 'height': 896,
                      'content': [(224 - nw) // 2 / 224, (224 - nh) // 2 / 224, nw / 224, nh / 224]},
            'partContours': P.contours(part), 'bandContours': P.contours(band),
            'curve': {'from': layer - n_curve + 1, 'to': layer, 'layers': history},
            'records': history[::-1][:n_records],
        }, layer)
        self.log('异常溯源', layer, f'第{layer}层 {result["conclusion"]}')
        return result

    def trace_curve(self, layer: int, band_px: int, n: int = 41) -> dict:
        """当前层及之前若干层在设备诱发异常概率上的两区贡献（参照层规则同上）。"""
        L = self.layers()
        lo = layer - n + 1
        up = self.cfg['trace']['upper_dev']
        rows = []
        for v in [q for q in L if lo <= q <= layer]:
            ref = self.ref_layer(v)
            if ref is None:
                continue
            s = self.shapley(v, band_px, ref)
            sup = [z for z, val in (('零件区', s['part']), ('粉床区', s['powder'])) if val >= up]
            rows.append({'layer': v, 'ref': ref, 'part': s['part'], 'powder': s['powder'], 'total': s['part'] + s['powder'],
                         'p': self.probs(v)['fused'], 'support': sup, 'conclusion': conclusion_of(bool(sup), False)})
        return {'from': lo, 'to': layer, 'upper': {'dev': up}, 'layers': rows}

    def _trace_pack(self, layer, n_curve: int = 41, n_records: int = 4):
        d = self.pack
        if layer is not None and int(layer) != int(d['layer']):
            raise ApiError(404, f'第{layer}层无溯源结果')
        sh, up = d['shapley'], d['upper']
        f = {k: self.factor(n, sh[k]['part'], sh[k]['powder'], up[k], d['prob'][k])
             for k, n in (('dev', '设备诱发异常概率'), ('proc', '工艺诱发异常概率'))}
        res = self._result(f)
        lay = [r for r in d['layers'] if r['layer'] <= d['layer']]
        win = [r for r in d['layers'] if d['layer'] - n_curve < r['layer'] <= d['layer'] + n_curve // 2]
        out = {
            'device': {'id': self.id, 'name': self.cfg['name']}, 'task': self.task_public(), 'layer': d['layer'], 'time': None,
            'refLayer': d['refLayer'], 'refMode': 'prev_normal', 'params': {'bandPx': d['bandPx']}, 'mode': 'dual',
            'image': {'url': f'media/{self.id}/{self.task_cfg["id"]}/{d["layer"]}/model_view', 'width': d['image']['width'],
                      'height': d['image']['height'], 'content': [0, 0, 1, 1]},
            'partContours': d['partContours'], 'bandContours': d['bandContours'], 'factors': f, 'synergy': d['synergy'], **res,
            'curve': {'from': win[0]['layer'], 'to': win[-1]['layer'], 'upper': up, 'layers': win},
            'records': lay[::-1][:n_records], 'replay': True,
        }
        self.log('异常溯源', d['layer'], f'第{d["layer"]}层 {res["conclusion"]}，处置对象：{"、".join(res["actions"])}')
        return out

    # ------------------------------------------------------------------ 数据接入
    def access(self, layer: int | None, task_id=None, n_records: int = 7) -> dict:
        self.need('access')
        self.check_task(task_id)
        layer = self.check_layer(layer if layer is not None else self.cursor())
        tid = self.task_cfg['id']
        fr = self.source.frame(tid, layer)
        info = self.source.tasks()[0]
        L = self.layers()
        recs = [self.source.record(tid, v) for v in [q for q in L if q <= layer][-n_records:][::-1]]
        return {
            'device': {'id': self.id, 'name': self.cfg['name']}, 'task': {**self.task_public(), 'layers': info['layers']},
            'layer': layer, 'progress': {'layer': layer, 'total': info['layers']},
            'images': {k: {'url': f'media/{self.id}/{tid}/{layer}/{k}', 'w': 2592, 'h': 1944, 'time': fr['times'][k]} for k in ('before', 'after')},
            'torque': fr['torque'], 'env': fr['env'], 'channels': fr['channels'], 'records': recs,
            'alarms': self.source.alarms(tid, until=fr['times']['after'], n=3), 'acquisition': self.acq_status(),
        }

    # ------------------------------------------------------------------ 总览与事件
    def log(self, kind: str, layer: int, text: str):
        t = self.layer_time(layer)
        e = {'time': (t or '')[5:16], 'type': kind, 'text': text, 'layer': layer}
        if not any(x['type'] == e['type'] and x['layer'] == layer and x['text'] == text for x in self.events):
            self.events.appendleft(e)

    def overview(self) -> dict:
        layer = self.cursor()
        latest = None
        if 'recognition' in self.cfg['modules']:
            p = self.probs(layer)['fused']
            th = self.cfg['recognizer']['threshold']
            latest = {'type': '异常识别', 'layer': layer, 'label': '异常' if p >= th else '正常', 'detail': f'异常概率 {p * 100:.2f}%'}
            self.log('异常识别', layer, f'第{layer}层 {latest["label"]}（异常概率 {p * 100:.2f}%）')
        elif self.pack is not None:
            d = self.pack
            latest = {'type': '异常溯源', 'layer': d['layer'], 'label': d['conclusion'],
                      'detail': f"工艺诱发异常概率 {d['prob']['proc'] * 100:.2f}%　设备诱发异常概率 {d['prob']['dev'] * 100:.2f}%"}
        t = self.layer_time(layer)
        alarms = self.source.alarms(self.task_cfg['id'], until=t, n=3) if self.source else []
        ev = list(self.events) + [{'time': a['time'][5:16], 'type': '设备报警', 'text': a['text'], 'layer': None} for a in alarms]
        ev.sort(key=lambda e: e['time'], reverse=True)
        info = self.tasks()[0]
        return {'device': self.public(), 'task': {**self.task_public(), 'layers': info.get('layers')}, 'layer': layer, 'time': t,
                'acquisition': self.acq_status() if self.source else None, 'latest': latest, 'events': ev[:6]}

    # ------------------------------------------------------------------ 媒体
    def media(self, layer: int, kind: str, width: int) -> Path:
        out = config.CACHE_DIR / self.id / 'media' / f'{layer}_{kind}_{width}.jpg'
        if out.is_file():
            return out
        out.parent.mkdir(parents=True, exist_ok=True)
        if self.pack is not None:
            if kind != 'model_view' or int(layer) != int(self.pack['layer']):
                raise ApiError(404, '无此图像')
            img = cv2.imread(str(config.PACK_DIR / 'm130' / self.pack['image']['src']))
        else:
            layer = self.check_layer(layer)
            if kind in ('before', 'after'):
                img = cv2.imread(str(self.source.image_path(self.task_cfg['id'], layer, kind)))
            elif kind == 'model_view':
                rgb = P.read_rgb(self.source.image_path(self.task_cfg['id'], layer, 'before'))
                img = cv2.cvtColor(cv2.resize(P.crop_letterbox(rgb, self.rec.crop), (896, 896), interpolation=cv2.INTER_LANCZOS4), cv2.COLOR_RGB2BGR)
            else:
                raise ApiError(404, '无此图像')
        if img.shape[1] > width:
            img = cv2.resize(img, (width, round(img.shape[0] * width / img.shape[1])), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(out), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return out

    def photo(self) -> Path:
        if not self.cfg.get('photo'):
            raise ApiError(404, '无设备照片')
        return config.PACK_DIR / self.cfg['photo']


class FormingService:
    def __init__(self):
        cfg = json.loads((config.PACK_DIR / 'devices.json').read_text(encoding='utf-8'))
        recognizers = {}
        self.devices = {c['id']: Device(c, recognizers) for c in cfg['devices']}
        self.started = datetime.now().isoformat(timespec='seconds')

    def get(self, device_id: str) -> Device:
        """device_id 可以是本模块的设备编号，也可以是 SmartAM 中的设备编号（devices.json 的 aliases）。"""
        if device_id in self.devices:
            return self.devices[device_id]
        for d in self.devices.values():
            if device_id in d.cfg.get('aliases', []):
                return d
        raise ApiError(404, f'设备 {device_id} 未接入成形监测')

    def status(self) -> dict:
        return {'name': '增材制造异常识别系统', 'version': '1.0', 'mode': 'replay', 'modeLabel': config.MODE_LABEL, 'started': self.started,
                'devices': len(self.devices)}

    def warmup(self):
        """后台预算各设备当前层附近的识别与溯源结果，使首次打开页面不必等待。"""
        for d in self.devices.values():
            try:
                if 'trace' in d.cfg['modules'] and d.source is not None:
                    d.trace_curve(d.cfg['default_layer'], d.cfg['trace']['band_px'])
                if 'recognition' in d.cfg['modules']:
                    L = d.layers()
                    for v in [q for q in L if q <= d.cfg['default_layer']][-8:]:
                        d.probs(v)
            except Exception as e:  # 预热失败不影响服务，首次请求时再计算
                print(f'[forming] 预热 {d.id} 失败: {e}')


_service = None
_lock = threading.Lock()


def get_service() -> FormingService:
    global _service
    with _lock:
        if _service is None:
            _service = FormingService()
            threading.Thread(target=_service.warmup, daemon=True).start()
        return _service
