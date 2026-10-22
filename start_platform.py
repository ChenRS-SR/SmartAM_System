"""独立部署入口：使用当前 Python 环境，不依赖 Codex、VS Code 或固定 Conda 环境名。"""

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PORT = 8000


def main():
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("未找到 npm，请先安装 Node.js 18+。")
    frontend = ROOT / "frontend"
    environment = os.environ.copy()
    # 独立部署始终同源，防止继承开发机的后端地址或构建模式。
    environment["VITE_API_BASE_URL"] = ""
    environment["VITE_MOCK_MODE"] = "false"
    if not (frontend / "node_modules").is_dir():
        subprocess.run([npm, "install"], cwd=frontend, env=environment, check=True)
    subprocess.run([npm, "run", "build"], cwd=frontend, env=environment, check=True)

    environment["SMARTAM_PORT_START"] = str(PORT)
    environment["SMARTAM_RELOAD"] = "0"
    environment["SMARTAM_ACCESS_LOG"] = "0"
    print(f"\n平台监听全部网卡，从 {PORT} 起自动选择可用端口；实际端口见后端启动输出。", flush=True)
    print("按 Ctrl+C 停止。", flush=True)
    return subprocess.call(
        [sys.executable, "main.py"], cwd=ROOT / "backend", env=environment,
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"启动失败：{error}", file=sys.stderr)
        sys.exit(1)
