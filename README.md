# TSecBench

TSecBench is a FastAPI service for authenticated challenge-task lifecycle management. It lists challenges, starts and closes challenge instances, provides optional hints, and records flag submissions. Task, challenge, container, and submission state is persisted in SQLite.

The repository also contains a separate Kali headless workspace for challenge operations. The Kali container is not the API server; run the FastAPI application separately.

## Requirements

- Python 3.10 or newer. No Python version is pinned in repository metadata.
- Docker and Docker Compose v2 for the Kali workspace.
- Docker CLI only when using the Docker challenge provisioner.

## Quick start

### 1. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

### 2. Configure benchmark settings

Copy the safe template and replace the placeholder with the token issued for your benchmark task:

```bash
cp .env.example .env
```

The root `.env` should contain the task-specific values:

```dotenv
BENCHMARK_BASE_URL=https://tsecbench.zc.tencent.com
BENCHMARK_TOKEN=your-task-issued-token
```

`.env` is ignored by Git. Never commit it or print the token. Process environment variables take precedence over values loaded from `.env`.

### 3. Supply a task catalog

Point the service at a JSON task catalog when challenges should be seeded at startup:

```bash
export TSECBENCH_CONFIG=/absolute/path/to/tasks.json
```

The loader accepts a single task object, a task array, or an object containing `tasks`. Each task contains a `token` and a `challenges` array. A challenge may define `unique_code`, `description`, `difficulty`, `level`, `total_score`, `flags`, and `container_addr`; Docker-backed challenges may also define `image`, `container_port`, and `docker_network`. `TSECBENCH_TASKS_JSON` is the inline-JSON alternative.

If no catalog is configured, a token-only task is created, but it contains no challenges to list.

### 4. Start the API

```bash
python main.py
```

Or run the exported ASGI application with Uvicorn:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

`main.py` initializes configuration, the SQLite database, and task state while importing `main:app`. Set configuration before starting the process.

## Configuration reference

`Settings.from_env()` loads the repository-root `.env` when it exists, without overriding variables already exported by the shell.

| Variable | Default | Purpose |
|---|---|---|
| `BENCHMARK_BASE_URL` | unset | Benchmark platform base URL exposed through runtime settings. |
| `BENCHMARK_TOKEN` | unset | Task token used for task loading and request authentication. |
| `TSECBENCH_CONFIG` | unset | Path to a JSON task catalog. |
| `TSECBENCH_TASKS_JSON` | unset | Inline JSON task catalog. |
| `TSECBENCH_DB_PATH` | `./data/tsecbench.sqlite3` | SQLite database path. |
| `TSECBENCH_DATABASE` | fallback only | Legacy database variable used when `TSECBENCH_DB_PATH` is unset. |
| `TSECBENCH_MAX_ACTIVE_CHALLENGES` | `3` | Maximum simultaneously active challenges; must be at least 1. |
| `TSECBENCH_PROVISIONER` | `static` | Provisioner mode: `static` or `docker`. |
| `HOST` | `0.0.0.0` | Host used by `python main.py`. |
| `PORT` | `8000` | Port used by `python main.py`; valid range is 1–65535. |

## Challenges API

All challenge routes are under `/openapi/v1/challenges` and require the task-issued `BENCHMARK_TOKEN` header:

```bash
curl \
  -H 'BENCHMARK_TOKEN: your-task-issued-token' \
  http://127.0.0.1:8000/openapi/v1/challenges
```

The normal workflow is:

1. `GET /openapi/v1/challenges` to list challenges and progress.
2. `POST /openapi/v1/challenges/start?unique_code=<code>` to start a challenge and obtain `container_addr`.
3. Connect to the challenge address through the required SSLVPN.
4. Optionally call `GET /openapi/v1/challenges/hint?unique_code=<code>`; hints reduce later scores.
5. Submit each flag with `POST /openapi/v1/challenges/submit`.
6. Call `POST /openapi/v1/challenges/close?unique_code=<code>` to release resources.

At most three challenges are active by default. Re-submitting a correct flag returns `duplicate`; expired or stopped tasks return `invalid_state`; missing or invalid tokens return `task_not_found`. See [`CHALLENGES_API.md`](CHALLENGES_API.md) for complete request/response and error contracts.

## Kali workspace

The Compose service builds and runs an interactive Kali headless container with the persistent `kali-data` volume mounted at `/workspace`:

```bash
docker compose build
docker compose up -d
docker compose ps
docker compose exec -it kali bash
```

Stop or restart without deleting the volume:

```bash
docker compose stop
docker compose start
```

Rebuild and start in one step:

```bash
docker compose up -d --build
```

The Compose file does not publish an API port, inject benchmark environment variables, or start Uvicorn. Do not run `docker compose down -v`; it deletes the persistent volume.

## Development and testing

Run the current test suite from the repository root:

```bash
python -m pytest -q
```

Tests use pytest and FastAPI `TestClient`. Endpoint tests create isolated SQLite databases with `tmp_path`; settings tests use temporary dotenv files and `monkeypatch`. Coverage includes authentication, challenge lifecycle, scoring, duplicate submissions, validation, resource limits, expiry, restart persistence, dotenv loading, and environment precedence.

There is no configured linter, formatter, coverage threshold, Makefile, lockfile, or CI workflow. Keep changes focused and add behavior tests for new observable contracts.

## Project layout

- `main.py` — ASGI application export and direct Uvicorn runner.
- `tsecbench/api.py` — FastAPI factory, routes, request/response models, and exception handlers.
- `tsecbench/config.py` — environment loading, validation, and task catalog loading.
- `tsecbench/models.py` — task/challenge/flag normalization and scoring helpers.
- `tsecbench/service.py` — authenticated business rules and lifecycle transitions.
- `tsecbench/store.py` — SQLite schema, transactions, persistence, and startup recovery.
- `tsecbench/provisioner.py` — static and Docker challenge provisioning.
- `tests/test_challenges_api.py` — endpoint and settings behavior tests.
- `.env.example` — safe configuration template; copy to local `.env`.
- `Dockerfile` and `docker-compose.yaml` — Kali workspace image and lifecycle.
