"""双输出模型的离线溯源结果适配；保留原始贡献与概率，不进行截断或补值。"""
import json
from pathlib import Path


class DualTraceResults:
    def __init__(self, path: Path):
        self.pack = json.loads(path.read_text(encoding='utf-8'))
        self.rows = {r['layer']: r for r in self.pack['layers']}

    def apply(self, trace: dict, layer: int):
        """替换分析字段，图像、轮廓和历史时间继续使用同层原始数据。"""
        row = self.rows[layer]
        factors = {}
        for key, name in [('proc', '工艺诱发异常概率'), ('dev', '设备诱发异常概率')]:
            upper = self.pack['upper'][key]
            zones = [
                {'key': zone, 'name': title, 'v': row[f'{key}_{zone}'],
                 'over': row[f'{key}_{zone}'] > upper}
                for zone, title in [('part', '零件区'), ('powder', '粉床区')]
            ]
            support = [z['name'] for z in zones if z['over']]
            factors[key] = {
                'name': name, 'zones': zones, 'total': sum(z['v'] for z in zones),
                'upper': upper, 'present': bool(support), 'support': support,
                'prob': row[f'p_{key}'], 'illustrative': False,
            }
        # 结论沿用导出时的双输出概率与贡献联合判据，不用单侧模型重新推断。
        active = {'未见异常': [], '由工艺因素诱发': ['proc'], '由设备因素诱发': ['dev'],
                  '由二者共同诱发': ['proc', 'dev']}[row['conclusion']]
        actions = {'proc': '调整工艺参数', 'dev': '检修刮刀与供粉机构'}
        trace.update(
            mode='dual', refLayer=int(row['ref']), refMode='prev_normal',
            params={'bandPx': self.pack['bandPx']}, factors=factors, synergy={},
            conclusion=row['conclusion'],
            support=[z for z in ('零件区', '粉床区') if any(z in factors[k]['support'] for k in active)],
            actions=[actions[k] for k in active],
            notes={'upper': self.pack['upper_rule'], 'source': self.pack['source']})
        trace['curve']['upper'] = self.pack['upper']
        return trace
