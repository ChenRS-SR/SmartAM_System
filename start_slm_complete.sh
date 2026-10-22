#!/usr/bin/env bash
set -euo pipefail

# Linux/SSH环境启动脚本；Windows 使用 deploy_windows.bat 或 start_platform.bat。
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONDA_ENV="pytorch_env"

# 日志存储上限：单文件5MB，保留5份，总日志目录128MB。
export SMARTAM_LOG_MAX_BYTES=5242880
export SMARTAM_LOG_BACKUP_COUNT=5
export SMARTAM_LOG_TOTAL_BYTES=134217728
export SMARTAM_RELOAD=0
export SMARTAM_ACCESS_LOG=0

echo "========================================="
echo " SmartAM SLM Monitoring System - Linux Startup"
echo "========================================="
echo

echo "[1/6] Checking runtime environment..."
if ! command -v conda >/dev/null 2>&1; then
    echo "  [ERROR] Conda not found. Please initialize conda in this shell."
    exit 1
fi
if ! command -v node >/dev/null 2>&1; then
    echo "  [ERROR] Node.js not found. Please install Node.js 18+."
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "  [ERROR] npm not found. Please reinstall Node.js."
    exit 1
fi
# 激活conda环境，避免误用系统Python。
CONDA_BASE="$(conda info --base)"
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV}"
echo "  Conda environment: ${CONDA_ENV}"
python --version
node --version
echo

echo "[2/6] Cleaning managed logs..."
python "${ROOT_DIR}/scripts/manage_logs.py" --clean --status
echo

# 与独立部署共用端口选择，保留占用端口的其他服务。
exec python "${ROOT_DIR}/start_platform.py"
