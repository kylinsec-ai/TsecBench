# Repository Guidelines

## Project Overview

TSecBench is a FastAPI service for authenticated challenge-task lifecycle management. It exposes challenge listing, start, hint, flag submission, and close operations; task/challenge state is persisted in SQLite, and challenge instances are supplied either by static catalog data or a Docker provisioner.

The Docker Compose stack is a separate Kali headless workspace for challenge operations. It does not run the FastAPI server or publish an API port.

## Architecture & Data Flow

- `main.py` is the ASGI entry point. Importing `main:app` eagerly calls `create_app()`, which loads settings, opens/initializes SQLite, selects a provisioner, and seeds configured tasks before serving.
- `tsecbench/api.py:create_app` is the composition root. It accepts injectable settings, database path, task data, provisioner, and active-challenge limit; it stores the `Store`, `ChallengeService`, and `Settings` on `app.state`.
- Requests use synchronous FastAPI route handlers. The `BENCHMARK_TOKEN` header dependency authenticates against an active task, then delegates to `ChallengeService`.
- `ChallengeService` owns business rules and serializes lifecycle transitions with `RLock`. Start and close call the injected `ContainerProvisioner`; list, hint, submit, and lifecycle state changes use `Store`.
- `Store` is a thread-safe SQLite repository. Mutations run in transactions (`BEGIN IMMEDIATE`); file-backed databases use WAL. Startup recovery resets in-flight container states to stopped.
- `models.py` normalizes and validates task/challenge/flag input. Flag values are stored as SHA-256 digests, not plaintext. `config.py` loads task JSON from a file or inline environment value and can inject the benchmark token into a bare challenge catalog.
- Business failures use `APIError` helpers and stable `{code, message, detail}` responses. Unexpected API exceptions are converted to a generic 500 response.
- Lifecycle state is coordinated across service and store: reserve a stopped challenge, provision it, mark it available with runtime addresses, and clear runtime state on close. Preserve these transitions and their error rollback behavior when changing code.
- The app also serves the Range Console: `/` returns the static SPA in `tsecbench/static/` with the console config embedded, and `/benchmark/{path}` is a same-origin proxy forwarding to the configured `BENCHMARK_BASE_URL` `/openapi/v1/challenges*` routes while injecting `BENCHMARK_TOKEN` server-side (the remote platform lacks CORS). The proxy forwards query strings verbatim and returns 502 on upstream failures.

## Key Directories

- `tsecbench/` — application source: API, settings, domain models, service rules, SQLite persistence, error types, provisioners, and the served console SPA (`tsecbench/static/`).
- `tests/` — pytest unit tests; currently centered on `test_challenges_api.py`.
- `e2e/` — Playwright end-to-end tests that boot real server processes and drive Chromium (`pytest e2e`).
- `tsecbench-frontend/` — Vue 3 source for the console; development-only, build output is ignored.
- `data/` — local SQLite runtime data; ignored by Git.
- Repository root — `main.py`, dependency files, Docker configuration, `.env.example`, and integration documentation. There is no repository `scripts/` directory.

## Development Commands

Install the development dependencies from the repository root:

```bash
python -m pip install -r requirements-dev.txt
```

Run the complete unit test suite (default `pytest` run, `testpaths = tests`):

```bash
python -m pytest -q
```

Run the end-to-end console suite (boots real servers and Chromium; install browsers once):

```bash
python -m playwright install chromium
python -m pytest e2e
```

Run the API directly using `HOST`/`PORT` settings:

```bash
python main.py
```

Run the ASGI app with Uvicorn (the module-level app performs initialization on import):

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

Build and operate the Kali workspace:

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose exec -it kali bash
docker compose stop
docker compose start
docker compose up -d --build
```

Do not use `docker compose down -v`; it deletes the persistent `kali-data` volume. No lint, formatter, Makefile, `pyproject.toml`, or CI command is configured in this repository.

## Code Conventions & Common Patterns

- Follow the existing Python style: `from __future__ import annotations`, type annotations, `snake_case` functions/variables, and `PascalCase` classes.
- Use frozen dataclasses for immutable settings and domain/value rows. Put input coercion and validation in `models.py` classmethods rather than duplicating it in routes.
- Keep route handlers thin. Put authentication, state transitions, scoring, locking, and provisioning decisions in `ChallengeService`; put SQL and transaction boundaries in `Store`.
- Prefer dependency injection through `create_app(...)` for database paths, task catalogs, provisioners, settings, and limits. Tests should inject temporary resources instead of changing process-wide defaults.
- Preserve the synchronous boundary: service and provisioner methods are synchronous and lifecycle-critical sections are protected by `RLock`. Use the existing transaction helpers for SQLite writes.
- Raise `ConfigurationError` for invalid configuration and use the existing `APIError` constructors for expected HTTP business failures. Do not leak internal exception details through the catch-all API handler.
- Preserve idempotency and state semantics: repeated correct submissions produce `duplicate`; completed/expired tasks reject invalid operations; closing a challenge releases runtime addresses.
- Keep secrets out of source, tests, documentation, and command output. `.env` is local and ignored; `.env.example` uses placeholders. Never copy a real benchmark or GitHub token into a tracked file.

## Important Files

- `main.py` — module-level ASGI app and direct Uvicorn runner.
- `tsecbench/static/` — served Range Console SPA (`index.html`, `app.js`, `styles.css`).
- `tsecbench/api.py` — FastAPI factory, request/response models, routes, exception handlers, and the `/benchmark` proxy.
- `tsecbench/config.py` — `Settings.from_env`, dotenv loading, numeric validation, and task loading.
- `tsecbench/models.py` — configuration normalization, domain dataclasses, digest handling, and score calculation.
- `tsecbench/service.py` — authenticated challenge business rules and lifecycle state machine.
- `tsecbench/store.py` — SQLite schema, transactions, persistence, and recovery.
- `tsecbench/provisioner.py` — `StaticProvisioner`, `DockerProvisioner`, and the provisioner protocol.
- `tsecbench/errors.py` — stable API error types and constructors.
- `tests/test_challenges_api.py` — endpoint lifecycle, persistence, and dotenv precedence coverage.
- `e2e/conftest.py` / `e2e/test_frontend.py` — real-server Playwright fixtures and console e2e tests (including proxy mode).
- `pytest.ini` — pytest root configuration (`testpaths = tests`).
- `requirements.txt` / `requirements-dev.txt` — runtime dependencies and the pip-style development include.
- `Dockerfile` / `docker-compose.yaml` — Kali workspace image and lifecycle.
- `CHALLENGES_API.md` — benchmark caller workflow, routes, headers, errors, VPN, and scoring rules.
- `.env.example` / `.gitignore` — safe environment template and local-secret/artifact exclusions.

## Runtime/Tooling Preferences

- Use Python with a repository-local virtual environment (`.venv` is the local convention). The current environment is Python 3.13, but no Python version is pinned in repository metadata.
- Use pip requirement files; there is no lockfile or alternate package manager configuration. Runtime dependencies are FastAPI, Uvicorn, Pydantic, `python-dotenv`, and HTTPX (used by the proxy); development dependencies include pytest, Playwright, and pytest-playwright.
- `Settings.from_env()` loads the repository-root `.env` when present with `override=False`, so explicitly exported environment variables win. Important settings include `BENCHMARK_BASE_URL`, `BENCHMARK_TOKEN`, `TSECBENCH_DB_PATH`/`TSECBENCH_DATABASE`, `TSECBENCH_CONFIG`, `TSECBENCH_TASKS_JSON`, `TSECBENCH_MAX_ACTIVE_CHALLENGES`, `TSECBENCH_PROVISIONER`, `HOST`, and `PORT`.
- Docker tooling requires Docker and Docker Compose v2. The image is based on `kalilinux/kali-rolling`, installs `kali-linux-headless`, and idles with `tail -f /dev/null`; application dependencies are installed in the host/virtualenv workflow, not by the Dockerfile.
- Treat the FastAPI process and the Compose Kali container as distinct runtime pieces. Compose has no API port mapping or environment injection.
- Keep local `.env`, SQLite files, Python caches, `.venv`, and pytest cache out of commits. Use task-issued placeholders in examples and tests.

## Testing & QA

- Unit tests use pytest, direct `test_*` functions, bare assertions, and FastAPI `TestClient`; `pytest.ini` limits the default `pytest` run to `tests/`. There is no marker set, coverage threshold, or CI workflow.
- `tests/test_challenges_api.py` uses `tmp_path` for isolated SQLite databases and injects `create_app(..., database_path=..., tasks=...)`. Dotenv tests use `monkeypatch` to isolate environment variables and temporary dotenv files.
- `e2e/` tests use pytest-playwright and boot real `main.py` subprocesses against isolated databases (`e2e/conftest.py`); `proxy_server_url` boots an upstream API plus a console proxying to it to exercise the `/benchmark` proxy. Run with `python -m pytest e2e` (requires `python -m playwright install chromium`).
- Existing unit-test coverage includes authentication and response shape, start/hint/submit/close lifecycle, hint score discounts, duplicate submissions, validation and unknown challenges, active limits, unavailable resources, expiry, restart persistence, dotenv loading, and exported-variable precedence.
- For changes to service or persistence logic, test observable transitions, rollback/error codes, scoring boundaries, duplicate protection, and persistence across app construction. For settings changes, use fake temporary dotenv contents and never write or assert against the real local token.
- Neither suite makes external benchmark calls, needs VPN access, or uses Docker provisioning. Run a local server smoke check separately when changing startup/configuration behavior.
