"""发布包必须能脱离外部数据目录读取，且不能混用其他设备的模型结果。"""
import sqlite3
import unittest
from contextlib import closing
from replay.service import catalog, get_case, case_for_device, device_descriptor

class PortableReplayTests(unittest.TestCase):
    def test_catalog_has_distinct_devices_and_bundles(self):
        items = catalog()
        self.assertEqual(len(items), 4)
        self.assertEqual(len({i['deviceId'] for i in items}), 4)
        for device in ['slm-b17-replay', 'slm-b44', 'slm-b10', 'slm-b15']:
            self.assertIsNotNone(case_for_device(device))
            self.assertEqual(device_descriptor(device)['id'], device)
        self.assertIsNone(case_for_device('not-a-device'))

    def test_all_packs_verify_and_play_without_original_paths(self):
        for item in catalog():
            with self.subTest(case=item['id']):
                case = get_case(item['id'])  # 首次读取验证分卷与各文件的哈希。
                self.assertEqual(len(case.layers), item['layerCount'])
                for offset in [0, case.manifest['defaultOffset'], case.manifest['duration']/2, case.manifest['duration']]:
                    frame = case.snapshot(offset)
                    self.assertEqual(frame['caseId'], item['id'])
                    self.assertTrue(all(t <= frame['timestamp'] for t in frame['liveTorque']['t']))
                    self.assertLessEqual(len(frame['liveTorque']['t']), 50)
                    self.assertTrue(all(s is None or s['age'] >= 0 for s in frame['samples'].values()))
                    for kind, image in frame['access']['images'].items():
                        if image['available']:
                            self.assertTrue((case.root/'assets'/f"{image['layer']}_{kind}.jpg").is_file())
                    if not case.manifest['capabilities']['recognition']:
                        self.assertIsNone(frame['recognition'])
                        self.assertIsNone(frame['trace'])

    def test_parameter_values_match_latest_original_sample(self):
        for item in catalog():
            case=get_case(item['id'])
            frame=case.snapshot(case.manifest['defaultOffset'])
            with closing(sqlite3.connect(case.root/'samples.sqlite')) as db:
                row=db.execute('SELECT chamber_temperature FROM env_a WHERE time <= ? ORDER BY time DESC, sequence DESC LIMIT 1',(frame['timestamp'],)).fetchone()
            self.assertEqual(frame['access']['env']['成形室温度'], row[0])

    def test_unavailable_case_is_not_substituted(self):
        with self.assertRaises(KeyError): get_case('nonexistent-case')

if __name__ == '__main__': unittest.main()
