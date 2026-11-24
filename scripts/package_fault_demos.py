"""封存九台故障设备自身记录；缺图设备使用经确认的同型号截面示意，不生成模型输出。"""
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import cv2
import numpy as np
from package_control_regions import annotated_svg

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'frontend/src/assets'
PUBLIC = ROOT / 'frontend/public/control-regions'


def build():
    records = json.loads((ROOT / 'slm_device_data/manifest.json').read_text())['devices']
    result = {}
    for device in records:
        if device.get('health') != 'fault':
            continue
        device_id = device['id']
        directory = ROOT / device['dataDirectory']
        diagnosis = device['diagnosis']
        code = int(device['healthData']['status_code'])
        item = {'id': device_id, 'status': device['statusText'], 'diagnosis': diagnosis,
                'image': {1:'fault_powder.png',2:'fault_laser.png',3:'fault_gas.png',4:'fault_multi.png'}[code],
                'source': device['source'], 'media': [], 'records': [], 'control': {'side':'dev','direction':'wait'}}
        # 使用设备原有 CSV；完整列名与时间保留，展示时不冒充当前层模型分析。
        preview = directory / 'real_data/preview.csv'
        if preview.exists():
            with preview.open(encoding='utf-8-sig') as stream:
                item['records'] = list(csv.DictReader(stream))
            item['recordSource'] = str(preview.relative_to(ROOT))
        alarm = directory / 'real_data/alarm_records.csv'
        if alarm.exists():
            with alarm.open(encoding='utf-16') as stream:
                reader=csv.reader(stream); headers=next(reader)
                item['records']=[dict(zip(headers, row[:4]+[','.join(row[4:])] )) for row in reader if row]
            item['recordSource']=str(alarm.relative_to(ROOT))
        if device['source'] == 'mock_case':
            for folder, name in [('CH1','同轴图像'),('CH2','侧轴图像'),('CH3','红外图像')]:
                video = sorted((directory/'mock_video'/folder).glob('*.mp4'))[0]
                item['media'].append({'name':name, 'url':'/'+quote(str(video.relative_to(ROOT)),safe='/')})
            destination = PUBLIC / device_id
            destination.mkdir(parents=True, exist_ok=True)
            source = sorted((directory/'mock_video/CH1').glob('*.mp4'))[0]
            capture = cv2.VideoCapture(str(source)); capture.set(cv2.CAP_PROP_POS_MSEC,10000)
            ok, frame = capture.read(); capture.release()
            if not ok: raise ValueError(f'无法读取 {source}')
            cv2.imwrite(str(destination/'source-frame.png'),frame)
            # 已核对视频第10秒的两个方形截面，裁取零件局部，排除设备平台及激光亮斑。
            cv2.imwrite(str(destination/'section.png'),frame[202:242,344:446])
            regions = [dict(id=f'region-{n}',number=n,name=f'区域{n}',color=color,label=point)
                       for n,color,point in [(1,'#ffb0da',[140,100]),(2,'#4150b4',[370,100])]]
            section=destination/'section.png'
            # 两个可见截面以原帧内的轮廓外框作彩色示意；保留原局部供对照，不外推未知几何。
            polygons = [[[8,7],[45,7],[47,31],[9,31]], [[56,7],[94,7],[95,30],[56,31]]]
            display = np.full((200,510,3),255,dtype=np.uint8)
            for polygon,color in zip(polygons,[(218,176,255),(180,80,65)]):
                cv2.fillPoly(display,[np.array(polygon,dtype=np.int32)*5],color)
            cv2.imwrite(str(destination/'section_display.png'),display)
            (destination/'section_regions.svg').write_text(annotated_svg(destination/'section_display.png',510,200,regions),encoding='utf-8')
            item['slice']={'image':f'/control-regions/{device_id}/section.png', 'annotatedImage':f'/control-regions/{device_id}/section_regions.svg',
                          'sourceFile':'section.png','width':510,'height':200,'regions':regions,'sourcePolygons':polygons,
                          'sourceVideo':str(source.relative_to(ROOT)),'sourceVideoSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                          'sourceTimeSeconds':10, 'sourceBox':[344,202,446,242], 'representation':'video-section-demo'}
            case = device['mockCase']['id']
            item['control']={'side':'proc','direction':'decrease' if case=='scene_overpower' else 'increase', 'stop':case=='scene_underpower_critical'}
            item['advice']='核对激光功率与扫描参数；停机检查光路和激光器。' if item['control']['stop'] else '核对激光功率与填充速度，检查能量输入。'
        else:
            reference = 'blt-s430-20240828' if 'S430' in device['model'] else 'b15-20250107-20-02'
            data=json.loads((DATA/'control-regions'/f'{reference}.json').read_text())
            item['slice']={**(data.get('representative') or next(iter(data['layers'].values()))), 'referenceCase':reference,'representation':'same-model-section-demo'}
            item['advice']={1:'检查铺粉机构、落粉轴与扭矩状态，确认供粉及运动恢复后继续。',
                            3:'检查收粉桶料位、卸灰机构与气体循环状态。',
                            4:'停机检查铺粉机构、激光器及水冷系统，逐项复核报警记录。'}[code]
        if not item['records'] and not item['media']:
            raise ValueError(f'{device_id} 无自身采集资料')
        result[device_id]=item
    if len(result)!=9: raise ValueError(f'故障设备清单数量发生变化：{len(result)}')
    (DATA/'fault-demos.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    # 页面只加载类别证据，避免把原始采样表打入前端脚本。
    labels={k:{'status':v['status'],'diagnosis':{'evidence':v['diagnosis']['evidence']},'control':{'side':v['control']['side']}} for k,v in result.items()}
    (DATA/'fault-labels.json').write_text(json.dumps(labels,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print('封存九台故障设备：', {k: {'records':len(v['records']),'media':len(v['media'])} for k,v in result.items()})

if __name__=='__main__': build()
