#!/bin/bash

echo "============================================"
echo "  SmartAM_System - 智能制造监控系统"
echo "============================================"
echo ""

# 检查 Python
echo "[1/3] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3"
    exit 1
fi

# 检查虚拟环境
echo "[2/3] 检查依赖..."
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

# 检查并安装依赖
if ! pip show fastapi &> /dev/null; then
    echo "安装依赖..."
    pip install -r requirements.txt
fi

echo "[3/3] 启动服务..."
echo ""
echo "服务地址："
echo "  - API 文档: http://localhost:8000/docs"
echo "  - 视频流:   http://localhost:8000/video_feed"
echo ""
echo "按 Ctrl+C 停止服务"
echo "============================================"
echo ""

python main.py
