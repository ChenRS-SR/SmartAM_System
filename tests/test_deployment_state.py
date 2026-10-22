"""覆盖重复部署、输入更新、产物丢失和旧后端地址污染。"""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("deployment_state", Path(__file__).resolve().parents[1] / "scripts/deployment_state.py")
deployment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deployment)


class DeploymentStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, content in {
            "frontend/package.json": "{}", "frontend/package-lock.json": "{}",
            "frontend/index.html": "entry", "frontend/vite.config.js": "config",
            "frontend/src/main.js": "source", "frontend/public/photo.jpg": "image",
            "frontend/dist/index.html": "built entry", "frontend/dist/assets/main.js": "built script",
            "frontend/node_modules/.bin/vite.cmd": "installed",
            "backend/replay_cases/catalog.json": "{}", "backend/requirements.txt": "fastapi>=0.104\n",
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.root_patch = patch.object(deployment, "ROOT", self.root)
        self.state_patch = patch.object(deployment, "STATE", self.root / ".deployment")
        self.root_patch.start()
        self.state_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.addCleanup(self.state_patch.stop)

    def test_existing_directory_is_not_success_and_repeat_is_skipped(self):
        self.assertFalse(deployment.stage_ready("frontend", "node24"))
        deployment.record_success("frontend", "node24")
        self.assertTrue(deployment.stage_ready("frontend", "node24"))
        self.assertFalse(deployment.stage_ready("frontend", "node26"))
        (self.root / "frontend/node_modules/.bin/vite.cmd").unlink()
        self.assertFalse(deployment.stage_ready("frontend", "node24"))

    def test_changed_dependency_file_requires_install(self):
        deployment.record_success("frontend", "node24")
        (self.root / "frontend/package-lock.json").write_text('{"changed":true}')
        self.assertFalse(deployment.stage_ready("frontend", "node24"))

    def test_changed_sources_and_damaged_assets_require_build(self):
        deployment.record_success("build", "node24")
        self.assertTrue(deployment.stage_ready("build", "node24"))
        (self.root / "frontend/src/main.js").write_text("new source")
        self.assertFalse(deployment.stage_ready("build", "node24"))
        deployment.record_success("build", "node24")
        (self.root / "frontend/dist/assets/main.js").unlink()
        self.assertFalse(deployment.stage_ready("build", "node24"))
        with self.assertRaises(RuntimeError):
            deployment.record_success("build", "node24")

    def test_backend_versions_are_checked_without_installing(self):
        with patch.object(deployment.metadata, "version", return_value="0.120.0"), patch.object(deployment.subprocess, "call", return_value=0):
            self.assertTrue(deployment.backend_ready())
        with patch.object(deployment.metadata, "version", return_value="0.90.0"):
            self.assertFalse(deployment.backend_ready())
        with patch.object(deployment.metadata, "version", side_effect=deployment.metadata.PackageNotFoundError):
            self.assertFalse(deployment.backend_ready())

    def test_base_install_does_not_require_inference(self):
        root = Path(__file__).resolve().parents[1]
        requirements = (root / 'backend/requirements.txt').read_text()
        active = [line.strip().lower() for line in requirements.splitlines() if line.strip() and not line.startswith('#')]
        self.assertFalse(any(line.startswith(('torch', 'torchvision', '-r')) for line in active))
        script = (root / 'scripts/deploy_windows.ps1').read_text(encoding='utf-8-sig')
        self.assertNotIn('import fastapi, uvicorn, cv2, torch', script)
        self.assertIn("'requirements.txt'", script)
        self.assertNotIn('requirements-inference.txt', script)

    def test_build_clears_old_host_and_mock_mode(self):
        with patch.dict(deployment.os.environ, {"VITE_API_BASE_URL": "http://old-pc", "VITE_MOCK_MODE": "true"}), patch.object(deployment.shutil, "which", return_value="npm.cmd"), patch.object(deployment.subprocess, "run") as run:
            deployment.build_frontend()
            self.assertEqual(run.call_args.kwargs["env"]["VITE_API_BASE_URL"], "")
            self.assertEqual(run.call_args.kwargs["env"]["VITE_MOCK_MODE"], "false")
            self.assertEqual(run.call_args.kwargs["cwd"], self.root / "frontend")


if __name__ == "__main__":
    unittest.main()
