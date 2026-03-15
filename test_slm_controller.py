#!/usr/bin/env python3
"""
SLM 设备控制器通信测试脚本
基于《上位机监控接口JSON定义V1.2》

功能：
1. 自动探测设备连接方式（TCP/HTTP）
2. 测试 4 个核心接口
3. 记录响应数据和延迟
"""

import socket
import json
import time
import sys
from typing import Optional, Dict, Any
from datetime import datetime


class SLMControllerTester:
    """SLM 设备控制器测试客户端"""
    
    # 常见端口列表（用于自动探测）
    COMMON_PORTS = [502, 8080, 8000, 9000, 10001, 2000, 3000, 4000, 5000]
    
    def __init__(self, host: str, port: Optional[int] = None):
        self.host = host
        self.port = port
        self.socket_conn = None
        self.http_base_url = None
        self.connection_type = None  # 'tcp' or 'http'
        self.timeout = 5
        
    def _log(self, message: str, level: str = "INFO"):
        """打印日志"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        prefix = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️"}.get(level, "ℹ️")
        print(f"[{timestamp}] {prefix} {message}")
        
    def detect_port(self) -> Optional[int]:
        """自动探测设备端口"""
        self._log(f"开始探测设备 {self.host} 的开放端口...")
        
        for port in self.COMMON_PORTS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((self.host, port))
                sock.close()
                
                if result == 0:
                    self._log(f"发现开放端口: {port}", "SUCCESS")
                    return port
            except Exception as e:
                continue
                
        self._log("未找到开放端口，请手动指定", "ERROR")
        return None
        
    def test_tcp_connection(self, port: int) -> bool:
        """测试 TCP Socket 连接"""
        try:
            self.socket_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_conn.settimeout(self.timeout)
            self.socket_conn.connect((self.host, port))
            self.port = port
            self.connection_type = 'tcp'
            self._log(f"TCP 连接成功: {self.host}:{port}", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"TCP 连接失败: {e}", "ERROR")
            return False
            
    def send_tcp_command(self, command: Dict) -> Optional[Dict]:
        """通过 TCP 发送命令"""
        if not self.socket_conn:
            self._log("TCP 未连接", "ERROR")
            return None
            
        try:
            # 发送 JSON 数据
            data = json.dumps(command).encode('utf-8')
            self.socket_conn.sendall(data)
            
            # 接收响应
            response = b""
            while True:
                chunk = self.socket_conn.recv(4096)
                if not chunk:
                    break
                response += chunk
                # 简单判断 JSON 完整性
                try:
                    json.loads(response.decode('utf-8'))
                    break
                except:
                    continue
                    
            return json.loads(response.decode('utf-8'))
        except Exception as e:
            self._log(f"TCP 通信错误: {e}", "ERROR")
            return None
            
    def test_http_connection(self, port: int) -> bool:
        """测试 HTTP 连接"""
        try:
            import urllib.request
            import urllib.error
            
            url = f"http://{self.host}:{port}/"
            req = urllib.request.Request(url, method='GET')
            req.add_header('Content-Type', 'application/json')
            
            response = urllib.request.urlopen(req, timeout=self.timeout)
            self.http_base_url = f"http://{self.host}:{port}"
            self.port = port
            self.connection_type = 'http'
            self._log(f"HTTP 连接成功: {url}", "SUCCESS")
            return True
        except urllib.error.HTTPError as e:
            # 某些设备会返回 404，但说明 HTTP 服务存在
            if e.code in [404, 405]:
                self.http_base_url = f"http://{self.host}:{port}"
                self.port = port
                self.connection_type = 'http'
                self._log(f"HTTP 服务存在 (返回 {e.code}): {self.host}:{port}", "SUCCESS")
                return True
            return False
        except Exception as e:
            self._log(f"HTTP 连接失败: {e}", "WARNING")
            return False
            
    def send_http_command(self, command: Dict) -> Optional[Dict]:
        """通过 HTTP 发送命令"""
        try:
            import urllib.request
            import urllib.error
            
            url = f"{self.http_base_url}/api/command"  # 假设的端点
            data = json.dumps(command).encode('utf-8')
            
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header('Content-Type', 'application/json')
            
            response = urllib.request.urlopen(req, timeout=self.timeout)
            return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            self._log(f"HTTP 通信错误: {e}", "ERROR")
            return None
            
    def send_command(self, command: Dict) -> Optional[Dict]:
        """统一发送命令接口"""
        if self.connection_type == 'tcp':
            return self.send_tcp_command(command)
        elif self.connection_type == 'http':
            return self.send_http_command(command)
        else:
            self._log("未建立连接", "ERROR")
            return None
            
    # ==================== 接口测试 ====================
    
    def test_get_status(self) -> bool:
        """测试 1: get_status - 获取设备状态"""
        self._log("\n" + "="*60)
        self._log("测试 1: get_status (获取设备状态)")
        self._log("="*60)
        
        command = {
            "command_id": 1,
            "data": None
        }
        
        start_time = time.time()
        response = self.send_command(command)
        elapsed = (time.time() - start_time) * 1000
        
        if response:
            self._log(f"响应时间: {elapsed:.1f}ms", "SUCCESS")
            self._log(f"响应数据:\n{json.dumps(response, indent=2, ensure_ascii=False)}")
            
            # 验证数据结构
            if self._validate_status_response(response):
                self._log("数据结构验证通过", "SUCCESS")
                return True
            else:
                self._log("数据结构验证失败", "WARNING")
                return False
        else:
            self._log("未收到响应", "ERROR")
            return False
            
    def test_manu_control(self, action: int = 1) -> bool:
        """测试 2: manu - 制造控制"""
        self._log("\n" + "="*60)
        self._log(f"测试 2: manu (制造控制 - action={action})")
        self._log("="*60)
        
        action_names = {1: "Prepare(准备)", 2: "Pause(暂停)", 3: "Stop(停止)"}
        self._log(f"动作: {action_names.get(action, 'Unknown')}")
        
        command = {
            "command_id": 2,
            "data": {
                "action": action,
                "device_id": "SLM_001",
                "job_name": "test_job.slc"
            }
        }
        
        start_time = time.time()
        response = self.send_command(command)
        elapsed = (time.time() - start_time) * 1000
        
        if response:
            self._log(f"响应时间: {elapsed:.1f}ms", "SUCCESS")
            self._log(f"响应数据:\n{json.dumps(response, indent=2, ensure_ascii=False)}")
            return True
        else:
            self._log("未收到响应", "ERROR")
            return False
            
    def test_send_message(self) -> bool:
        """测试 3: send_msg - 发送消息"""
        self._log("\n" + "="*60)
        self._log("测试 3: send_msg (发送消息)")
        self._log("="*60)
        
        command = {
            "command_id": 3,
            "data": {
                "id": 1,
                "device_id": "SLM_001",
                "type": "Important",
                "content": "测试消息 - SmartAM System",
                "job_name": "test.slc"
            }
        }
        
        start_time = time.time()
        response = self.send_command(command)
        elapsed = (time.time() - start_time) * 1000
        
        if response:
            self._log(f"响应时间: {elapsed:.1f}ms", "SUCCESS")
            self._log(f"响应数据:\n{json.dumps(response, indent=2, ensure_ascii=False)}")
            return True
        else:
            self._log("未收到响应", "ERROR")
            return False
            
    def test_set_parameter(self, action: int = 1) -> bool:
        """测试 4: set_parameter - 修改参数"""
        self._log("\n" + "="*60)
        self._log(f"测试 4: set_parameter (修改参数 - action={action})")
        self._log("="*60)
        
        if action == 1:
            # 修改供粉量
            command = {
                "command_id": 4,
                "data": {
                    "action": 1,
                    "device_id": "SLM_001",
                    "powder": 1.25
                }
            }
            self._log("操作: 修改供粉量为 1.25")
        else:
            # 取消零件
            command = {
                "command_id": 4,
                "data": {
                    "action": 2,
                    "device_id": "SLM_001",
                    "cancel_parts_id": 1
                }
            }
            self._log("操作: 取消零件 ID=1")
        
        start_time = time.time()
        response = self.send_command(command)
        elapsed = (time.time() - start_time) * 1000
        
        if response:
            self._log(f"响应时间: {elapsed:.1f}ms", "SUCCESS")
            self._log(f"响应数据:\n{json.dumps(response, indent=2, ensure_ascii=False)}")
            return True
        else:
            self._log("未收到响应", "ERROR")
            return False
            
    def _validate_status_response(self, response: Dict) -> bool:
        """验证 get_status 响应数据结构"""
        required_fields = ["command_id", "code", "data"]
        data_fields = ["device_id", "priting_status", "time", "part_info", 
                      "powder", "machine_status", "alarms"]
        
        # 检查顶层字段
        for field in required_fields:
            if field not in response:
                return False
                
        # 检查 data 字段
        data = response.get("data", {})
        for field in data_fields:
            if field not in data:
                self._log(f"  缺少字段: {field}", "WARNING")
                
        return True
        
    def run_all_tests(self):
        """运行全部测试"""
        self._log("\n" + "="*60)
        self._log("开始 SLM 控制器接口测试")
        self._log("="*60)
        
        results = {
            "get_status": False,
            "manu_control": False,
            "send_message": False,
            "set_parameter": False
        }
        
        # 测试 1: 获取状态
        results["get_status"] = self.test_get_status()
        time.sleep(1)
        
        # 测试 2: 制造控制（仅测试 Prepare，不实际暂停/停止）
        # results["manu_control"] = self.test_manu_control(action=1)
        # time.sleep(1)
        
        # 测试 3: 发送消息
        # results["send_message"] = self.test_send_message()
        # time.sleep(1)
        
        # 测试 4: 修改参数
        # results["set_parameter"] = self.test_set_parameter(action=1)
        
        # 打印总结
        self._log("\n" + "="*60)
        self._log("测试总结")
        self._log("="*60)
        for test_name, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            self._log(f"{test_name}: {status}")
            
        return results


def interactive_test():
    """交互式测试"""
    print("="*60)
    print("SLM 设备控制器通信测试工具")
    print("="*60)
    print()
    
    # 获取设备 IP
    host = input("请输入 SLM 设备 IP 地址 (如 192.168.1.100): ").strip()
    if not host:
        print("❌ 必须输入 IP 地址")
        return
        
    # 获取端口（可选）
    port_input = input("请输入端口号 (直接回车自动探测): ").strip()
    port = int(port_input) if port_input else None
    
    # 创建测试器
    tester = SLMControllerTester(host, port)
    
    # 如果没有指定端口，自动探测
    if port is None:
        detected_port = tester.detect_port()
        if detected_port:
            port = detected_port
        else:
            print("❌ 无法自动探测端口，请手动指定")
            return
            
    # 尝试连接
    print(f"\n尝试连接到 {host}:{port}...")
    
    # 先尝试 TCP
    if tester.test_tcp_connection(port):
        pass
    # 再尝试 HTTP
    elif tester.test_http_connection(port):
        pass
    else:
        print("❌ 无法建立连接，请检查:")
        print("   1. 设备是否开机")
        print("   2. 网线是否连接")
        print("   3. IP 地址是否正确")
        print("   4. 防火墙是否阻止连接")
        return
        
    # 运行测试
    print(f"\n使用 {tester.connection_type.upper()} 模式进行测试\n")
    
    # 菜单
    while True:
        print("\n" + "="*60)
        print("测试菜单:")
        print("  1. 获取设备状态 (get_status)")
        print("  2. 制造控制 - 准备 (manu/prepare)")
        print("  3. 制造控制 - 暂停 (manu/pause)")
        print("  4. 制造控制 - 停止 (manu/stop)")
        print("  5. 发送消息 (send_msg)")
        print("  6. 修改供粉量 (set_parameter/powder)")
        print("  7. 取消零件 (set_parameter/cancel)")
        print("  8. 运行全部测试")
        print("  0. 退出")
        print("="*60)
        
        choice = input("请选择: ").strip()
        
        if choice == "1":
            tester.test_get_status()
        elif choice == "2":
            tester.test_manu_control(action=1)
        elif choice == "3":
            confirm = input("⚠️ 确认要暂停打印吗? (yes/no): ")
            if confirm.lower() == "yes":
                tester.test_manu_control(action=2)
        elif choice == "4":
            confirm = input("⚠️ 确认要停止打印吗? (yes/no): ")
            if confirm.lower() == "yes":
                tester.test_manu_control(action=3)
        elif choice == "5":
            tester.test_send_message()
        elif choice == "6":
            tester.test_set_parameter(action=1)
        elif choice == "7":
            tester.test_set_parameter(action=2)
        elif choice == "8":
            tester.run_all_tests()
        elif choice == "0":
            break
        else:
            print("无效选择")
            
    # 关闭连接
    if tester.socket_conn:
        tester.socket_conn.close()
    print("\n测试结束")


if __name__ == "__main__":
    interactive_test()
