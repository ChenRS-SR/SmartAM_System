#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✅ 完整的M114坐标提取解决方案
通过实时监听OctoPrint的serial.log来获取M114响应

工作原理：
1. 发送M114命令通过REST API
2. 立即开始监听serial.log文件的新增内容
3. 检测到M114响应后提取坐标
4. 返回X,Y,Z坐标值
"""

import os
import re
import time
import requests
import json
import weakref
import atexit
from threading import Thread, Lock
from datetime import datetime

# 全局活跃实例跟踪（用于程序退出时强制停止）
_active_coordinators = weakref.WeakSet()

def _stop_all_coordinators():
    """程序退出时停止所有活跃的 coordinator"""
    for coord in list(_active_coordinators):
        try:
            coord.stop()
        except:
            pass

# 注册退出处理
atexit.register(_stop_all_coordinators)

OCTOPRINT_URL = "http://127.0.0.1:5000"
API_KEY = "UGjrS2T5n_48GF0YsWADx1EoTILjwn7ZkeWUfgGvW2Q"

class M114Coordinator:
    """通过serial.log获取打印机坐标"""
    
    def __init__(self):
        self.log_file = os.path.expanduser("~/AppData/Roaming/OctoPrint/logs/serial.log")
        self.coordinates = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        self.lock = Lock()
        self.last_position = 0  # 日志文件上次读到的位置
        self._stopped = False   # 停止标志
        
        # 注册到全局跟踪
        _active_coordinators.add(self)
        
        # 初始化日志位置
        if os.path.exists(self.log_file):
            self.last_position = os.path.getsize(self.log_file)
            print("[M114] Serial log found at: {}".format(self.log_file))
            print("[M114] Log file size: {} bytes".format(self.last_position))
        else:
            print("[M114ERROR] Serial log file NOT found!")
            print("[M114ERROR] Expected path: {}".format(self.log_file))
            print("[M114WARNING] Coordinates may not be available")
    
    def stop(self):
        """停止等待响应"""
        self._stopped = True
        print("[M114] Coordinator stopped")
    
    def send_m114(self, caller="unknown", verbose=True):
        """发送M114命令到打印机"""
        # 如果已停止，拒绝发送
        if self._stopped:
            if verbose:
                print("[M114] Rejected (stopped) from {}".format(caller))
            return False
        
        headers = {"X-Api-Key": API_KEY}
        try:
            if verbose:
                print("[M114] Sending from {}...".format(caller))
            resp = requests.post(
                f"{OCTOPRINT_URL}/api/printer/command",
                headers=headers,
                json={"command": "M114"},
                timeout=5
            )
            # 只在失败时输出
            if resp.status_code != 204:
                print("[M114] Send failed (status: {})".format(resp.status_code))
                return False
            return True
        except Exception as e:
            print("[M114] Send failed: {}".format(e))
            return False
    
    def wait_for_m114_response(self, timeout=5, caller="unknown", verbose=True):
        """
        发送M114后，等待并解析响应
        
        Args:
            timeout: 超时时间
            caller: 调用者标识
            verbose: 是否打印详细日志
        """
        # 如果已停止，不发送新命令
        if self._stopped:
            if verbose:
                print("[M114] Request rejected (stopped) from {}".format(caller))
            return None
        
        # 检查日志文件是否存在
        if not os.path.exists(self.log_file):
            if verbose:
                print("[M114] Serial.log not found")
            return None
        
        # 发送命令前记录文件位置
        pre_send_position = os.path.getsize(self.log_file)
        
        # 发送命令
        if not self.send_m114(caller=caller, verbose=verbose):
            return None
        
        # 监听日志
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 检查是否已停止
            if self._stopped:
                return None
            
            try:
                current_size = os.path.getsize(self.log_file)
                
                # 检查文件是否有新增内容（从发送命令前的位置开始读取）
                if current_size > pre_send_position:
                    with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        # 从发送命令前的位置开始读取
                        f.seek(pre_send_position)
                        new_content = f.read()
                        # 更新最后读取位置
                        self.last_position = f.tell()
                    
                    # 在新内容中查找M114响应（直接查找Recv行，不找Send行）
                    lines = new_content.split('\n')
                    for line in lines:
                        # 查找包含 X: Y: Z: 的 Recv 行
                        if 'Recv:' in line and 'X:' in line and 'Y:' in line and 'Z:' in line:
                            coords = self.extract_coordinates(line)
                            if coords:
                                if verbose:
                                    print("[M114] Got response: X={:.2f}, Y={:.2f}, Z={:.2f}".format(
                                        coords['X'], coords['Y'], coords['Z']))
                                with self.lock:
                                    self.coordinates = coords
                                return coords
                
                time.sleep(0.05)
                
            except Exception as e:
                if verbose:
                    print("[M114] Error reading log: {}".format(e))
                time.sleep(0.1)
        
        # 超时
        if verbose:
            print("[M114] Timeout after {}s (file size: {}->{})".format(
                timeout, pre_send_position, os.path.getsize(self.log_file)))
        return None
    
    def extract_coordinates(self, line):
        """
        从serial.log行提取X,Y,Z坐标
        格式: "2026-01-22 19:43:04,921 - Recv: X:117.49 Y:107.44 Z:7.20 E:566.01 Count X:9400 Y:9301 Z:1025"
        """
        try:
            # 使用正则表达式提取坐标（支持负数）
            match = re.search(r'X:([-\d.]+)\s+Y:([-\d.]+)\s+Z:([-\d.]+)', line)
            if match:
                x, y, z = match.groups()
                return {
                    "X": float(x),
                    "Y": float(y),
                    "Z": float(z)
                }
        except Exception as e:
            pass
        
        return None
    
    def get_current_coordinates(self):
        """获取最后一次读取的坐标"""
        with self.lock:
            return dict(self.coordinates)
    
    def get_m851_z_offset(self, timeout=3, verbose=True):
        """
        发送 M851 获取当前 Z Probe Offset
        返回: float 类型的 Z offset 值（如 -2.55）
        """
        if self._stopped:
            return None
        
        # 检查缓存（5秒内有效）
        if hasattr(self, '_m851_cache_value') and hasattr(self, '_m851_cache_time'):
            if time.time() - self._m851_cache_time < 5.0:
                if verbose:
                    print("[M851] Using cached value: {:.2f}".format(self._m851_cache_value))
                return self._m851_cache_value
        
        # 发送 M851 命令
        headers = {"X-Api-Key": API_KEY}
        try:
            resp = requests.post(
                f"{OCTOPRINT_URL}/api/printer/command",
                headers=headers,
                json={"command": "M851"},
                timeout=5
            )
            if resp.status_code != 204:
                if verbose:
                    print("[M851] Send failed (status: {})".format(resp.status_code))
                return None
        except Exception as e:
            if verbose:
                print("[M851] Send failed: {}".format(e))
            return None
        
        # 监听日志获取响应
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._stopped:
                return None
            try:
                current_size = os.path.getsize(self.log_file)
                if current_size > self.last_position:
                    with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_position)
                        new_content = f.read()
                        self.last_position = f.tell()
                    
                    # 查找 M851 响应: "Recv: Probe Offset X-31.80 Y-40.50 Z-2.55"
                    lines = new_content.split('\n')
                    for line in lines:
                        if 'Probe Offset' in line and 'Z' in line:
                            match = re.search(r'Z([-\d.]+)', line)
                            if match:
                                z_offset = float(match.group(1))
                                # 缓存结果
                                self._m851_cache_value = z_offset
                                self._m851_cache_time = time.time()
                                if verbose:
                                    print("[M851] Current Z offset: {:.2f}".format(z_offset))
                                return z_offset
                
                time.sleep(0.05)
            except Exception as e:
                time.sleep(0.1)
        
        if verbose:
            print("[M851] Timeout waiting for response")
        return None
    
    def set_z_offset_relative(self, delta, timeout=3, verbose=True, current=None):
        """
        使用 M290 相对调整 Z offset
        
        Args:
            delta: 调整量（如 +0.25 表示抬高 0.25mm）
            timeout: 超时时间
            verbose: 是否打印详细日志
            current: 当前Z offset值（如果已知道，避免重复查询）
        
        Returns:
            调整后的新 Z offset 值，失败返回 None
        """
        if self._stopped:
            return None
        
        # 如果没有提供当前值，则查询
        if current is None:
            current = self.get_m851_z_offset(timeout=timeout, verbose=verbose)
            if current is None:
                return None
        
        # 发送 M290 Z{delta}
        headers = {"X-Api-Key": API_KEY}
        try:
            if verbose:
                print("[M290] Sending M290 Z{:.2f} (delta={:+.2f})...".format(delta, delta))
            resp = requests.post(
                f"{OCTOPRINT_URL}/api/printer/command",
                headers=headers,
                json={"command": "M290 Z{:.2f}".format(delta)},
                timeout=5
            )
            if resp.status_code != 204:
                if verbose:
                    print("[M290] Send failed (status: {})".format(resp.status_code))
                return None
            if verbose:
                print("[M290] Command sent successfully")
        except Exception as e:
            if verbose:
                print("[M290] Send failed: {}".format(e))
            return None
        
        # 等待并验证新值
        time.sleep(0.5)  # 给打印机一点时间应用
        new_offset = self.get_m851_z_offset(timeout=timeout, verbose=verbose)
        if new_offset is not None:
            if verbose:
                print("[M290] Z offset changed: {:.2f} -> {:.2f}".format(current, new_offset))
            return new_offset
        
        return None

def continuous_coordinate_monitoring():
    """
    持续监控坐标（每1.5秒获取一次）
    """
    print("=" * 70)
    print("Continuous coordinate monitoring (every 1.5 sec)")
    print("=" * 70)
    
    coord = M114Coordinator()
    
    try:
        for i in range(20):  # 采集20次
            print("\n[Collection #{}]".format(i+1))
            coords = coord.wait_for_m114_response(timeout=3)
            
            if coords:
                print("X: {:.2f} mm".format(coords['X']))
                print("Y: {:.2f} mm".format(coords['Y']))
                print("Z: {:.2f} mm".format(coords['Z']))
            else:
                print("Failed to get coordinates")
            
            # 等待一下再采集
            if i < 19:
                time.sleep(1.5)
    
    except KeyboardInterrupt:
        print("\n\nStopped")

def single_coordinate_test():
    """
    单次坐标获取测试
    """
    print("=" * 70)
    print("Single M114 coordinate test")
    print("=" * 70)
    
    coord = M114Coordinator()
    coords = coord.wait_for_m114_response(timeout=5)
    
    if coords:
        print("\nSuccess!")
        print("X = {}".format(coords['X']))
        print("Y = {}".format(coords['Y']))
        print("Z = {}".format(coords['Z']))
    else:
        print("\nFailed")

if __name__ == "__main__":
    print("\nOctoPrint M114 Coordinate Acquisition System\n")
    
    # 测试单次
    single_coordinate_test()
    
    # 如果需要连续监控，取消注释下一行
    # continuous_coordinate_monitoring()


# ȫ��Э����ʵ��
_coordinator_instance = None


# 全局协调器实例
_coordinator_instance = None

def get_coordinator():
    global _coordinator_instance
    if _coordinator_instance is None:
        _coordinator_instance = M114Coordinator()
    return _coordinator_instance

def reset_coordinator():
    global _coordinator_instance
    if _coordinator_instance:
        _coordinator_instance.stop()
        _coordinator_instance = None

