"""轻量 SQLite 持久化；只统计登记的事件，不将查询次数或模拟操作计作实际故障。"""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from fastapi import HTTPException


@contextmanager
def database():
    path = Path(os.environ.get('SMARTAM_TASK4_DB', Path(__file__).resolve().parents[1]/'data/task4.sqlite'))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.executescript('''
          CREATE TABLE IF NOT EXISTS plans (
            id TEXT PRIMARY KEY, device TEXT NOT NULL, request_id TEXT NOT NULL,
            request_json TEXT NOT NULL, response_json TEXT NOT NULL, UNIQUE(device, request_id));
          CREATE TABLE IF NOT EXISTS region_strategies (
            device TEXT NOT NULL, task TEXT NOT NULL, region TEXT NOT NULL,
            plan_id TEXT NOT NULL, strategy TEXT NOT NULL, automatic INTEGER NOT NULL,
            PRIMARY KEY(device,task,region));
          CREATE TABLE IF NOT EXISTS layer_strategies (
            device TEXT NOT NULL, task TEXT NOT NULL, plan_id TEXT NOT NULL, strategy TEXT NOT NULL,
            PRIMARY KEY(device,task));
          CREATE TABLE IF NOT EXISTS tasks (
            device TEXT NOT NULL, id TEXT NOT NULL, at REAL NOT NULL, faulted INTEGER NOT NULL,
            PRIMARY KEY(device,id));
          CREATE TABLE IF NOT EXISTS maintenance (
            device TEXT NOT NULL, id TEXT NOT NULL, at REAL NOT NULL, description TEXT NOT NULL,
            PRIMARY KEY(device,id));
        ''')
        if db.execute('PRAGMA user_version').fetchone()[0] < 1:
            # 一次性迁移旧版已生效且全区域一致的整层策略，保留升级前的选择。
            db.execute('''INSERT OR IGNORE INTO layer_strategies
                SELECT device,task,MIN(plan_id),MIN(strategy) FROM region_strategies
                GROUP BY device,task
                HAVING MIN(strategy)=MAX(strategy) AND MIN(strategy) IN ('recoat','stop')
                   AND MIN(plan_id)=MAX(plan_id)''')
            db.execute('PRAGMA user_version=1')
            db.commit()
        with db:
            yield db
    finally:
        db.close()


def remember(table, device, identifier, at, value):
    column = {'tasks':'faulted', 'maintenance':'description'}[table]
    # 事件按业务编号幂等；同编号内容冲突明确报错，不能悄悄覆盖历史记录。
    with database() as db:
        db.execute(f'INSERT OR IGNORE INTO {table} VALUES (?,?,?,?)', (device, identifier, at, value))
        row = db.execute(f'SELECT * FROM {table} WHERE device=? AND id=?', (device, identifier)).fetchone()
        if row['at'] != at or row[column] != value:
            raise HTTPException(409, '该编号已登记不同内容，请使用新的记录编号')


def stored_plan(device, plan_id):
    with database() as db:
        row = db.execute('SELECT response_json FROM plans WHERE id=? AND device=?', (plan_id,device)).fetchone()
    if not row:
        raise HTTPException(404, '未找到该设备的调控方案')
    return json.loads(row[0])


def active_control_state(device, task):
    # 同一读事务取分区/整层状态，避免并发切换时拼接出两种时刻的状态。
    with database() as db:
        db.execute('BEGIN')
        regions = {r['region']: dict(r) for r in db.execute(
            'SELECT * FROM region_strategies WHERE device=? AND task=?', (device,task or ''))}
        layer = db.execute('SELECT * FROM layer_strategies WHERE device=? AND task=?', (device,task or '')).fetchone()
    return regions, dict(layer, automatic=0) if layer else None


def activate_plan(device, plan_id, layer_regions=None):
    # 区域状态与方案状态同事务更新；重复模拟旧方案不能覆盖后来选择的新策略。
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT response_json,request_json FROM plans WHERE id=? AND device=?', (plan_id,device)).fetchone()
        if not row:
            raise HTTPException(404, '未找到该设备的调控方案')
        result, request = json.loads(row[0]), json.loads(row[1])
        if result['state'] == 'simulated':
            return result
        if result['strategy'] in ('recoat', 'stop'):
            # 整层策略独立存储，后续层新增区域也受同一策略约束。
            db.execute('''INSERT INTO layer_strategies VALUES (?,?,?,?)
                ON CONFLICT(device,task) DO UPDATE SET plan_id=excluded.plan_id,strategy=excluded.strategy''',
                (device, result['taskId'] or '', plan_id, result['strategy']))
            # 旧版本可能保存了只含单个区域的全局方案，应用前按该任务切片展开。
            template = result['regions'][0]
            result['regions'] = [dict(template, regionId=r['id'], name=r['name'], color=r['color'],
                                      strategy=result['strategy'], scope='layer', automatic=False)
                                 for r in layer_regions]
        # 切回分区策略即退出整层覆盖；其余区域恢复默认策略1，不能留下半层停机/重铺粉。
        if result['strategy'] in ('adjust', 'remelt'):
            db.execute('DELETE FROM layer_strategies WHERE device=? AND task=?', (device, result['taskId'] or ''))
            db.execute("DELETE FROM region_strategies WHERE device=? AND task=? AND strategy IN ('recoat','stop')",
                       (device, result['taskId'] or ''))
        for region in result['regions']:
            db.execute('''INSERT INTO region_strategies VALUES (?,?,?,?,?,?)
                ON CONFLICT(device,task,region) DO UPDATE SET
                plan_id=excluded.plan_id,strategy=excluded.strategy,automatic=excluded.automatic''',
                (device, result['taskId'] or '', region['regionId'], plan_id, result['strategy'], int(request['automatic'])))
        result.update(state='simulated', executed=False)
        db.execute('UPDATE plans SET response_json=? WHERE id=?', (json.dumps(result,ensure_ascii=False),plan_id))
    return result
