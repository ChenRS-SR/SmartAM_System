"""验证独立部署不会继承旧 IP，也不会抢占已有服务端口。"""

import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import start_platform


class DeploymentTests(unittest.TestCase):
    def test_build_uses_same_origin_and_current_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "frontend" / "node_modules").mkdir(parents=True)
            with (
                patch.object(start_platform, "ROOT", root),
                patch.object(start_platform, "PORT", 0),
                patch.object(start_platform, "lan_addresses", return_value=["192.168.1.20"]),
                patch.object(start_platform.shutil, "which", return_value="npm"),
                patch.object(start_platform.subprocess, "run") as build,
                patch.object(start_platform.subprocess, "call", return_value=0) as server,
                patch.dict(os.environ, {"VITE_API_BASE_URL": "http://old-host:9999", "VITE_MOCK_MODE": "true"}),
            ):
                self.assertEqual(start_platform.main(), 0)
                environment = build.call_args.kwargs["env"]
                self.assertEqual(environment["VITE_API_BASE_URL"], "")
                self.assertEqual(environment["VITE_MOCK_MODE"], "false")
                self.assertEqual(server.call_args.args[0], [start_platform.sys.executable, "main.py"])
                self.assertEqual(server.call_args.kwargs["cwd"], root / "backend")

    def test_occupied_port_stops_before_build(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as existing:
            existing.bind(("0.0.0.0", 0))
            existing.listen()
            with (
                patch.object(start_platform, "PORT", existing.getsockname()[1]),
                patch.object(start_platform.subprocess, "run") as build,
            ):
                with self.assertRaises(OSError):
                    start_platform.main()
                build.assert_not_called()
                self.assertGreater(existing.getsockname()[1], 0)

    def test_windows_single_address_is_an_array(self):
        with (
            patch.object(start_platform.sys, "platform", "win32"),
            patch.object(start_platform.subprocess, "check_output", return_value='["192.168.1.20"]'),
        ):
            self.assertEqual(start_platform.lan_addresses(), ["192.168.1.20"])


if __name__ == "__main__":
    unittest.main()
