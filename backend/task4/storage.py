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
          CREATE TABLE IF NOT EXISTS tasks (
            device TEXT NOT NULL, id TEXT NOT NULL, at REAL NOT NULL, faulted INTEGER NOT NULL,
            PRIMARY KEY(device,id));
          CREATE TABLE IF NOT EXISTS maintenance (
            device TEXT NOT NULL, id TEXT NOT NULL, at REAL NOT NULL, description TEXT NOT NULL,
            PRIMARY KEY(device,id));
        ''')
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
