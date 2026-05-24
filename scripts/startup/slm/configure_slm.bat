@echo off
chcp 65001 >nul
title SmartAM SLM 配置工具
echo ========================================
echo   SLM 系统配置工具
echo ========================================
echo.

cd /d "%~dp0"

:: 默认配置
set CH1_INDEX=2
set CH2_INDEX=3
set VIB_COM=COM5
set USE_MOCK=false

:MENU
echo 当前配置:
echo   CH1摄像头索引: %CH1_INDEX%
echo   CH2摄像头索引: %CH2_INDEX%
echo   振动传感器COM口: %VIB_COM%
echo   模拟模式: %USE_MOCK%
echo.
echo 请选择操作:
echo   1. 设置CH1摄像头索引
echo   2. 设置CH2摄像头索引
echo   3. 设置振动传感器COM口
echo   4. 切换模拟模式 (当前: %USE_MOCK%)
echo   5. 运行设备检测
echo   6. 启动SLM仪表盘
echo   0. 退出
echo.
set /p choice="请输入选项 (0-6): "

if "%choice%"=="1" goto SET_CH1
if "%choice%"=="2" goto SET_CH2
if "%choice%"=="3" goto SET_COM
if "%choice%"=="4" goto TOGGLE_MOCK
if "%choice%"=="5" goto CHECK_DEVICES
if "%choice%"=="6" goto START_DASHBOARD
if "%choice%"=="0" goto EXIT
goto MENU

:SET_CH1
echo.
set /p CH1_INDEX="请输入CH1摄像头索引 (0-9): "
echo 已设置CH1摄像头索引为: %CH1_INDEX%
echo.
goto MENU

:SET_CH2
echo.
set /p CH2_INDEX="请输入CH2摄像头索引 (0-9): "
echo 已设置CH2摄像头索引为: %CH2_INDEX%
echo.
goto MENU

:SET_COM
echo.
echo 可用COM口:
python -c "import serial.tools.list_ports; [print(f'  {p.device} - {p.description}') for p in serial.tools.list_ports.comports()]"
echo.
set /p VIB_COM="请输入振动传感器COM口 (如COM5): "
echo 已设置振动传感器COM口为: %VIB_COM%
echo.
goto MENU

:TOGGLE_MOCK
if "%USE_MOCK%"=="false" (
    set USE_MOCK=true
    echo 已切换到: 模拟模式 (无需硬件)
) else (
    set USE_MOCK=false
    echo 已切换到: 真实硬件模式
)
echo.
goto MENU

:CHECK_DEVICES
call check_slm_devices.bat
goto MENU

:START_DASHBOARD
echo.
echo ========================================
echo 使用以下配置启动SLM仪表盘:
echo   CH1摄像头索引: %CH1_INDEX%
echo   CH2摄像头索引: %CH2_INDEX%
echo   振动传感器COM口: %VIB_COM%
echo   模拟模式: %USE_MOCK%
echo ========================================
echo.
echo 正在启动...
timeout /t 2 >nul

:: 创建临时启动脚本
echo @echo off > temp_start_slm.bat
echo chcp 65001 ^>nul >> temp_start_slm.bat
echo cd /d "%~dp0" >> temp_start_slm.bat
echo set CH1_INDEX=%CH1_INDEX% >> temp_start_slm.bat
echo set CH2_INDEX=%CH2_INDEX% >> temp_start_slm.bat
echo set VIB_COM=%VIB_COM% >> temp_start_slm.bat
echo set USE_MOCK=%USE_MOCK% >> temp_start_slm.bat
echo call start_slm_dashboard.bat >> temp_start_slm.bat
echo del "%%~f0" >> temp_start_slm.bat

start cmd /c temp_start_slm.bat
goto EXIT

:EXIT
echo.
echo 感谢使用!
timeout /t 1 >nul
exit
