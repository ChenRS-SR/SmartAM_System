"""维护者用原始数据实跑模型并封存输入/输出；运行端无需访问论文目录。"""
import argparse, csv, hashlib, io, json, re, sqlite3, sys, zipfile
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
import cv2
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from analysis_engine.runtime import Runtime
from analysis_engine.results import format_result
from forming_monitor.engine import preprocess as P
from replay.service import get_case

TZ=timezone(timedelta(hours=8))
CROPS={'B17':[796,148,2388,1612],'B10':[720,248,1864,1384],'B15':[652,224,2212,1588],'B44':[260,160,2344,1488]}
BUILDS={'B17':'20240827-09-33','B10':'20250509-07-47','B15':'20250107-20-02','B44':'20250321-09-20'}

def dump(path,data): path.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def timestamp(epoch): return datetime.fromtimestamp(epoch,TZ).strftime('%Y-%m-%d %H:%M:%S')

class Writer:
    def __init__(self, case_id, device, task, model_id, upper, note, preserve=False):
        self.root=Path(os.environ.get('SMARTAM_ANALYSIS_OUTPUT', ROOT/'backend/analysis_packages'))/case_id;self.root.mkdir(parents=True,exist_ok=True)
        self.runtime=Runtime(model_id)
        self.meta={'caseId':case_id,'device':device,'task':task,'modelId':model_id,'modelName':self.runtime.meta['name'],
            'modelSha256':self.runtime.meta['sha256'],'resultRuleVersion':'recognition-attribution-status-v2','upper':upper,'bandPx':12,'calibrationNote':note,
            'weights':self.runtime.meta.get('weights',{'vis':1.,'tq':0.}), 'preserveOriginalRecognition':preserve,'layers':[]}
        if model_id == 'blt-dual': self.meta['maskVersion'] = P.MASK_VERSION
        self.results={};self.previous=None;self.previousLayer=None
    def append(self,layer,sample,meta):
        number=len(self.meta['layers'])//200
        archive=f'inputs-{number:03d}.zip'
        data=io.BytesIO();np.savez_compressed(data,**sample)
        # 每个分卷只在首次写入时新建，避免重复构建时出现同名 ZIP 条目。
        mode='w' if len(self.meta['layers'])%200==0 else 'a'
        with zipfile.ZipFile(self.root/archive,mode,compression=zipfile.ZIP_STORED) as z:z.writestr(f'{layer}.npz',data.getvalue())
        meta.update(layer=layer,archive=archive)
        self.meta['layers'].append(meta)
        row=self.runtime.infer(sample,self.previous)
        if self.previous is not None:row['ref']=self.previousLayer
        self.results[str(layer)]=format_result(self.meta,meta,row)
        if row['p_proc']<.5 and row['p_dev']<.5:self.previous,self.previousLayer=sample,layer
        if len(self.results)%25==0:print(self.meta['device']['name'],len(self.results),flush=True)
    def finish(self):
        dump(self.root/'results.json',self.results)
        files={item['archive'] for item in self.meta['layers']}|{'results.json'}
        self.meta['checksums']={name:sha(self.root/name) for name in sorted(files)}
        dump(self.root/'manifest.json',self.meta)
        print('封存完成',self.meta['caseId'],len(self.results),flush=True)

def blt(case_id, raw):
    c=get_case(case_id);m=c.manifest;code='B17' if case_id=='blt-s430-20240828' else m['sourceDevice']
    device={'id':m['deviceId'],'name':m['name']}
    upper=json.loads((ROOT/'backend/data_pack/blt_s430/trace_dual.json').read_text())['upper']
    writer=Writer(case_id,device,m['task'],'blt-dual',upper,'随模型封存的源设备正常验证阈值；新设备未重新标定，推理结果不代表跨设备精度已验证。',code=='B17')
    provenance=json.loads((c.root/'provenance.json').read_text())['images']
    images=raw/'raw'/code/BUILDS[code]/'camera_zd'
    crop=CROPS[code]
    if code=='B17':
        with (raw/'manifests/review_all.csv').open(encoding='utf-8-sig') as f:
            original={int(r['layer_id']):r for r in csv.DictReader(f) if r['device']=='B17' and r['build']==BUILDS[code] and r['pair_status']=='paired'}
    with sqlite3.connect(c.root/'samples.sqlite') as db:
        for row in c.layers:
            layer=row['layer']
            paths={kind:images/provenance[f'assets/{layer}_{kind}.jpg']['sourceName'] for kind in ('before','after')}
            if code=='B17':
                paths={kind:raw/original[layer][kind+'_path'] for kind in ('before','after')}
            before,after=P.read_rgb(paths['before']),P.read_rgb(paths['after'])
            samples=db.execute('SELECT time,scraper,platform FROM torque WHERE time>=? AND time<=? ORDER BY time,sequence',(row['recoat'],row['melt'])).fetchall()
            if len(samples)<2:raise ValueError(f'{code}/{layer}铺粉段扭矩不足')
            times=[datetime.fromtimestamp(v[0],TZ).replace(tzinfo=None) for v in samples]
            torque,grid=P.resample_torque(times,[v[1] for v in samples],[v[2] for v in samples])
            part,band,valid=P.part_regions(after,before,crop,12)
            rgb=P.crop_letterbox(before,crop)
            height,width=before.shape[:2];scale=min(1200/height,1200/width,1)
            x0,y0,x1,y1=crop;sc=min(224/(x1-x0),224/(y1-y0));nw,nh=round((x1-x0)*sc),round((y1-y0)*sc)
            writer.append(layer,{'rgb':rgb,'torque':torque,'part':part,'band':band,'valid':valid},{
                'time':timestamp(row['recognitionAt']),
                'image':{'url':f'/api/slm/replay/cases/{case_id}/media/{layer}/before','w':round(width*scale),'h':round(height*scale),'box':[round(v*scale) for v in crop]},
                'modelView':f'/api/slm/replay/cases/{case_id}/analysis-image/{layer}',
                'partContours':P.contours(part),'bandContours':P.contours(band),
                'content':[(224-nw)/448,(224-nh)/448,nw/224,nh/224],
                'torque':{'t':grid.tolist(),'scraper':torque[0].tolist(),'platform':torque[1].tolist()},
                'sourceImages':{k:{'name':p.name,'sha256':sha(p)} for k,p in paths.items()}})
    writer.finish()

def m130(chapters, photo):
    # 使用已有 M130 实验的真实图像时间，不以其他设备采样填充缺少的扭矩或环境量。
    data=chapters.parent/'章节数据终稿/第五章可解释用数据/M130'
    ch5=chapters/'ch05_大论文定稿实验'
    with (data/'样本清单.csv').open(encoding='utf-8-sig') as f:rows=[r for r in csv.DictReader(f) if r['来源批次']=='11月20日-高功率翘曲' and r['零件']=='牙冠']
    rows.sort(key=lambda r:int(r['层号']))
    norm=json.loads((ch5/'02_实验工作区/results_ch5/normalization_draft.json').read_text())
    patches=ch5/'03_探索性诊断_20261010/真值与掩膜修订'
    with (patches/'掩膜修正记录_20261010.csv').open(encoding='utf-8-sig') as f: masks={r['样本编号']:patches/r['修订掩膜'] for r in csv.DictReader(f) if r['修订掩膜']}
    case_id='m130-20251120';device={'id':'huake-crpbfm130','name':'华科 CRPBFM130'}
    task={'id':'M130-20251120','name':'2025年11月20日成形任务','layers':max(int(r['层号']) for r in rows)}
    upper=json.loads((ROOT/'backend/data_pack/m130/trace_pack.json').read_text())['upper']
    writer=Writer(case_id,device,task,'m130-dual',upper,'第五章正常验证层阈值，模型输出顺序已适配为工艺侧与设备侧。')
    import tempfile
    sys.path.insert(0,str(ROOT/'scripts'))
    import build_portable_replays as portable
    portable.DEST=Path(os.environ.get('SMARTAM_REPLAY_OUTPUT',ROOT/'backend/replay_cases'))
    portable.DEST.mkdir(parents=True,exist_ok=True)
    publish=portable.publish
    with tempfile.TemporaryDirectory() as tmp:
        stage=Path(tmp);(stage/'assets').mkdir();(stage/'layers').mkdir()
        Image.open(photo).convert('RGB').save(stage/'assets/photo.jpg',quality=92)
        layers=[];segments=[];offset=0.;provenance={'kind':'m130-real-image-sequence','images':{}}
        for r in rows:
            layer=int(r['层号']);before=np.array(Image.open(data/r['铺粉后可见光']).convert('RGB'))
            mask=np.array(Image.open(masks.get(r['样本编号'],data/r['零件区掩膜'])).convert('L'))>0
            background=before[~mask].astype(np.float32);sd=background.std(0)
            if np.any(sd<=0):raise ValueError('M130粉床标准差无效')
            normalized=np.clip((before.astype(np.float32)-background.mean(0))/sd*np.array(norm['rgb_std_255'])+np.array(norm['rgb_mean_255']),0,255)
            rgb=np.round(cv2.resize(normalized,(224,224),interpolation=cv2.INTER_AREA)).astype(np.uint8)
            part=cv2.resize(mask.astype(np.uint8),(224,224),interpolation=cv2.INTER_NEAREST)>0
            band=cv2.dilate(part.astype(np.uint8),cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(25,25)))>0
            times={};images={}
            for kind,field in [('before','铺粉后可见光'),('after','熔化后可见光'),('ir_before','铺粉后红外'),('ir_after','熔化后红外')]:
                path=data/r[field]
                match=re.search(r'_(\d{8})_(\d{6})_(\d{3})',path.name)
                t=datetime.strptime(''.join(match.groups()[:2]),'%Y%m%d%H%M%S').replace(tzinfo=TZ).timestamp()+int(match.group(3))/1000
                times[kind]=t
                im=Image.open(path).convert('RGB');im.save(stage/'assets'/f'{layer}_{kind}.jpg',quality=95)
                images[kind]={'url':None,'w':im.width,'h':im.height,'time':timestamp(t)}
                provenance['images'][f'assets/{layer}_{kind}.jpg']={'sourceName':path.name,'sourceSha256':sha(path),'originalSize':list(im.size)}
            start,end=min(times['before'],times['ir_before']),max(times['after'],times['ir_after'])
            if end<start:raise ValueError('M130图像时序错误')
            duration=end-start
            layers.append({'layer':layer,'start':start,'recoat':start,'melt':start,'end':end,'offset':offset,'recognitionAt':max(times['before'],times['ir_before']),'imageTimes':times})
            segments.append({'firstLayer':layer,'lastLayer':layer,'start':start,'end':end,'offset':offset,'duration':duration});offset+=duration
            channels=[{'name':n,'spec':'红外图像' if '红外' in n else '可见光图像','rate':'逐层'} for n in ['铺粉后图像','熔化后图像','铺粉后红外图像','熔化后红外图像']]
            access={'device':device,'task':task,'layer':layer,'progress':{'layer':layer,'total':task['layers']},'images':images,
                'torque':{'t':[],'scraper':[],'platform':[],'events':[],'recoatDur':None},'env':{},'channels':channels,
                'records':[{'layer':layer,'start':timestamp(start),'recoat':None,'dur':None,'torqueN':None,'images':4,'imageTotal':4,'complete':True}], 'alarms':[]}
            dump(stage/'layers'/f'{layer}.json',{'access':access,'recognition':None,'trace':None,'traceReason':'等待正常参照层'})
            h,w=before.shape[:2]
            writer.append(layer,{'rgb':rgb,'part':part,'band':band,'infrared':np.frombuffer((data/r['铺粉后红外']).read_bytes(),dtype=np.uint8)},{'infraredImage':{'url':f'/api/slm/replay/cases/{case_id}/media/{layer}/ir_before','time':timestamp(times['ir_before'])},'time':timestamp(start),'image':{'url':f'/api/slm/replay/cases/{case_id}/media/{layer}/before','w':w,'h':h,'box':[0,0,w,h]},
                'modelView':f'/api/slm/replay/cases/{case_id}/analysis-image/{layer}','partContours':P.contours(part),'bandContours':P.contours(band),
                'torque':{'t':[],'scraper':[],'platform':[]}})
        with sqlite3.connect(stage/'samples.sqlite') as db:
            for table,columns in [('torque','scraper,platform'),('env_a','chamber_pressure,chamber_temperature,heater_temperature,argon_pressure'),('env_b','powder_level,oxygen'),('env_c','gas_flow,fan_speed')]:
                db.execute(f'CREATE TABLE {table} (time REAL,sequence INTEGER,{columns})')
        manifest={'schemaVersion':1,'id':case_id,'deviceId':device['id'],'name':device['name'],'model':'CRPBFM130','task':task,'imageOnly':True,'timezone':'Asia/Shanghai','sourceDevice':'M130',
            'segments':segments,'layers':layers,'duration':offset,'defaultOffset':0,'photo':'assets/photo.jpg',
            'analysis':{'origin':'model-output','controlHistoryAvailable':False},'capabilities':{'access':True,'recognition':True,'trace':True},
            'timeNotes':'真实铺粉后/熔化后可见光与红外图像时间；每段为两帧之间的采集窗口，不作为完整层工艺时长。没有扭矩和设备环境采样，不填充其他设备数据。'}
        dump(stage/'manifest.json',manifest);dump(stage/'alarms.json',[])
        item=publish(stage,{'id':case_id,'deviceId':device['id'],'name':device['name'],'model':'CRPBFM130','owner':'华科','location':'华科设备群','thumbnail':'/device-images/crpbfm130.jpg','layerCount':len(layers)},provenance)
        catalog=ROOT/'backend/replay_cases/catalog.json';d=json.loads(catalog.read_text());d['cases']=[c for c in d['cases'] if c['id']!=case_id]+[item];dump(portable.DEST/'catalog.json',d)
    writer.finish()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--raw',type=Path);parser.add_argument('--chapters',type=Path);parser.add_argument('--case',required=True)
    args=parser.parse_args()
    if args.case=='m130': m130(args.chapters,args.chapters/'ch06_新实验/设备图/CRPBFM130.jpg')
    else:blt(args.case,args.raw)
