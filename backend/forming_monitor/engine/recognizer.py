"""识别与溯源计算。

识别：第四章跨设备适配识别模型，输出融合缺粉概率与只用单一模态时的缺粉概率。
溯源：第五章两区联盟博弈。因子为零件区（含边缘邻域）与粉床区，收益为缺粉输出的 logit，精确求两区 Shapley 值；
  缺席区域用参照层同位置像素替代，扭矩为整层模态，各联盟中均保持当前层扭矩。
"""
from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
import torch

from .nets import Branches, fuse


class Recognizer:
    def __init__(self, bundle_path: Path, device: str = 'cpu'):
        b = torch.load(bundle_path, map_location='cpu', weights_only=False)
        self.meta = b['meta']
        self.crop = b['crop_box']
        self.weights = b['modality_weights']
        self.dev = torch.device(device)
        self.br = Branches(b['common_dim'], b['proj_dropout'])
        self.br.load_state_dict(b['branches'])
        self.clf = torch.nn.Linear(b['common_dim'], 2)
        self.clf.load_state_dict(b['clf'])
        self.br.to(self.dev).eval()
        self.clf.to(self.dev).eval()
        self.tq_mean = torch.tensor(b['torque_norm']['mean']).view(2, 1)
        self.tq_std = torch.tensor(b['torque_norm']['std']).view(2, 1)
        self._lock = threading.Lock()  # BN 为 eval 模式，加锁只为避免多线程同时占用 CPU 线程池

    def norm_torque(self, tq224: np.ndarray) -> torch.Tensor:
        return (torch.from_numpy(tq224).float() - self.tq_mean) / self.tq_std

    @torch.no_grad()
    def _forward(self, vis: torch.Tensor, tq: torch.Tensor):
        z = self.br(vis.to(self.dev), tq.to(self.dev))
        out = self.clf(fuse(z, self.weights)).float()
        logit = (out[:, 1] - out[:, 0]).cpu().numpy().astype(np.float64)
        p = torch.softmax(out, 1)[:, 1].cpu().numpy()
        pv = torch.softmax(self.clf(z['vis']).float(), 1)[:, 1].cpu().numpy()
        pt = torch.softmax(self.clf(z['tq']).float(), 1)[:, 1].cpu().numpy()
        return logit, p, pv, pt

    def recognize(self, vis: torch.Tensor, tq: torch.Tensor) -> dict:
        """vis: (3,224,224) 已标准化；tq: (2,224) 已标准化。"""
        with self._lock:
            _, p, pv, pt = self._forward(vis[None], tq[None])
        return {'fused': float(p[0]), 'vis': float(pv[0]), 'tq': float(pt[0])}

    def shapley(self, cur: torch.Tensor, ref: torch.Tensor, region: np.ndarray, tq: torch.Tensor) -> dict:
        """两区精确 Shapley。region 为零件区（含边缘邻域）布尔掩膜，其余为粉床区。"""
        m = torch.from_numpy(region)
        xs = torch.stack([torch.where(((m & bool(c & 1)) | (~m & bool(c & 2)))[None], cur, ref) for c in range(4)])
        with self._lock:
            v, p, _, _ = self._forward(xs, tq[None].expand(4, -1, -1))
        return {'part': float(0.5 * (v[1] - v[0]) + 0.5 * (v[3] - v[2])),
                'powder': float(0.5 * (v[2] - v[0]) + 0.5 * (v[3] - v[1])),
                'synergy': float(v[3] - v[1] - v[2] + v[0]), 'logit_cur': float(v[3]), 'logit_ref': float(v[0])}
