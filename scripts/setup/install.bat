@echo off
chcp 65001 >nul
echo ==========================================
echo SmartAM_System 环境安装脚本
echo ==========================================
echo.

:: 检查 Conda
echo [1/4] 检查 Conda 环境...
conda --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Conda，请先安装 Anaconda 或 Miniconda
    pause
    exit /b 1
)
echo Conda 检查通过

:: 创建 Python 环境
echo.
echo [2/4] 创建 Python 环境 (pytorch_env)...
conda env list | findstr "pytorch_env" >nul
if errorlevel 1 (
    echo 创建新的 conda 环境...
    conda create -n pytorch_env python=3.9 -y
) else (
    echo 环境已存在，跳过创建
)

:: 激活环境并安装依赖
echo.
echo [3/4] 安装后端依赖...
call conda activate pytorch_env
pip install -r ..\..\backend\requirements.txt
if errorlevel 1 (
    echo 错误: 后端依赖安装失败
    pause
    exit /b 1
)

:: 安装前端依赖
echo.
echo [4/4] 安装前端依赖...
cd ..\..\frontend
call npm install
if errorlevel 1 (
    echo 警告: 前端依赖安装失败，请手动运行 npm install
)
cd ..\..\scripts\setup

echo.
echo ==========================================
echo 安装完成！
echo ==========================================
echo.
echo 启动方式:
echo   1. 双击 start_all.bat
echo   2. 或分别启动前后端
echo.
pause
