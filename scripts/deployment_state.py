"""部署检查与成功状态记录；只在步骤成功后写入状态，不用空目录代表已安装。"""

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".deployment"


def backend_ready():
    # pip 自带版本约束解析器，干净 venv 不需要先安装额外的检测依赖。
    from pip._vendor.packaging.requirements import Requirement

    missing = []
    for line in (ROOT / "backend/requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        requirement = Requirement(line)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            installed = metadata.version(requirement.name)
        except metadata.PackageNotFoundError:
            missing.append(str(requirement))
            continue
        if installed not in requirement.specifier:
            missing.append(f"{requirement} (installed: {installed})")
    if missing:
        print("Missing or incompatible dependencies: " + ", ".join(missing))
        return False
    return subprocess.call([sys.executable, "-m", "pip", "check"]) == 0


def digest(paths):
    result = hashlib.sha256()
    for path in sorted(paths):
        result.update(path.relative_to(ROOT).as_posix().encode())
        result.update(b"\0")
        result.update(path.read_bytes())
        result.update(b"\0")
    return result.hexdigest()


def fingerprint(stage, runtime):
    frontend = ROOT / "frontend"
    files = [frontend / "package.json", frontend / "package-lock.json"]
    if stage == "build":
        files += [frontend / "index.html", frontend / "vite.config.js", ROOT / "backend/replay_cases/catalog.json"]
        for directory in ("src", "public"):
            files += [path for path in (frontend / directory).rglob("*") if path.is_file()]
        files += list(frontend.glob(".env*"))
    return {"inputs": digest(files), "runtime": runtime, "same_origin": True, "mock": False}


def build_outputs():
    dist = ROOT / "frontend/dist"
    # 缺少入口或构建脚本时，不能把损坏的 dist 当成有效构建。
    if not (dist / "index.html").is_file() or not list((dist / "assets").glob("*.js")):
        return None
    return digest([path for path in dist.rglob("*") if path.is_file()])


def stage_ready(stage, runtime):
    record = STATE / f"{stage}.json"
    if not record.exists():
        return False
    saved = json.loads(record.read_text(encoding="utf-8"))
    if saved["fingerprint"] != fingerprint(stage, runtime):
        return False
    if stage == "frontend":
        return (ROOT / "frontend/node_modules/.bin/vite.cmd").is_file()
    return saved["outputs"] is not None and saved["outputs"] == build_outputs()


def record_success(stage, runtime):
    record = {"fingerprint": fingerprint(stage, runtime)}
    if stage == "build":
        record["outputs"] = build_outputs()
        if record["outputs"] is None:
            raise RuntimeError("Build did not produce index.html and JavaScript assets")
    STATE.mkdir(exist_ok=True)
    temporary = STATE / f"{stage}.tmp"
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    os.replace(temporary, STATE / f"{stage}.json")


def build_frontend():
    # 显式传入空地址，不让 .env.local 或 PowerShell 5.1 的空值语义影响同源部署。
    environment = os.environ.copy()
    environment.update(VITE_API_BASE_URL="", VITE_MOCK_MODE="false")
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm was not found")
    subprocess.run([npm, "run", "build"], cwd=ROOT / "frontend", env=environment, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["build", "check-backend", "check-frontend", "record-frontend", "check-build", "record-build"])
    parser.add_argument("--runtime", default="")
    args = parser.parse_args()
    if args.action == "build":
        build_frontend()
        sys.exit(0)
    if args.action == "check-backend":
        sys.exit(0 if backend_ready() else 1)
    operation, stage = args.action.split("-", 1)
    if operation == "check":
        sys.exit(0 if stage_ready(stage, args.runtime) else 1)
    record_success(stage, args.runtime)
