"""用户授权的缺数据设备展示场景；与封存模型输出分离，不参与真实推理。"""
import copy
import math
import time
from datetime import datetime, timezone, timedelta
from functools import lru_cache

# 已有故障档案的展示类别；无故障档案的设备维持正常场景。
FAULTS = {'slm-b17':['feeder'], 'slm-b28':['scraper','laser','chiller'],
          'slm-b34':['scraper'], 'slm-b40':['scraper'], 'slm-b45':['filter'], 'slm-b46':['feeder']}
PARAMETERS = [
    ('scraper_torque','刮刀扭矩','%',18,2), ('platform_torque','加工平台扭矩','%',12,1.5),
    ('oxygen','成形室氧含量','%',.012,.002), ('ambient_oxygen','环境氧含量','%',20.9,.08),
    ('chamber_temperature','成形室温度','℃',35,1.2), ('chamber_pressure','成形室压力','mBar',8,.5),
    ('bed_temperature','加热板温度','℃',80,1.5), ('gas_flow','循环气体流量','m3/h',420,12),
    ('fan_speed','风机转速','%',65,2), ('gas_pressure','气源压力','Bar',4.8,.15),
    ('powder_level','储粉桶物位','mm',150,3), ('medium_filter_resistance','中效滤芯阻力','mBar',12,.8),
    ('high_filter_resistance','高效滤芯阻力','mBar',8,.5), ('compressed_air_pressure','压缩空气压力','Bar',5,.15),
    ('servo_temperature_x','X轴伺服温度','℃',38,1), ('servo_temperature_y','Y轴伺服温度','℃',39,1),
    ('galvo_temperature_x','X轴振镜温度','℃',32,.8), ('galvo_temperature_y','Y轴振镜温度','℃',33,.8),
    ('output_current_x','X轴输出电流','mA',260,8), ('output_current_y','Y轴输出电流','mA',265,8),
]


def reference_case(device):
    return 'blt-s430-20240828' if 'S430' in device.get('model', '') else 'b10-20250509-07-47'


@lru_cache(maxsize=2)
def template(case_id):
    from replay.router import snapshot, manifest
    return snapshot(case_id, manifest(case_id)['defaultOffset'], 'archive')


def demo_slice(device):
    from task4.service import asset
    fault = asset('fault-demos.json').get(device['id'])
    if fault:
        return copy.deepcopy(fault['slice'])
    case_id = reference_case(device)
    data = asset('control-regions/' + case_id + '.json')
    return dict(copy.deepcopy(data['representative']), referenceCase=case_id, representation='reference-section-demo')


def complete_workspace(payload, now=None):
    from task4.service import asset
    result = copy.deepcopy(payload)
    device, frame = result['device'], result['snapshot']
    device_id = device['id']
    fault = asset('fault-demos.json').get(device_id)
    seconds = int(time.time() if now is None else now)
    tick = seconds % 10000
    layer = 50 + (seconds // 5) % 200
    seed = sum((i + 1) * ord(c) for i, c in enumerate(device_id))
    stamp = datetime.fromtimestamp(seconds, timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    case_id = reference_case(device)
    reference = copy.deepcopy(template(case_id))
    task = dict(id='display-' + device_id, name='当前成形任务', layers=250)
    context = dict(device=dict(id=device_id, name=device['name']), task=task, layer=layer, time=stamp)
    frame.update(layer=layer, time=stamp, phase='采集中', demonstration=dict(kind='generated-workspace',
                 referenceCase=case_id, originalParameters=copy.deepcopy(frame['parameters']), generatedAt=stamp))
    # 已有数值作为演示基准；缺失量使用登记的合理基准。原始记录独立保留。
    original = {p['id']: p for p in frame['parameters']}
    parameters = []
    for index, (key, name, unit, base, amplitude) in enumerate(PARAMETERS):
        value = original.get(key, {}).get('value')
        try:
            actual = float(value)
        except (TypeError, ValueError):
            actual = None
        if actual is not None and math.isfinite(actual) and actual > 0 and original[key].get('unit') == unit:
            base = actual
            amplitude = min(amplitude, base * .05)
        wave = .65 * math.sin(tick * .73 + seed + index) + .35 * math.sin(tick * 1.19 + index)
        parameters.append(dict(id=key, name=name, unit=unit, value=round(max(0,base+amplitude*wave),4), source='generated-demo'))
    values = {p['id']:p['value'] for p in parameters}
    frame['parameters'] = parameters
    access = frame['access']
    access.update(context, progress=dict(layer=layer,total=250), acquisition=dict(running=True,mode='demo',layer=layer))
    env_keys = {'成形室温度':'chamber_temperature','成形室压力':'chamber_pressure','加热板温度':'bed_temperature',
                '循环气体实时流量':'gas_flow','风机转速':'fan_speed','气源压力':'gas_pressure','储粉桶物位计':'powder_level'}
    access['env'] = {key:values[value] for key,value in env_keys.items()}
    access['env']['成形室氧含量ppm'] = values['oxygen'] * 10000
    for key in ('before','after'):
        if not access['images'][key].get('url'):
            access['images'][key] = dict(reference['access']['images'][key], sourceKind='reference-case-demo', referenceCase=case_id)
    torque = dict(t=list(range(tick-49,tick+1)), scraper=[round(values['scraper_torque']+math.sin(n*.45+seed),3) for n in range(50)],
                  platform=[round(values['platform_torque']+math.cos(n*.32+seed),3) for n in range(50)], events=[], recoatDur=50)
    access['torque'] = torque
    for channel in access['channels']:
        key = channel.get('imageKey')
        channel['rate'] = '在线' if not key or access['images'].get(key,{}).get('url') else '未启用'
    access['records'] = [dict(layer=n,start=stamp,recoat=5.0,dur=10.0,torqueN=50,images=2,imageTotal=2,complete=True,state='完整') for n in range(layer,max(0,layer-40),-1)]
    if not access['rawRecords']:
        access['rawRecords'] = [dict(参数=p['name'],数值=p['value'],单位=p['unit']) for p in parameters]
    side = fault['control']['side'] if fault else None
    def probabilities(n):
        small = .06 + .025 * (1 + math.sin(n*.37+seed))
        high = .8 + .055 * math.sin(n*.27+seed)
        return (high if side=='proc' else small, high if side=='dev' else small*.6)
    proc, dev = probabilities(layer)
    probability = max(proc,dev)
    recognition = copy.deepcopy(reference['recognition'])
    recognition.update(context,available=True,modelVersion='display-v1',model=dict(name='多模态异常识别',source='generated-demo'),
                       prob=dict(proc=proc,dev=dev,**{'def':probability,'vis':proc if side!='dev' else probability*.75,'tq':dev}),
                       label='异常' if probability>=.5 else '正常',torque=torque,weights=dict(vis=.65,tq=.35))
    recognition['image'].update(url=access['images']['before']['url'],box=None)
    recognition['singles']=[dict(key=k,name=name,p=recognition['prob'][k],label='异常' if recognition['prob'][k]>=.5 else '正常',used=True)
                            for k,name in [('vis','铺粉后图像'),('tq','刮刀与平台扭矩')]]
    recognition['records']=[dict(layer=n,p=max(probabilities(n)),label='异常' if max(probabilities(n))>=.5 else '正常') for n in range(layer,layer-40,-1)]
    trace = copy.deepcopy(reference['trace'])
    trace.update(context,available=True,refLayer=layer-1,source='generated-demo',faultTypes=FAULTS.get(device_id,[]),
                 conclusion='由设备因素诱发' if side=='dev' else '由工艺因素诱发' if side=='proc' else '未见异常',
                 actions=[fault['advice']] if fault else ['保持当前运行参数，按计划开展维护检查。'])
    trace['subsystemHealth'] = {key:dict(state='fault' if set(names) & set(trace['faultTypes']) else 'normal',source='generated-demo')
                                for key,names in {'powder':['scraper','feeder'],'optics':['laser'],'gas':['filter','gas','fan'],'other':['chiller']}.items()}
    if fault:
        trace['recordDiagnosis'] = frame['trace']['recordDiagnosis']
    for key, probability in [('proc',proc),('dev',dev)]:
        factor = trace['factors'][key]
        factor.update(name='工艺问题' if key=='proc' else '设备问题',prob=probability,upper=.5,total=probability,present=probability>=.5,illustrative=True)
        for i,zone in enumerate(factor['zones']):
            zone.update(v=probability*(1 if i==0 else .7),over=probability>=.5)
    trace['curve'] = dict(upper=dict(proc=.5,dev=.5),layers=[dict(layer=n,ref=n-1,p_proc=probabilities(n)[0],p_dev=probabilities(n)[1],
                     proc_part=probabilities(n)[0],proc_powder=probabilities(n)[0]*.7,dev_part=probabilities(n)[1],dev_powder=probabilities(n)[1]*.7)
                     for n in range(layer-39,layer+1)])
    frame.update(recognition=recognition,trace=trace,slice=demo_slice(device))
    result['manifest'].update(task=task,capabilities=dict(access=True,recognition=True,trace=True,control=True))
    return result
