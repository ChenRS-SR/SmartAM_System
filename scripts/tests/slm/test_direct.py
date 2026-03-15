#!/usr/bin/env python3
"""
直接测试 192.168.1.2
"""

import socket
import json
import sys

HOST = "192.168.1.2"
PORTS = [502, 8080, 8000, 9000, 10001, 2000, 3000, 4000, 5000, 80, 443]


def test_port(port):
    """测试单个端口"""
    print(f"\n[*] 测试 {HOST}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        if sock.connect_ex((HOST, port)) != 0:
            print(f"  [-] 端口未开放")
            sock.close()
            return False
            
        print(f"  [+] 端口开放!")
        
        # 尝试 SLM 协议
        command = b'{"command_id": 1, "data": null}'
        print(f"  [*] 发送: {command.decode()}")
        
        sock.sendall(command)
        sock.settimeout(5)
        
        response = b""
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                print(f"  [*] 收到 {len(chunk)} 字节")
                
                # 尝试解析 JSON
                try:
                    resp = json.loads(response.decode('utf-8'))
                    print(f"\n  [!!!] SLM 协议响应!")
                    print(f"  响应内容:")
                    print(json.dumps(resp, indent=4, ensure_ascii=False))
                    sock.close()
                    return True
                except json.JSONDecodeError:
                    continue
                    
        except socket.timeout:
            print(f"  [-] 接收超时")
            
        if response:
            print(f"  [?] 原始响应 (非JSON): {response[:100]}")
        else:
            print(f"  [-] 无响应数据")
            
        sock.close()
        return False
        
    except Exception as e:
        print(f"  [-] 错误: {e}")
        return False


def main():
    print("="*60)
    print(f"直接测试 {HOST}")
    print("="*60)
    
    # 先 ping
    import subprocess
    print(f"\n[*] Ping {HOST}...")
    result = subprocess.run(['ping', '-n', '2', HOST], capture_output=True)
    if result.returncode == 0:
        print("  [+] 设备在线")
    else:
        print("  [-] Ping 失败")
        
    # 测试端口
    print(f"\n[*] 测试常见端口...")
    for port in PORTS:
        if test_port(port):
            print(f"\n[+] 发现 SLM 设备: {HOST}:{port}")
            
            # 继续测试其他命令
            print("\n[*] 测试其他命令...")
            test_commands(port)
            return
            
    print("\n[-] 未找到 SLM 协议端口")
    print("[*] 可能原因:")
    print("    1. 设备使用非标准端口")
    print("    2. 设备需要特定初始化")
    print("    3. 协议格式不同")


def test_commands(port):
    """测试其他命令"""
    commands = [
        ("获取状态", {"command_id": 1, "data": None}),
        ("发送消息", {"command_id": 3, "data": {"id": 1, "device_id": "SLM_001", "type": "Normal", "content": "测试", "job_name": "test.slc"}}),
    ]
    
    for name, cmd in commands:
        print(f"\n[*] 测试: {name}")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((HOST, port))
            
            data = json.dumps(cmd).encode('utf-8')
            sock.sendall(data)
            
            response = b""
            sock.settimeout(3)
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    try:
                        resp = json.loads(response.decode('utf-8'))
                        print(f"  [+] 响应: {json.dumps(resp, indent=2, ensure_ascii=False)[:200]}")
                        break
                    except:
                        continue
            except socket.timeout:
                print(f"  [-] 超时")
                
            sock.close()
        except Exception as e:
            print(f"  [-] 错误: {e}")


if __name__ == "__main__":
    main()
    input("\n按回车键退出...")
