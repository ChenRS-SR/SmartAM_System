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


def extract_regions(pixels, color_ids):
    """每种原始填充颜色代表一个区域，数量由当前图片决定；同色离散岛屿仍属同一区域。"""
    colors = [c for c in np.unique(pixels.reshape(-1, 3), axis=0) if not np.all(c == 255)]
    if len(colors) > 64:
        raise ValueError('输入须为离散颜色的切片区域图')
    found = []
    for color in colors:
        mask = np.all(pixels == color, axis=2).astype(np.uint8)
        ys, xs = np.where(mask)
        found.append((float(xs.mean()), color, mask))
    items = []
    for _, color, mask in sorted(found, key=lambda r: r[0]):
        hex_color = '#' + ''.join(f'{int(v):02x}' for v in color)
        if hex_color not in color_ids:
            color_ids[hex_color] = len(color_ids) + 1
        # 引线终点选区域内部最宽处，避免凹形或空心零件的质心落在背景上。
        y, x = np.unravel_index(np.argmax(cv2.distanceTransform(mask, cv2.DIST_L2, 5)), mask.shape)
        items.append({'id': f'region-{color_ids[hex_color]}', 'number': color_ids[hex_color],
                      'name': f'区域{color_ids[hex_color]}', 'color': hex_color,
                      'pixels': int(mask.sum()), 'label': [int(x), int(y)]})
    return sorted(items, key=lambda r: r['number'])



def annotated_svg(source, width, height, regions):
    """原图内嵌，标签分列两侧并均匀排布；浏览器直接用 img 加载，无外部图片依赖。"""
    margin = 190
    sides = [[r for r in regions if r['label'][0] < width / 2],
             [r for r in regions if r['label'][0] >= width / 2]]
    canvas_height = max(height, (max(map(len, sides)) + 1) * 80)
    top = (canvas_height - height) / 2
    encoded = base64.b64encode(source.read_bytes()).decode('ascii')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width + 2 * margin} {canvas_height}" role="img">',
             '<title>切片区域与引线标注</title>', '<rect width="100%" height="100%" fill="white"/>',
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
    parser.add_argument('--binary', action='store_true', help='黑底白色切片或零件掩膜分区')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'backend/analysis_packages' / args.case / 'manifest.json').read_text())
    destination = ROOT / 'frontend/public/control-regions' / args.case
    destination.mkdir(parents=True, exist_ok=True)
    output = {'caseId': args.case, 'deviceId': manifest['device']['id'], 'task': manifest['task'],
              'mapping': '任务典型截面，固定展示，不表示逐层几何变化' if args.representative else 'bp_<layer>.png 与当前层号一一对应',
              'representation': 'representative' if args.representative else 'per-layer',
              'segmentation': 'section-spatial-groups-max4' if args.binary else 'original-colors-max4', 'layers': {}}
    color_ids = {}
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
        shutil.copyfile(source, destination / source.name)
        display = source
        # 彩色示意最多四区：少量原色保持原分区；碎片较多时按实际截面的空间位置归并。
        if args.binary:
            foreground = (pixels.mean(axis=2) > 127).astype(np.uint8)
            count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, connectivity=8)
            usable = [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 16]
            foreground = np.isin(labels, usable)
            needs_group = len(usable) > 1
        else:
            foreground = np.any(pixels != 255, axis=2)
            needs_group = len(np.unique(pixels[foreground], axis=0)) > 4
        if not foreground.any():
            raise ValueError(f'第 {layer} 层没有零件截面')
        if args.binary or needs_group:
            yy, xx = np.where(foreground)
            center_x, center_y = (xx.min()+xx.max())/2, (yy.min()+yy.max())/2
            groups = ((xx > center_x).astype(int) + 2*(yy > center_y)) if needs_group else np.zeros(len(xx), dtype=int)
            palette = np.array([[255,176,218],[65,80,180],[75,167,149],[219,173,80]],dtype=np.uint8)
            colored = np.full_like(pixels,255)
            colored[yy,xx] = palette[groups]
            pixels = colored
            color_ids.update({'#' + ''.join(f'{int(v):02x}' for v in color): i+1 for i,color in enumerate(palette)})
            display = destination / (source.stem + '_display.png')
            Image.fromarray(colored).save(display)
        items = extract_regions(pixels, color_ids)
        if len(items) > 4:
            raise ValueError('展示区域不得超过四个')
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
