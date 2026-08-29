"""TSecBench FastAPI 控制台 — 网页管理端（替代 Django 版后端）。

页面: Dashboard / Agent 舰队 / 工作区 / 设置 / 管理后台
API: 挑战 / VPN / AI 解题 / 舰队控制 / 派单
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from tsecbench.errors import APIError

from . import services as svc
from .cfg import get_cfg, remote_config, save_cfg
from .session import SessionMiddleware, mark_dirty
from .services import (
    challenge_brief,
    close_challenge,
    fleet_start,
    fleet_status,
    fleet_stop,
    get_hint,
    list_challenges,
    run_ai_auto,
    run_ai_round,
    single_status,
    solve_one,
    start_challenge,
    submit_flag,
    vpn,
    worker_logs,
)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="TSecBench 控制台", version="2.0.0")
app.add_middleware(SessionMiddleware)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _error(error: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"code": error.code, "message": error.message, "detail": getattr(error, "detail", {})},
    )


def _page_context(request: Request, *, title: str, kicker: str) -> dict:
    session = request.state.session
    from .agent import load_agent_env

    return {
        "request": request,
        "page_title": title,
        "page_kicker": kicker,
        "active_dashboard": request.url.path == "/",
        "active_agent": request.url.path == "/agent",
        "active_settings": request.url.path == "/settings",
        "llm": get_cfg(session),
        "agent_env": load_agent_env(),
    }


# ── 页面 ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request,
        "dashboard.html", _page_context(request, title="题目列表", kicker="OVERVIEW / DASHBOARD")
    )


@app.get("/agent", response_class=HTMLResponse)
def agent_page(request: Request):
    return templates.TemplateResponse(request,
        "agent.html", _page_context(request, title="Agent 舰队", kicker="FLEET / WORKERS")
    )


@app.get("/challenges/{unique_code}/", response_class=HTMLResponse)
def workspace(request: Request, unique_code: str):
    return templates.TemplateResponse(request,
        "workspace.html",
        {**_page_context(request, title="题目工作区", kicker="RUN / WORKSPACE"), "unique_code": unique_code},
    )


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(request,
        "settings.html", _page_context(request, title="设置", kicker="SYSTEM / CONFIG")
    )


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    """简化管理后台：题目列表（远端/本地）+ 删除。"""
    try:
        rows = list_challenges(request.state.session)
    except APIError:
        rows = []
    return templates.TemplateResponse(request,
        "admin.html",
        {**_page_context(request, title="管理后台", kicker="ADMIN / DATA"), "challenges": rows},
    )


# ── 会话/设置 ────────────────────────────────────────

class SettingsPayload(BaseModel):
    baseUrl: str = ""
    token: str = ""
    llmBaseUrl: str = ""
    llmApiKey: str = ""
    llmModel: str = ""
    llmThinking: bool = False
    llmReasoningEffort: str = "medium"
    useHint: bool = False
    maxRounds: int = 6
    autoClose: bool = True


@app.post("/settings/save")
def settings_save(request: Request, payload: SettingsPayload):
    save_cfg(request.state.session, payload.model_dump())
    mark_dirty(request)
    return {"ok": True}


@app.post("/settings/save-agent")
def settings_save_agent(request: Request, payload: dict):
    from .agent import save_agent_env

    save_agent_env({k: str(v).strip() for k, v in payload.items()})
    return {"ok": True, "message": "Agent 舰队配置已保存"}


@app.post("/settings/test-platform")
def settings_test_platform(request: Request):
    try:
        rows = list_challenges(request.state.session)
        remote = remote_config(request.state.session)
        label = "远端平台" if remote else "本地平台"
        return {"ok": True, "message": f"{label}连接成功，共 {len(rows)} 道题"}
    except APIError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "message": f"连接失败 [{exc.code}]: {exc.message}"},
        )


@app.post("/settings/test-llm")
def settings_test_llm(request: Request):
    cfg = get_cfg(request.state.session)
    if not (cfg["llmApiKey"] or "").strip():
        return {"ok": False, "message": "请先填写 LLM API Key"}
    try:
        from .solver import ask_llm

        ask_llm(cfg, [
            {"role": "system", "content": "你是一个测试助手。"},
            {"role": "user", "content": "只回复两个字：正常"},
        ])
        return {"ok": True, "message": "LLM 连接成功"}
    except APIError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "message": f"LLM 连接失败: {exc.message}"},
        )


# ── 挑战 API ─────────────────────────────────────────

@app.get("/api/v1/challenges")
def api_list_challenges(request: Request):
    try:
        return list_challenges(request.state.session)
    except APIError as exc:
        return _error(exc)


@app.post("/api/v1/challenges/start")
def api_start_challenge(request: Request, unique_code: str = ""):
    try:
        return start_challenge(request.state.session, unique_code)
    except APIError as exc:
        return _error(exc)


@app.get("/api/v1/challenges/hint")
def api_get_hint(request: Request, unique_code: str = ""):
    try:
        result = get_hint(request.state.session, unique_code)
        mark_dirty(request)
        return result
    except APIError as exc:
        return _error(exc)


class SubmitPayload(BaseModel):
    unique_code: str
    flag: str = Field(min_length=1, max_length=4096)


@app.post("/api/v1/challenges/submit")
def api_submit_flag(request: Request, payload: SubmitPayload):
    try:
        return submit_flag(request.state.session, payload.unique_code, payload.flag)
    except APIError as exc:
        return _error(exc)


@app.post("/api/v1/challenges/close")
def api_close_challenge(request: Request, unique_code: str = ""):
    try:
        return close_challenge(request.state.session, unique_code)
    except APIError as exc:
        return _error(exc)


# ── VPN API ──────────────────────────────────────────

@app.get("/api/v1/vpn/status")
def api_vpn_status():
    return vpn.as_dict()


class VPNConfigPayload(BaseModel):
    content: str


@app.post("/api/v1/vpn/config")
def api_vpn_upload(payload: VPNConfigPayload):
    try:
        return vpn.as_dict(vpn.save_config(payload.content))
    except APIError as exc:
        return _error(exc)


@app.post("/api/v1/vpn/start")
def api_vpn_start():
    try:
        return vpn.as_dict(vpn.start())
    except APIError as exc:
        return _error(exc)


@app.post("/api/v1/vpn/stop")
def api_vpn_stop():
    return vpn.as_dict(vpn.stop())


# ── AI 解题 ──────────────────────────────────────────

class AiPayload(BaseModel):
    unique_code: str


@app.post("/api/v1/ai/round")
def api_ai_round(request: Request, payload: AiPayload):
    try:
        result = run_ai_round(request.state.session, payload.unique_code)
        mark_dirty(request)
        return result
    except APIError as exc:
        return _error(exc)


@app.post("/api/v1/ai/auto")
def api_ai_auto(request: Request, payload: AiPayload):
    try:
        result = run_ai_auto(request.state.session, payload.unique_code)
        mark_dirty(request)
        return result
    except APIError as exc:
        return _error(exc)


# ── Agent 舰队 ───────────────────────────────────────

@app.get("/api/v1/agent/status")
def api_agent_status():
    try:
        return fleet_status()
    except APIError as exc:
        return _error(exc)


@app.post("/api/v1/agent/start")
def api_agent_start():
    try:
        return fleet_start()
    except APIError as exc:
        return _error(exc)


@app.post("/api/v1/agent/stop")
def api_agent_stop():
    try:
        return fleet_stop()
    except APIError as exc:
        return _error(exc)


@app.get("/api/v1/agent/logs")
def api_agent_logs(worker: str = "tsecbench-worker-1", tail: int = 200):
    try:
        return {"worker": worker, "logs": worker_logs(worker, max(1, min(500, tail)))}
    except APIError as exc:
        return _error(exc)


@app.post("/api/v1/agent/solve-one")
def api_agent_solve_one(request: Request, payload: AiPayload):
    try:
        return solve_one(payload.unique_code)
    except APIError as exc:
        return _error(exc)


@app.get("/api/v1/agent/single-status")
def api_agent_single_status(request: Request, unique_code: str = ""):
    return single_status(unique_code)


# ── 管理后台 API ─────────────────────────────────────

@app.post("/api/v1/admin/delete-challenge")
def api_admin_delete_challenge(request: Request, payload: AiPayload):
    """删除题目（远端/本地）：删除提交记录 + 题目行。"""
    code = payload.unique_code
    try:
        session = request.state.session
        remote = remote_config(session)
        if remote:
            raise APIError(400, "remote_mode", "远端模式不支持删除，请在平台侧操作")
        import sqlite3

        conn = sqlite3.connect(svc.store.database_path)
        with conn:
            conn.execute("DELETE FROM submissions WHERE task_token = ? AND unique_code = ?",
                         (svc.DEFAULT_TOKEN, code))
            cur = conn.execute("DELETE FROM challenges WHERE task_token = ? AND unique_code = ?",
                               (svc.DEFAULT_TOKEN, code))
        return {"ok": True, "message": f"已删除 {code}（删除行数 {cur.rowcount}）"}
    except APIError as exc:
        return _error(exc)


# ── 状态 ─────────────────────────────────────────────

@app.get("/api/v1/state")
def api_state(request: Request):
    remote = remote_config(request.state.session)
    if remote:
        try:
            rows = list_challenges(request.state.session)
            total = len(rows)
            configured = True
        except APIError:
            total = 0
            configured = False
    else:
        try:
            rows = list_challenges(request.state.session)
            total = len(rows)
        except APIError:
            total = 0
        configured = bool(svc.settings.benchmark_token or svc.settings.load_tasks())
    return {
        "configured": configured,
        "total_challenges": total,
        "remote": bool(remote),
        "vpn": vpn.as_dict(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)