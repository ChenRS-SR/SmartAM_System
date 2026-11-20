"""切片区域数由图片决定，引线图独立加载且保留原图。"""
import base64
import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image
from scripts.package_control_regions import extract_regions, annotated_svg, ROOT


class ControlRegionsTests(unittest.TestCase):
    def test_three_and_four_colors_and_stable_identity(self):
        pixels = np.full((200, 400, 3), 255, dtype=np.uint8)
        colors = [(180, 20, 30), (40, 150, 60), (20, 50, 180), (170, 60, 180)]
        identities = {}
        for i, color in enumerate(colors[:3]):
            pixels[30:130, i * 90 + 10:i * 90 + 80] = color
        first = extract_regions(pixels, identities)
        self.assertEqual(len(first), 3)
        pixels[30:130, 280:350] = colors[3]
        second = extract_regions(pixels, identities)
        self.assertEqual(len(second), 4)
        self.assertEqual([r['id'] for r in first], [r['id'] for r in second[:3]])
        for r in second:
            x, y = r['label']
            self.assertEqual('#' + ''.join(f'{int(v):02x}' for v in pixels[y, x]), r['color'])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'slice.png'
            Image.fromarray(pixels).save(source)
            svg = ET.fromstring(annotated_svg(source, 400, 200, second))
            ns = {'s': 'http://www.w3.org/2000/svg'}
            self.assertEqual(len(svg.findall('s:polyline', ns)), 4)
            self.assertEqual([t.text for t in svg.findall('s:text', ns)], ['区域1', '区域2', '区域3', '区域4'])
            embedded = svg.find('s:image', ns).attrib['href'].split(',', 1)[1]
            self.assertEqual(base64.b64decode(embedded), source.read_bytes())

    def test_repository_assets_match_metadata(self):
        meta = json.loads((ROOT / 'frontend/src/assets/control-regions/b44-20250321-09-20.json').read_text())
        self.assertEqual(set(map(int, meta['layers'])), set(range(2, 28)))
        for layer, row in meta['layers'].items():
            self.assertEqual(row['sourceFile'], f'bp_{layer}.png')
            for key, digest in [('image', 'sha256'), ('annotatedImage', 'annotatedSha256')]:
                path = ROOT / 'frontend/public' / row[key].lstrip('/')
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), row[digest])


if __name__ == '__main__':
    unittest.main()
