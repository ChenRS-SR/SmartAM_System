#!/usr/bin/env python3
"""
SLM实时数据接口最小客户端示例。

运行前确保后端已启动：
  conda run -n pytorch_env python -m uvicorn main:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8000/api"
DEFAULT_SAMPLE = Path(__file__).with_name("slm_realtime_fault_sample.json")
DEFAULT_EXPECT_STATUS_LABEL = "刮刀扭矩/位置故障"


def request_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def load_sample(path: Path, use_now: bool) -> dict:
    sample = json.loads(path.read_text(encoding="utf-8"))
    if use_now:
        # event_time模拟真实采集事件时间；真实系统应由采集端直接填入。
        event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sample["event_time"] = event_time
        for alarm in sample.get("alarms", []):
            alarm["time"] = event_time
    return sample


def main() -> int:
    parser = argparse.ArgumentParser(description="推送一条SLM实时事件并读取诊断结果")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="后端API根地址")
    parser.add_argument("--sample", default=str(DEFAULT_SAMPLE), help="样例JSON路径")
    parser.add_argument("--keep", action="store_true", help="保留后台实时缓存，便于打开前端查看")
    parser.add_argument("--no-now", action="store_true", help="不把样例event_time替换为当前时间")
    parser.add_argument(
        "--expect-status-label",
        default=DEFAULT_EXPECT_STATUS_LABEL,
        help="期望诊断标签；传空字符串时只验证链路是否返回实时事件",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    sample = load_sample(Path(args.sample), use_now=not args.no_now)
    device_id = sample["device_id"]

    schema = request_json(f"{base_url}/slm/realtime/schema")
    print(f"[schema] success={schema['success']} parameters={len(schema['parameterSchema'])}")

    posted = request_json(f"{base_url}/slm/realtime/data", method="POST", payload=sample)
    diagnosis = posted["sample"]["diagnosis"]
    print(
        "[post] "
        f"status={diagnosis['statusCode']} {diagnosis['statusLabel']} "
        f"frontend={diagnosis['frontendStatusCode']} "
        f"confidence={diagnosis['confidenceText']} "
        f"layer={diagnosis['modelLayer']}"
    )

    latest = request_json(f"{base_url}/slm/realtime/data/{quote(device_id)}")
    latest_sample = latest["sample"]
    print(
        "[latest] "
        f"hasData={latest_sample['hasData']} "
        f"eventTime={latest_sample['eventTime']} "
        f"ch1={bool(latest_sample.get('media', {}).get('ch1'))}"
    )

    expected_label = args.expect_status_label.strip()
    if expected_label and diagnosis["statusLabel"] != expected_label:
        raise SystemExit("诊断结果与样例预期不一致")
    if not latest_sample["hasData"]:
        raise SystemExit("未读取到最近实时事件")

    if not args.keep:
        cleared = request_json(f"{base_url}/slm/realtime/data/{quote(device_id)}", method="DELETE")
        print(f"[clear] success={cleared['success']} device={cleared['device_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
