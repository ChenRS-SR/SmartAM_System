"""
测试视频帧是否连续更新
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

print('\n=== 2. 测试帧是否更新 ===')
time.sleep(2)

# 连续获取5帧，比较大小（应该不同）
for ch in ['CH1', 'CH2', 'CH3']:
    print(f"\n  {ch}:")
    sizes = []
    for i in range(5):
        try:
            res = urllib.request.urlopen(f'{BASE}/stream/camera/{ch}?quality=50', timeout=5)
            # 读取第一帧 JPEG 数据
            data = b''
            while b'\r\n\r\n' not in data and len(data) < 200000:
                chunk = res.read(4096)
                if not chunk:
                    break
                data += chunk
            
            # 找到 JPEG 起始和结束
            jpeg_start = data.find(b'\xff\xd8\xff')
            jpeg_end = data.find(b'\xff\xd9', jpeg_start)
            
            if jpeg_start >= 0 and jpeg_end > jpeg_start:
                jpeg_data = data[jpeg_start:jpeg_end+2]
                sizes.append(len(jpeg_data))
                print(f"    帧{i+1}: {len(jpeg_data)} bytes")
            else:
                print(f"    帧{i+1}: 未找到JPEG")
            
            res.close()
            time.sleep(0.5)  # 间隔500ms
            
        except Exception as e:
            print(f"    帧{i+1}: 错误 - {e}")
    
    # 检查是否有变化
    if len(set(sizes)) > 1:
        print(f"    ✅ 帧大小有变化，画面在更新")
    else:
        print(f"    ⚠️ 帧大小相同，可能画面未更新")

print('\n=== 测试完成 ===')
