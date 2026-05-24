@echo off
chcp 65001 >nul
title SmartAM SLM 设备检测工具
echo ========================================
echo   SLM 设备检测与配置工具
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] 检测COM口设备...
echo ========================================
python -c "
import serial.tools.list_ports
ports = list(serial.tools.list_ports.comports())
print(f'发现 {len(ports)} 个串口设备:\n')
for i, port in enumerate(ports, 1):
    print(f'{i}. {port.device}')
    print(f'   描述: {port.description}')
    print(f'   硬件ID: {port.hwid}')
    print()
if not ports:
    print('警告: 未检测到任何COM口设备')
    print('请检查振动传感器是否正确连接')
"
echo.

echo [2/4] 检测摄像头设备...
echo ========================================
python -c "
import cv2
print('正在扫描摄像头设备...\n')
available_cameras = []
for i in range(10):
    try:
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                available_cameras.append((i, w, h))
                print(f'✓ 摄像头 {i}: {w}x{h}')
        cap.release()
    except Exception as e:
        pass

if not available_cameras:
    print('✗ 未检测到可用摄像头')
else:
    print(f'\n共发现 {len(available_cameras)} 个摄像头')
    print('\n建议配置:')
    if len(available_cameras) >= 2:
        print(f'  CH1 (主摄): 摄像头 {available_cameras[0][0]}')
        print(f'  CH2 (副摄): 摄像头 {available_cameras[1][0]}')
    elif len(available_cameras) == 1:
        print(f'  CH1 (主摄): 摄像头 {available_cameras[0][0]}')
        print('  CH2: 无可用摄像头')
"
echo.

echo [3/4] 检查红外热像仪SDK...
echo ========================================
python -c "
import os
sdk_path = r'D:\SLM\OPT-PIX-Connect-Rel.-3.24.3127.0\OPT PIX Connect Rel. 3.24.3127.0\SDK\Connect SDK\Lib\v120'
dll_path = os.path.join(sdk_path, 'ImagerIPC2x64.dll')

if os.path.exists(dll_path):
    print('✓ 红外热像仪SDK已找到')
    print(f'  路径: {sdk_path}')
else:
    print('✗ 红外热像仪SDK未找到')
    print('  请确保已安装PIX Connect软件')
    print('  预期路径:', sdk_path)
"
echo.

echo [4/4] 检查SLM数据采集模块...
echo ========================================
python -c "
import os
slm_path = r'D:\FDM_Monitor_Diagnosis\SLM数据采集'
if os.path.exists(slm_path):
    print(f'✓ SLM数据采集目录存在')
    files = os.listdir(slm_path)
    py_files = [f for f in files if f.endswith('.py')]
    print(f'  发现 {len(py_files)} 个Python文件')
    if 'VB02_SLM_9月9日稳定版.py' in files:
        print('  ✓ 找到主采集程序')
    if 'device_model.py' in files:
        print('  ✓ 找到设备模型模块')
else:
    print(f'✗ SLM数据采集目录不存在: {slm_path}')
"
echo.

echo ========================================
echo   检测完成
echo ========================================
echo.
echo 推荐配置:
echo   1. 振动传感器COM口: 根据上方检测结果选择
echo   2. CH1摄像头: 通常是索引2或0
echo   3. CH2摄像头: 通常是索引3或1
echo   4. 红外热像仪: 确保PIX Connect软件已启动
echo.
echo 提示:
echo   - 如果设备未检测到，请检查USB连接
echo   - 首次使用前请确保已安装所有驱动
echo   - 可以在仪表盘页面的"设置"中修改配置
echo.
pause
