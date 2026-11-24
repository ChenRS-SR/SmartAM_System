"""统一结果格式，封存结果和真实推理向页面提供相同字段。"""
import copy
import math


def trace_availability(frame, results, rows):
    """等待状态来自当前分析包；预计等待时间按压缩后的回放时间轴计算。"""
    if frame['trace'] is not None:
        return {'state': 'ready', 'reason': None, 'resultLayer': frame['trace']['layer']}
    current = results[str(frame['layer'])]['trace']
    if current is None:
        reason = '当前层缺少前序正常参照层，等待可用参照与后续完整层。'
    else:
        reason = f'等待第 {frame["layer"]} 层完整图像到达。'
    upcoming = next((r for r in rows if r['end'] > frame['timestamp'] and results[str(r['layer'])]['trace'] is not None), None)
    if upcoming is None:
        return {'state': 'unavailable', 'reason': '当前案例没有可用的后续溯源结果。'}
    return {'state': 'waiting', 'reason': reason, 'nextLayer': upcoming['layer'],
            'remainingSeconds': max(0, math.ceil(upcoming['offset'] + upcoming['end'] - upcoming['start'] - frame['offset']))}


def conclusion(row, factors):
    # 双输出概率与分区贡献共同支持时才给出处置方向。
    proc, dev = [row['p_'+k] >= .5 and factors[k]['present'] for k in ('proc','dev')]
    if proc or dev:
        return '由二者共同诱发' if proc and dev else '由工艺因素诱发' if proc else '由设备因素诱发'
    # 归因未确认不能反推“正常”；概率与贡献衡量的量不同，需保留待确认状态。
    if max(row['p_proc'], row['p_dev']) >= .5:
        return '已识别异常，归因待确认'
    if any(factors[k]['present'] for k in ('proc', 'dev')):
        return '贡献超限，待复核'
    return '未见异常'


def format_result(meta, item, row):
    layer = item['layer']
    base = {'device': meta['device'], 'task': meta['task'], 'layer': layer, 'time': item['time']}
    probability = max(row['p_proc'], row['p_dev'])
    label = '异常' if probability >= .5 else '正常'
    singles = row['singles']
    recognition = {**base, 'model': {'name': meta['modelName'], 'source': meta['modelId']},
        'params': {'threshold': .5, 'modalities': list(singles)}, 'image': item['image'],
        'prob': {'def': probability, **singles, 'proc': row['p_proc'], 'dev': row['p_dev']},
        'label': label, 'weights': meta['weights'],
        'singles': [{'key': k, 'name': '铺粉后图像' if k=='vis' else '刮刀与平台扭矩', 'p': value, 'label': '异常' if value>=.5 else '正常', 'used': True} for k,value in singles.items()],
        'torque': item['torque'], 'records': [], 'modelVersion': meta['modelSha256']}
    if 'infrared' in row:
        recognition['infrared'] = {**row['infrared'], 'image':item['infraredImage']}
    trace = None
    if 'ref' in row:
        factors={}
        for key,name in [('proc','工艺诱发异常概率'),('dev','设备诱发异常概率')]:
            zones=[{'key':z,'name':n,'v':row[key+'_'+z],'over':row[key+'_'+z]>meta['upper'][key]} for z,n in [('part','零件区'),('powder','粉床区')]]
            support=[z['name'] for z in zones if z['over']]
            factors[key]={'name':name,'zones':zones,'total':sum(z['v'] for z in zones),'upper':meta['upper'][key], 'present':bool(support),'support':support,'prob':row['p_'+key],'illustrative':False}
        verdict=conclusion(row,factors)
        actions=[text for k,text in [('proc','调整工艺参数'),('dev','检修刮刀与供粉机构')] if row['p_'+k]>=.5 and factors[k]['present']]
        if verdict == '已识别异常，归因待确认': actions = ['复核异常层与归因证据']
        elif verdict == '贡献超限，待复核': actions = ['复核超限区域与识别结果']
        trace={**base,'mode':'dual','refLayer':row['ref'],'refMode':'prev_normal','params':{'bandPx':meta['bandPx']},
            'image':{'url':item['modelView'],'width':224,'height':224,'content':item.get('content',[0,0,1,1])},
            'partContours':item['partContours'],'bandContours':item['bandContours'],'factors':factors,
            'synergy':{k:row[k+'_synergy'] for k in ('proc','dev')},'conclusion':verdict,
            'support':list(dict.fromkeys(factors['proc']['support']+factors['dev']['support'])),
            'actions':actions,
            'curve':{'from':layer,'to':layer,'upper':meta['upper'],'layers':[]},'records':[],
            'notes':{'upper':meta['calibrationNote']},'modelVersion':meta['modelSha256']}
    return {'recognition':recognition,'trace':trace,'row':row}


def attach(frame, results, rows):
    """仅使用当前时间已经到达的层，定位回退时不得泄漏未来分析结果。"""
    arrived=[r for r in rows if r['recognitionAt']<=frame['timestamp'] and str(r['layer']) in results]
    complete=[r for r in arrived if r['end']<=frame['timestamp'] and results[str(r['layer'])]['trace'] is not None]
    # B44 本次任务第2、3层为用户确认的启动稳定阶段，仅排除识别展示，保留原始模型输出。
    recognition_rows = [r for r in arrived if not (frame.get('caseId') == 'b44-20250321-09-20' and r['layer'] in (2, 3))]
    if recognition_rows:
        recognition=copy.deepcopy(results[str(recognition_rows[-1]['layer'])]['recognition'])
        recognition['records']=[{'layer':r['layer'],'p':results[str(r['layer'])]['recognition']['prob']['def'],'label':results[str(r['layer'])]['recognition']['label']} for r in recognition_rows[::-1]]
        frame['recognition']=recognition
    else: frame['recognition']=None
    if complete:
        trace=copy.deepcopy(results[str(complete[-1]['layer'])]['trace'])
        history=[dict(results[str(r['layer'])]['row'],layer=r['layer'],conclusion=results[str(r['layer'])]['trace']['conclusion']) for r in complete[-50:]]
        trace['curve'].update(layers=history,**{'from':history[0]['layer'],'to':history[-1]['layer']})
        trace['records']=history[-5:][::-1]
        frame['trace']=trace
    else: frame['trace']=None
    return frame
