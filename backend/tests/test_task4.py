"""四个开放接口的契约、时序、幂等与持久化测试，默认环境无需 torch。"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from task4.router import router
from task4 import service
from replay.service import catalog, get_case
from analysis_engine.service import package


class Task4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, SMARTAM_TASK4_DB=str(Path(self.tmp.name)/'task4.sqlite'))
        self.env.start()
        app = FastAPI()
        app.include_router(router, prefix='/api')
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()
        self.tmp.cleanup()

    def call(self, path, body, status=200):
        r = self.client.post('/api/task4/'+path, json=body)
        self.assertEqual(r.status_code, status, r.text)
        result = r.json()
        self.assertEqual(set(result), {'status', 'message', 'data'})
        self.assertEqual(result['status'], status)
        return result['data']

    def test_five_archives_no_inference_and_exact_layer(self):
        with patch('analysis_engine.service.AnalysisPackage.compute', side_effect=AssertionError('不应推理')):
            for entry in catalog():
                data = self.call('defect-recognition', {'deviceId':entry['deviceId']})
                self.assertTrue(data['ready'])
                self.assertEqual(data['recognition']['layer'], data['layerNo'])
                layer = get_case(entry['id']).layers[-1]['layer']
                data = self.call('defect-recognition', {'deviceId':entry['deviceId'], 'layerNo':layer})
                self.assertEqual(data['trace']['layer'], layer)
                self.assertEqual(data['source'], 'sealed-model-results')
        self.assertNotIn('torch', sys.modules)

    def test_no_future_results_and_invalid_selectors(self):
        data = self.call('defect-recognition', {'deviceId':'slm-b44', 'offset':0})
        self.assertFalse(data['ready'])
        self.assertIsNone(data['recognition'])
        self.call('defect-recognition', {'deviceId':'slm-b44', 'layerNo':8, 'offset':0}, 409)
        self.call('defect-recognition', {'deviceId':'slm-b44', 'layerNo':999999}, 404)
        self.call('defect-recognition', {'deviceId':'missing'}, 404)
        self.call('defect-recognition', {'deviceId':'slm-b44', 'offset':999999999}, 400)
        self.call('defect-recognition', {'deviceId':'slm-b44', 'taskId':'other-task', 'layerNo':8}, 404)
        self.call('defect-recognition', {'deviceId':'slm-b44', 'taskId':'../other'}, 400)
        self.call('defect-recognition', {'deviceId':'slm-b44', 'layreNo':8}, 400)
        r=self.client.post('/api/task4/defect-recognition', content='{', headers={'Content-Type':'application/json'})
        self.assertEqual(r.status_code,400)
        self.assertEqual(r.json()['status'],400)

    def test_real_unavailable_is_not_archive_success(self):
        with patch('analysis_engine.service.AnalysisPackage.compute', side_effect=ModuleNotFoundError('torch')):
            self.call('defect-recognition', {'deviceId':'slm-b44','layerNo':8,'processingMode':'real'},503)
        self.call('defect-recognition', {'deviceId':'huake-slm-02','processingMode':'real'},409)

    def test_real_returns_runtime_output(self):
        output = package('b44-20250321-09-20').archived['8']
        with patch('analysis_engine.service.AnalysisPackage.compute', return_value=output) as compute:
            data=self.call('defect-recognition', {'deviceId':'slm-b44','layerNo':8,'processingMode':'real'})
            compute.assert_called_once_with(8)
            self.assertEqual(data['source'],'model-runtime')

    def test_new_task_results_are_isolated(self):
        from analysis_engine import intake
        root=Path(self.tmp.name)/'live'
        folder=root/'slm-b44'/'new-task';folder.mkdir(parents=True)
        import json
        (folder/'8.json').write_text(json.dumps({'recognition':{'layer':8,'task':{'id':'new-task'}},'trace':None}))
        with patch.object(intake,'ROOT',root):
            data=self.call('defect-recognition',{'deviceId':'slm-b44','taskId':'new-task','layerNo':8})
            self.assertEqual(data['source'],'saved-inference')
            self.call('defect-recognition',{'deviceId':'slm-b10','taskId':'new-task','layerNo':8},404)
            self.call('quality-control',{'deviceId':'slm-b44','taskId':'new-task','layerNo':8},409)

    def test_all_faults_and_cases_have_matching_regions(self):
        for key in service.asset('fault-demos.json'):
            data=self.call('quality-control',{'deviceId':key})
            self.assertGreaterEqual(len(data['regions']),1)
            self.assertLessEqual(len(data['regions']),4)
            self.assertFalse(data['executed'])
            source=self.call('defect-recognition',{'deviceId':key})
            self.assertIsNone(source['recognition'])
        for entry in catalog():
            data=self.call('quality-control',{'deviceId':entry['deviceId']})
            drawing=service.slice_for(entry['deviceId'],data['taskId'],data['layerNo'])
            self.assertEqual([r['regionId'] for r in data['regions']],[r['id'] for r in drawing['regions']])
            self.assertTrue((service.ROOT/'frontend/public'/data['image'].lstrip('/')).is_file())

    def test_control_directions_validation_and_pause(self):
        for key,power,wait in [('huake-slm-02',180,2),('huake-slm-03',220,2),('huake-slm-04',200,2),('slm-b17',200,4)]:
            data=self.call('quality-control',{'deviceId':key,'regionIds':['region-1']})
            self.assertEqual(len(data['regions']),1)
            values=data['regions'][0]['controlParameters']
            self.assertEqual(values,dict(laserPower=power,fillSpeed=1000,layerWaitTime=wait))
        data=self.call('quality-control',{'deviceId':'huake-slm-02','automatic':False})
        self.assertEqual(data['regions'][0]['controlParameters']['laserPower'],200)
        self.call('quality-control',{'deviceId':'slm-b44','regionIds':['region-99']},400)
        self.call('quality-control',{'deviceId':'slm-b44','currentParameters':{'laserPower':0}},400)
        self.call('quality-control',{'deviceId':'huake-slm-03','currentParameters':{'laserPower':500}},409)

    def test_plan_persistence_idempotency_and_simulation(self):
        request={'deviceId':'slm-b44','layerNo':8,'operation':'save','requestId':'request-1','strategy':'remelt'}
        first=self.call('quality-control',request)
        self.assertEqual(self.call('quality-control',request), first)
        self.call('quality-control',dict(request,strategy='stop'),409)
        identifier={'deviceId':'slm-b44','planId':first['planId']}
        self.assertEqual(self.call('quality-control',dict(identifier,operation='get')),first)
        self.call('quality-control',dict(identifier,deviceId='slm-b10',operation='get'),404)
        simulated=self.call('quality-control',dict(identifier,operation='simulate'))
        self.assertEqual(simulated['state'],'simulated');self.assertFalse(simulated['executed'])
        self.assertEqual(self.call('quality-control',dict(identifier,operation='get')),simulated)
        self.call('quality-control',dict(identifier,operation='execute'),409)
        self.assertEqual(self.call('maintenance-statistics',{})['maintenanceCount'],0)
        with ThreadPoolExecutor(max_workers=4) as pool:
            values=list(pool.map(lambda _: self.call('quality-control',dict(request,requestId='parallel')),range(4)))
        self.assertEqual(len({v['planId'] for v in values}),1)

    def test_region_strategies_replace_each_other_and_survive_refresh(self):
        base={'deviceId':'slm-b44','layerNo':8}
        def apply(region, strategy, number):
            plan=self.call('quality-control',dict(base,regionIds=[region],strategy=strategy,operation='save',requestId=number))
            self.call('quality-control',dict(deviceId='slm-b44',planId=plan['planId'],operation='simulate'))
            return plan
        first=apply('region-1','remelt','R1')
        result=self.call('quality-control',base)
        self.assertEqual(result['strategy'],'mixed')
        self.assertEqual([r['strategy'] for r in result['regions']],['remelt','adjust'])
        self.assertFalse(result['regions'][0]['automatic'])
        self.assertEqual(result['regions'][0]['controlParameters'],result['regions'][0]['currentParameters'])
        apply('region-2','recoat','R2')
        apply('region-1','stop','R3')
        # 重复旧请求不可重新启用已经被停机策略替换的重熔方案。
        self.call('quality-control',dict(deviceId='slm-b44',planId=first['planId'],operation='simulate'))
        result=self.call('quality-control',dict(base,layerNo=9))
        self.assertEqual([r['strategy'] for r in result['regions']],['stop','recoat'])
        self.assertTrue(all(r['strategy']=='adjust' for r in self.call('quality-control',{'deviceId':'slm-b10'})['regions']))
        from task4.storage import active_strategies
        self.assertEqual(active_strategies('slm-b44','another-task'),{})
        apply('region-1','adjust','R4')
        result=self.call('quality-control',base)
        self.assertEqual([r['strategy'] for r in result['regions']],['adjust','recoat'])
        self.assertTrue(result['regions'][0]['automatic'])
        self.assertFalse(result['executed'])

    def test_equipment_diagnosis(self):
        data=self.call('equipment-diagnosis',{})
        self.assertEqual(data['deviceCount'],32)
        self.assertEqual(data['faultDeviceCount'],9)
        data=self.call('equipment-diagnosis',{'deviceIds':['slm-b17','slm-b44']})
        self.assertEqual(data['devices'][0]['name'],'铂力特 S430 B17')
        self.assertEqual(data['devices'][0]['status'],'fault')
        self.assertIn(data['devices'][1]['status'],['normal','review','abnormal'])
        self.call('equipment-diagnosis',{'deviceIds':['slm-b44','slm-b44']},400)

    def test_display_export_matches_all_five_workspace_snapshots(self):
        from replay.router import manifest, snapshot
        for entry in catalog():
            offset=manifest(entry['id'])['defaultOffset']
            for position in (offset, get_case(entry['id']).manifest['duration']):
                displayed=snapshot(entry['id'], offset=position)
                body={'deviceId':entry['deviceId'], 'offset':position, 'resultScope':'display'}
                result=self.call('defect-recognition',body)
                self.assertEqual(result['recognition'],displayed['recognition'])
                self.assertEqual(result['trace'],displayed['trace'])
                self.assertEqual(result['offset'],displayed['offset'])
                equipment=self.call('equipment-diagnosis',{'deviceIds':[entry['deviceId']], 'offset':position, 'resultScope':'display'})['devices'][0]
                self.assertEqual(equipment['parameters'],displayed['parameters'])
                self.assertEqual(equipment['alarms'],displayed['access']['alarms'])
                self.assertEqual(equipment['trace'],displayed['trace'])
        self.call('defect-recognition',{'deviceId':'slm-b44','resultScope':'display'},400)
        self.call('equipment-diagnosis',{'deviceIds':['slm-b44'],'resultScope':'display'},400)

        self.call('equipment-diagnosis',{'deviceIds':['slm-b17'],'resultScope':'display','offset':1},409)
        self.call('equipment-diagnosis',{'deviceIds':['slm-b44'],'parameterSource':'live','offset':1},400)

    def test_control_defaults_follow_platform_configuration(self):
        from slm_control.config import SAFE_RANGES
        with patch.dict(SAFE_RANGES['fill_power'], default=240):
            data=self.call('quality-control',{'deviceId':'huake-slm-02'})
            self.assertEqual(data['regions'][0]['currentParameters']['laserPower'],240)
            self.assertEqual(data['regions'][0]['controlParameters']['laserPower'],216)
            self.assertEqual(data['parameterSource'],'platform-config')
            data=self.call('quality-control',{'deviceId':'huake-slm-02','currentParameters':{'laserPower':250}})
            self.assertEqual(data['regions'][0]['currentParameters']['laserPower'],250)

    def test_live_parameters_never_replaced_by_archive_values(self):
        from core.slm_realtime import get_slm_realtime_store
        sample={'hasData':True,'eventTime':'2026-11-23T12:00:00+08:00',
                'parameters':[{'name':'激光功率','value':231.25,'unit':'W'}],
                'alarms':[], 'diagnosis':{'statusCode':0,'statusLabel':'正常'}}
        with patch.object(get_slm_realtime_store(),'latest',return_value=sample):
            result=self.call('equipment-diagnosis',{'deviceIds':['slm-b44'],'parameterSource':'live'})['devices'][0]
            self.assertEqual(result['parameters'], sample['parameters'])
            self.assertEqual(result['time'],sample['eventTime'])
            self.assertIsNone(result['trace'])
            self.assertEqual(result['source'],'live-acquisition')
        with patch.object(get_slm_realtime_store(),'latest',return_value={'hasData':False}):
            self.call('equipment-diagnosis',{'deviceIds':['slm-b44'],'parameterSource':'live'},404)

    def test_statistics_exact_period_deduplication_and_device_scope(self):
        empty=self.call('maintenance-statistics',{'deviceIds':['slm-b44']})
        self.assertIsNone(empty['taskFaultRate'])
        base=dict(deviceId='slm-b44',operation='recordTask',occurredAt='2026-11-23T00:00:00+08:00')
        one=dict(base,taskId='T1',faulted=True)
        self.call('maintenance-statistics',one);self.call('maintenance-statistics',one)
        self.call('maintenance-statistics',dict(one,faulted=False),409)
        self.call('maintenance-statistics',dict(base,taskId='T2',faulted=False))
        self.call('maintenance-statistics',dict(base,taskId='T3',faulted=True,occurredAt='2026-11-24T00:00:00+08:00'))
        event=dict(operation='recordMaintenance',deviceId='slm-b44',recordId='M1',description='检查铺粉机构',occurredAt=base['occurredAt'])
        self.call('maintenance-statistics',event);self.call('maintenance-statistics',event)
        data=self.call('maintenance-statistics',dict(deviceIds=['slm-b44'],startTime=base['occurredAt'],endTime='2026-11-24T00:00:00+08:00'))
        self.assertEqual((data['totalTasks'],data['faultTasks'],data['taskFaultRate'],data['maintenanceCount']),(2,1,.5,1))
        self.assertEqual(data['records'][0]['recordId'],'M1')
        other=self.call('maintenance-statistics',{'deviceIds':['slm-b10']})
        self.assertEqual(other['totalTasks'],0)
        self.call('maintenance-statistics',{'startTime':'2026-11-23T00:00:00'},400)
        self.call('maintenance-statistics',dict(event,description='不同内容'),409)
        global_stats=self.call('maintenance-statistics',{})
        self.assertEqual(global_stats['faultDeviceRatio'],9/32)


if __name__ == '__main__':
    unittest.main()
