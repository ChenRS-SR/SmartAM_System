"""完整应用必须在无推理依赖时提供五台设备的封存播放，不能靠跳过路由掩盖失败。"""
from pathlib import Path
import subprocess
import sys
import unittest


class PlaybackDeploymentTests(unittest.TestCase):
    def test_full_application_without_inference_dependencies(self):
        script = r'''
import builtins
import sys
original = builtins.__import__
attempts = []
def without_inference(name, *args, **kwargs):
    if name.split('.')[0] in ('torch', 'torchvision'):
        attempts.append(name)
        raise ModuleNotFoundError('测试环境无推理依赖', name=name.split('.')[0])
    return original(name, *args, **kwargs)
builtins.__import__ = without_inference
from fastapi.testclient import TestClient
from main import app
from replay.service import catalog
from forming_monitor.service import get_service
with TestClient(app) as client:
    for route in ['/api/health', '/api/device-type/current', '/api/slm/device-group/devices',
                  '/api/slm/forming/devices', '/api/slm/forming/status', '/api/slm/control/config']:
        response = client.get(route)
        assert response.status_code == 200, (route, response.text)
    assert get_service().devices == {}, '查询状态不能初始化模型'
    for entry in catalog():
        base = '/api/slm/replay/cases/' + entry['id']
        response = client.get(base + '/manifest')
        assert response.status_code == 200, response.text
        manifest = response.json()
        frame = client.get(base + '/snapshot', params={'offset': manifest['duration']}).json()
        assert frame['processing']['real'] is False
        assert frame['recognition'] and frame['trace']
        for image in frame['access']['images'].values():
            assert image['available']
            assert client.get(image['url']).status_code == 200
        assert client.get(frame['trace']['image']['url']).status_code == 200
        if entry['id'] == 'm130-20251120':
            assert len(frame['access']['images']) == 4
            assert frame['recognition']['infrared']['classes']
    assert attempts == [], attempts
    # 误开真实处理只影响当前请求，仍返回该设备自己的封存结果。
    response = client.get('/api/slm/replay/cases/b44-20250321-09-20/snapshot',
                          params={'offset': 9999999, 'processing':'real'})
    assert response.status_code == 200, response.text
    frame = response.json()
    assert not frame['processing']['real']
    assert frame['recognition']['device']['id'] == 'slm-b44'
    assert attempts, '真实处理开关必须实际尝试加载模型'
    assert 'torch' not in sys.modules and 'torchvision' not in sys.modules
print('PASS: full app, five archives, all images, IR, controls, optional inference')
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1],
                                text=True, capture_output=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__': unittest.main()
