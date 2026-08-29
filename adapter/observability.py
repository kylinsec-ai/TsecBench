"""
结构化事件日志
用于记录运行中的关键事件，便于事后分析和调试。
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Optional

log = logging.getLogger("adapter.obs")

_log_path: Optional[str] = None
_run_id: str = ""
_context: dict = {}
_lock = threading.Lock()
_file = None


def configure(path: str, *, run_id: str = ""):
    """配置事件日志输出文件"""
    global _log_path, _run_id, _file
    _log_path = path
    _run_id = run_id
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _file = open(path, "a", encoding="utf-8")


def context(**kwargs):
    """设置当前上下文 (线程安全)"""
    global _context
    with _lock:
        _context.update(kwargs)


def emit(event: str, *, layer: str = "adapter", payload: dict = None):
    """
    记录一条结构化事件。

    Args:
        event: 事件名称
        layer: 来源层 (adapter/driver/verify/etc)
        payload: 事件载荷
    """
    if _file is None:
        return

    entry = {
        "ts": time.time(),
        "run_id": _run_id,
        "event": event,
        "layer": layer,
    }

    with _lock:
        if _context:
            entry.update(_context)

    if payload:
        entry["payload"] = payload

    try:
        with _lock:
            _file.write(json.dumps(entry, ensure_ascii=False) + "\n")
            _file.flush()
    except Exception as e:
        log.warning("event emit failed: %s", e)


def close():
    """关闭日志文件"""
    global _file
    if _file:
        try:
            _file.close()
        except Exception:
            pass
        _file = None
