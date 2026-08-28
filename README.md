# TSecBench

TSecBench is a FastAPI service for authenticated challenge-task lifecycle management. It lists challenges, starts and closes challenge instances, provides optional hints, and records flag submissions. Task, challenge, container, and submission state is persisted in SQLite.

TSecBench 是一个用于管理认证挑战任务生命周期的 FastAPI 服务，支持列出题目、启动和关闭题目实例、获取可选提示以及提交 flag。任务、题目、容器和提交状态均持久化到 SQLite。

The repository also contains a separate Kali headless workspace for challenge operations. The Kali container is not the API server; run the FastAPI application separately.

仓库还包含一个用于挑战操作的独立 Kali 无头工作区。Kali 容器不是 API 服务，需要单独运行 FastAPI 应用。

## Requirements / 环境要求

- Python 3.10 or newer. No Python version is pinned in repository metadata.
- Python 3.10 或更高版本。仓库元数据未固定 Python 版本。
- Docker and Docker Compose v2 for the Kali workspace.
- Kali 工作区需要 Docker 和 Docker Compose v2。
- Docker CLI is required only when using the Docker challenge provisioner.
- 只有使用 Docker 题目配置器时才需要 Docker CLI。

## Quick start / 快速开始

### 1. Create a virtual environment / 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

### 2. Configure benchmark settings / 配置跑分参数

Copy the safe template and replace the placeholder with the token issued for your benchmark task.

复制安全模板，并将占位符替换为跑分任务下发的 token。

```bash
cp .env.example .env
```

The root `.env` should contain task-specific values:

根目录 `.env` 应包含当前任务的配置：

```dotenv
BENCHMARK_BASE_URL=https://tsecbench.zc.tencent.com
BENCHMARK_TOKEN=your-task-issued-token
```

`.env` is ignored by Git. Never commit it or print the token. Process environment variables take precedence over values loaded from `.env`.

`.env` 已被 Git 排除。不要提交或打印其中的 token。进程环境变量优先于 `.env` 中加载的值。

### 3. Supply a task catalog / 提供题目任务目录

Point the service at a JSON task catalog when challenges should be seeded at startup:

如果需要在启动时初始化题目，请将服务指向 JSON 任务目录：

```bash
export TSECBENCH_CONFIG=/absolute/path/to/tasks.json
```

The loader accepts a single task object, a task array, or an object containing `tasks`. Each task contains a `token` and a `challenges` array. A challenge may define `unique_code`, `description`, `difficulty`, `level`, `total_score`, `flags`, and `container_addr`; Docker-backed challenges may also define `image`, `container_port`, and `docker_network`. `TSECBENCH_TASKS_JSON` is the inline-JSON alternative.

加载器支持单个任务对象、任务数组或包含 `tasks` 的对象。每个任务包含 `token` 和 `challenges` 数组。题目可定义 `unique_code`、`description`、`difficulty`、`level`、`total_score`、`flags` 和 `container_addr`；Docker 题目还可以定义 `image`、`container_port` 和 `docker_network`。`TSECBENCH_TASKS_JSON` 可用于传入内联 JSON。

If no catalog is configured, a token-only task is created, but it contains no challenges to list.

如果未配置任务目录，服务会创建一个仅含 token 的任务，但其中没有可列出的题目。

### 4. Start the API / 启动 API

```bash
python main.py
```

Or run the exported ASGI application with Uvicorn:

也可以使用 Uvicorn 运行导出的 ASGI 应用：

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

`main.py` initializes configuration, the SQLite database, and task state while importing `main:app`. Set configuration before starting the process.

导入 `main:app` 时，`main.py` 会初始化配置、SQLite 数据库和任务状态。启动进程前请先完成配置。

## Configuration reference / 配置参考

`Settings.from_env()` loads the repository-root `.env` when it exists, without overriding variables already exported by the shell.

当根目录存在 `.env` 时，`Settings.from_env()` 会加载它，但不会覆盖 shell 中已经导出的变量。

| Variable / 变量 | Default / 默认值 | Purpose / 用途 |
|---|---|---|
| `BENCHMARK_BASE_URL` | unset | Benchmark platform base URL exposed through runtime settings / 通过运行时设置提供的跑分平台基础 URL |
| `BENCHMARK_TOKEN` | unset | Task token used for task loading and request authentication / 用于加载任务和请求认证的任务 token |
| `TSECBENCH_CONFIG` | unset | Path to a JSON task catalog / JSON 任务目录路径 |
| `TSECBENCH_TASKS_JSON` | unset | Inline JSON task catalog / 内联 JSON 任务目录 |
| `TSECBENCH_DB_PATH` | `./data/tsecbench.sqlite3` | SQLite database path / SQLite 数据库路径 |
| `TSECBENCH_DATABASE` | fallback only | Legacy database variable used when `TSECBENCH_DB_PATH` is unset / 当 `TSECBENCH_DB_PATH` 未设置时使用的旧数据库变量 |
| `TSECBENCH_MAX_ACTIVE_CHALLENGES` | `3` | Maximum simultaneous active challenges; must be at least 1 / 同时激活的题目上限，必须至少为 1 |
| `TSECBENCH_PROVISIONER` | `static` | Provisioner mode: `static` or `docker` / 配置器模式：`static` 或 `docker` |
| `HOST` | `0.0.0.0` | Host used by `python main.py` / `python main.py` 使用的监听地址 |
| `PORT` | `8000` | Port used by `python main.py`; valid range is 1–65535 / `python main.py` 使用的端口，有效范围为 1–65535 |

## Challenges API / 题目 API

All challenge routes are under `/openapi/v1/challenges` and require the task-issued `BENCHMARK_TOKEN` header.

所有题目接口都位于 `/openapi/v1/challenges` 下，并要求在请求头中携带任务下发的 `BENCHMARK_TOKEN`：

```bash
curl \
  -H 'BENCHMARK_TOKEN: your-task-issued-token' \
  http://127.0.0.1:8000/openapi/v1/challenges
```

The normal workflow is:

标准调用流程如下：

1. `GET /openapi/v1/challenges` to list challenges and progress. / 使用该接口列出题目和作答进度。
2. `POST /openapi/v1/challenges/start?unique_code=<code>` to start a challenge and obtain `container_addr`. / 启动题目并获取 `container_addr`。
3. Connect to the challenge address through the required SSLVPN. / 通过要求的 SSLVPN 连接题目地址。
4. Optionally call `GET /openapi/v1/challenges/hint?unique_code=<code>`; hints reduce later scores. / 可选调用提示接口；提示会降低后续得分。
5. Submit each flag with `POST /openapi/v1/challenges/submit`. / 使用提交接口逐个提交 flag。
6. Call `POST /openapi/v1/challenges/close?unique_code=<code>` to release resources. / 调用关闭接口释放资源。

At most three challenges are active by default. Re-submitting a correct flag returns `duplicate`; expired or stopped tasks return `invalid_state`; missing or invalid tokens return `task_not_found`.

默认最多同时激活三道题目。重复提交正确 flag 会返回 `duplicate`；过期或已停止的任务返回 `invalid_state`；缺失或无效 token 返回 `task_not_found`。

See [`CHALLENGES_API.md`](CHALLENGES_API.md) for complete request/response and error contracts.

完整的请求、响应和错误约定请参阅 [`CHALLENGES_API.md`](CHALLENGES_API.md)。

## Range Console / 靶场控制台

The same process serves a browser console: `GET /` returns the SPA in `tsecbench/static/`, and the console calls the challenge API through the same origin.

同一进程还提供浏览器控制台：`GET /` 返回 `tsecbench/static/` 中的单页应用，控制台通过同源路径调用题目 API。

- **Local mode / 本地模式**: when `BENCHMARK_BASE_URL` is unset, the console calls `/openapi/v1/challenges*` directly and uses the `BENCHMARK_TOKEN` typed at the gate (kept in `sessionStorage`).
- **Proxy mode / 代理模式**: when `BENCHMARK_BASE_URL` is set, the console calls `/benchmark/{path}`; the server forwards to `<base>/openapi/v1/challenges/{path}` injecting `BENCHMARK_TOKEN` server-side. This bypasses the remote platform's missing CORS support.

  When `BENCHMARK_BASE_URL` 未设置时，控制台直接调用 `/openapi/v1/challenges*`，使用登录时输入的 `BENCHMARK_TOKEN`（保存在 `sessionStorage`）。设置 `BENCHMARK_BASE_URL` 后，控制台改走 `/benchmark/{path}`，由服务端转发到 `<base>/openapi/v1/challenges/{path}` 并注入 `BENCHMARK_TOKEN`，从而绕开远端平台缺失的 CORS 支持。

> **Security boundary / 安全边界**: the console page embeds `BENCHMARK_TOKEN` into the served HTML, and the `/benchmark` proxy authenticates any caller against the platform with that token. Anyone with network access to the console can read the token and drive the full API (start containers, submit flags). Expose the console only on a trusted, network-restricted range; do not bind it to a public interface. Proxy mode forwards query strings and returns `502 upstream_error` if the upstream is unreachable.

> **安全边界**：控制台页面会把 `BENCHMARK_TOKEN` 嵌入到返回的 HTML 中，`/benchmark` 代理也会用该 token 为任意调用者鉴权。任何能访问控制台的网络主体都能读取 token 并驱动完整 API（启动容器、提交 flag）。控制台只能在受信任且受限的网络范围内暴露，请勿绑定到公网接口。代理模式会透传查询参数；上游不可达时返回 `502 upstream_error`。

## Kali workspace / Kali 工作区

The Compose service builds and runs an interactive Kali headless container with the persistent `kali-data` volume mounted at `/workspace`.

Compose 服务会构建并运行交互式 Kali 无头容器，并将持久化卷 `kali-data` 挂载到 `/workspace`。

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose exec -it kali bash
```

Stop or restart without deleting the volume:

停止或重启时不要删除数据卷：

```bash
docker compose stop
docker compose start
```

Rebuild and start in one step:

重新构建并启动：

```bash
docker compose up -d --build
```

The Compose file does not publish an API port, inject benchmark environment variables, or start Uvicorn. Do not run `docker compose down -v`; it deletes the persistent volume.

Compose 文件不会发布 API 端口、注入跑分环境变量或启动 Uvicorn。不要执行 `docker compose down -v`，该命令会删除持久化卷。

## Development and testing / 开发与测试

Run the unit test suite from the repository root (`pytest.ini` restricts the default run to `tests/`):

在仓库根目录运行单元测试套件（`pytest.ini` 将默认运行范围限定为 `tests/`）：

```bash
python -m pytest -q
```

Run the end-to-end console suite (boots real `main.py` server processes and Chromium; install browsers once):

运行控制台端到端测试（会启动真实的 `main.py` 服务进程与 Chromium；首次需安装浏览器）：

```bash
python -m playwright install chromium
python -m pytest e2e
```

The e2e suite drives the served console in both local mode and proxy mode (`proxy_server_url` boots an upstream API plus a console proxying to it), exercising list/start/hint/submit/close against real SQLite databases.

e2e 套件以本地模式与代理模式两种方式驱动控制台（`proxy_server_url` 会启动一个上游 API 和一个代理到它的控制台），针对真实 SQLite 数据库验证列表/启动/提示/提交/关闭全流程。

Tests use pytest and FastAPI `TestClient` for units and pytest-playwright for e2e. Unit tests create isolated SQLite databases with `tmp_path`; settings tests use temporary dotenv files and `monkeypatch`. Coverage includes authentication, challenge lifecycle, scoring, duplicate submissions, validation, resource limits, expiry, restart persistence, dotenv loading, and environment precedence.

单元测试使用 pytest 和 FastAPI `TestClient`，e2e 使用 pytest-playwright。单元测试通过 `tmp_path` 创建隔离的 SQLite 数据库；设置测试使用临时 dotenv 文件和 `monkeypatch`。覆盖内容包括认证、题目生命周期、计分、重复提交、参数校验、资源限制、过期任务、重启持久化、dotenv 加载和环境变量优先级。

There is no configured linter, formatter, coverage threshold, Makefile, lockfile, or CI workflow. Keep changes focused and add behavior tests for new observable contracts.

仓库未配置 linter、formatter、覆盖率阈值、Makefile、锁文件或 CI 工作流。请保持改动聚焦，并为新的可观测行为增加测试。

## Project layout / 项目结构

- `main.py` — ASGI application export and direct Uvicorn runner / ASGI 应用导出和直接 Uvicorn 启动入口。
- `tsecbench/api.py` — FastAPI factory, routes, request/response models, exception handlers, and the `/benchmark` proxy / FastAPI 工厂、路由、请求响应模型、异常处理器和 `/benchmark` 代理。
- `tsecbench/static/` — served Range Console SPA (`index.html`, `app.js`, `styles.css`) / 提供的靶场控制台单页应用。
- `tsecbench/config.py` — environment loading, validation, and task catalog loading / 环境加载、校验和任务目录加载。
- `tsecbench/models.py` — task/challenge/flag normalization and scoring helpers / 任务、题目、flag 规范化和计分辅助函数。
- `tsecbench/service.py` — authenticated business rules and lifecycle transitions / 认证业务规则和生命周期状态转换。
- `tsecbench/store.py` — SQLite schema, transactions, persistence, and startup recovery / SQLite 模式、事务、持久化和启动恢复。
- `tsecbench/provisioner.py` — static and Docker challenge provisioning / static 和 Docker 题目配置器。
- `tests/test_challenges_api.py` — endpoint and settings behavior tests / 接口和设置行为测试。
- `e2e/` — Playwright console tests booting real server processes / 启动真实服务进程的 Playwright 控制台测试。
- `tsecbench-frontend/` — Vue 3 console source (dev-only; build output ignored) / Vue 3 控制台源码（仅开发用，构建产物被忽略）。
- `.env.example` — safe configuration template; copy to local `.env` / 安全配置模板，复制为本地 `.env`。
- `Dockerfile` and `docker-compose.yaml` — Kali workspace image and lifecycle / Kali 工作区镜像和生命周期配置。
