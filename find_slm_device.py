#!/usr/bin/env python3
"""
自动扫描局域网内的 SLM 设备
"""

import socket
import json
import subprocess
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def get_local_network():
    """获取本机 IP 和网段"""
    try:
        # 创建 UDP 连接来获取本机 IP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        
        # 提取网段 (如 192.168.1.x -> 192.168.1)
        ip_parts = local_ip.split('.')
        network = '.'.join(ip_parts[:3])
        
        return local_ip, network
    except Exception as e:
        print(f"[-] 获取本机 IP 失败: {e}")
        return None, None


def ping_host(ip):
    """Ping 主机检查是否在线"""
    try:
        # Windows 使用 -n, Linux/Mac 使用 -c
        result = subprocess.run(
            ['ping', '-n', '1', '-w', '500', ip],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        return False


def test_slm_port(ip, port):
    """测试端口是否开放并尝试 SLM 协议通信"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, port))
        
        if result != 0:
            sock.close()
            return None
            
        # 端口开放，尝试 SLM 协议
        command = {"command_id": 1, "data": None}
        data = json.dumps(command).encode('utf-8')
        
        sock.settimeout(3)
        sock.sendall(data)
        
        # 接收响应
        response = b""
        sock.settimeout(5)
        
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                
                # 尝试解析
                try:
                    resp_json = json.loads(response.decode('utf-8'))
                    sock.close()
                    return {
                        'ip': ip,
                        'port': port,
                        'type': 'SLM_DEVICE',
                        'response': resp_json
                    }
                except:
                    continue
        except socket.timeout:
            pass
            
        sock.close()
        
        # 端口开放但不是 SLM 协议
        if response:
            return {
                'ip': ip,
                'port': port,
                'type': 'UNKNOWN',
                'raw_response': response[:100]
            }
        else:
            return {
                'ip': ip,
                'port': port,
                'type': 'OPEN_PORT',
                'raw_response': None
            }
            
    except Exception as e:
        return None


def scan_ip_range(network, start=1, end=254):
    """扫描 IP 段"""
    print(f"[*] 扫描网段 {network}.0/24...")
    print(f"[*] 范围: {network}.{start} - {network}.{end}")
    
    # 先快速 ping 扫描找出在线主机
    print("\n[1/3] 快速发现在线主机...")
    online_hosts = []
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(ping_host, f"{network}.{i}"): i 
                  for i in range(start, end+1)}
        
        for future in as_completed(futures):
            i = futures[future]
            if future.result():
                ip = f"{network}.{i}"
                online_hosts.append(ip)
                print(f"  [+] 发现在线主机: {ip}")
                
    print(f"\n[*] 发现 {len(online_hosts)} 个在线主机")
    
    if not online_hosts:
        print("[-] 未发现在线主机，请检查:")
        print("    1. 网线是否插好")
        print("    2. 设备是否开机")
        print("    3. 电脑和设备是否在同一网段")
        return []
        
    # 扫描常见端口
    print("\n[2/3] 扫描开放端口...")
    common_ports = [502, 8080, 8000, 9000, 10001, 2000, 3000, 4000, 5000, 
                   80, 443, 22, 23, 445, 139, 135]
    
    open_ports = []
    
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = []
        for ip in online_hosts:
            for port in common_ports:
                futures.append(executor.submit(test_slm_port, ip, port))
                
        for future in as_completed(futures):
            result = future.result()
            if result:
                open_ports.append(result)
                if result['type'] == 'SLM_DEVICE':
                    print(f"  [!!!] 发现 SLM 设备: {result['ip']}:{result['port']}")
                elif result['type'] == 'UNKNOWN' and result.get('raw_response'):
                    print(f"  [?] {result['ip']}:{result['port']} 有响应但非 SLM 协议")
                else:
                    print(f"  [+] {result['ip']}:{result['port']} 端口开放")
                    
    return open_ports


def arp_scan():
    """使用 ARP 表查找设备"""
    print("\n[3/3] 检查 ARP 表...")
    try:
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
        arp_output = result.stdout
        
        # 解析 ARP 表
        ip_pattern = r'(\d+\.\d+\.\d+\.\d+)\s+([\w-]+)'
        matches = re.findall(ip_pattern, arp_output)
        
        devices = []
        for ip, mac in matches:
            if mac != 'ff-ff-ff-ff-ff-ff':  # 跳过广播地址
                devices.append({'ip': ip, 'mac': mac})
                
        return devices
    except Exception as e:
        print(f"[-] ARP 扫描失败: {e}")
        return []


def interactive_test_device(ip, port):
    """交互式测试设备"""
    print(f"\n{'='*60}")
    print(f"开始测试 SLM 设备: {ip}:{port}")
    print(f"{'='*60}")
    
    while True:
        print("\n测试选项:")
        print("  1. 获取设备状态 (get_status)")
        print("  2. 发送测试消息 (send_msg)")
        print("  3. 获取设备信息 (get_status + 解析)")
        print("  0. 返回")
        
        choice = input("\n选择: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            test_command(ip, port, {"command_id": 1, "data": None})
        elif choice == "2":
            test_command(ip, port, {
                "command_id": 3,
                "data": {
                    "id": 1,
                    "device_id": "SLM_001",
                    "type": "Normal",
                    "content": "测试消息",
                    "job_name": "test.slc"
                }
            })
        elif choice == "3":
            get_device_info(ip, port)


def test_command(ip, port, command):
    """发送测试命令"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, port))
        
        data = json.dumps(command).encode('utf-8')
        print(f"[*] 发送: {data.decode()}")
        
        sock.sendall(data)
        
        response = b""
        sock.settimeout(10)
        
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                
                try:
                    resp_json = json.loads(response.decode('utf-8'))
                    print(f"[+] 响应:")
                    print(json.dumps(resp_json, indent=2, ensure_ascii=False))
                    sock.close()
                    return resp_json
                except:
                    continue
        except socket.timeout:
            print("[-] 接收超时")
            
        if response:
            print(f"[*] 原始响应: {response}")
        else:
            print("[-] 无响应")
            
        sock.close()
        
    except Exception as e:
        print(f"[-] 错误: {e}")


def get_device_info(ip, port):
    """获取并解析设备信息"""
    resp = test_command(ip, port, {"command_id": 1, "data": None})
    
    if not resp or 'data' not in resp:
        return
        
    data = resp['data']
    
    print(f"\n{'='*60}")
    print("设备信息解析:")
    print(f"{'='*60}")
    
    # 基本信息
    print(f"设备 ID: {data.get('device_id', 'N/A')}")
    print(f"打印状态: {data.get('priting_status', 'N/A')}")
    
    # 时间信息
    time_info = data.get('time', {})
    if time_info:
        print(f"\n[时间信息]")
        print(f"  开始时间: {time_info.get('start_time', 'N/A')}")
        print(f"  已运行: {time_info.get('elapsed_seconds', 'N/A')}")
        print(f"  剩余: {time_info.get('remaining_seconds', 'N/A')}")
        
    # 零件信息
    part_info = data.get('part_info', {})
    jobs = part_info.get('jobs', [])
    if jobs:
        print(f"\n[零件信息]")
        for job in jobs:
            print(f"  名称: {job.get('name', 'N/A')}")
            print(f"  层数: {job.get('current_layer', 0)}/{job.get('layer_count', 0)}")
            print(f"  状态: {'已取消' if job.get('is_canceled') else '正常'}")
            
    # 粉量信息
    powder = data.get('powder', {})
    if powder:
        print(f"\n[粉量信息]")
        print(f"  剩余: {powder.get('remaining_powder', 0)} L")
        print(f"  状态: {powder.get('status', 'N/A')}")
        print(f"  供粉量: {powder.get('powder_supply_amount', 0)} L")
        
    # 设备状态
    machine = data.get('machine_status', {})
    if machine:
        print(f"\n[设备状态]")
        print(f"  风速: {machine.get('wind_speed', 0)} m/s")
        print(f"  温度: {machine.get('temperature', 0)} °C")
        print(f"  氧含量: {machine.get('oxygen_content', 0)} %")
        print(f"  压力: {machine.get('pressure', 0)} kPa")
        
    # 报警信息
    alarms = data.get('alarms', [])
    if alarms:
        print(f"\n[报警信息]")
        for alarm in alarms:
            print(f"  [{alarm.get('level', 'N/A')}] {alarm.get('message', 'N/A')}")


def main():
    print("="*60)
    print("SLM 设备自动发现工具")
    print("="*60)
    
    # 获取本机网络信息
    local_ip, network = get_local_network()
    
    if not local_ip:
        print("[-] 无法获取本机网络信息")
        print("[*] 请手动输入网段 (如 192.168.1)")
        network = input("网段: ").strip()
        if not network:
            print("[-] 必须输入网段")
            return
    else:
        print(f"[*] 本机 IP: {local_ip}")
        print(f"[*] 网段: {network}")
        
    # 确认扫描范围
    print(f"\n准备扫描网段 {network}.0/24")
    confirm = input("开始扫描? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("取消扫描")
        return
        
    # 开始扫描
    results = scan_ip_range(network)
    
    # 显示结果
    print(f"\n{'='*60}")
    print("扫描结果")
    print(f"{'='*60}")
    
    slm_devices = [r for r in results if r['type'] == 'SLM_DEVICE']
    
    if slm_devices:
        print(f"\n[+] 发现 {len(slm_devices)} 个 SLM 设备:")
        for i, dev in enumerate(slm_devices, 1):
            print(f"\n  设备 {i}:")
            print(f"    IP: {dev['ip']}")
            print(f"    端口: {dev['port']}")
            print(f"    响应: {json.dumps(dev['response'], indent=2, ensure_ascii=False)[:200]}...")
            
        # 选择设备进行测试
        if len(slm_devices) == 1:
            dev = slm_devices[0]
            test = input(f"\n是否测试设备 {dev['ip']}:{dev['port']}? (yes/no): ").strip().lower()
            if test == 'yes':
                interactive_test_device(dev['ip'], dev['port'])
        else:
            idx = input(f"\n选择要测试的设备编号 (1-{len(slm_devices)}): ").strip()
            try:
                dev = slm_devices[int(idx)-1]
                interactive_test_device(dev['ip'], dev['port'])
            except:
                print("[-] 无效选择")
    else:
        print("[-] 未发现 SLM 设备")
        
        # 显示其他开放端口
        other_ports = [r for r in results if r['type'] != 'SLM_DEVICE']
        if other_ports:
            print(f"\n[*] 但发现 {len(other_ports)} 个其他开放端口:")
            for r in other_ports[:10]:
                print(f"    {r['ip']}:{r['port']} ({r['type']})")
                
        print("\n[*] 建议:")
        print("    1. 确认设备已开机并进入就绪状态")
        print("    2. 检查网线连接")
        print("    3. 尝试重启设备网络模块")
        print("    4. 联系设备供应商获取默认 IP")


if __name__ == "__main__":
    main()
