"""验证同源构建及真正占住可用端口，不结束占用端口的程序。"""
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import start_platform
from backend.utils import platform_port


class DeploymentTests(unittest.TestCase):
    def test_build_uses_same_origin_and_current_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'frontend' / 'node_modules').mkdir(parents=True)
            with (
                patch.object(start_platform, 'ROOT', root),
                patch.object(start_platform.shutil, 'which', return_value='npm'),
                patch.object(start_platform.subprocess, 'run') as build,
                patch.object(start_platform.subprocess, 'call', return_value=0) as server,
                patch.dict(os.environ, {'VITE_API_BASE_URL':'http://old-host:9999','VITE_MOCK_MODE':'true'}),
            ):
                self.assertEqual(start_platform.main(),0)
                environment = build.call_args.kwargs['env']
                self.assertEqual(environment['VITE_API_BASE_URL'],'')
                self.assertEqual(environment['VITE_MOCK_MODE'],'false')
                self.assertEqual(server.call_args.args[0],[start_platform.sys.executable,'main.py'])
                self.assertEqual(server.call_args.kwargs['env']['SMARTAM_PORT_START'],'8000')
                self.assertEqual(server.call_args.kwargs['cwd'],root/'backend')

    def test_occupied_port_is_skipped_and_socket_stays_reserved(self):
        with socket.socket() as existing:
            existing.bind(('0.0.0.0',0)); existing.listen()
            first = existing.getsockname()[1]
            with platform_port.reserve_listener(first,first+10) as chosen:
                selected = chosen.getsockname()[1]
                self.assertGreater(selected,first)
                # 再次启动不能抢占刚选中的端口，已有服务也仍然可连接。
                with platform_port.reserve_listener(selected,selected+10) as another:
                    self.assertGreater(another.getsockname()[1],selected)
                with socket.create_connection(('127.0.0.1',first),timeout=1): pass
                with self.assertRaises(RuntimeError): platform_port.reserve_listener(selected,selected)

    def test_all_ports_unavailable_reports_error(self):
        with socket.socket() as existing:
            existing.bind(('0.0.0.0',0)); existing.listen()
            port = existing.getsockname()[1]
            with self.assertRaisesRegex(RuntimeError,'均被占用或不可绑定'):
                platform_port.reserve_listener(port,port)
        with self.assertRaises(ValueError): platform_port.reserve_listener(9000,8000)

    def test_windows_single_address_is_an_array(self):
        with patch.object(platform_port.sys,'platform','win32'), patch.object(platform_port.subprocess,'check_output',return_value='["192.168.1.20"]'):
            self.assertEqual(platform_port.lan_addresses(),['192.168.1.20'])

    def test_root_has_only_two_batch_entrypoints(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual({p.name for p in root.glob('*.bat')},{'deploy_windows.bat','start_platform.bat'})
        self.assertIn('-StartOnly',(root/'start_platform.bat').read_text())

if __name__ == '__main__': unittest.main()
