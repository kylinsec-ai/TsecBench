"""
提示词模板系统

灵感来自 Pi Agent 的 Prompt Templates，但实现原创：
- Markdown + YAML frontmatter
- 参数替换: $1, $2, $@, ${1:-默认值}
- 文件名即模板命令名
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("adapter.templates")


@dataclass
class TemplateMeta:
    """模板元信息"""
    name: str
    description: str
    argument_hint: str
    path: str
    body: str


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 YAML frontmatter"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    fm_text = text[3:end].strip()
    body = text[end + 4:].strip()
    meta = {}
    for line in fm_text.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def _substitute(body: str, args: tuple) -> str:
    """
    参数替换:
    - $1, $2, ... → 位置参数
    - $@ → 所有参数空格连接
    - ${1:-默认值} → 带默认值
    - ${@:N} → 从第N个开始的所有参数
    """
    result = body

    # ${N:-默认值}
    def _default_sub(m):
        idx = int(m.group(1)) - 1
        default = m.group(2)
        return args[idx] if idx < len(args) else default
    result = re.sub(r"\$\{(\d+):-([^}]*)\}", _default_sub, result)

    # ${@:N}
    def _slice_sub(m):
        start = int(m.group(1)) - 1
        return " ".join(args[start:])
    result = re.sub(r"\$\{@:(\d+)\}", _slice_sub, result)

    # $@
    result = result.replace("$@", " ".join(args))
    result = result.replace("$ARGUMENTS", " ".join(args))

    # $1, $2, ...
    for i, arg in enumerate(args):
        result = result.replace(f"${i + 1}", arg)

    return result


class TemplateStore:
    """提示词模板仓库"""

    def __init__(self, prompts_dir: str = None):
        self._dir = prompts_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")
        self._templates: dict[str, TemplateMeta] = {}
        self._scan()

    def _scan(self):
        if not os.path.isdir(self._dir):
            return
        for entry in os.listdir(self._dir):
            if not entry.endswith(".md"):
                continue
            path = os.path.join(self._dir, entry)
            name = entry[:-3]  # 去掉 .md
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                meta, body = _parse_frontmatter(text)
                self._templates[name] = TemplateMeta(
                    name=name,
                    description=meta.get("description", body.split("\n")[0][:80]),
                    argument_hint=meta.get("argument-hint", ""),
                    path=path,
                    body=body,
                )
            except Exception as e:
                log.warning("failed to load template %s: %s", name, e)
        log.info("loaded %d prompt templates: %s", len(self._templates),
                 ", ".join(self._templates.keys()))

    def list_templates(self) -> list[dict]:
        return [{"name": t.name, "description": t.description,
                 "argument_hint": t.argument_hint}
                for t in self._templates.values()]

    def expand_template(self, name: str, *args: str) -> Optional[str]:
        """展开模板并替换参数"""
        tmpl = self._templates.get(name)
        if tmpl is None:
            return None
        return _substitute(tmpl.body, args)

    def get(self, name: str) -> Optional[TemplateMeta]:
        return self._templates.get(name)
