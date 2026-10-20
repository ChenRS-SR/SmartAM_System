"""验证回放时间边界、跳转与数据真实性，不依赖模型或现场数据文件。"""
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from replay.service import ReplayCase


class ReplayTimelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'layers').mkdir()
        self.rows = [
            {'layer': 1, 'start': 100, 'recoat': 101, 'melt': 105, 'recognitionAt': 105, 'end': 110, 'offset': 0},
            {'layer': 2, 'start': 110, 'recoat': 111, 'melt': 115, 'recognitionAt': 115, 'end': 120, 'offset': 10},
            {'layer': 8, 'start': 200, 'recoat': 201, 'melt': 205, 'recognitionAt': 205, 'end': 210, 'offset': 20},
        ]
        manifest = {'id': 'test-case', 'duration': 30, 'layers': self.rows, 'segments': [
            {'firstLayer': 1, 'lastLayer': 2, 'start': 100, 'end': 120, 'offset': 0, 'duration': 20},
            {'firstLayer': 8, 'lastLayer': 8, 'start': 200, 'end': 210, 'offset': 20, 'duration': 10}]}
        (self.root / 'manifest.json').write_text(json.dumps(manifest))
        (self.root / 'alarms.json').write_text(json.dumps([{'time': 107, 'text': '报警A'}, {'time': 118, 'text': '报警B'}]))
        for row in self.rows:
            layer = row['layer']
            f = {'zones': [{'v': 1}, {'v': 2}], 'total': 3, 'prob': .7, 'support': []}
            data = {
                'access': {'images': {'before': {}, 'after': {}}, 'records': [
                    {'layer': layer, 'recoat': 4, 'dur': 10, 'torqueN': 3, 'images': 2, 'complete': True}]},
                'recognition': {'layer': layer, 'prob': {'def': .7}, 'label': '异常', 'image': {}, 'records': []},
                'trace': {'layer': layer, 'refLayer': 0, 'factors': {'dev': f}, 'conclusion': '未见异常', 'image': {}, 'curve': {}, 'records': []},
                'traceReason': None,
            }
            (self.root / 'layers' / f'{layer}.json').write_text(json.dumps(data))
        with closing(sqlite3.connect(self.root / 'samples.sqlite')) as db:
            schemas = {
                'torque': 'scraper REAL, platform REAL',
                'env_a': 'chamber_pressure REAL, chamber_temperature REAL, heater_temperature REAL, argon_pressure REAL',
                'env_b': 'powder_level REAL, oxygen REAL', 'env_c': 'gas_flow REAL, fan_speed REAL'}
            for table, cols in schemas.items():
                db.execute(f'CREATE TABLE {table} (time REAL, sequence INTEGER, {cols})')
                count = len(cols.split(','))
                marks = ','.join('?' * (count + 2))
                for t, sequence, value in [(100, 1, 0), (106, 2, 6), (106, 3, 7), (117, 4, 17), (201, 5, 21)]:
                    db.execute(f'INSERT INTO {table} VALUES ({marks})', [t, sequence] + [value] * count)
            db.commit()
        self.case = ReplayCase(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_no_future_samples_images_results_or_alarms(self):
        s = self.case.snapshot(4)
        self.assertEqual(s['parameters'][1]['value'], 0)
        self.assertIsNone(s['access']['images']['before']['url'])
        self.assertIsNone(s['recognition'])
        self.assertIsNone(s['trace'])
        self.assertEqual(s['access']['alarms'], [])
        self.assertEqual(s['access']['records'][0]['state'], '接入中')
        self.assertIsNone(s['access']['records'][0]['dur'])

    def test_same_second_uses_original_sequence_and_preserves_zero(self):
        self.assertEqual(self.case.snapshot(0)['access']['env']['成形室氧含量ppm'], 0)
        s = self.case.snapshot(6)
        self.assertEqual(s['parameters'][1]['value'], 7)
        self.assertEqual(s['recognition']['layer'], 1)
        self.assertIsNone(s['trace'])

    def test_layer_boundary_retains_last_arrived_image_with_its_layer(self):
        s = self.case.snapshot(10)
        self.assertEqual(s['layer'], 2)
        self.assertEqual(s['trace']['layer'], 1)
        self.assertEqual(s['access']['images']['after']['layer'], 1)
        self.assertEqual(s['access']['images']['before']['layer'], 1)

    def test_backward_seek_has_no_future_history_and_is_repeatable(self):
        before = self.case.snapshot(6)
        self.case.snapshot(19)
        self.assertEqual(before, self.case.snapshot(6))
        self.assertEqual([r['layer'] for r in before['recognition']['records']], [1])
        self.assertEqual(before['access']['alarms'], [])

    def test_missing_segment_is_skipped_without_carrying_old_samples(self):
        s = self.case.snapshot(20)
        self.assertEqual(s['timestamp'], 200)
        self.assertEqual(s['layer'], 8)
        self.assertIsNone(s['parameters'][1]['value'])
        self.assertIsNone(s['recognition'])
        self.assertIsNone(s['trace'])
        self.assertIsNone(s['access']['images']['after']['url'])

    def test_end_is_clamped_and_last_layer_results_are_reachable(self):
        s = self.case.snapshot(999)
        self.assertEqual(s['offset'], 30)
        self.assertEqual(s['phase'], '层结束')
        self.assertEqual(s['trace']['layer'], 8)

    def test_live_torque_keeps_latest_50_points_and_does_not_read_future(self):
        with closing(sqlite3.connect(self.root / 'samples.sqlite')) as db:
            for i in range(80):
                db.execute('INSERT INTO torque VALUES (?, ?, ?, ?)', (206 + i / 100, 10 + i, i, -i))
            db.commit()
        live = self.case.snapshot(26.6)['liveTorque']
        self.assertEqual(len(live['t']), 50)
        self.assertEqual(live['scraper'][-1], 60)
        self.assertEqual(live['platform'][-1], -60)
        self.assertTrue(all(156.6 <= t <= 206.6 for t in live['t']))
        earlier = self.case.snapshot(24)['liveTorque']
        self.assertEqual(earlier['t'], [201])
        self.assertEqual(self.case.snapshot(24.5)['liveTorque']['t'], earlier['t'])
        self.assertEqual(self.case.snapshot(24.5)['liveTorque']['cursor'], 204.5)

    def test_live_torque_continues_during_melting_after_single_layer_input_window(self):
        manifest = json.loads((self.root / 'manifest.json').read_text())
        manifest['layers'][-1]['end'] = 260
        manifest['segments'][-1].update(end=260, duration=60)
        manifest['duration'] = 80
        (self.root / 'manifest.json').write_text(json.dumps(manifest))
        with closing(sqlite3.connect(self.root / 'samples.sqlite')) as db:
            db.execute('INSERT INTO torque VALUES (240, 99, -12, 0)')
            db.commit()
        case = ReplayCase(self.root)
        frame = case.snapshot(61)
        self.assertEqual(frame['phase'], '熔化')
        self.assertEqual(frame['liveTorque']['t'][-1], 240)
        self.assertEqual(frame['liveTorque']['scraper'][-1], -12)
        self.assertEqual(frame['liveTorque']['platform'][-1], 0)
        self.assertTrue(all(t <= 19 for t in frame['access']['torque']['t']))

    def test_dual_results_preserve_small_and_negative_values_without_future_layers(self):
        manifest = json.loads((self.root / 'manifest.json').read_text())
        manifest['analysis'] = {}
        (self.root / 'manifest.json').write_text(json.dumps(manifest))
        pack = {'source': '双输出测试结果', 'bandPx': 12, 'upper': {'proc': .6, 'dev': 12},
                'upper_rule': '正常层分位值', 'layers': [
                    {'layer': r['layer'], 'ref': 0, 'p_proc': .00012, 'p_dev': .9989,
                     'proc_part': -.000001, 'proc_powder': -.000002,
                     'dev_part': 27.24, 'dev_powder': 5.17, 'conclusion': '由设备因素诱发'}
                    for r in self.rows]}
        path = self.root / 'dual.json'
        path.write_text(json.dumps(pack))
        case = ReplayCase(self.root, path)
        trace = case.snapshot(10)['trace']
        self.assertEqual(trace['mode'], 'dual')
        self.assertEqual(trace['factors']['proc']['prob'], .00012)
        self.assertEqual(trace['factors']['proc']['zones'][0]['v'], -.000001)
        self.assertEqual([r['layer'] for r in trace['curve']['layers']], [1])
        self.assertEqual(trace['curve']['upper'], pack['upper'])
        self.assertEqual(trace['actions'], ['检修刮刀与供粉机构'])
        case.snapshot(30)
        self.assertEqual(case.snapshot(10)['trace'], trace)
        self.assertIsNone(case.snapshot(4)['trace'])


if __name__ == '__main__':
    unittest.main()
