"""
TSecBench 平台 HTTP 适配器

直接调用平台 REST API（CHALLENGES_API.md）：
- 认证: 请求头 BENCHMARK_TOKEN
- GET  /openapi/v1/challenges         — 题目列表
- POST /openapi/v1/challenges/start    — 启动容器
- GET  /openapi/v1/challenges/hint     — 获取提示（扣分）
- POST /openapi/v1/challenges/submit   — 提交 flag
- POST /openapi/v1/challenges/close    — 关闭容器
- VPN 预检: GET http://10.0.100.58     — 平台下发的 VPN 健康检查地址

不依赖任何第三方 SDK。
"""

from __future__ import annotations

from typing import Optional

import requests

from .base import (
    APIError, Challenge, ChallengeNotFound, CloseResult, DuplicateSubmit,
    HintResult, InvalidState, PlatformBackend, ResourceUnavailable,
    StartResult, SubmitResult, TaskNotFound, VpnCheckError, VpnCheckResult,
)

DEFAULT_VPN_CHECK_URL = "http://10.0.100.58"


class TSecBenchHTTPBackend(PlatformBackend):
    """
    TSecBench 平台 HTTP API 适配器。
    严格按 CHALLENGES_API.md 实现，不依赖任何第三方 SDK。
    """

    name = "tsecbench-http"
    MAX_CONCURRENT = 3  # 平台限制同时启动 3 道题

    def __init__(self, base_url: str, token: str, *,
                 timeout: int = 30,
                 vpn_check_url: str = DEFAULT_VPN_CHECK_URL):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.vpn_check_url = vpn_check_url
        self._session = requests.Session()
        # 认证通过请求头 BENCHMARK_TOKEN
        self._session.headers.update({
            "BENCHMARK_TOKEN": token,
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _handle_error(self, resp: requests.Response):
        """统一异常处理"""
        if resp.status_code < 400:
            return

        try:
            body = resp.json()
        except Exception:
            resp.raise_for_status()
            return

        code = body.get("code", "unknown")
        message = body.get("message", resp.text[:200])
        detail = body.get("detail") or {}
        status = resp.status_code

        exc_map = {
            "task_not_found": TaskNotFound,
            "challenge_not_found": ChallengeNotFound,
            "invalid_state": InvalidState,
            "duplicate": DuplicateSubmit,
            "resource_unavailable": ResourceUnavailable,
        }
        exc_cls = exc_map.get(code, APIError)
        raise exc_cls(code=code, message=message, status=status, detail=detail)

    # ── 1. 题目列表 ──

    def list_challenges(self) -> list[Challenge]:
        """GET /openapi/v1/challenges"""
        resp = self._session.get(
            self._url("/openapi/v1/challenges"),
            timeout=self.timeout,
        )
        self._handle_error(resp)
        data = resp.json()
        # API 直接返回数组；兼容 data 包裹
        items = data if isinstance(data, list) else data.get("data", data)
        return [Challenge.from_dict(c) for c in items]

    # ── 2. 启动容器 ──

    def start_challenge(self, unique_code: str) -> StartResult:
        """POST /openapi/v1/challenges/start?unique_code={unique_code}"""
        resp = self._session.post(
            self._url("/openapi/v1/challenges/start"),
            params={"unique_code": unique_code},
            timeout=self.timeout,
        )
        self._handle_error(resp)
        d = resp.json()
        return StartResult(
            unique_code=d.get("unique_code", unique_code),
            container_addr=d.get("container_addr") or [],
        )

    # ── 3. 获取提示（扣分） ──

    def get_hint(self, unique_code: str) -> HintResult:
        """GET /openapi/v1/challenges/hint?unique_code={unique_code}"""
        resp = self._session.get(
            self._url("/openapi/v1/challenges/hint"),
            params={"unique_code": unique_code},
            timeout=self.timeout,
        )
        self._handle_error(resp)
        d = resp.json()
        return HintResult(
            unique_code=d.get("unique_code", unique_code),
            hint=d.get("hint"),
        )

    # ── 4. 提交 flag ──

    def submit_flag(self, unique_code: str, flag: str) -> SubmitResult:
        """POST /openapi/v1/challenges/submit — JSON body"""
        resp = self._session.post(
            self._url("/openapi/v1/challenges/submit"),
            json={"unique_code": unique_code, "flag": flag},
            timeout=self.timeout,
        )
        # 特殊处理 duplicate (409)
        if resp.status_code == 409:
            try:
                body = resp.json()
                if body.get("code") == "duplicate":
                    return SubmitResult(correct=False, duplicate=True,
                                       error="duplicate")
            except Exception:
                pass
        self._handle_error(resp)
        d = resp.json()
        return SubmitResult(
            correct=d.get("correct", False),
            awarded=int(d.get("awarded", 0) or 0),
            cumulative_score=int(d.get("cumulative_score", 0) or 0),
            correct_flag_count=int(d.get("correct_flag_count", 0) or 0),
            total_flag_count=int(d.get("total_flag_count", 0) or 0),
            matched_flag_index=d.get("matched_flag_index"),
        )

    # ── 5. 关闭容器 ──

    def close_challenge(self, unique_code: str) -> CloseResult:
        """POST /openapi/v1/challenges/close?unique_code={unique_code}"""
        resp = self._session.post(
            self._url("/openapi/v1/challenges/close"),
            params={"unique_code": unique_code},
            timeout=self.timeout,
        )
        # 关闭时 invalid_state / challenge_not_found 不视为致命错误
        if resp.status_code in (409, 404):
            return CloseResult(unique_code=unique_code, closed=False)
        self._handle_error(resp)
        d = resp.json()
        return CloseResult(
            unique_code=d.get("unique_code", unique_code),
            closed=d.get("closed", True),
        )

    # ── VPN 预检 ──

    def check_vpn(self, *, timeout: float = 10.0) -> VpnCheckResult:
        """
        VPN 联通预检：GET {vpn_check_url}
        平台下发要求：status == "ok" 才视为 VPN 已连通。
        """
        try:
            resp = requests.get(self.vpn_check_url, timeout=timeout)
            body = resp.json()
        except requests.RequestException as e:
            raise VpnCheckError(reason="network_error") from e
        except ValueError:
            raise VpnCheckError(reason="bad_body") from None
        if resp.status_code != 200:
            raise VpnCheckError(reason="bad_status")
        status = body.get("status", "")
        if status != "ok":
            raise VpnCheckError(reason="status_not_ok")
        return VpnCheckResult(
            status=status,
            client_ip=body.get("client_ip", ""),
            time=body.get("time", ""),
            ok=True,
        )

    def health_check(self) -> bool:
        """尝试调用列表接口验证连通性"""
        try:
            self.list_challenges()
            return True
        except TaskNotFound:
            return False  # token 无效
        except Exception:
            return False