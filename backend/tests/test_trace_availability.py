"""验证 B44 首次诊断边界、等待原因以及回退时不显示未来结果。"""
import unittest
from analysis_engine.service import package
from replay.service import get_case, catalog


class TraceAvailabilityTests(unittest.TestCase):
    def test_b44_waits_for_reference_and_complete_layer(self):
        case = get_case('b44-20250321-09-20')
        analysis = package('b44-20250321-09-20')
        for offset in (0, 30, 1316):
            frame = analysis.apply(case.snapshot(offset), case.layers)
            self.assertIsNone(frame['trace'])
            self.assertEqual(frame['traceAvailability']['nextLayer'], 5)
            self.assertEqual(frame['traceAvailability']['remainingSeconds'], 1317 - offset)
            self.assertNotIn('尚未接入', frame['tracePending'])
        frame = analysis.apply(case.snapshot(1317), case.layers)
        self.assertEqual(frame['trace']['layer'], 5)
        self.assertEqual(frame['trace']['refLayer'], 4)
        self.assertIsNone(frame['tracePending'])
        self.assertEqual(frame['traceAvailability']['state'], 'ready')
        frame = analysis.apply(case.snapshot(0), case.layers)
        self.assertIsNone(frame['trace'])
        self.assertEqual(frame['traceAvailability']['state'], 'waiting')

    def test_all_cases_report_ready_at_end(self):
        for item in catalog():
            case = get_case(item['id'])
            frame = package(item['id']).apply(case.snapshot(case.manifest['duration']), case.layers)
            self.assertEqual(frame['traceAvailability']['state'], 'ready')
            self.assertIsNone(frame['tracePending'])


if __name__ == '__main__':
    unittest.main()
