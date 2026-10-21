"""独立部署入口：使用当前 Python 环境，不依赖 Codex、VS Code 或固定 Conda 环境名。"""

import ipaddress
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
PORT = 8000


def lan_addresses():
    """枚举已启用网卡的 IPv4 地址，不向外网发起探测请求。"""
    if sys.platform == "win32":
        command = [
            "powershell", "-NoProfile", "-Command",
            "ConvertTo-Json -Compress -InputObject @(Get-NetIPAddress "
            "-AddressFamily IPv4 -AddressState Preferred | "
            "Select-Object -ExpandProperty IPAddress)",
        ]
        addresses = json.loads(subprocess.check_output(command, text=True))
    elif sys.platform.startswith("linux"):
        interfaces = json.loads(subprocess.check_output(
            ["ip", "-j", "-4", "address", "show", "up"], text=True,
        ))
        addresses = [
            entry["local"] for interface in interfaces
            for entry in interface["addr_info"] if entry["family"] == "inet"
        ]
    else:
        raise RuntimeError("此启动入口支持 Windows 和 Linux。")
    return sorted({
        address for address in addresses
        if not ipaddress.ip_address(address).is_loopback
        and not ipaddress.ip_address(address).is_link_local
    })


def main():
    # 端口被占用时明确停止，不终止其他程序，也不悄悄更换端口。
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        # Linux 重启后允许复用 TIME_WAIT 连接；Windows 使用独占绑定检查。
        if sys.platform == "win32":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("0.0.0.0", PORT))

    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("未找到 npm，请先安装 Node.js 18+。")
    addresses = lan_addresses()
    frontend = ROOT / "frontend"
    environment = os.environ.copy()
    # 独立部署始终同源，防止继承开发机的后端地址或构建模式。
    environment["VITE_API_BASE_URL"] = ""
    environment["VITE_MOCK_MODE"] = "false"
    if not (frontend / "node_modules").is_dir():
        subprocess.run([npm, "install"], cwd=frontend, env=environment, check=True)
    subprocess.run([npm, "run", "build"], cwd=frontend, env=environment, check=True)

    environment["SMARTAM_RELOAD"] = "0"
    environment["SMARTAM_ACCESS_LOG"] = "0"
    print("\n平台将监听全部网卡，端口 8000；按 Ctrl+C 停止。", flush=True)
    print("本机：http://127.0.0.1:8000/slm/dashboard", flush=True)
    for address in addresses:
        print(f"网卡地址：http://{address}:8000/slm/dashboard", flush=True)
    print("请使用访问电脑可达的网卡地址；看到 Uvicorn 启动成功后即可打开。", flush=True)
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
