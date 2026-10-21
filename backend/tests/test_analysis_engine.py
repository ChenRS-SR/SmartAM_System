"""两条路径必须分别真实可用，封存输出不能触发模型运行，也不能混入未来层。"""
import copy
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from replay.service import catalog, get_case
from analysis_engine.service import AnalysisPackage


class AnalysisTests(unittest.TestCase):
    def test_archive_readable_with_torch_import_blocked(self):
        import subprocess
        import sys
        script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in ('torch', 'torchvision'):
        raise ImportError('本测试环境禁止加载推理依赖')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from analysis_engine.service import package
from replay.service import get_case, catalog
for entry in catalog():
    case = get_case(entry['id'])
    frame = package(entry['id']).apply(case.snapshot(case.manifest['duration']), case.layers)
    assert frame['recognition'] and frame['trace']
    assert not frame['processing']['real']
'''
        subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).parents[1], check=True)

    def test_all_archives_have_real_outputs_and_default_does_not_infer(self):
        for entry in catalog():
            case = get_case(entry['id'])
            p = AnalysisPackage(entry['id'])
            self.assertEqual(set(p.archived), {str(r['layer']) for r in case.layers})
            self.assertTrue(any(v['trace'] for v in p.archived.values()))
            # 让计算方法直接报错，证明默认路径不可能偷偷调用真实模型。
            with patch.object(p, 'compute', side_effect=AssertionError('离线不能推理')):
                for offset in [0, case.manifest['duration']/2, case.manifest['duration']]:
                    frame = p.apply(case.snapshot(offset), case.layers)
                    self.assertFalse(frame['processing']['real'])
                    if frame['trace']:
                        self.assertLessEqual(frame['trace']['layer'], frame['layer'])
                        self.assertLessEqual(len(frame['trace']['curve']['layers']), 50)
                    if frame['recognition']:
                        self.assertLessEqual(frame['recognition']['layer'], frame['layer'])
                        expected_id = case.manifest['sourceDevice'] if p.meta.get('preserveOriginalRecognition') else entry['deviceId']
                        self.assertEqual(frame['recognition']['device']['id'], expected_id)
            self.assertIsNone(p.runtime)

    def test_real_cpu_models_reproduce_sealed_results(self):
        # 两种模型各验证有正常参照的一层，包括逐侧概率与四种区域组合的真实贡献。
        for case_id in ['b44-20250321-09-20', 'm130-20251120']:
            p = AnalysisPackage(case_id)
            key = next(k for k,v in p.archived.items() if v['trace'])
            actual = p.compute(int(key))
            expected = p.archived[key]
            for field in ['p_proc','p_dev','proc_part','proc_powder','dev_part','dev_powder']:
                self.assertAlmostEqual(actual['row'][field], expected['row'][field], places=5)
            self.assertEqual(actual['trace']['refLayer'], expected['trace']['refLayer'])
            self.assertEqual(set(p.live), {int(key)})

    def test_infrared_archive_matches_actual_model_and_arrival_times(self):
        p = AnalysisPackage('m130-20251120')
        case = get_case('m130-20251120')
        layer = p.meta['layers'][3]['layer']
        actual = p.compute(layer)['recognition']['infrared']
        expected = p.archived[str(layer)]['recognition']['infrared']
        self.assertEqual(actual['label'], expected['label'])
        self.assertAlmostEqual(actual['anomalyProbability'], expected['anomalyProbability'], places=6)
        self.assertEqual(len(actual['classes']), 5)
        for offset in (0, case.layers[3]['offset'], case.manifest['duration']):
            frame = case.snapshot(offset)
            for kind, image in frame['access']['images'].items():
                if image['available']:
                    arrived = [r for r in case.layers if r['imageTimes'][kind] <= frame['timestamp']]
                    self.assertEqual(image['layer'], arrived[-1]['layer'])
                    self.assertTrue((case.root/'assets'/f"{image['layer']}_{kind}.jpg").is_file())
        self.assertEqual(set(frame['access']['images']), {'before','after','ir_before','ir_after'})

    def test_intake_accepts_real_infrared_and_serves_its_own_image(self):
        from analysis_engine.intake import LayerInfo, process_layer, input_image
        from starlette.datastructures import UploadFile
        from PIL import Image
        p = AnalysisPackage('m130-20251120')
        raw = p.inputs(p.meta['layers'][0]['layer'])
        def file(pixels):
            b = io.BytesIO(); Image.fromarray(pixels).save(b,format='PNG'); b.seek(0)
            return UploadFile(file=b,filename='sample.png')
        info = LayerInfo(task_id='infrared-test',task_name='红外接入',layer=1,total_layers=10,time='2026-10-21T12:00:00+08:00')
        with tempfile.TemporaryDirectory() as directory, patch('analysis_engine.intake.ROOT', Path(directory)):
            result = process_layer('huake-crpbfm130',info.model_dump_json(),file(raw['rgb']),None,
                file(raw['part'].astype(np.uint8)*255), UploadFile(file=io.BytesIO(raw['infrared'].tobytes()),filename='ir.jpg'))
            ir = result['recognition']['infrared']
            self.assertIn('?kind=infrared',ir['image']['url'])
            expected = p.archived[str(p.meta['layers'][0]['layer'])]['recognition']['infrared']
            self.assertAlmostEqual(ir['anomalyProbability'],expected['anomalyProbability'],places=6)
            response = input_image('huake-crpbfm130','infrared-test',1,'infrared')
            actual_image = np.array(Image.open(io.BytesIO(response.body)))
            expected_image = np.array(Image.open(io.BytesIO(raw['infrared'].tobytes())).convert('RGB'))
            np.testing.assert_array_equal(actual_image, expected_image)

    def test_unavailable_inference_returns_own_archive_and_logs_only(self):
        case_id = 'b44-20250321-09-20'
        case = get_case(case_id)
        p = AnalysisPackage(case_id)
        initial = case.snapshot(case.manifest['duration'])
        expected = p.apply(copy.deepcopy(initial), case.layers)
        with patch.object(p, 'compute', side_effect=RuntimeError('test missing runtime')):
            with self.assertLogs('analysis_engine.service', level='ERROR') as captured:
                actual = p.apply(copy.deepcopy(initial), case.layers, True)
        self.assertEqual(actual, expected)
        self.assertNotIn('reason', actual['processing'])
        self.assertIn('test missing runtime', '\n'.join(captured.output))

    def test_m130_has_no_invented_torque_and_keeps_last_after_frame(self):
        case = get_case('m130-20251120')
        frame = case.snapshot(case.layers[3]['offset'])
        self.assertEqual(frame['liveTorque']['t'], [])
        self.assertEqual(len(frame['parameters']), 1)
        self.assertEqual(frame['access']['images']['after']['layer'], case.layers[2]['layer'])
        self.assertTrue(all(v is None for v in frame['access']['env'].values()))
        self.assertEqual(len(frame['access']['channels']), 4)

    def test_intake_rejects_incomplete_input_and_processes_new_task(self):
        from analysis_engine.intake import LayerInfo, prepare, process_layer
        from starlette.datastructures import UploadFile
        from PIL import Image
        from fastapi import HTTPException
        p = AnalysisPackage('m130-20251120')
        raw = p.inputs(p.meta['layers'][0]['layer'])
        registry = json.loads((Path(__file__).parents[1]/'inference_models/registry.json').read_text())
        info = LayerInfo(task_id='test', task_name='新任务', layer=1, total_layers=10, time='2026-10-21T12:00:00+08:00')
        with self.assertRaises(ValueError): prepare(raw['rgb'], None, None, info, registry['m130-dual'])
        with self.assertRaises(ValueError): prepare(raw['rgb'], None, None, info, registry['blt-dual'])
        def file(pixels):
            b = io.BytesIO(); Image.fromarray(pixels).save(b,format='PNG'); b.seek(0)
            return UploadFile(file=b,filename='sample.png')
        def submit(metadata):
            return process_layer('huake-crpbfm130', metadata, file(raw['rgb']), None, file(raw['part'].astype(np.uint8)*255), None)
        with tempfile.TemporaryDirectory() as directory, patch('analysis_engine.intake.ROOT', Path(directory)):
            metadata = info.model_dump_json()
            result = submit(metadata)
            self.assertEqual(result['recognition']['task']['id'], 'test')
            self.assertEqual(result['recognition']['device']['id'], 'huake-crpbfm130')
            self.assertEqual(result, submit(metadata))
            self.assertIsNone(result['trace'])  # 首层没有正常参照，不伪造贡献。
            changed = info.model_copy(update={'task_name':'改名'}).model_dump_json()
            with self.assertRaises(HTTPException) as error: submit(changed)
            self.assertEqual(error.exception.status_code, 409)

if __name__ == '__main__': unittest.main()
