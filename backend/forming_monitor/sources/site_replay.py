"""现场设备离线回放数据源：读取设备导出的原始数据（只读）。

- 图像：raw/<设备>/<批次>/camera_zd/ 中每层的铺粉后（a）与烧结后（b）帧，2592×1944。
- 扭矩、设备状态参数、打印日志、报警日志、单层用时、任务信息：raw/<设备>/<批次>/csv_data/*.csv（UTF-16）。
- 逐层事件时刻（层开始、铺粉开始、烧结开始、层结束）：manifests/review_all.csv。
- 识别用的铺粉段扭矩窗口：第四章预处理的 torque_layer/<类别>/*_torque.csv（窗口截取规则与第四章一致；类别目录不对外暴露）。
设备内部编号、批次号与路径只在服务端使用。
"""
from __future__ import annotations

import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .base import DataSource, LayerInputs

TQ_EVENTS = ['刮刀移动开始', '刮刀结束移动', '平台移动开始', '烧结开始']
EV_SHOW = {'烧结开始': '熔化开始'}  # 设备日志写“烧结”，界面统一称“熔化”


def _read16(p: Path, **kw) -> pd.DataFrame:
    return pd.read_csv(p, encoding='utf-16', **kw)


def _ts(s) -> pd.Series:
    return pd.to_datetime(s)


class SiteReplaySource(DataSource):
    def __init__(self, raw_root: Path, pre_root: Path, device_code: str, build: str, part: str, task: dict):
        self.raw_root = raw_root
        self.raw = raw_root / 'raw' / device_code / build
        self.csv = self.raw / 'csv_data'
        self.pre = pre_root / device_code / part / 'torque_layer'
        self.device_code, self.build = device_code, build
        self.task_cfg = task
        self._lock = threading.Lock()
        self._big = None

    # ------------------------------------------------------------------ 索引
    @lru_cache(maxsize=1)
    def _index(self) -> pd.DataFrame:
        idx = pd.read_csv(self.pre / '层样本索引.csv')
        idx = idx.rename(columns={'层号': 'layer', '铺粉后图像': 'before_name', '熔化后图像': 'after_name', '扭矩文件': 'tq_file'})
        rv = pd.read_csv(self.raw_root / 'manifests' / 'review_all.csv')
        rv = rv[(rv.device == self.device_code) & (rv.build == self.build) & (rv.pair_status == 'paired') & (rv.torque_status == 'aligned')]
        rv = rv.sort_values('layer_id').drop_duplicates('layer_id').rename(columns={'layer_id': 'layer'})
        m = idx[['layer', 'before_name', 'after_name', 'tq_file']].merge(
            rv[['layer', 'event_start', 'recoating_start', 'sintering_start', 'event_end']], on='layer')
        m = m[[(self.raw / 'camera_zd' / a).is_file() and (self.raw / 'camera_zd' / b).is_file() for a, b in zip(m.before_name, m.after_name)]]
        for c in ('event_start', 'recoating_start', 'sintering_start', 'event_end'):
            m[c] = _ts(m[c])
        return m.sort_values('layer').set_index('layer')

    def _row(self, layer: int):
        idx = self._index()
        if layer not in idx.index:
            raise KeyError(f'第{layer}层无完整数据')
        return idx.loc[layer]

    def _tables(self) -> dict:
        """大表只在首次使用时读入内存（每个约0.3 s）。"""
        with self._lock:
            if self._big is None:
                tq = _read16(self.csv / '刮刀位置_刮刀扭矩_加工平台位置_加工平台扭矩.csv', usecols=[1, 3, 5])
                tq.columns = ['t', 'scraper', 'platform']
                a = _read16(self.csv / '成形室压力_成形室温度_加热板温度_氩气压力.csv', usecols=[1, 2, 3, 4, 5])
                a.columns = ['t', '成形室压力', '成形室温度', '加热板温度', '氩气压力']
                b = _read16(self.csv / '落粉轴角度_落粉轴扭矩_储粉桶物位计_成形室氧含量.csv', usecols=[1, 4, 5])
                b.columns = ['t', '储粉桶物位计', '成形室氧含量']
                c = _read16(self.csv / '气动蝶阀压力_循环气体实时流量_风机转速_净气室压力.csv', usecols=[1, 3, 4])
                c.columns = ['t', '循环气体实时流量', '风机转速']
                log = _read16(self.csv / '打印日志.csv')
                log.columns = ['i', 't', 'ev', 'info']
                al = _read16(self.csv / '报警日志.csv')
                al.columns = ['i', 'no', 't', 'h', 'text', 'level', 'parts']
                lt = _read16(self.csv / '每层工作时间统计.csv')
                lt.columns = ['layer', 'sec']
                for d in (tq, a, b, c, log, al):
                    d['t'] = _ts(d['t'])
                self._big = {'tq': tq, 'env_a': a, 'env_b': b, 'env_c': c, 'log': log[log.ev.isin(TQ_EVENTS)],
                             'alarm': al.sort_values('t'), 'layer_sec': lt.set_index('layer')['sec']}
            return self._big

    @lru_cache(maxsize=1)
    def _task_info(self) -> dict:
        info = (self.csv / '任务信息.csv').read_bytes().decode('utf-16')

        def num(k):
            i = info.find(k + ':')
            return info[i + len(k) + 1:].split(',')[0].split('"')[0].split('\n')[0].strip()
        return {'layers': int(num('零件层数')), 'height': float(num('零件高度(mm)')), 'parts': int(num('零件数量'))}

    # ------------------------------------------------------------------ 接口实现
    def tasks(self) -> list[dict]:
        t = self._task_info()
        return [{**self.task_cfg, 'layers': t['layers'], 'height': t['height'], 'parts': t['parts']}]

    def _check(self, task_id):
        if task_id != self.task_cfg['id']:
            raise KeyError(f'无成形任务 {task_id}')

    def layers(self, task_id: str) -> list[int]:
        self._check(task_id)
        return [int(v) for v in self._index().index]

    def image_path(self, task_id: str, layer: int, kind: str) -> Path:
        self._check(task_id)
        r = self._row(layer)
        return self.raw / 'camera_zd' / (r.before_name if kind == 'before' else r.after_name)

    def layer_time(self, task_id: str, layer: int) -> str:
        return str(self._row(layer).event_start)

    def inputs(self, task_id: str, layer: int) -> LayerInputs:
        self._check(task_id)
        r = self._row(layer)
        w = pd.read_csv(self.pre / r.tq_file)
        return LayerInputs(layer=layer, before=self.image_path(task_id, layer, 'before'), after=self.image_path(task_id, layer, 'after'),
                           torque_times=w['时间'].tolist(), scraper=w['刮刀扭矩(%)'].tolist(), platform=w['加工平台扭矩(%)'].tolist())

    def _torque_curve(self, r) -> dict:
        """铺粉开始前3 s 至烧结开始后15 s；同一秒内的采样点按序号在该秒内均匀排布，仅用于作图。"""
        T = self._tables()
        t_rec, t_sin = r.recoating_start, r.sintering_start
        lo, hi = t_rec - pd.Timedelta(seconds=3), t_sin + pd.Timedelta(seconds=15)
        tq = T['tq']
        w = tq[(tq.t >= lo) & (tq.t <= hi)].copy()
        k = w.groupby('t').cumcount()
        w['s'] = (w.t - t_rec).dt.total_seconds() + k / w.groupby('t')['t'].transform('count')
        log = T['log']
        ev = log[(log.t >= lo) & (log.t <= hi)]
        return {'t': [round(float(v), 3) for v in w.s], 'scraper': [round(float(v), 3) for v in w.scraper],
                'platform': [round(float(v), 3) for v in w.platform],
                'events': [{'s': float((e.t - t_rec).total_seconds()), 'name': EV_SHOW.get(e.ev, e.ev)} for e in ev.itertuples()],
                'recoatDur': float((t_sin - t_rec).total_seconds())}

    def _env(self, t0) -> dict:
        T = self._tables()

        def at(df, cols):
            i = int(np.searchsorted(df.t.values, np.datetime64(t0)))
            i = min(max(i, 0), len(df) - 1)
            return {c: float(df[c].iloc[i]) for c in cols}
        env = {**at(T['env_a'], ['成形室压力', '成形室温度', '加热板温度', '氩气压力']),
               **at(T['env_b'], ['储粉桶物位计']), **at(T['env_c'], ['循环气体实时流量', '风机转速'])}
        # 氧含量常低于传感器分辨率（读数为0），显示该时刻之前最近一次非零读数，换算为 ppm（1% = 10000 ppm）
        b = T['env_b']
        nz = b[(b.t <= t0) & (b['成形室氧含量'] > 0)]
        env['成形室氧含量ppm'] = round(float(nz['成形室氧含量'].iloc[-1]) * 1e4, 2) if len(nz) else None
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in env.items()}

    def frame(self, task_id: str, layer: int) -> dict:
        self._check(task_id)
        r = self._row(layer)
        tq = self._tables()['tq']
        rate = float(tq.t.iloc[:20000].groupby(tq.t.iloc[:20000]).size().median())
        return {
            'times': {'before': str(r.event_start), 'after': str(r.event_end)},
            'torque': self._torque_curve(r), 'env': self._env(r.event_start),
            'channels': [
                {'name': '铺粉后图像', 'spec': '2592×1944', 'rate': '每层1帧'},
                {'name': '熔化后图像', 'spec': '2592×1944', 'rate': '每层1帧'},
                {'name': '刮刀扭矩', 'spec': '%', 'rate': f'约{rate:.0f}次/s'},
                {'name': '加工平台扭矩', 'spec': '%', 'rate': f'约{rate:.0f}次/s'},
                {'name': '设备状态参数', 'spec': '压力、温度、氧含量等', 'rate': f'约{rate:.0f}次/s'},
            ],
        }

    def record(self, task_id: str, layer: int) -> dict:
        self._check(task_id)
        r = self._row(layer)
        T = self._tables()
        tq = T['tq']
        n = int(((tq.t >= r.recoating_start) & (tq.t <= r.sintering_start)).sum())
        sec = T['layer_sec'].get(layer, np.nan)
        return {'layer': int(layer), 'start': str(r.event_start.time()), 'recoat': round(float((r.sintering_start - r.recoating_start).total_seconds()), 1),
                'dur': None if pd.isna(sec) else round(float(sec), 1), 'torqueN': n, 'images': 2, 'complete': True}

    def alarms(self, task_id: str, until: str | None = None, n: int = 5) -> list[dict]:
        al = self._tables()['alarm']
        if until is not None:
            al = al[al.t <= pd.Timestamp(until)]
        return [{'time': str(z.t), 'text': str(z.text).replace('$', '；')} for z in al.iloc[::-1].head(n).itertuples()]
