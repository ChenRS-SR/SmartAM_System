"""网络结构，与第四章 03_本章方法/src_base/backbones.py、cmwt/cmwt.py 中的定义一致（推理用，不加载 ImageNet 预训练）。"""
from __future__ import annotations

import torch
import torch.nn as nn
from torchvision.models import resnet18


class TwinFrameResNet18(nn.Module):
    """单个 ResNet-18，两帧共享权重分别提取后拼接（第四章只用铺粉后图像，两路输入同一张图）。"""

    def __init__(self):
        super().__init__()
        base = resnet18(weights=None)
        self.body = nn.Sequential(base.conv1, base.bn1, base.relu, base.maxpool,
                                  base.layer1, base.layer2, base.layer3, base.layer4)
        self.pool = nn.AdaptiveAvgPool2d(1)

    def forward(self, before: torch.Tensor, after: torch.Tensor) -> torch.Tensor:
        return torch.cat([self.pool(self.body(before)).flatten(1), self.pool(self.body(after)).flatten(1)], dim=1)


class Torque1DCNN(nn.Module):
    """刮刀扭矩/加工平台扭矩 2 通道 × 224 点的一维卷积编码器。"""

    def __init__(self, in_ch: int = 2, out_dim: int = 1024):
        super().__init__()
        layers, c_in = [], in_ch
        for c_out in (32, 64, 128, 256):
            layers += [nn.Conv1d(c_in, c_out, 5, 2, 2), nn.BatchNorm1d(c_out), nn.ReLU(inplace=True)]
            c_in = c_out
        self.net = nn.Sequential(*layers)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.proj = nn.Linear(c_in, out_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.proj(self.pool(self.net(x)).flatten(1))


class Branches(nn.Module):
    """各模态编码器 + 映射层，输出各模态在共同空间中的特征。"""

    def __init__(self, common_dim: int = 512, dropout: float = 0.2):
        super().__init__()
        self.enc = nn.ModuleDict({'vis': TwinFrameResNet18(), 'tq': Torque1DCNN()})
        self.proj = nn.ModuleDict({m: nn.Sequential(nn.Linear(1024, common_dim), nn.ReLU(inplace=True), nn.Dropout(dropout))
                                   for m in ('vis', 'tq')})

    def forward(self, vis: torch.Tensor | None, tq: torch.Tensor | None) -> dict:
        out = {}
        if vis is not None:
            out['vis'] = self.proj['vis'](self.enc['vis'](vis, vis))
        if tq is not None:
            out['tq'] = self.proj['tq'](self.enc['tq'](tq))
        return out


def fuse(z: dict, w: dict) -> torch.Tensor:
    """按模态权重加权求和，权重在当前可用模态上归一化。"""
    num, den = 0.0, 0.0
    for m, zm in z.items():
        wm = torch.full((zm.size(0),), float(w.get(m, 0.0)), device=zm.device, dtype=zm.dtype)
        num = num + wm[:, None] * zm
        den = den + wm
    return num / den.clamp_min(1e-8)[:, None]
