#!/usr/bin/env python3
"""
扫描 192.168.1.x 网段找 SLM 设备
"""

import socket
import json
import subprocess
import concurrent.futures
import time

NETWORK = "192.168.1"
COMMON_PORTS = [502, 8080, 8000, 9000, 10001, 2000, 3000, 4000, 5000, 80]


def ping_host(ip):
    """Ping 主机"""
    try:
        result = subprocess.run(
            ['ping', '-n', '1', '-w', '300', ip],
            capture_output=True,
            timeout=3
        )
        return result.returncode == 0
    except:
        return False


def test_port(ip, port):
    """测试端口并尝试 SLM 协议"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        if sock.connect_ex((ip, port)) != 0:
            sock.close()
            return None
            
        # 尝试 SLM 协议
        command = b'{"command_id": 1, "data": null}'
        sock.sendall(command)
        sock.settimeout(3)
        
        response = b""
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                try:
                    resp = json.loads(response.decode('utf-8'))
                    sock.close()
                    return {
                        'ip': ip,
                        'port': port,
                        'is_slm': True,
                        'response': resp
                    }
                except:
                    continue
        except socket.timeout:
            pass
            
        sock.close()
        
        if response:
            return {
                'ip': ip,
                'port': port,
                'is_slm': False,
                'raw': response[:50]
            }
        return {'ip': ip, 'port': port, 'is_slm': False, 'raw': None}
        
    except Exception as e:
        return None


def main():
    print("="*60)
    print("扫描 192.168.1.x 网段找 SLM 设备")
    print("="*60)
    
    # 1. 快速 ping 扫描
    print("\n[1/3] 扫描在线主机...")
    online = []
    
    with concurrent.futures.ThreadPoolExecutor(50) as ex:
        futures = {ex.submit(ping_host, f"{NETWORK}.{i}"): i for i in range(1, 255)}
        for f in concurrent.futures.as_completed(futures):
            i = futures[f]
            if f.result():
                ip = f"{NETWORK}.{i}"
                online.append(ip)
                print(f"  [+] {ip}")
                
    print(f"\n发现 {len(online)} 个在线主机")
    
    if not online:
        print("[-] 没有在线主机，请检查网线连接")
        return
        
    # 2. 扫描端口
    print("\n[2/3] 扫描开放端口...")
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(30) as ex:
        futures = []
        for ip in online:
            for port in COMMON_PORTS:
                futures.append(ex.submit(test_port, ip, port))
                
        for f in concurrent.futures.as_completed(futures):
            r = f.result()
            if r:
                results.append(r)
                if r.get('is_slm'):
                    print(f"  [!!!] SLM 设备: {r['ip']}:{r['port']}")
                elif r.get('raw'):
                    print(f"  [?] {r['ip']}:{r['port']} 有响应")
                else:
                    print(f"  [+] {r['ip']}:{r['port']} 开放")
                    
    # 3. 显示结果
    print("\n" + "="*60)
    print("扫描结果")
    print("="*60)
    
    slm_devices = [r for r in results if r.get('is_slm')]
    
    if slm_devices:
        print(f"\n[+] 发现 {len(slm_devices)} 个 SLM 设备:")
        for dev in slm_devices:
            print(f"\n  IP: {dev['ip']}")
            print(f"  端口: {dev['port']}")
            print(f"  响应预览:")
            resp = dev['response']
            if 'data' in resp:
                data = resp['data']
                print(f"    设备ID: {data.get('device_id', 'N/A')}")
                print(f"    状态: {data.get('priting_status', 'N/A')}")
    else:
        print("\n[-] 未发现 SLM 设备")
        
        # 检查是否有其他响应
        other = [r for r in results if r.get('raw') and not r.get('is_slm')]
        if other:
            print(f"\n[*] 但发现 {len(other)} 个有响应的端口:")
            for r in other[:5]:
                print(f"    {r['ip']}:{r['port']} - {r['raw']}")
                
        print("\n[*] 建议:")
        print("    1. 确认 SLM 设备已开机并进入就绪状态")
        print("    2. 检查设备网络配置（可能需要手动设置 IP）")
        print("    3. 尝试直接连接设备查看网络设置")


if __name__ == "__main__":
    main()
    input("\n按回车键退出...")
