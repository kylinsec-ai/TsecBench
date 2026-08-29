"""
Agent 能力层 — 统一结果模型、flag 提取与 SolverBackend 抽象接口

设计目标：解题 Agent（solver）固定使用 Pi Agent 编排网络安全 Agent。
- pi_agent.py      Pi Agent CLI 适配器（唯一求解引擎）
- factory.py       创建 Pi Agent 后端

上层（driver）只依赖本文件的 SolveResult 与 solve() 接口。
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger("adapter.solver")

# flag 提取正则
_FLAG_RX = re.compile(r"flag\{[^}]{1,200}\}", re.IGNORECASE)
_FINAL_ANSWER_RX = re.compile(r"<FinalAnswer>(.*?)</FinalAnswer>", re.DOTALL)
# flag body 合法字符：字母数字 + 常见分隔符（防命令注入 payload 误提取）
_FLAG_BODY_RX = re.compile(r"^[A-Za-z0-9_\-.:/]{3,200}$")


def is_valid_flag(flag: str) -> bool:
    """校验 flag 整体合法性：外壳完整 + body 无引号/空格/命令字符"""
    m = re.match(r"flag\{(.+)\}", flag, re.IGNORECASE)
    if not m:
        return False
    return bool(_FLAG_BODY_RX.match(m.group(1)))


def extract_flags(text: str) -> list[str]:
    """从文本中提取所有 flag{...} 格式的候选（过滤非法 body）"""
    if not text:
        return []
    found = set()
    for m in _FLAG_RX.finditer(text):
        f = m.group(0)
        if is_valid_flag(f):
            found.add(f)
    for m in _FINAL_ANSWER_RX.finditer(text):
        for fm in _FLAG_RX.finditer(m.group(1)):
            if is_valid_flag(fm.group(0)):
                found.add(fm.group(0))
    return list(found)


@dataclass
class SolveResult:
    """Agent 会话执行结果（各后端统一输出）"""
    flags: list[str] = field(default_factory=list)
    final_answer: str = ""
    final_text: str = ""
    handoff: str = ""
    tool_outputs: list = field(default_factory=list)
    observed_output: str = ""
    error: str = ""
    turns: int = 0
    duration_s: float = 0.0
    infra_blocked: bool = False

    @property
    def has_flags(self) -> bool:
        return bool(self.flags)


# 兼容旧名
CCResult = SolveResult


class SolverBackend(ABC):
    """
    Agent 求解器抽象接口。
    所有求解器实现本接口，上层 driver 只依赖 solve()。
    """

    name: str = "abstract"

    @abstractmethod
    def solve(
        self,
        prompt: str,
        workdir: str,
        cfg,
        *,
        flag_format: str = "flag{...}",
        on_fact: Optional[Callable] = None,
        transcript_path: Optional[str] = None,
        max_retries: int = 2,
    ) -> SolveResult:
        """执行一次解题会话，返回统一结果"""

    @staticmethod
    def _read_flag_files(workdir: str, flags: list[str]) -> list[str]:
        """从工作目录的标准 flag 文件补录候选"""
        for name in ("FLAG", "flag.txt", "FLAG.txt"):
            p = os.path.join(workdir, name)
            try:
                if os.path.isfile(p):
                    with open(p, encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            v = line.strip()
                            if v and "{" in v and v.endswith("}") and len(v) <= 200:
                                if v not in flags:
                                    flags.append(v)
            except Exception:
                pass
        return flags