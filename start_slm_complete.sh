#!/usr/bin/env bash
set -euo pipefail

# Linux/SSH环境启动脚本；Windows环境继续使用 start_slm_complete.bat。
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
if ! command -v lsof >/dev/null 2>&1; then
    echo "  [ERROR] lsof not found. Please install lsof for port cleanup."
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

echo "[3/6] Checking port usage..."
for port in 8000 5173; do
    pids="$(lsof -ti "tcp:${port}" || true)"
    if [[ -n "${pids}" ]]; then
        echo "  Terminating processes using port ${port}: ${pids//$'\n'/ }"
        kill ${pids}
        sleep 1
        remain_pids="$(lsof -ti "tcp:${port}" || true)"
        if [[ -n "${remain_pids}" ]]; then
            kill -9 ${remain_pids}
        fi
    fi
done
echo

echo "[4/6] Building frontend static assets..."
cd "${ROOT_DIR}/frontend"
if [[ ! -d node_modules ]]; then
    npm install
fi
npm run build
echo

echo "[5/6] Starting backend service..."
cd "${ROOT_DIR}/backend"
# 不把stdout/stderr重定向到项目日志文件，避免外部重定向绕开后端日志轮转。
nohup python main.py >/dev/null 2>&1 &
BACKEND_PID=$!
echo "${BACKEND_PID}" > "${ROOT_DIR}/.smartam_backend.pid"
echo "  Backend PID: ${BACKEND_PID}"

echo "  Waiting for backend to start..."
for _ in {1..20}; do
    if curl -fsS "http://127.0.0.1:8000/" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! curl -fsS "http://127.0.0.1:8000/" >/dev/null 2>&1; then
    echo "  [ERROR] Backend service did not start properly."
    exit 1
fi

LOCAL_IP="$(hostname -I | awk '{print $1}')"
if [[ -z "${LOCAL_IP}" ]]; then
    LOCAL_IP="127.0.0.1"
fi

URL="http://${LOCAL_IP}:8000/slm/dashboard"
echo
echo "[6/6] Services startup complete!"
echo "========================================="
echo " Full Interface: ${URL}"
echo " API Docs: http://${LOCAL_IP}:8000/docs"
echo " Managed Logs: ${ROOT_DIR}/logs"
echo " PID File: ${ROOT_DIR}/.smartam_backend.pid"
echo "========================================="

# 有桌面会话时尝试打开浏览器；纯SSH环境下直接使用上面的URL访问。
if [[ -n "${DISPLAY:-}" ]] && command -v xdg-open >/dev/null 2>&1; then
    xdg-open "${URL}" >/dev/null 2>&1 &
fi
