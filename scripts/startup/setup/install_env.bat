@echo off
chcp 65001 >nul
echo ==========================================
echo    SmartAM System 环境安装脚本
echo ==========================================
echo.

:: 设置 Conda 路径
set "CONDA_PATH=D:\Anaconda\Scripts\conda.exe"
set "PYTORCH_ENV=C:\Users\18320\.conda\envs\pytorch_env"

echo [1/4] 检查 Conda...
if not exist "%CONDA_PATH%" (
    echo [错误] 找不到 Conda: %CONDA_PATH%
    echo 请修改脚本中的 CONDA_PATH 为您的 Conda 安装路径
    pause
    exit /b 1
)
echo        Conda 路径: %CONDA_PATH%

echo.
echo [2/4] 创建 pytorch_env 环境...
"%CONDA_PATH%" env list | findstr "pytorch_env" >nul
if errorlevel 1 (
    echo        正在创建 pytorch_env 环境...
    "%CONDA_PATH%" create -n pytorch_env python=3.11 -y
) else (
    echo        pytorch_env 环境已存在
)

echo.
echo [3/4] 安装后端依赖...
set "PYTHON=%PYTORCH_ENV%\python.exe"
set "PIP=%PYTORCH_ENV%\python.exe -m pip"

:: 设置清华镜像
%PIP% config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

:: 分批安装依赖
echo        安装基础依赖...
%PIP% install fastapi uvicorn python-multipart websockets numpy opencv-python pillow pydantic pydantic-settings pyserial requests python-dotenv python-jose pytest pytest-asyncio

echo        安装 PyTorch (这可能需要较长时间)...
%PIP% install torch torchvision --index-url https://download.pytorch.org/whl/cu121

echo        安装数据处理依赖...
%PIP% install pandas scikit-learn scipy

echo.
echo [4/4] 检查 Node.js...
where node >nul 2>&1
if errorlevel 1 (
    echo        Node.js 未安装
    echo        请从 https://nodejs.org/ 下载安装 LTS 版本
    echo        或使用 winget: winget install OpenJS.NodeJS.LTS
) else (
    echo        Node.js 已安装
    
    echo        安装前端依赖...
    cd frontend
    call npm install
    cd ..
)

echo.
echo ==========================================
echo    安装完成！
echo ==========================================
echo.
echo 现在可以运行 start_all.bat 启动服务了
echo.
pause
