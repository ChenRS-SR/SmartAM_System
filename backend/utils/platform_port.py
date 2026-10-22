"""启动时占住实际监听端口，避免检查通过后又被其他进程抢占。"""
import errno
import ipaddress
import json
import subprocess
import socket
import sys

DEFAULT_PORT = 8000
LAST_PORT = 8099


def reserve_listener(first=DEFAULT_PORT, last=LAST_PORT):
    if not 1 <= first <= last <= 65535:
        raise ValueError('监听端口范围无效')
    for port in range(first, last + 1):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if sys.platform == 'win32':
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('0.0.0.0', port))
            listener.listen(128)
            listener.setblocking(False)
            return listener
        except OSError as error:
            listener.close()
            # Windows 保留端口可能返回拒绝访问，同样尝试下一个端口。
            if error.errno not in (errno.EADDRINUSE, errno.EACCES) and getattr(error, 'winerror', None) not in (10048, 10013):
                raise
    raise RuntimeError(f'{first}–{last} 端口均被占用或不可绑定，无法启动平台')


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

