import unittest
from analysis_engine.results import attach


class RecognitionHistoryTests(unittest.TestCase):
    def test_all_arrived_layers_are_visible_without_future_results(self):
        rows = [{'layer': i, 'recognitionAt': i * 10, 'end': i * 10 + 5} for i in range(1, 11)]
        results = {str(i): {'recognition': {'layer': i, 'prob': {'def': .1}, 'label': '正常'},
                            'trace': None} for i in range(1, 11)}
        frame = attach({'timestamp': 85}, results, rows)
        self.assertEqual([r['layer'] for r in frame['recognition']['records']], list(range(8, 0, -1)))
        earlier = attach({'timestamp': 35}, results, rows)
        self.assertEqual([r['layer'] for r in earlier['recognition']['records']], [3, 2, 1])

    def test_b44_startup_layers_are_excluded_only_for_that_case(self):
        rows = [{'layer': i, 'recognitionAt': i * 10, 'end': i * 10 + 5} for i in range(2, 6)]
        results = {str(i): {'recognition': {'layer': i, 'prob': {'def': .8}, 'label': '异常'}, 'trace': None} for i in range(2, 6)}
        startup = attach({'caseId':'b44-20250321-09-20', 'timestamp':35}, results, rows)
        self.assertIsNone(startup['recognition'])
        frame = attach({'caseId':'b44-20250321-09-20', 'timestamp':55}, results, rows)
        self.assertEqual([r['layer'] for r in frame['recognition']['records']], [5,4])
        other = attach({'caseId':'other', 'timestamp':55}, results, rows)
        self.assertEqual([r['layer'] for r in other['recognition']['records']], [5,4,3,2])
        self.assertEqual(results['2']['recognition']['label'], '异常')
