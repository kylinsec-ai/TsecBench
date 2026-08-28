"""Playwright end-to-end fixtures for the TSecBench Range Console.

A session-scoped fixture boots the real FastAPI server (main.py) against a
temporary SQLite database and a seeded task catalog, so the browser drives the
actual running API rather than a mock.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN = "e2e-token"
CHALLENGES = [
    {
        "unique_code": "web_sql_injection_01",
        "description": "通过 SQL 注入获取管理员凭证并读取 flag",
        "difficulty": "easy",
        "level": 1,
        "total_score": 100,
        "hint": "尝试在登录表单的用户名字段使用单引号测试注入点",
        "hint_cost_radio": 0.3,
        "container_addr": ["10.0.1.5:8080"],
        "flags": [
            {"value": "flag{admin_sql}", "score": 40},
            {"value": "flag{second_sql}", "score": 60},
        ],
    },
    {
        "unique_code": "crypto_rsa_02",
        "description": "RSA 参数不当导致私钥可恢复",
        "difficulty": "hard",
        "level": 3,
        "total_score": 200,
        "hint": "检查模数是否可分解",
        "hint_cost_radio": 0.2,
        "container_addr": ["10.0.2.10:443"],
        "flags": ["flag{rsa_priv}"],
    },
    {
        "unique_code": "rev_maze_03",
        "description": "逆向迷宫程序找到出口 flag",
        "difficulty": "medium",
        "level": 2,
        "total_score": 150,
        "hint": "跟踪出口分支的条件",
        "hint_cost_radio": 0.5,
        "container_addr": [],
        "flags": ["flag{maze_end}"],
    },
]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_ready(url: str, proc: subprocess.Popen[bytes], timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            output = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            pytest.fail(f"server exited early with code {proc.returncode}:\n{output}")
        try:
            if httpx.get(url + "/", timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    proc.terminate()
    pytest.fail("server did not become ready in time")


def _launch_server(
    tmp_path: Path,
    *,
    env_overrides: dict[str, str] | None = None,
    wait: bool = True,
) -> tuple[str, subprocess.Popen[bytes]]:
    """Boot a real server (main.py) against an isolated DB and seeded catalog.

    Returns (base_url, process). The tasks file is written once per tmp_path so
    multiple servers in one test share the same catalog. With wait=False the
    caller boots several servers first and waits on all of them afterwards,
    so startup windows overlap.
    """
    tasks_file = tmp_path / "tasks.json"
    if not tasks_file.exists():
        tasks_file.write_text(json.dumps({"token": TOKEN, "challenges": CHALLENGES}), encoding="utf-8")

    port = _free_port()
    env = dict(os.environ)
    env.update(
        {
            "TSECBENCH_DB_PATH": str(tmp_path / f"e2e-{port}.sqlite3"),
            "TSECBENCH_CONFIG": str(tasks_file),
            "HOST": "127.0.0.1",
            "PORT": str(port),
            # 隔离本地 e2e：禁用远程 .env 配置，让前端走本地 API
            "BENCHMARK_BASE_URL": "",
            "BENCHMARK_TOKEN": "",
            **(env_overrides or {}),
        }
    )
    proc = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "main.py")],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    url = f"http://127.0.0.1:{port}"
    if wait:
        _wait_until_ready(url, proc)
    return url, proc


def _stop_server(proc: subprocess.Popen[bytes]) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def server_url(tmp_path) -> str:
    """Boot a fresh server per test (fresh DB) and yield its base URL.

    Function scope gives each test an isolated database, so container state and
    submitted flags from one test never leak into the next.
    """
    url, proc = _launch_server(tmp_path)
    try:
        yield url
    finally:
        _stop_server(proc)


@pytest.fixture
def proxy_server_url(tmp_path) -> str:
    """Boot an upstream API plus a console server proxying to it.

    The console's BENCHMARK_BASE_URL points at a second local server playing
    the remote platform, so list/start/hint/close run through the /benchmark
    proxy — the deployment mode this feature exists for.
    """
    upstream_url, upstream = _launch_server(
        tmp_path,
        env_overrides={"TSECBENCH_DB_PATH": str(tmp_path / "upstream.sqlite3")},
        wait=False,
    )
    console_url, console = _launch_server(
        tmp_path,
        env_overrides={
            "TSECBENCH_DB_PATH": str(tmp_path / "console.sqlite3"),
            "BENCHMARK_BASE_URL": upstream_url,
            "BENCHMARK_TOKEN": TOKEN,
        },
        wait=False,
    )
    _wait_until_ready(upstream_url, upstream)
    _wait_until_ready(console_url, console)
    try:
        yield console_url
    finally:
        _stop_server(console)
        _stop_server(upstream)
