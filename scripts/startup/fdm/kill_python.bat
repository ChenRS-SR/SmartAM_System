@echo off
chcp 65001 >nul
echo 正在查找并终止 Python 进程...

taskkill /F /IM python.exe 2>nul
taskkill /F /IM pythonw.exe 2>nul

echo 清理 Python 缓存...
cd /d "%~dp0\backend"
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul

echo 完成！所有 Python 进程已终止，缓存已清除。
pause
