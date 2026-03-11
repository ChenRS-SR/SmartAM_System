"""
完整 API 测试
=============
测试视频文件模式的完整流程
"""
import urllib.request
import json
import socket
import time

socket.setdefaulttimeout(10)

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

BASE = 'http://localhost:8000/api/slm'

print('=== 1. 初始状态 ===')
status = call_api(f'{BASE}/status')
print(f"is_running: {status.get('is_running')}")

print('\n=== 2. 配置视频文件模式 ===')
config = call_api(f'{BASE}/video_file_mode/setup', {
    'video_files': {
        'CH1': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH1_segment011_20260310_170803.mp4',
        'CH2': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH2_segment011_20260310_170803.mp4',
        'CH3': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH3_segment011_20260310_170803.mp4'
    },
    'enable_correction': False
})
print(f"success: {config.get('success')}")

print('\n=== 3. 检查配置 ===')
config = call_api(f'{BASE}/video_file_mode/config')
print(f"enabled: {config.get('enabled')}")

print('\n=== 4. 启动采集（use_mock=true）===')
start = call_api(f'{BASE}/start?use_mock=true', method='POST')
print(f"success: {start.get('success')}")
print(f"message: {start.get('message')}")

print('\n=== 5. 等待2秒后检查状态 ===')
time.sleep(2)
status = call_api(f'{BASE}/status')
print(f"is_running: {status.get('is_running')}")
print(f"connected_channels: {status.get('connected_channels')}")
print(f"fps: {status.get('fps')}")

print('\n=== 6. 测试视频流 ===')
try:
    res = urllib.request.urlopen(f'{BASE}/video/stream?channel=CH1', timeout=5)
    data = res.read(1000)
    print(f"Stream response: {len(data)} bytes")
    print(f"Starts with: {data[:100]}")
except Exception as e:
    print(f"Stream error: {e}")

print('\n=== 测试完成 ===')
