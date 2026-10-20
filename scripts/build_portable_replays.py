"""构建仓库随附案例。只导出真实数据；缺少模型结果时明确标记不可用。"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'backend/replay_cases'
TZ = timezone(timedelta(hours=8))

def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')), encoding='utf-8')

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def epoch(value):
    return pd.Timestamp(value).tz_localize('Asia/Shanghai').timestamp()

def preview(source, target, provenance, root):
    # 图像仅生成页面预览版本，数值与已封存模型输出不重算；记录原图哈希供追溯。
    with Image.open(source) as im:
        original_size = list(im.size)
        im.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        im.convert('RGB').save(target, quality=90, optimize=True)
    provenance[str(target.relative_to(root))] = {'sourceName': source.name, 'sourceSha256': sha(source), 'originalSize': original_size}

def publish(root, item, provenance):
    dump(root/'provenance.json', provenance)
    dump(root/'checksums.json', {str(p.relative_to(root)): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(root.rglob('*')) if p.is_file()})
    # 分卷随 Git 分发，每卷低于 GitHub 单文件限制，不依赖 LFS 或外部下载。
    groups=[[]];size=0
    for file in sorted(root.rglob('*')):
        if not file.is_file(): continue
        if size+file.stat().st_size>40*1024*1024 and groups[-1]: groups.append([]);size=0
        groups[-1].append(file);size+=file.stat().st_size
    archives=[]
    for i, group in enumerate(groups):
        archive=DEST/f"{item['id']}.part{i+1:02d}.zip"
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for file in group: z.write(file,str(file.relative_to(root)))
        assert archive.stat().st_size<95*1024*1024
        archives.append({'file':archive.name,'sha256':sha(archive),'bytes':archive.stat().st_size})
    version=hashlib.sha256(''.join(a['sha256'] for a in archives).encode()).hexdigest()
    result={**item,'archives':archives,'sha256':version,'bytes':sum(a['bytes'] for a in archives)}
    print(f"完成 {item['name']}：{result['bytes']/1024/1024:.1f} MiB，{len(archives)} 卷",flush=True)
    return result

def current_case(source, root):
    provenance = {'kind': 'sealed-case-export', 'sourceManifestSha256': sha(source/'manifest.json'), 'images': {}}
    for folder in ['assets','layers']: (root/folder).mkdir()
    for name in ['manifest.json','alarms.json','samples.sqlite']: shutil.copy2(source/name, root/name)
    m = json.loads((root/'manifest.json').read_text())
    m.update(name='BLT-S430 B17', capabilities={'access': True, 'recognition': True, 'trace': True})
    m['photo'] = 'assets/photo.jpg'
    for p in sorted((source/'assets').glob('*.jpg')): preview(p,root/'assets'/p.name,provenance['images'],root)
    for p in (source/'layers').glob('*.json'): shutil.copy2(p,root/'layers'/p.name)
    shutil.copy2(ROOT/'backend/data_pack/blt_s430/trace_dual.json',root/'trace_dual.json')
    m['dualPack'] = 'trace_dual.json'
    dump(root/'manifest.json',m)
    return publish(root, {'id':m['id'],'deviceId':m['deviceId'],'name':m['name'],'model':m['model'], 'thumbnail':'/device-images/blt-site.jpg','layerCount':len(m['layers'])}, provenance)

SOURCES = [
 ('torque', '刮刀位置_刮刀扭矩_加工平台位置_加工平台扭矩*.csv', [1,3,5], ['time','scraper','platform']),
 ('env_a', '成形室压力_成形室温度_加热板温度_*.csv', [1,2,3,4,5], ['time','chamber_pressure','chamber_temperature','heater_temperature','argon_pressure']),
 ('env_b', '落粉轴角度_落粉轴扭矩_储粉桶物位计_成形室氧含量*.csv', [1,4,5], ['time','powder_level','oxygen']),
 ('env_c', '气动蝶阀压力_循环气体实时流量_风机转速_净气室压力*.csv', [1,3,4], ['time','gas_flow','fan_speed']),
]

def export_device(code, build, raw_root, pre_root, root):
    raw = raw_root/'raw'/code/build
    csv_dir = raw/'csv_data'
    provenance = {'kind':'factory-layer-export','device':code,'build':build,'sources':{},'images':{},'excludedLayers':[]}
    def record_source(p): provenance['sources'][str(p.relative_to(raw_root))] = sha(p)
    log_path = csv_dir/'打印日志.csv';record_source(log_path)
    log = pd.read_csv(log_path,encoding='utf-16')
    log.columns = ['sequence','time','event','info']
    log['epoch'] = pd.to_datetime(log.time).dt.tz_localize('Asia/Shanghai').astype('int64')/1e9
    log['layer'] = pd.to_numeric(log['info'].where(log.event == '更新层号'),errors='coerce').ffill()
    rows=[]
    if code=='B44':
        review=raw_root/'manifests/review_all.csv'; record_source(review)
        df=pd.read_csv(review)
        df=df[(df.device==code)&(df.build==build)&(df.pair_status=='paired')&(df.alignment_source=='print_log')].sort_values(['layer_id','acquisition_id']).drop_duplicates('layer_id')
        for r in df.itertuples():
            rows.append({'layer':int(r.layer_id), 'start':epoch(r.event_start), 'recoat':epoch(r.recoating_start), 'melt':epoch(r.sintering_start), 'end':epoch(r.event_end), 'before':raw_root/r.before_path,'after':raw_root/r.after_path})
    else:
        idx=pre_root/code/'torque_layer/层样本索引.csv'
        provenance['indexSha256']=sha(idx)
        for r in pd.read_csv(idx).to_dict('records'):
            layer=int(r['层号']); events=log[log.layer==layer]
            recoat=epoch(r['铺粉开始']);melt=epoch(r['铺粉结束'])
            starts=events[(events.event=='更新层号')&(events.epoch<=recoat)]
            ends=events[(events.event=='烧结结束')&(events.epoch>=melt)]
            if starts.empty or ends.empty:
                provenance['excludedLayers'].append({'layer':layer,'reason':'缺少打印日志起止事件'});continue
            rows.append({'layer':layer,'start':float(starts.iloc[-1].epoch),'recoat':recoat,'melt':melt,'end':float(ends.iloc[0].epoch),'before':raw/'camera_zd'/r['铺粉后图像'],'after':raw/'camera_zd'/r['熔化后图像']})
    rows.sort(key=lambda r:r['start'])
    assert rows and len({r['layer'] for r in rows})==len(rows)
    for r in rows:
        assert r['start']<=r['recoat']<=r['melt']<=r['end'], r
        assert r['before'].is_file() and r['after'].is_file(),r
    segments=[]
    for r in rows:
        if not segments or r['layer']!=segments[-1]['lastLayer']+1 or r['start']-segments[-1]['end']>5:
            segments.append({'firstLayer':r['layer'],'lastLayer':r['layer'],'start':r['start'],'end':r['end']})
        else: segments[-1].update(lastLayer=r['layer'],end=r['end'])
    offset=0
    for s in segments:
        s.update(offset=offset,duration=s['end']-s['start']);offset+=s['duration']
    for r in rows:
        s=next(s for s in segments if s['firstLayer']<=r['layer']<=s['lastLayer'])
        r.update(offset=s['offset']+r['start']-s['start'],recognitionAt=r['melt'])
    with sqlite3.connect(root/'samples.sqlite') as db:
        for table,pattern,cols,names in SOURCES:
            files=sorted(csv_dir.glob(pattern));assert files,(code,pattern)
            chunks=[];seq=0
            for file in files:
                record_source(file)
                for df in pd.read_csv(file,encoding='utf-16',usecols=cols,chunksize=100000):
                    df.columns=names
                    df['time']=pd.to_datetime(df.time).dt.tz_localize('Asia/Shanghai').astype('int64')/1e9
                    df['sequence']=range(seq,seq+len(df));seq+=len(df)
                    keep=pd.Series(False,index=df.index)
                    for s in segments: keep|=(df.time>=s['start'])&(df.time<=s['end'])
                    if keep.any(): chunks.append(df[keep])
            assert chunks,(code,table)
            values=pd.concat(chunks).sort_values(['time','sequence'])
            # 多个分卷边界可能重复导出同一采样；只有完全相同的原始通道值才去重。
            values=values.drop_duplicates(names)
            values.to_sql(table,db,index=False,if_exists='replace')
            db.execute(f'CREATE INDEX {table}_time ON {table}(time,sequence)')
            print(code,table,len(values),flush=True)
        db.commit()
    task_info=(csv_dir/'任务信息.csv').read_text(encoding='utf-16');record_source(csv_dir/'任务信息.csv')
    total=int(re.search(r'零件层数:(\d+)',task_info).group(1))
    task={'id':f'{code}-{build}','name':f'{build[:4]}年{int(build[4:6])}月{int(build[6:8])}日成形任务','layers':total}
    device={'id':f'slm-{code.lower()}','name':f"铂力特 {'S430' if code=='B44' else 'S310'} {code}"}
    for folder in ['assets','layers']:(root/folder).mkdir()
    photo=ROOT/'frontend/public/device-images'/('blt-site.jpg' if code=='B44' else 'blt-s310.png')
    preview(photo,root/'assets/photo.jpg',provenance['images'],root)
    with sqlite3.connect(root/'samples.sqlite') as db:
        for r in rows:
            layer=r['layer'];images={}
            for kind in ['before','after']:
                preview(r.pop(kind),root/'assets'/f'{layer}_{kind}.jpg',provenance['images'],root)
                images[kind]={'url':None,'w':1200,'h':900,'time':''}
            tq_n=db.execute('SELECT COUNT(*) FROM torque WHERE time BETWEEN ? AND ?',(r['recoat'],r['melt'])).fetchone()[0]
            channels=[{'name':n,'spec':spec,'rate':rate} for n,spec,rate in [('铺粉后图像','图像','每层1帧'),('熔化后图像','图像','每层1帧'),('刮刀扭矩','%','原始时间采样'),('加工平台扭矩','%','原始时间采样'),('设备状态参数','压力、温度、氧含量等','原始时间采样')]]
            access={'device':device,'task':task,'layer':layer,'progress':{'layer':layer,'total':total},'images':images,'env':{},'torque':{},'channels':channels,'alarms':[],'records':[{'layer':layer,'start':datetime.fromtimestamp(r['start'],TZ).strftime('%H:%M:%S'),'recoat':r['melt']-r['recoat'],'dur':r['end']-r['start'],'torqueN':tq_n,'images':2,'complete':True}]}
            dump(root/'layers'/f'{layer}.json',{'access':access,'recognition':None,'trace':None,'traceReason':'该设备尚未接入逐层溯源结果'})
    alarms_path=csv_dir/'报警日志.csv';record_source(alarms_path)
    # 报警内容含未转义逗号，时间固定在第三列，正文重组至末尾的级别/零件数字段。
    with alarms_path.open(encoding='utf-16', newline='') as stream:
        reader=csv.reader(stream);next(reader)
        alarms=[{'time':epoch(row[2]),'text':','.join(row[4:-2]).replace('$','；')} for row in reader if row]
    dump(root/'alarms.json', alarms)
    m={'schemaVersion':1,'id':f'{code.lower()}-{build}','deviceId':device['id'],'name':device['name'],'model':'铂力特 S430' if code=='B44' else '铂力特 S310','task':task,'timezone':'Asia/Shanghai','sourceDevice':code,'segments':segments,'layers':rows,'duration':offset,'defaultOffset':min(20,offset),'photo':'assets/photo.jpg','gasPressureLabel':'氩气压力' if code=='B10' else '气源压力','analysis':{'origin':None,'controlHistoryAvailable':False},'capabilities':{'access':True,'recognition':False,'trace':False},'timeNotes':'按打印日志与逐层索引对齐图像。传感器值和秒级时间保持原值，缺少采集数据的层区间跳过；未接入识别或溯源结果，不用标签替代模型输出。'}
    dump(root/'manifest.json',m)
    return publish(root,{'id':m['id'],'deviceId':m['deviceId'],'name':m['name'],'model':m['model'],'thumbnail':'/device-images/'+photo.name,'layerCount':len(rows)},provenance)

def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-root',type=Path,required=True);p.add_argument('--pre-root',type=Path,required=True);p.add_argument('--current-case',type=Path,required=True);a=p.parse_args()
    DEST.mkdir(exist_ok=True)
    entries=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        d=root/'current';d.mkdir();entries.append(current_case(a.current_case,d))
        for code,build in [('B44','20250321-09-20'),('B10','20250509-07-47'),('B15','20250107-20-02')]:
            d=root/code;d.mkdir();entries.append(export_device(code,build,a.raw_root,a.pre_root,d))
    dump(DEST/'catalog.json',{'schemaVersion':1,'cases':entries})
if __name__=='__main__':main()
