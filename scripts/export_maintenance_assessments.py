"""导出案例二运维计算缓存；运行软件不依赖 Excel 或推理环境。"""
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/第2章案例二_B10_B15_B17_B44风险阈值与可靠性计算结果.xlsx'
OUTPUT = ROOT / 'frontend/src/assets/maintenance-assessments.json'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
# key、名称、役龄、W/WL/WU/WR、可靠性，严格对应原表列。
SYSTEMS = [
    ('powder', '刮刀', 'Q', ('V', 'W', 'X', 'Y'), 'AR'),
    ('fan', '风机', 'R', ('Z', 'AA', 'AB', 'AC'), 'AS'),
    ('filter', '滤芯', 'T', ('AD', 'AE', 'AF', 'AG'), 'AT'),
    ('feeder', '落粉轴', 'S', ('AH', 'AI', 'AJ', 'AK'), 'AU'),
    ('argon', '气源系统', 'U', ('AL', 'AM', 'AN', 'AO'), 'AV'),
    ('laser', '激光器', 'O', (), 'AP'),
    ('chiller', '水冷机', 'P', (), 'AQ'),
]


def export():
    with ZipFile(SOURCE) as archive:
        strings = [''.join(item.itertext()) for item in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', NS)]

        def rows(sheet):
            for row in ET.fromstring(archive.read(f'xl/worksheets/sheet{sheet}.xml')).findall('.//s:row', NS):
                result = {}
                for cell in row.findall('s:c', NS):
                    value = cell.find('s:v', NS)
                    if value is None or value.text is None:
                        continue
                    key = re.sub(r'\d', '', cell.attrib['r'])
                    result[key] = strings[int(value.text)] if cell.get('t') == 's' else value.text if cell.get('t') == 'str' else float(value.text)
                yield result

        models = {r['A']: r for r in rows(3) if r.get('B') in ('PLP', 'PHM')}
        devices = {name: [] for name in ('B10', 'B15', 'B17', 'B44')}
        for row in list(rows(1))[1:]:
            systems = []
            for key, name, age, risk, reliability in SYSTEMS:
                model = models[name]
                values = {field: row.get(col) for field, col in zip(('w', 'wl', 'wu', 'wr'), risk)}
                values.update(key=key, name=name, model=model['B'], age=row.get(age), unit='km' if key == 'powder' else 'h', reliability=row.get(reliability), rmin=model['H'])
                assert all(not isinstance(v, float) or math.isfinite(v) for v in values.values())
                if values['reliability'] is not None:
                    assert 0 <= values['reliability'] <= 1
                systems.append(values)
            devices[row['A']].append({'task': row['D'], 'systems': systems})
        for records in devices.values():
            assert len({r['task'] for r in records}) == len(records)
            records.sort(key=lambda r: r['task'])
        output = {'source': SOURCE.name, 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'devices': devices}
        OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        print({key: len(value) for key, value in devices.items()})


if __name__ == '__main__':
    export()
