"""根据现场光源配置更新已封存切片标注；原始文件保留，黑白截面按确认分区生成彩色展示图。"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from package_control_regions import ROOT, annotated_svg, extract_regions, colorize_section


def refresh():
    assets = ROOT / 'frontend/src/assets'
    packages = {}
    for path in (assets / 'control-regions').glob('*.json'):
        data = json.loads(path.read_text())
        manifest = json.loads((ROOT / 'backend/analysis_packages' / data['caseId'] / 'manifest.json').read_text())
        model = manifest['device']['name']
        count = 2 if 'S430' in model else 1
        binary = data['caseId'] in ('blt-s430-20240828', 'm130-20251120')
        cached = {}
        entries = list(data['layers'].values()) + ([data['representative']] if data.get('representative') else [])
        for entry in entries:
            source = ROOT / 'frontend/public' / entry['image'].lstrip('/')
            if source not in cached:
                pixels = np.array(Image.open(source).convert('RGB'))
                rendered = colorize_section(pixels, count, binary)
                display = source.with_name(source.stem + '_display.png')
                Image.fromarray(rendered).save(display)
                regions = extract_regions(rendered[:, :, :3], count)
                target = ROOT / 'frontend/public' / entry['annotatedImage'].lstrip('/')
                target.write_text(annotated_svg(display, pixels.shape[1], pixels.shape[0], regions), encoding='utf-8')
                cached[source] = (regions, hashlib.sha256(target.read_bytes()).hexdigest())
            entry['regions'], entry['annotatedSha256'] = cached[source]
            entry['rendering'] = 'laser-count-color-demo-transparent'
        data.update(segmentation='original-image-device-control-groups', controlRegionCount=count,
                    mapping='原始文件留档；展示图按 S310 单区、S430 双区着色并使用透明背景')
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
        packages[data['caseId']] = data
        print(data['caseId'], count, len(cached))
    path = assets / 'fault-demos.json'
    demos = json.loads(path.read_text())
    for demo in demos.values():
        entry = demo.get('slice')
        if not entry:
            continue
        if entry.get('referenceCase'):
            data = packages[entry['referenceCase']]
            demo['slice'] = {**(data.get('representative') or next(iter(data['layers'].values()))),
                             'referenceCase': entry['referenceCase'], 'representation': 'same-model-section-demo'}
        elif entry.get('representation') == 'video-section-demo':
            # 沿用已核验的两个原始零件局部，不再覆盖彩色多边形。
            source = ROOT / 'frontend/public' / entry['image'].lstrip('/')
            width, height = Image.open(source).size
            for region, polygon in zip(entry['regions'], entry['sourcePolygons']):
                region.update(color='#707070', label=(np.mean(polygon, axis=0)*5).astype(int).tolist())
            width, height = width * 5, height * 5
            entry.update(width=width, height=height)
            target = ROOT / 'frontend/public' / entry['annotatedImage'].lstrip('/')
            target.write_text(annotated_svg(source, width, height, entry['regions']), encoding='utf-8')
    path.write_text(json.dumps(demos, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    refresh()
