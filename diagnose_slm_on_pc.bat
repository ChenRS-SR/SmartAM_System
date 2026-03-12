@echo off
chcp 65001 >nul
echo ==========================================
echo SLM 设备连接诊断脚本
echo 请在工控机上运行此脚本
echo ==========================================
echo.

echo [1] 网络配置信息
echo ------------------------------------------
ipconfig /all > network_info.txt
type network_info.txt
echo.

echo [2] 串口列表
echo ------------------------------------------
mode > com_ports.txt 2>nul
type com_ports.txt
echo.

echo [3] 设备管理器中的串口
echo ------------------------------------------
wmic path Win32_SerialPort get DeviceID,Description,Name 2>nul
echo.

echo [4] 所有网络连接
echo ------------------------------------------
netstat -an > netstat.txt
type netstat.txt | findstr "LISTENING"
echo.

echo [5] ARP 表（已连接设备）
echo ------------------------------------------
arp -a > arp_table.txt
type arp_table.txt
echo.

echo [6] 查找可能的 SLM 相关进程
echo ------------------------------------------
tasklist | findstr /i "slm print laser"
echo.

echo ==========================================
echo 诊断信息已保存到以下文件:
echo   - network_info.txt
echo   - com_ports.txt
echo   - netstat.txt
echo   - arp_table.txt
echo ==========================================
pause
