@echo off
chcp 65001 >nul
echo ==========================================
echo    安装 SmartAM System 依赖
echo    (请在已激活的 pytorch_env 中运行)
echo ==========================================
echo.

cd /d "%~dp0"

echo [1/3] 设置清华镜像加速...
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo [2/3] 安装基础依赖...
pip install fastapi uvicorn python-multipart websockets numpy opencv-python pillow pydantic pydantic-settings pyserial requests python-dotenv python-jose pytest pytest-asyncio

echo.
echo [3/3] 安装 PyTorch 和数据处理库...
echo        (这可能需要较长时间，请耐心等待...)
pip install torch torchvision
pip install pandas scikit-learn scipy

echo.
echo ==========================================
echo    依赖安装完成！
echo ==========================================
echo.
echo 现在可以运行以下命令启动后端：
echo    cd backend
echo    python main.py
echo.
pause
