"""输入预处理：成形区裁剪 + letterbox、扭矩铺粉段重采样到224点、零件区提取。

与第四章（datasets.py）和第六章示例脚本（离线数据导出/compute_site_trace.py）的处理一致：
- 图像：BGR→RGB，按成形区框裁剪，letterbox 到 224（灰边127，INTER_AREA），ImageNet 均值方差标准化。
- 扭矩：原始记录时间只到秒，同一秒内的 n 个采样点放在该秒的 (k+0.5)/n 处，在首末采样点之间等间隔线性插值到224点
  （已与第四章 torque_layer/resample224 全部402层逐点核对一致）。
- 零件区：同层烧结后/铺粉后两帧亮度对数比 → Otsu → 开闭运算、去小块、只填小孔，letterbox 到 224 后外扩 k 像素作为边缘邻域。
"""
from __future__ import annotations

import cv2
import numpy as np
import pandas as pd
import torch
from scipy import ndimage

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
SIZE = 224


def letterbox(img: np.ndarray, size: int = SIZE, pad: int = 127) -> np.ndarray:
    h, w = img.shape[:2]
    s = min(size / h, size / w)
    nh, nw = max(1, round(h * s)), max(1, round(w * s))
    out = np.full((size, size, 3), pad, dtype=np.uint8)
    t, l = (size - nh) // 2, (size - nw) // 2
    out[t:t + nh, l:l + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    return out


def read_rgb(path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def crop_letterbox(rgb: np.ndarray, crop) -> np.ndarray:
    x0, y0, x1, y1 = crop
    return letterbox(rgb[y0:y1, x0:x1])


def to_tensor(lb: np.ndarray) -> torch.Tensor:
    f = (lb.astype(np.float32) / 255.0 - MEAN) / STD
    return torch.from_numpy(f.transpose(2, 0, 1).copy()).float()


def resample_torque(times, scraper, platform, n: int = SIZE) -> np.ndarray:
    """铺粉段扭矩窗口 → (2, n)。times 为只精确到秒的时间戳序列。"""
    t = pd.to_datetime(pd.Series(list(times))).reset_index(drop=True)
    k = t.groupby(t).cumcount()
    cnt = t.groupby(t).transform('count')
    s = (t - t.iloc[0]).dt.total_seconds() + (k + 0.5) / cnt
    s = (s - s.iloc[0]).to_numpy()
    g = np.linspace(0, s[-1], n)
    return np.stack([np.interp(g, s, np.asarray(scraper, float)), np.interp(g, s, np.asarray(platform, float))]).astype(np.float32), g


def _letterbox_mask(m: np.ndarray) -> np.ndarray:
    h, w = m.shape
    s = min(SIZE / h, SIZE / w)
    nh, nw = max(1, round(h * s)), max(1, round(w * s))
    out = np.zeros((SIZE, SIZE), np.uint8)
    t, l = (SIZE - nh) // 2, (SIZE - nw) // 2
    out[t:t + nh, l:l + nw] = cv2.resize(m, (nw, nh), interpolation=cv2.INTER_NEAREST)
    return out


def part_mask(after_rgb: np.ndarray, before_rgb: np.ndarray, crop, band_px: int):
    """返回 (零件区, 零件区含边缘邻域)，均为 224×224 布尔数组。"""
    x0, y0, x1, y1 = crop
    g = lambda im: cv2.cvtColor(im, cv2.COLOR_RGB2GRAY).astype(np.float32)[y0:y1, x0:x1]
    a, b = cv2.GaussianBlur(g(after_rgb), (0, 0), 3), cv2.GaussianBlur(g(before_rgb), (0, 0), 3)
    r = np.abs(np.log((a + 5) / (b + 5)))
    r8 = np.clip(r / np.percentile(r, 99.5) * 255, 0, 255).astype(np.uint8)
    th, _ = cv2.threshold(r8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    m = (r8 > th).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= 8000:
            keep[lab == i] = 1
    filled = ndimage.binary_fill_holes(keep)
    hl, nh_ = ndimage.label(filled & ~keep.astype(bool))
    if nh_:
        sz = ndimage.sum(np.ones_like(hl), hl, index=range(1, nh_ + 1))
        keep = (keep.astype(bool) | np.isin(hl, [k + 1 for k, a_ in enumerate(sz) if a_ < 100000])).astype(np.uint8)
    part = _letterbox_mask(keep)
    band = cv2.dilate(part, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * band_px + 1,) * 2)) if band_px > 0 else part
    return part.astype(bool), band.astype(bool)


def contours(mask: np.ndarray):
    """224 网格上的外轮廓，坐标归一化到 [0,1]。"""
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [[[round(float(q[0][0]) / SIZE, 4), round(float(q[0][1]) / SIZE, 4)] for q in c] for c in cs if len(c) >= 3]
