"""双输出真实推理与分输出两区 Shapley；不依赖论文代码目录或外网权重。"""
from pathlib import Path
import json
import hashlib
import threading
import numpy as np
import torch
from torch import nn
from torchvision.models import resnet18
from forming_monitor.engine.nets import Branches, fuse

MODELS = Path(__file__).resolve().parents[1] / 'inference_models'
MEAN = np.array([.485, .456, .406], np.float32)[:, None, None]
STD = np.array([.229, .224, .225], np.float32)[:, None, None]

class VisionDual(nn.Module):
    def __init__(self, outputs=2):
        super().__init__()
        encoder = resnet18(weights=None)
        encoder.fc = nn.Identity()
        self.encoders = nn.ModuleList([encoder])
        self.classifier = nn.Linear(512, outputs)
    def forward(self, x):
        return self.classifier(self.encoders[0](x))

class MultimodalDual(nn.Module):
    def __init__(self):
        super().__init__()
        self.br = Branches(512, .2)
        self.head = nn.Linear(512, 2)

class Runtime:
    def __init__(self, model_id):
        self.meta = json.loads((MODELS / 'registry.json').read_text(encoding='utf-8'))[model_id]
        path = MODELS / self.meta['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != self.meta['sha256']:
            raise ValueError('模型权重校验失败')
        # CPU 是可部署的真实推理执行器，不要求 CUDA，也不触发在线下载。
        torch.set_num_threads(min(4, torch.get_num_threads()))
        self.model = MultimodalDual() if self.meta['architecture'] == 'vis_torque' else VisionDual()
        self.model.load_state_dict(torch.load(path, map_location='cpu', weights_only=True))
        self.model.eval()
        self.lock = threading.Lock()
        self.infrared = None

    def forward(self, image, torque=None):
        x = torch.from_numpy((image.transpose(0, 3, 1, 2).astype(np.float32) / 255 - MEAN) / STD)
        with self.lock, torch.inference_mode():
            if self.meta['architecture'] == 'vis_torque':
                if torque is None or torque.shape != (2, 224) or not np.isfinite(torque).all():
                    raise ValueError('该模型需要完整的两通道铺粉段扭矩')
                normal = self.meta['torque_norm']
                q = (torque - np.asarray(normal['mean'])) / np.asarray(normal['std'])
                t = torch.from_numpy(q.astype(np.float32))[None].expand(len(image), -1, -1)
                features = self.model.br(x, t)
                z = self.model.head(fuse(features, self.meta['weights']))
                singles = {k: torch.sigmoid(self.model.head(v)).numpy() for k, v in features.items()}
            else:
                z = self.model(x)
                singles = {'vis': torch.sigmoid(z).numpy()}
            z = z.numpy().astype(np.float64)
            p = 1 / (1 + np.exp(-np.clip(z, -700, 700)))
        # 各模型输出顺序不同，在接口层统一成 proc/dev，不能通过标签互相替代。
        order = [self.meta['outputs'].index(k) for k in ('proc', 'dev')]
        return z[:, order], p[:, order], {k: v[:, order] for k, v in singles.items()}

    def infer(self, current, reference=None):
        rgb, torque = current['rgb'], current.get('torque')
        z, p, singles = self.forward(rgb[None], torque)
        out = {'p_proc': float(p[0, 0]), 'p_dev': float(p[0, 1]),
               'singles': {k: float(v[0].max()) for k, v in singles.items()}}
        if 'infrared' in current:
            if self.infrared is None:
                from .infrared import InfraredRuntime
                self.infrared = InfraredRuntime()
            out['infrared'] = self.infrared.predict(current['infrared'])
        if reference is not None:
            mask = current['band'].astype(bool)
            valid = current['valid'].astype(bool) if self.meta['architecture'] == 'vis_torque' else np.ones_like(mask)
            # 平台/刮刀和灰边固定为当前图像，不将其变化错误转移到粉床贡献。
            baseline = np.where(valid[..., None], reference['rgb'], rgb)
            coalition = np.stack([np.where(((mask & bool(c & 1)) | (valid & ~mask & bool(c & 2)))[..., None], rgb, baseline) for c in range(4)])
            values, _, _ = self.forward(coalition, torque)
            for column, key in enumerate(('proc', 'dev')):
                a, b, c, d = values[:, column]
                out.update({key+'_part': float((b-a+d-c)/2), key+'_powder': float((c-a+d-b)/2), key+'_synergy': float(d-b-c+a)})
        return out
