#!/usr/bin/env python3
"""
在工控机上查找 SLM 设备连接
"""

import subprocess
import json
import os
import sys


def run_cmd(cmd):
    """运行命令并返回输出"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        return result.stdout
    except Exception as e:
        return f"Error: {e}"


def check_com_ports():
    """检查串口"""
    print("\n" + "="*60)
    print("[1] 串口检查")
    print("="*60)
    
    # 使用 mode 命令
    output = run_cmd("mode")
    lines = output.split('\n')
    
    com_ports = []
    for line in lines:
        if 'COM' in line and 'Status' in line:
            com_ports.append(line.strip())
            print(f"  [+] {line.strip()}")
            
    if not com_ports:
        print("  [-] 未找到串口")
        
    # 使用 WMIC
    print("\n  设备管理器串口列表:")
    output = run_cmd("wmic path Win32_SerialPort get DeviceID,Description,Name /format:csv")
    print(output)
    
    return com_ports


def check_network():
    """检查网络"""
    print("\n" + "="*60)
    print("[2] 网络检查")
    print("="*60)
    
    # IP 配置
    print("\n  IP 配置:")
    output = run_cmd("ipconfig")
    print(output)
    
    # 监听端口
    print("\n  监听端口:")
    output = run_cmd("netstat -an | findstr LISTENING")
    lines = output.split('\n')[:20]  # 只显示前20行
    for line in lines:
        if line.strip():
            print(f"    {line.strip()}")
            
    return output


def check_arp():
    """检查 ARP 表"""
    print("\n" + "="*60)
    print("[3] ARP 表（已连接设备）")
    print("="*60)
    
    output = run_cmd("arp -a")
    print(output)
    
    return output


def check_processes():
    """检查相关进程"""
    print("\n" + "="*60)
    print("[4] 相关进程")
    print("="*60)
    
    keywords = ['slm', 'print', 'laser', 'modbus', 'serial', 'tcp', 'server']
    
    output = run_cmd("tasklist /fo csv")
    lines = output.split('\n')
    
    found = []
    for line in lines:
        for keyword in keywords:
            if keyword.lower() in line.lower():
                found.append(line)
                break
                
    if found:
        print("  发现相关进程:")
        for f in found[:10]:
            print(f"    {f}")
    else:
        print("  未发现明显相关进程")
        
    return found


def check_services():
    """检查服务"""
    print("\n" + "="*60)
    print("[5] 系统服务")
    print("="*60)
    
    keywords = ['slm', 'print', 'laser', 'modbus', 'serial']
    
    output = run_cmd("sc query type= service state= all")
    lines = output.split('\n\n')
    
    for block in lines:
        for keyword in keywords:
            if keyword.lower() in block.lower():
                print(block)
                print("-" * 40)
                break


def test_local_ports():
    """测试本地端口"""
    print("\n" + "="*60)
    print("[6] 测试本地 SLM 服务端口")
    print("="*60)
    
    import socket
    
    ports = [502, 8080, 8000, 9000, 10001, 2000, 3000, 4000, 5000, 
             8081, 8082, 8090, 5001, 5002]
    
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"  [+] 127.0.0.1:{port} 开放")
                
                # 尝试 SLM 协议
                try:
                    command = b'{"command_id": 1, "data": null}'
                    sock.sendall(command)
                    sock.settimeout(2)
                    response = sock.recv(1024)
                    if response:
                        print(f"      [!] 有响应: {response[:50]}")
                        try:
                            resp_json = json.loads(response.decode('utf-8'))
                            print(f"      [!!!] 发现 SLM 服务!")
                            print(f"      响应: {json.dumps(resp_json, indent=2)[:200]}")
                        except:
                            pass
                except:
                    pass
            sock.close()
        except:
            pass


def generate_report():
    """生成报告"""
    report = {
        'timestamp': subprocess.run(['date', '/t'], capture_output=True, text=True).stdout.strip(),
        'computer': os.environ.get('COMPUTERNAME', 'Unknown'),
        'findings': {}
    }
    
    return report


def main():
    print("="*60)
    print("SLM 设备连接诊断工具")
    print("="*60)
    print("\n此工具将检查工控机上的 SLM 设备连接方式")
    print("包括: 串口、网络服务、进程等\n")
    
    input("按回车键开始诊断...")
    
    check_com_ports()
    check_network()
    check_arp()
    check_processes()
    check_services()
    test_local_ports()
    
    print("\n" + "="*60)
    print("诊断完成")
    print("="*60)
    print("\n请查看以上输出，寻找 SLM 设备的连接线索:")
    print("  - 如果有串口，可能是通过串口连接")
    print("  - 如果有本地端口开放，可能是服务方式")
    print("  - 查看相关进程，可能有设备厂商软件在运行")
    
    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
