import subprocess
import sys
import os

# 使用 venv 中的 python 和 uvicorn
venv_python = os.path.join('venv', 'Scripts', 'python.exe')
backend_dir = 'backend'
log_file = 'backend_daemon.log'

# 构建启动命令：python -m uvicorn main:app --host 0.0.0.0 --port 8000
# 使用 python -m uvicorn 更可靠
cmd = [venv_python, '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000']

# Windows  detached process flags
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

with open(log_file, 'w') as f:
    process = subprocess.Popen(
        cmd,
        cwd=backend_dir,
        stdout=f,
        stderr=subprocess.STDOUT,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        close_fds=True
    )

print(f'Backend started with PID: {process.pid}')
print(f'Log file: {os.path.abspath(log_file)}')
