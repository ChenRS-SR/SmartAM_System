@echo off
chcp 65001 >nul
title SmartAM SLM 依赖安装
echo ========================================
echo   安装SLM系统依赖
echo ========================================
echo.

cd /d "%~dp0\backend"

echo [1/4] 配置清华镜像源...
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
echo.

echo [2/4] 升级pip...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.

echo [3/4] 安装核心依赖...
pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] python-multipart -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install numpy opencv-python pyserial scipy -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install websockets aiofiles -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.

echo [4/4] 验证安装...
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"
python -c "import uvicorn; print(f'Uvicorn: {uvicorn.__version__}')"
python -c "import jose; print(f'Python-JOSE: OK')"
python -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "import serial; print(f'PySerial: OK')"
echo.

echo ========================================
echo   依赖安装完成！
echo ========================================
echo.
pause
