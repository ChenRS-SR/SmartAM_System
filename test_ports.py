#!/usr/bin/env python3
"""
测试工控机的 1947 和 2010 端口
"""

import socket
import json

HOST = "192.168.1.2"
PORTS = [1947, 2010, 8080, 8000, 9000]


def test_port(port):
    """测试单个端口"""
    print(f"\n{'='*60}")
    print(f"测试 {HOST}:{port}")
    print(f"{'='*60}")
    
    try:
        # 建立连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        print(f"[*] 连接中...")
        result = sock.connect_ex((HOST, port))
        
        if result != 0:
            print(f"[-] 端口未开放 (错误码: {result})")
            sock.close()
            return False
            
        print(f"[+] 连接成功!")
        
        # 尝试发送 SLM 协议命令
        command = {"command_id": 1, "data": None}
        data = json.dumps(command).encode('utf-8')
        
        print(f"[*] 发送: {data.decode()}")
        sock.sendall(data)
        
        # 接收响应
        sock.settimeout(10)
        response = b""
        
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                print(f"[*] 收到 {len(chunk)} 字节")
                
                # 尝试解析 JSON
                try:
                    resp_json = json.loads(response.decode('utf-8'))
                    print(f"\n[!!!] SLM 协议响应!")
                    print(json.dumps(resp_json, indent=2, ensure_ascii=False))
                    sock.close()
                    return True
                except json.JSONDecodeError:
                    continue
                    
        except socket.timeout:
            print(f"[-] 接收超时")
            
        if response:
            print(f"[*] 原始响应: {response[:100]}")
            print(f"[*] 可能不是 SLM 协议，或需要不同格式")
        else:
            print(f"[-] 无响应数据")
            
        sock.close()
        return False
        
    except Exception as e:
        print(f"[-] 错误: {e}")
        return False


def main():
    print("="*60)
    print("SLM 打印控制软件端口测试")
    print("="*60)
    print(f"目标: {HOST}")
    print(f"测试端口: {PORTS}")
    
    found = False
    for port in PORTS:
        if test_port(port):
            print(f"\n{'='*60}")
            print(f"[SUCCESS] 发现 SLM 服务: {HOST}:{port}")
            print(f"{'='*60}")
            found = True
            break
            
    if not found:
        print(f"\n{'='*60}")
        print("[-] 未找到 SLM 服务")
        print("="*60)
        print("\n可能原因:")
        print("  1. 打印控制软件未运行")
        print("  2. 端口不是 1947/2010")
        print("  3. 需要特定初始化命令")
        print("  4. 协议格式不同")
        print("\n建议:")
        print("  - 确认打印控制软件已启动")
        print("  - 查看软件配置中的端口设置")
        print("  - 联系软件提供方确认端口号")


if __name__ == "__main__":
    main()
    input("\n按回车键退出...")
