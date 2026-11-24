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
