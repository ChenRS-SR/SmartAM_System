"""维护者封装已训练权重，运行端仅依赖仓库内模型；不训练、不改动论文结果。"""
import argparse, hashlib, json
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parents[1]
def export(chapters):
    target = ROOT/'backend/inference_models'
    target.mkdir(exist_ok=True)
    blt = chapters/'ch06_新实验/工程案例实验_B44/双输出模型/dual_seed0.pt'
    source = chapters/'ch04_大论文定稿实验/03_本章方法/results_ch4_method/source_models/c2rsr_seed0.pt'
    m130 = chapters/'ch05_大论文定稿实验/03_探索性诊断_20261010/修订后双机理试验/results/mechanism_v2_seed0.pt'
    metadata = torch.load(source,map_location='cpu',weights_only=False)['meta']
    registry = {}
    for key,path,architecture,outputs in [('blt-dual',blt,'vis_torque',['proc','dev']),('m130-dual',m130,'vision',['dev','proc'])]:
        state = torch.load(path,map_location='cpu',weights_only=False)
        if architecture=='vision': state=state['model']
        file=target/(key+'.pt');torch.save(state,file)
        registry[key]={'file':file.name,'architecture':architecture,'outputs':outputs,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
            'source':str(path.relative_to(chapters)),'sourceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'name':'图像与扭矩双输出识别' if architecture=='vis_torque' else 'M130视觉双输出识别'}
        if architecture=='vis_torque': registry[key].update(weights=metadata['source_modality_weights'],torque_norm=metadata['torque_norm'])
    norm=json.loads((chapters/'ch05_大论文定稿实验/02_实验工作区/results_ch5/normalization_draft.json').read_text())
    registry['m130-dual']['background_norm']={k:norm[k] for k in ('rgb_mean_255','rgb_std_255')}
    (target/'registry.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--chapters',type=Path,required=True)
    export(parser.parse_args().chapters)
