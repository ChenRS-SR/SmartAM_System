"""SLM 试验台 HTTP API 客户端（requests 版）。

移植自 Desktop/slm/slm_api_client.py，把 urllib 换成项目内普遍使用的 requests。
三个端点：
  GET  /api/slc/parts       — 获取 SLC 零件列表（含当前打印参数）
  POST /api/slc/fill-params — 设置指定零件的填充参数
  POST /api/powder/amount   — 设置铺粉量

试验台不可达时不抛异常，而是置 offline 标志并降级：get_parts() 回退到
COMM_DIR/parts.json 样例零件列表，保证无试验台时页面仍可演示「发送调整」→ 写 feedback.json。
"""

import json
import logging
from typing import Optional, List, Dict, Any

import requests

from .config import API_BASE_URL, API_TIMEOUT_MS, COMM_DIR, SAMPLE_PARTS_FILE

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """API 调用异常（连接失败 / 响应异常）。"""


class SLMApiClient:
    """SLM 试验台 HTTP API 客户端（同步、单例模式）。"""

    def __init__(self, base_url: str = API_BASE_URL, timeout_ms: int = API_TIMEOUT_MS):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_ms / 1000.0
        self._parts_cache: Optional[List[Dict[str, Any]]] = None
        self._selected_part: Optional[Dict[str, Any]] = None
        self.offline = False
        self.parts_fallback = False  # 是否因试验台离线而使用了样例零件

    # ---- 零件列表 ----

    def get_parts(self) -> List[Dict[str, Any]]:
        """获取 SLC 零件列表；试验台不可达时回退到样例零件列表。"""
        parts = self._fetch_parts()
        self.parts_fallback = False
        if not parts and self.offline:
            # 试验台不可达 → 回退样例零件，保证无试验台时页面仍可演示
            parts = self._load_sample_parts()
            self.parts_fallback = bool(parts)
        self._parts_cache = parts
        return parts

    def _fetch_parts(self) -> List[Dict[str, Any]]:
        url = f"{self._base_url}/api/slc/parts"
        try:
            data = self._get(url)
        except ApiError as e:
            self.offline = True
            logger.error(f"获取零件列表失败: {e}")
            return []
        self.offline = False
        code = data.get("code", -1)
        if code == 0:
            parts = data.get("parts", [])
            logger.info(f"获取零件列表成功: {len(parts)} 个零件")
            return parts
        logger.warning(f"零件列表 API 返回异常: code={code}")
        return []

    def _load_sample_parts(self) -> List[Dict[str, Any]]:
        """试验台离线时回退读取样例零件列表。"""
        path = COMM_DIR / SAMPLE_PARTS_FILE
        try:
            with open(path, "r", encoding="utf-8") as f:
                parts = json.load(f)
            if isinstance(parts, list):
                logger.info(f"试验台不可达，回退样例零件列表: {len(parts)} 个")
                return parts
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.debug(f"无样例零件列表 {path}: {e}")
        return []

    def get_cached_parts(self) -> List[Dict[str, Any]]:
        return self._parts_cache or []

    def is_part_valid(self, part_id: int) -> bool:
        if self._parts_cache is None:
            return False
        return any(p.get("part_id") == part_id for p in self._parts_cache)

    @property
    def selected_part(self) -> Optional[Dict[str, Any]]:
        return self._selected_part

    def select_part(self, part_id: int) -> Optional[Dict[str, Any]]:
        if not self.is_part_valid(part_id):
            logger.warning(f"无效的 part_id: {part_id}")
            return None
        for p in (self._parts_cache or []):
            if p.get("part_id") == part_id:
                self._selected_part = p
                return p
        return None

    # ---- 填充参数 ----

    def set_fill_params(
        self,
        part_id: int,
        fill_power: float,
        fill_speed: float,
        scan_spacing: float,
    ) -> bool:
        if not self.is_part_valid(part_id):
            logger.error(f"part_id={part_id} 不在零件列表中，拒绝发送")
            return False

        url = f"{self._base_url}/api/slc/fill-params"
        body = {
            "part_id": part_id,
            "fill_power": fill_power,
            "fill_speed": fill_speed,
            "scan_spacing": scan_spacing,
        }
        try:
            data = self._post(url, body)
        except ApiError as e:
            self.offline = True
            logger.error(f"设置填充参数请求失败: {e}")
            return False
        self.offline = False
        if data.get("code") == 0:
            logger.info(
                f"填充参数已发送: part_id={part_id} "
                f"P={fill_power}W v={fill_speed}mm/s h={scan_spacing}mm"
            )
            return True
        msg = data.get("message", "未知错误")
        logger.error(f"设置填充参数失败: code={data.get('code')}, msg={msg}")
        return False

    # ---- 铺粉量 ----

    def set_powder_amount(self, amount: float) -> bool:
        url = f"{self._base_url}/api/powder/amount"
        body = {"amount": amount}
        try:
            data = self._post(url, body)
        except ApiError as e:
            self.offline = True
            logger.error(f"设置铺粉量请求失败: {e}")
            return False
        self.offline = False
        if data.get("code") == 0:
            logger.info(f"铺粉量已发送: amount={amount}")
            return True
        msg = data.get("message", "未知错误")
        logger.error(f"设置铺粉量失败: code={data.get('code')}, msg={msg}")
        return False

    # ---- 底层 HTTP 方法 ----

    def _get(self, url: str) -> Dict[str, Any]:
        try:
            resp = requests.get(url, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise ApiError(f"连接失败: {e}")
        except ValueError as e:
            raise ApiError(f"响应非 JSON: {e}")

    def _post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            resp = requests.post(url, json=data, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise ApiError(f"连接失败: {e}")
        except ValueError as e:
            raise ApiError(f"响应非 JSON: {e}")


# 全局单例
_api_client: Optional[SLMApiClient] = None


def get_api_client() -> SLMApiClient:
    """获取全局 API 客户端单例。"""
    global _api_client
    if _api_client is None:
        _api_client = SLMApiClient()
    return _api_client
