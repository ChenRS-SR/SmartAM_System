"""按真实层号封存切片原图、颜色区域和带引线的独立 SVG 示意图。"""
import argparse
import base64
import hashlib
import html
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def region_masks(pixels, region_count=1, binary=False):
    """保留原图颜色；调控区数量来自设备光源配置，不按颜色数量增加控制通道。"""
    foreground = (pixels.mean(axis=2) > 127) if binary else np.any(pixels < 250, axis=2)
    count, labels, stats, centers = cv2.connectedComponentsWithStats(foreground.astype(np.uint8), 8)
    usable = [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 16]
    foreground = np.isin(labels, usable)
    if not foreground.any():
        raise ValueError('原图没有可用零件截面')
    masks = [foreground]
    if region_count == 2:
        colors = np.unique(pixels[foreground], axis=0)
        if not binary and len(colors) == 2:
            # 双光彩色原图直接沿用分区；不改变跨区零件的原始颜色边界。
            masks = [foreground & np.all(pixels == color, axis=2) for color in colors]
        else:
            # 无分区元数据时仅作展示：按完整连通截面的中心归入左右两组，不切碎零件染色。
            xs = np.where(foreground)[1]
            mid = (int(xs.min()) + int(xs.max())) / 2
            groups = [[i for i in usable if (centers[i, 0] >= mid) == right] for right in (False, True)]
            masks = [np.isin(labels, group) for group in groups]
        if not all(mask.any() for mask in masks):
            raise ValueError('双光展示缺少两个有效截面分组，需提供分区映射')
        masks.sort(key=lambda mask: np.where(mask)[1].mean())
    return masks


def colorize_section(pixels, region_count, binary=False):
    """按已确认的单双光配置着色，背景透明；原始文件保持不变。"""
    display = np.full((*pixels.shape[:2], 4), 255, dtype=np.uint8)
    display[:, :, 3] = 0
    for mask, color in zip(region_masks(pixels, region_count, binary), [(255, 176, 218), (65, 80, 180)]):
        display[mask] = (*color, 255)
    return display


def extract_regions(pixels, region_count=1, binary=False):
    masks = region_masks(pixels, region_count, binary)
    items = []
    for number, mask in enumerate(masks, 1):
        y, x = np.unravel_index(np.argmax(cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)), mask.shape)
        colors, counts = np.unique(pixels[mask], axis=0, return_counts=True)
        color = colors[np.argmax(counts)]
        # 黑白原图统一用中性灰标识，不创建新的彩色零件图。
        hex_color = '#707070' if binary else '#' + ''.join(f'{int(v):02x}' for v in color)
        items.append({'id': f'region-{number}', 'number': number, 'name': f'区域{number}',
                      'color': hex_color, 'pixels': int(mask.sum()), 'label': [int(x), int(y)]})
    return items


def annotated_svg(source, width, height, regions):
    """原图内嵌，标签分列两侧并均匀排布；浏览器直接用 img 加载，无外部图片依赖。"""
    margin = 190
    sides = [[r for r in regions if r['label'][0] < width / 2],
             [r for r in regions if r['label'][0] >= width / 2]]
    canvas_height = max(height, (max(map(len, sides)) + 1) * 80)
    top = (canvas_height - height) / 2
    encoded = base64.b64encode(source.read_bytes()).decode('ascii')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width + 2 * margin} {canvas_height}" role="img">',
             '<title>切片区域与引线标注</title>',
             f'<image x="{margin}" y="{top}" width="{width}" height="{height}" href="data:image/png;base64,{encoded}"/>']
    for side, members in enumerate(sides):
        for i, region in enumerate(sorted(members, key=lambda r: r['label'][1])):
            y = (i + 1) * canvas_height / (len(members) + 1)
            x = 16 if side == 0 else margin + width + 26
            endpoint = x + 148 if side == 0 else x
            elbow = margin - 10 if side == 0 else margin + width + 10
            anchor_x, anchor_y = region['label'][0] + margin, region['label'][1] + top
            parts.extend([
                f'<polyline points="{anchor_x},{anchor_y} {elbow},{y} {endpoint},{y}" fill="none" stroke="#34485e" stroke-width="2.5"/>',
                f'<circle cx="{anchor_x}" cy="{anchor_y}" r="6" fill="white" stroke="#34485e" stroke-width="2.5"/>',
                f'<rect x="{x}" y="{y-25}" width="148" height="50" rx="4" fill="white" stroke="#8c9baa"/>',
                f'<rect x="{x+12}" y="{y-7}" width="14" height="14" fill="{region["color"]}" stroke="#8c9baa"/>',
                f'<text x="{x+84}" y="{y+10}" text-anchor="middle" font-family="sans-serif" font-size="30" font-weight="600" fill="#1d3557">{html.escape(region["name"])}</text>',
            ])
    return '\n'.join(parts + ['</svg>'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--representative', action='store_true', help='source 为本任务典型切片文件，供全案例展示')
    parser.add_argument('--regions', type=int, choices=(1, 2), help='非 S310/S430 设备的调控区数')
    parser.add_argument('--binary', action='store_true', help='黑底白色切片或零件掩膜分区')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'backend/analysis_packages' / args.case / 'manifest.json').read_text())
    model = manifest['device']['name']
    region_count = 1 if 'S310' in model else 2 if 'S430' in model else args.regions or 1
    destination = ROOT / 'frontend/public/control-regions' / args.case
    destination.mkdir(parents=True, exist_ok=True)
    output = {'caseId': args.case, 'deviceId': manifest['device']['id'], 'task': manifest['task'],
              'mapping': '任务典型截面，固定展示，不表示逐层几何变化' if args.representative else 'bp_<layer>.png 与当前层号一一对应',
              'representation': 'representative' if args.representative else 'per-layer',
              'segmentation': 'original-image-device-control-groups', 'controlRegionCount': region_count, 'layers': {}}
    packaged = {}
    for layer in [r['layer'] for r in manifest['layers']]:
        source = args.source if args.representative else args.source / f'bp_{layer}.png'
        if source in packaged:
            output['layers'][str(layer)] = {**packaged[source], 'layer': layer}
            continue
        # 缺层直接报错，不拿邻层切片代替当前层。
        with Image.open(source) as image:
            pixels = np.array(image.convert('RGB'))
        height, width = pixels.shape[:2]
        if source.resolve() != (destination / source.name).resolve():
            shutil.copyfile(source, destination / source.name)
        display = source
        display_pixels = colorize_section(pixels, region_count, args.binary)
        display = destination / (source.stem + '_display.png')
        Image.fromarray(display_pixels).save(display)
        items = extract_regions(display_pixels[:, :, :3], region_count)
        illustration = destination / (source.stem + '_regions.svg')
        illustration.write_text(annotated_svg(display, width, height, items), encoding='utf-8')
        output['layers'][str(layer)] = {'layer': layer, 'width': width, 'height': height,
            'image': f'/control-regions/{args.case}/{source.name}',
            'annotatedImage': f'/control-regions/{args.case}/{illustration.name}', 'regions': items,
            'sourceFile': source.name, 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'annotatedSha256': hashlib.sha256(illustration.read_bytes()).hexdigest()}
        packaged[source] = output['layers'][str(layer)]
    layer_count = len(output['layers'])
    if args.representative:
        output['availableLayers'] = [int(layer) for layer in output['layers']]
        output['representative'] = next(iter(output['layers'].values()))
        output['layers'] = {}
    data = ROOT / 'frontend/src/assets/control-regions'
    data.mkdir(parents=True, exist_ok=True)
    (data / f'{args.case}.json').write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(f'封存 {len(packaged)} 张截面图，覆盖 {layer_count} 个案例层')


if __name__ == '__main__':
    main()
