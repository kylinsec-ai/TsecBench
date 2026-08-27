"""
TsecBench 平台 API 客户端

严格按照 CHALLENGES_API.md 文档实现：
- 认证: 请求头 BENCHMARK_TOKEN
- GET  /openapi/v1/challenges         — 题目列表
- POST /openapi/v1/challenges/start    — 启动容器
- GET  /openapi/v1/challenges/hint     — 获取提示（扣分）
- POST /openapi/v1/challenges/submit   — 提交 flag
- POST /openapi/v1/challenges/close    — 关闭容器

限制: 同时最多 3 个活跃容器
"""

from __future__ import annotations

import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Optional

import requests

log = logging.getLogger("adapter.platform")


# ── 数据结构 ──────────────────────────────────────────────

@dataclass
class Challenge:
    """平台返回的题目信息"""
    unique_code: str
    description: str = ""
    difficulty: str = ""
    level: int = 1
    total_score: int = 0
    flag_count: int = 1
    correct_flag_count: int = 0
    is_completed: bool = False
    container_status: str = "stopped"      # pending/available/stop_pending/stopped
    container_addr: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Challenge":
        return cls(
            unique_code=d.get("unique_code", ""),
            description=d.get("description") or "",
            difficulty=d.get("difficulty", ""),
            level=int(d.get("level", 1) or 1),
            total_score=int(d.get("total_score", 0) or 0),
            flag_count=int(d.get("flag_count", 1) or 1),
            correct_flag_count=int(d.get("correct_flag_count", 0) or 0),
            is_completed=bool(d.get("is_completed", False)),
            container_status=d.get("container_status", "stopped"),
            container_addr=d.get("container_addr") or [],
        )

    @property
    def remaining_flags(self) -> int:
        return max(0, self.flag_count - self.correct_flag_count)


@dataclass
class StartResult:
    """启动容器结果"""
    unique_code: str
    container_addr: list[str] = field(default_factory=list)


@dataclass
class SubmitResult:
    """flag 提交结果"""
    correct: bool = False
    awarded: int = 0
    cumulative_score: int = 0
    correct_flag_count: int = 0
    total_flag_count: int = 0
    matched_flag_index: Optional[int] = None
    duplicate: bool = False
    error: str = ""


@dataclass
class HintResult:
    """提示结果"""
    unique_code: str = ""
    hint: Optional[str] = None


@dataclass
class CloseResult:
    """关闭容器结果"""
    unique_code: str = ""
    closed: bool = False


# ── API 异常 ──────────────────────────────────────────────

class APIError(Exception):
    """平台 API 业务异常"""
    def __init__(self, code: str, message: str, status: int = 0, detail: dict = None):
        self.code = code
        self.message = message
        self.status = status
        self.detail = detail or {}
        super().__init__(f"[{status}] {code}: {message}")


class TaskNotFound(APIError):
    pass

class ChallengeNotFound(APIError):
    pass

class InvalidState(APIError):
    """任务已结束 或 活跃实例达上限"""
    pass

class DuplicateSubmit(APIError):
    pass

class ResourceUnavailable(APIError):
    pass


# ── 平台客户端 ──────────────────────────────────────────────

class PlatformClient:
    """
    TsecBench 平台 API 客户端

    严格按 CHALLENGES_API.md 实现，不依赖任何第三方 SDK。
    """

    MAX_CONCURRENT = 3  # 平台限制同时启动 3 道题

    def __init__(self, base_url: str, token: str, *, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
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
        # API 直接返回数组
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
        # 关闭时 invalid_state 不视为致命错误
        if resp.status_code == 409:
            return CloseResult(unique_code=unique_code, closed=False)
        if resp.status_code == 404:
            return CloseResult(unique_code=unique_code, closed=False)
        self._handle_error(resp)
        d = resp.json()
        return CloseResult(
            unique_code=d.get("unique_code", unique_code),
            closed=d.get("closed", True),
        )

    # ── 健康检查 ──

    def health_check(self) -> bool:
        """尝试调用列表接口验证连通性"""
        try:
            self.list_challenges()
            return True
        except TaskNotFound:
            return False  # token 无效
        except Exception:
            return False


class RateLimitedClient:
    """带速率限制的客户端封装，防止 API 请求过密"""

    def __init__(self, client: PlatformClient, min_interval: float = 0.5):
        self._client = client
        self._min_interval = min_interval
        self._lock = threading.Lock()
        self._last_call = 0.0

    def _wait(self):
        with self._lock:
            now = time.monotonic()
            delta = now - self._last_call
            if delta < self._min_interval:
                time.sleep(self._min_interval - delta)
            self._last_call = time.monotonic()

    def list_challenges(self) -> list[Challenge]:
        self._wait()
        return self._client.list_challenges()

    def start_challenge(self, unique_code: str) -> StartResult:
        self._wait()
        return self._client.start_challenge(unique_code)

    def get_hint(self, unique_code: str) -> HintResult:
        self._wait()
        return self._client.get_hint(unique_code)

    def submit_flag(self, unique_code: str, flag: str) -> SubmitResult:
        self._wait()
        return self._client.submit_flag(unique_code, flag)

    def close_challenge(self, unique_code: str) -> CloseResult:
        self._wait()
        return self._client.close_challenge(unique_code)

    def health_check(self) -> bool:
        return self._client.health_check()
