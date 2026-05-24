@echo off
chcp 65001 >nul
title SLM 硬件连接诊断工具
echo ========================================
echo   SLM 硬件连接诊断工具
echo ========================================
echo.

cd /d "%~dp0"

echo [1/5] 检查系统摄像头设备...
echo ========================================
echo.
python -c "
import cv2
print('扫描摄像头设备 (0-9)...')
print()
found = []
for i in range(10):
    try:
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                found.append((i, w, h))
                print(f'✓ 摄像头索引 {i}: {w}x{h} (可用)')
        cap.release()
    except Exception as e:
        pass

print()
if not found:
    print('✗ 未检测到可用摄像头')
    print('  可能原因:')
    print('  1. 摄像头未插入USB')
    print('  2. 摄像头驱动未安装')
    print('  3. 摄像头被其他程序占用')
else:
    print(f'共发现 {len(found)} 个可用摄像头')
    print()
    print('建议配置:')
    if len(found) >= 2:
        print(f'  CH1主摄: 索引 {found[0][0]} ({found[0][1]}x{found[0][2]})')
        print(f'  CH2副摄: 索引 {found[1][0]} ({found[1][1]}x{found[1][2]})')
    elif len(found) == 1:
        print(f'  CH1主摄: 索引 {found[0][0]} ({found[0][1]}x{found[0][2]})')
        print('  CH2副摄: 无')
"
echo.

echo [2/5] 检查串口设备...
echo ========================================
echo.
python -c "
try:
    import serial.tools.list_ports
    ports = list(serial.tools.list_ports.comports())
    print(f'发现 {len(ports)} 个串口设备:')
    print()
    ch340_found = False
    for port in ports:
        print(f'  {port.device}: {port.description}')
        if 'CH340' in port.description or 'USB-SERIAL' in port.description:
            ch340_found = True
            print(f'    ↑ 这很可能是振动传感器')
    
    if not ch340_found:
        print()
        print('✗ 未检测到CH340设备（振动传感器）')
        print('  可能原因:')
        print('  1. 传感器未插入USB')
        print('  2. 驱动未安装（需要CH340驱动）')
        print('  3. USB线损坏')
except Exception as e:
    print(f'检查串口失败: {e}')
"
echo.

echo [3/5] 检查红外热像仪SDK...
echo ========================================
echo.
python -c "
import os
sdk_path = r'D:\SLM\OPT-PIX-Connect-Rel.-3.24.3127.0\OPT PIX Connect Rel. 3.24.3127.0\SDK\Connect SDK\Lib\v120'
dll_path = os.path.join(sdk_path, 'ImagerIPC2x64.dll')

if os.path.exists(dll_path):
    print('✓ 红外热像仪SDK已找到')
    print(f'  路径: {sdk_path}')
    print()
    print('提示: 请确保已启动PIX Connect软件')
else:
    print('✗ 红外热像仪SDK未找到')
    print('  预期路径:', sdk_path)
    print()
    print('请安装PIX Connect软件')
"
echo.

echo [4/5] 测试摄像头实时连接...
echo ========================================
echo.
python -c "
import cv2
import time

print('尝试连接摄像头索引 0 和 1...')
print()

for idx in [0, 1]:
    try:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            # 尝试读取几帧
            success_count = 0
            for _ in range(5):
                ret, frame = cap.read()
                if ret and frame is not None:
                    success_count += 1
                time.sleep(0.1)
            
            if success_count >= 3:
                h, w = frame.shape[:2]
                print(f'✓ 摄像头 {idx}: 连接正常，可稳定读取 ({w}x{h})')
            else:
                print(f'△ 摄像头 {idx}: 连接不稳定，部分帧读取失败')
        else:
            print(f'✗ 摄像头 {idx}: 无法打开')
        cap.release()
    except Exception as e:
        print(f'✗ 摄像头 {idx}: 错误 - {e}')
"
echo.

echo [5/5] 生成配置建议...
echo ========================================
echo.
echo 根据检测结果，建议如下配置:
echo.
echo 1. 打开前端页面 http://localhost:5173
echo 2. 进入 SLM 仪表盘
echo 3. 点击"设置"按钮
echo 4. 根据上述检测结果设置:
echo    - CH1摄像头索引: [检测到的第一个索引]
echo    - CH2摄像头索引: [检测到的第二个索引]
echo    - 振动传感器COM口: [CH340对应的COM口]
echo 5. 确保"模拟模式"为关闭状态
echo 6. 点击"开始采集"
echo.
echo 如果硬件检测不到，请:
echo - 重新插拔USB设备
echo - 检查设备管理器中的驱动状态
echo - 暂时使用"模拟模式"测试界面功能
echo.
pause
