#!/usr/bin/env python3
"""
SLM 设备控制器快速测试
用法: python test_slm_quick.py <IP地址> [端口]
"""

import socket
import json
import time
import sys


def test_connection(host, port):
    """测试 TCP 连接"""
    print(f"[*] 测试连接 {host}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        print(f"[+] TCP 连接成功!")
        
        # 发送 get_status 命令
        command = {"command_id": 1, "data": None}
        data = json.dumps(command).encode('utf-8')
        
        print(f"[*] 发送: {data}")
        sock.sendall(data)
        
        # 接收响应
        print("[*] 等待响应...")
        sock.settimeout(10)
        response = b""
        
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                
                # 尝试解析 JSON
                try:
                    resp_json = json.loads(response.decode('utf-8'))
                    print(f"[+] 收到响应:")
                    print(json.dumps(resp_json, indent=2, ensure_ascii=False))
                    sock.close()
                    return True
                except:
                    continue
            except socket.timeout:
                print("[-] 接收超时")
                break
                
        if response:
            print(f"[*] 原始响应: {response}")
        else:
            print("[-] 未收到数据")
            
        sock.close()
        return False
        
    except ConnectionRefusedError:
        print(f"[-] 连接被拒绝，端口 {port} 未开放")
        return False
    except socket.timeout:
        print(f"[-] 连接超时")
        return False
    except Exception as e:
        print(f"[-] 错误: {e}")
        return False


def scan_ports(host):
    """扫描常见端口"""
    common_ports = [502, 8080, 8000, 9000, 10001, 2000, 3000, 4000, 5000, 80, 443]
    
    print(f"[*] 扫描 {host} 的常见端口...")
    open_ports = []
    
    for port in common_ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"[+] 端口 {port} 开放")
                open_ports.append(port)
        except:
            pass
            
    return open_ports


def main():
    if len(sys.argv) < 2:
        print("用法: python test_slm_quick.py <IP地址> [端口]")
        print("示例: python test_slm_quick.py 192.168.1.100")
        print("      python test_slm_quick.py 192.168.1.100 8080")
        sys.exit(1)
        
    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    print("=" * 60)
    print("SLM 设备控制器快速测试")
    print("=" * 60)
    
    if port:
        # 直接测试指定端口
        test_connection(host, port)
    else:
        # 扫描端口
        open_ports = scan_ports(host)
        
        if open_ports:
            print(f"\n[*] 发现 {len(open_ports)} 个开放端口，开始测试...")
            for p in open_ports:
                print(f"\n{'='*60}")
                if test_connection(host, p):
                    print(f"\n[+] 端口 {p} 通信正常!")
                    break
        else:
            print("[-] 未发现开放端口")
            print("[*] 请检查:")
            print("    1. 设备是否开机")
            print("    2. 网线是否连接")
            print("    3. IP 地址是否正确")


if __name__ == "__main__":
    main()
