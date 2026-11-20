"""校验故障展示只依赖仓库内的记录与素材，并完整覆盖九台设备。"""
import json
import unittest
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]


class FaultDemoAssetsTests(unittest.TestCase):
    def test_every_fault_has_own_records_and_portable_visuals(self):
        devices = json.loads((ROOT/'slm_device_data/manifest.json').read_text())['devices']
        demos = json.loads((ROOT/'frontend/src/assets/fault-demos.json').read_text())
        self.assertEqual(set(demos), {d['id'] for d in devices if d.get('health') == 'fault'})
        for key, case in demos.items():
            with self.subTest(device=key):
                self.assertTrue(case['records'] or case['media'])
                self.assertTrue(0 < len(case['slice']['regions']) <= 4)
                for field in ['image', 'annotatedImage']:
                    path = ROOT/'frontend/public'/case['slice'][field].lstrip('/')
                    self.assertTrue(path.is_file(), path)
                for media in case['media']:
                    self.assertTrue((ROOT/unquote(media['url']).lstrip('/')).is_file())
                self.assertTrue(case['diagnosis']['rawStatusLabel'])
                self.assertNotIn('prob', case)
                if case['records']:
                    self.assertTrue((ROOT/case['recordSource']).is_file())


if __name__ == '__main__':
    unittest.main()
