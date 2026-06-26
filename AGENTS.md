# AGENTS.md

## What this is

Python + Flask student management system with SQLite. Single-file app (`app.py`), server-side rendered templates, Prometheus metrics, chaos testing blueprint.

## Commands

```bash
# Install deps
pip install -r requirements.txt
pip install -r requirements_test.txt  # for testing

# Run the app (port 5000)
python app.py

# Run all pytest tests (from project root)
python -m pytest -v

# Run a single test file
python -m pytest unit_test/test_app.py -v

# Run tests for one marker
python -m pytest -m unit -v
python -m pytest -m api -v

# Unified test executor (manages Flask server lifecycle)
python test_executor/test_runner.py
python test_executor/test_runner.py --stage unit  # single stage
python test_executor/test_runner.py --stage api --stage integration  # multiple

# Available stages: smoke, unit, db, contract, crud, api, integration, security, reliability, automation, performance, chaos
```

## Test infrastructure

- `conftest.py` (root): Shared fixtures. `client` fixture creates a **fresh temp DB per test function** by monkey-patching `app_module.DB_FILE`. This means tests are isolated but rely on this patch — do not hardcode DB paths in tests.
- `logged_in_client` fixture: Registers + logs in `testuser`/`testpass123` automatically.
- `pytest.ini` testpaths: `unit_test api_test integration_test security_test smoke_test db_test contract_test crud_test reliability_test`.
- Each test subdirectory (`api_test/`, `integration_test/`, `security_test/`) has its own `conftest.py` — check before adding shared fixtures.

## Key architecture

- `app.py`: All routes, DB init, Prometheus metrics, chaos hook. Runs on `0.0.0.0:5000`.
- DB: SQLite at `data/student_management.db` (auto-created). Tables: `users`, `students`.
- Chaos module: `chaos_test/chaos_api.py` registered as Flask blueprint. Skipped gracefully if import fails.
- Metrics: `/metrics` endpoint using `prometheus_client` (not the `prometheus-flask-exporter` package from requirements).
- Email config: `email_config.py` is **gitignored**. Copy `email_config.py.example` and fill in real credentials. Test executor falls back to placeholders without it.

## Gotchas

- SQL placeholder is `?` (SQLite). If migrating to MySQL, change to `%s`.
- `requirements.txt` has minimal deps (flask + prometheus). `requirements_test.txt` adds pytest/cov/xdist/requests.
- CI (`.github/workflows/ci.yml`) only runs `unit_test/test_app.py` — other test suites are manual.
- The test executor kills any process on port 5000 before starting the server. Don't run it alongside a dev server you want to keep.
- `app.py` has `debug=True` but `use_reloader=False` — the reloader is disabled intentionally to avoid double-start issues with the test executor.
