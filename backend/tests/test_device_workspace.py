"""统一设备工作区的数据隔离、缺失语义与部署契约。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from device_workspace import record_workspace, router, preview_records
from core.slm_device_data import SLMDeviceDataStore
from task4.service import devices, asset
from replay.service import case_for_device


class WorkspaceTests(unittest.TestCase):
    def test_every_record_device_uses_same_contract_without_inference(self):
        count = 0
        for device in devices():
            if case_for_device(device['id']):
                continue
            frame = record_workspace(device['id'])['snapshot']
            count += 1
            self.assertEqual(frame['caseId'], device['id'])
            self.assertIn('parameters', frame)
            for name in ('access', 'recognition', 'trace'):
                self.assertEqual(frame[name]['device']['id'], device['id'])
            self.assertFalse(frame['recognition']['available'])
            self.assertIsNone(frame['recognition']['prob']['def'])
            self.assertIsNone(frame['trace']['factors']['dev']['total'])
            self.assertIsNone(frame['trace']['factors']['proc']['prob'])
            self.assertLessEqual(len(frame['access']['torque']['t']), 50)
            json.dumps(frame, allow_nan=False)
        self.assertEqual(count, 27)
        self.assertNotIn('torch', sys.modules)

    def test_fault_diagnosis_and_regions_belong_to_device(self):
        for key, fault in asset('fault-demos.json').items():
            frame = record_workspace(key)['snapshot']
            self.assertEqual(frame['trace']['recordDiagnosis']['conclusion'], fault['status'])
            self.assertEqual(frame['trace']['recordDiagnosis']['source'], '设备档案')
            self.assertEqual(frame['slice'], fault['slice'])
            self.assertEqual(frame['controlSignal'], fault['control'])
        normal = record_workspace('slm-b5')['snapshot']
        self.assertIsNone(normal['slice'])
        self.assertEqual(normal['trace']['recordDiagnosis']['state'], 'pending')
        self.assertIsNone(record_workspace('huake-slm-01')['snapshot']['layer'])

    def test_video_not_mislabeled_as_model_input(self):
        frame = record_workspace('huake-slm-02')['snapshot']
        self.assertIsNone(frame['recognition']['image']['url'])
        self.assertIsNone(frame['access']['images']['before']['url'])
        self.assertEqual([c['name'] for c in frame['access']['channels'][-2:]], ['可见光图像', '红外图像'])
        image = frame['access']['images']['video_0']
        self.assertTrue(image['url'].endswith('/mock_video_corrected/CH1/frames/000001.jpg'))
        self.assertGreater(image['frameSequence']['count'], 1)
        self.assertNotIn('videoUrl', image)

    def test_corrected_image_and_missing_correction_never_use_raw(self):
        device = record_workspace('huake-slm-02')['device']
        with patch('device_workspace.get_slm_device_data_store') as store:
            store.return_value.get_device.return_value = device
            device['mockVideo']['correctedChannels'] = {
                'camera_ch1': dict(available=True, url='/corrected.jpg', media_type='image')}
            access = record_workspace('huake-slm-02')['snapshot']['access']
            self.assertEqual(access['images']['video_0']['url'], '/corrected.jpg')
            self.assertNotIn('videoUrl', access['images']['video_0'])
            self.assertTrue(access['images']['video_0']['distortionCorrected'])
            device['mockVideo']['correctedChannels'] = {}
            access = record_workspace('huake-slm-02')['snapshot']['access']
            self.assertFalse(any(c['name'] == '可见光图像' for c in access['channels']))

    def test_corrected_media_scanner_accepts_still_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'slm_device_data' / 'SLM' / 'demo' / 'mock_video_corrected'
            (folder / 'CH1').mkdir(parents=True)
            (folder / 'CH1' / 'frame.png').write_bytes(b'')
            result = SLMDeviceDataStore(project_root=root)._scan_channel_video(folder, 'CH1')
            self.assertTrue(result['available'])
            self.assertEqual(result['media_type'], 'image')
            self.assertIn('/mock_video_corrected/CH1/frame.png', result['url'])

    def test_missing_file_and_traversal_are_errors(self):
        for path in ('../README.md', 'SLM/not-found.csv'):
            with self.assertRaises(HTTPException) as cm:
                preview_records({'realData':{'preview_csv':path}})
            self.assertEqual(cm.exception.status_code, 409)

    def test_endpoint_unknown_device_and_archive_routing(self):
        app = FastAPI()
        app.include_router(router, prefix='/api')
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/slm/workspace/devices/missing').status_code, 404)
            self.assertEqual(client.get('/api/slm/workspace/devices/slm-b44').status_code, 409)
            response = client.get('/api/slm/workspace/devices/slm-b17')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['manifest']['deviceId'], 'slm-b17')
