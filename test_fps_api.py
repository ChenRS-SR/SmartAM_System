"""
测试 FPS API
"""
import urllib.request
import json

BASE = 'http://localhost:8000/api/slm'

def call_api(url, data=None, method='GET'):
    try:
        if data:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
        else:
            req = urllib.request.Request(url, method=method)
        res = urllib.request.urlopen(req, timeout=10)
        return json.loads(res.read().decode())
    except Exception as e:
        return {'error': str(e)}

print('=== 1. 配置视频文件 ===')
result = call_api(f'{BASE}/video_file_mode/setup', {
    'video_files': {
        'CH1': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH1_segment011_20260310_170803.mp4',
        'CH2': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH2_segment011_20260310_170803.mp4',
        'CH3': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH3_segment011_20260310_170803.mp4'
    },
    'enable_correction': False
})
print(f"Setup: {result}")

print('\n=== 2. 启动采集 ===')
result = call_api(f'{BASE}/start?use_mock=true', method='POST')
print(f"Start: {result.get('success')}")

print('\n=== 3. 检查当前配置 ===')
result = call_api(f'{BASE}/video_file_mode/config')
print(f"Config: {result}")

print('\n=== 4. 设置 FPS 为 10 ===')
result = call_api(f'{BASE}/video_file_mode/fps?fps=10', method='POST')
print(f"Set FPS: {result}")

print('\n=== 5. 设置 FPS 为 60 ===')
result = call_api(f'{BASE}/video_file_mode/fps?fps=60', method='POST')
print(f"Set FPS: {result}")

print('\n=== 完成 ===')
