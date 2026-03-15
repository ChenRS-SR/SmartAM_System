"""
测试视频流
"""
import urllib.request
import json
import socket
import time

socket.setdefaulttimeout(15)

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

print('=== 1. 配置并启动 ===')
result = call_api(f'{BASE}/video_file_mode/setup', {
    'video_files': {
        'CH1': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH1_segment011_20260310_170803.mp4',
        'CH2': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH2_segment011_20260310_170803.mp4',
        'CH3': 'D:/FDM_Monitor_Diagnosis/SmartAM_System/simulation_record/CH3_segment011_20260310_170803.mp4'
    },
    'enable_correction': False
})
print(f"Setup: {result.get('success')}")

result = call_api(f'{BASE}/start?use_mock=true', method='POST')
print(f"Start: {result.get('success')}")

time.sleep(2)

print('\n=== 2. 测试视频流 ===')
for ch in ['CH1', 'CH2', 'CH3']:
    try:
        res = urllib.request.urlopen(f'{BASE}/stream/camera/{ch}?quality=50', timeout=5)
        # 读取第一帧
        data = b''
        while b'\r\n\r\n' not in data and len(data) < 100000:
            chunk = res.read(4096)
            if not chunk:
                break
            data += chunk
        
        # 查找 JPEG 标记
        if b'\xff\xd8\xff' in data:
            print(f"  {ch}: 成功获取视频流 (JPEG 数据)")
        else:
            print(f"  {ch}: 收到数据但格式不对: {data[:100]}")
    except Exception as e:
        print(f"  {ch}: 错误 - {e}")

print('\n=== 3. 检查状态 ===')
status = call_api(f'{BASE}/status')
print(f"is_running: {status.get('is_running')}")
print(f"fps: {status.get('fps')}")

print('\n=== 测试完成 ===')
