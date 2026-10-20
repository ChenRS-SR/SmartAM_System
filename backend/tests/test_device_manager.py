"""设备类型切换回归测试：使用替身，不连接现场设备。"""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core.device_manager import DeviceManager, DeviceType


class DeviceManagerSwitchTests(unittest.TestCase):
    def setUp(self):
        self.manager = DeviceManager()
        self.cleanup = Mock()
        # 仅提供真实 SLS 采集器支持的方法，捕获不存在的接口调用。
        self.manager._sls_acquisition = SimpleNamespace(
            cleanup=self.cleanup, get_device_status=Mock(return_value={})
        )
        self.manager._current_type = DeviceType.SLS
        self.manager._initialized = True

    def test_switch_from_sls_to_slm_releases_sls(self):
        self.assertTrue(self.manager.set_device_type("slm"))
        self.cleanup.assert_called_once_with()
        self.assertEqual(self.manager.current_type, DeviceType.SLM)
        self.assertTrue(self.manager.get_status()["initialized"])

    def test_reselect_sls_schedules_initialization(self):
        with patch("threading.Thread") as thread:
            self.assertTrue(self.manager.set_device_type("sls"))
            thread.return_value.start.assert_called_once_with()
        self.cleanup.assert_called_once_with()
        self.assertEqual(self.manager.current_type, DeviceType.SLS)

    def test_stop_sls_marks_uninitialized(self):
        self.manager.stop_current_device()
        self.cleanup.assert_called_once_with()
        self.assertFalse(self.manager.get_status()["initialized"])


if __name__ == "__main__":
    unittest.main()
