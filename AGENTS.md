# AGENTS.md

## What this is

Flask 3 + SQLite student management system. All app logic lives in one file (`app.py`, ~1000 lines); UI is four Jinja templates (`templates/base.html` layout shell + `auth.html` / `index.html` / `error.html`) + `static/style.css` — no JS framework, no build step, no npm. Everything else (`*_test/`, `test_executor/`, `monitoring/`, `chaos_test/`, `performance_test_*`, `mq_sender/`, `automation_test/`) is test and observability tooling wrapped around it.

## Commands

```bash
pip install -r requirements.txt
pip install -r requirements_test.txt        # pytest/cov/xdist/requests

python app.py                               # dev server, 0.0.0.0:5000

python -m pytest smoke_test -q              # fast, in-process (no server needed)
python -m pytest unit_test/test_app.py -v   # what CI runs
python -m pytest -m unit -v                 # by marker (see pytest.ini)

# Unified executor: starts/kills the server, runs stages, writes reports, emails them
python test_executor/test_runner.py
python test_executor/test_runner.py --stage unit --stage api
# flags: --no-start-server --no-stop-server --no-email
# stages (EXECUTION_ORDER in test_executor/config.py):
#   smoke unit db contract crud api integration security reliability automation performance chaos
```

## Which tests need a live server

- **In-process** (use the `client` fixture, always safe): `unit_test smoke_test db_test contract_test crud_test integration_test security_test reliability_test`. All 123 of these currently pass clean.
- **HTTP against `http://localhost:5000`**: `api_test` only (plus `performance_test_locust`, `chaos_test/run_chaos_test.py`, `automation_test`). `api_test` fails with `ConnectionError` unless something is serving on 5000.
- So `python -m pytest` from the root (pytest.ini testpaths include `api_test`) fails on a clean machine. Start `python app.py` first, or exclude `api_test`.

## Test infrastructure

- Root `conftest.py`: `client` swaps `app_module.DB_FILE` to a fresh temp DB **per test function** — never hardcode a DB path in a test. `logged_in_client` auto-registers/logs in `testuser`/`testpass123`. `module_client` exists for perf-sensitive tests (module-scoped DB). An autouse fixture clears the in-process login rate-limiter between tests (`_reset_login_attempts`) — rate limiting is *not* disabled under `TESTING`. Fixtures are Chinese-docstring'd; source is UTF-8.
- Sub-dirs (`api_test/`, `integration_test/`, `security_test/`) have their own `conftest.py`; `api_test/conftest.py` writes `api_test/reports/api_test_report_*.{json,md}` on every session finish.
- `security_test` assertions are mostly `assert response.status_code in [200, 302]` — a green security suite is a smoke test, not proof of safety.
- Some suites claim to need a server but don't: `test_executor/config.py` `TEST_STAGES[*]["path"]` is partly stale (e.g. `automation_test/test_playwright.py` does not exist; the runner actually executes `automation_test/cli.py run` / Locust / `run_chaos_test.py`). Trust `test_runner.py`, not the config paths.
- CI (`.github/workflows/ci.yml`) runs only `unit_test/test_app.py` + a `from app import app` import check, on Python 3.11.

## Key architecture

- `app.py` layout (approx line numbers): config/secret key/cookies (41–75) → Prometheus metrics (93–104) → request/response hooks (117–140) → CSRF + `_same_origin` (146–211) → chaos blueprint registration + hook (217–260) → DB layer (263–367) → password/validation helpers (371–456) → login rate limiter (587–666) → routes (670–900) → error handlers → metrics thread + SkyWalking → `__main__` (1006).
- **`init_db()` is only called under `if __name__ == "__main__"` (line ~1006)** — importing `app` in a script/test does not create tables; call `init_db()` yourself (conftest does).
- DB: SQLite `data/student_management.db` (`data/` is gitignored, auto-created on start). Tables: `users`, `students`. Placeholder is `?`. Connections run `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=10000`. `db_session()` is a contextmanager doing commit/rollback per unit of work: **inside an app context it reuses one connection stored on `g`** (closed by `@app.teardown_appcontext`), outside it (scripts, the metrics thread) it opens a fresh connection and closes it. The path check in `db_session` matters — the `client` fixture rewrites `DB_FILE` per test. `get_db_connection()` is always a raw one-off connection (tests open these directly and close them themselves).
- Auth: `require_login()` guard on every student route; `session["user"]` is `{"id", "username"}`; `session.clear()` on login (session fixation) and logout. Passwords are **werkzeug `generate_password_hash` with `pbkdf2:sha256:600000`** (`HASH_METHOD`, overridable via `PASSWORD_HASH_METHOD` env) — deliberately *not* the default `scrypt`, which throws `ValueError: [digital envelope routines] malloc failure` under concurrent hashing on this machine's OpenSSL. `verify_password` accepts legacy unsalted SHA-256 (64-hex) and old scrypt hashes; any stored hash whose method differs from `HASH_METHOD` is silently re-hashed on successful login (`upgrade_password_hash`). `MIN_PASSWORD_LEN = 5` (integration cases use 5-char `pass1` — do not raise it).
- Login rate limiting: in-process dict keyed by `user:<name>` (5 fails/5 min → lock, doubling to 900s) and `ip:<addr>` (30 fails → lock); locked requests get **429 + `Retry-After`** and increment `login_rate_limited_total{scope}`. Knobs: `LOGIN_RATE_LIMIT` (0 disables), `LOGIN_MAX_FAILS_USER`, `LOGIN_MAX_FAILS_IP`, `LOGIN_FAIL_WINDOW`, `LOGIN_LOCK_SECONDS`, `LOGIN_LOCK_MAX_SECONDS`. Empty-field submissions are not counted; a successful login clears only the *user* key (IP key persists). Single-process only — a multi-worker deploy would need shared state.
- Session secret: `FLASK_SECRET_KEY` env, else a **random per-process key** (logged as a warning) — no hardcoded fallback, so restarts log everyone out unless the env var is set. `SESSION_COOKIE_SECURE` defaults to 0 (app is HTTP); set `SESSION_COOKIE_SECURE=1` behind TLS.
- CSRF: `csrf_protect` `before_request` checks form `csrf_token` or `X-CSRF-TOKEN` header on unsafe methods. **Bypasses**: `app.config['TESTING']` (all pytest runs), `CSRF_ENABLED=0` env, `/chaos/*`, and `X-Requested-With` **only when `_same_origin()` holds** (no Origin/Referer, or netloc equals `request.host`). Templates emit `{{ csrf_token() }}` — non-browser clients must scrape it or set `X-Requested-With` from the same origin.
- Metrics: `/metrics` via `prometheus_client` directly, **unauthenticated**. Path labels use `request.url_rule.rule` (`_metric_path`, line 121) — do not "fix" this back to `request.path`, it was a deliberate cardinality fix. `prometheus_client` is only a transitive dep of `prometheus-flask-exporter` in `requirements.txt` — don't drop that line without adding `prometheus_client`.
- Chaos: `chaos_test/chaos_api.py` blueprint, in-memory state in the server process. `/chaos/*` is **restricted to loopback or `X-Chaos-Token: $CHAOS_API_TOKEN`** (403 otherwise). When enabled, `app.py` `chaos_before_request` (228) sleeps 0.1–3s or aborts with 500/503/408 on ~10% of requests, on every route except `/chaos/*`. If a test enables chaos and never stops it, all later traffic against that server is randomly broken.
- Rendering: all pages extend `templates/base.html` (sidebar + topbar + `user-chip` + logout form). `render_index()` is the single entry for the student list (handles `q` search — LIKE wildcards escaped via `_escape_like` + `ESCAPE '\'`, `page`, `stats`, edit row, toasts). Pagination renders a collapsed window (`_page_window` → `pagination.pages`, `'…'` separators) plus 上一页/下一页. Zero rows shows `.empty-state` (different copy for "no data" vs "no search hit"). Errors 404/400/413/500 render `error.html`.
- The metrics updater thread and the SkyWalking APM agent (optional dep, not in requirements, guarded import) start only when `python app.py` runs directly.
- Email: `email_config.py` is gitignored; copy `email_config.py.example`. Without it the executor falls back to placeholders and warns. The `.env` file is not read by any code — config comes from `os.environ` only.

## Gotchas

- `test_executor/test_runner.py` **force-kills whatever holds port 5000** before starting its own server — never run it alongside a dev server you want to keep.
- `performance_test_jmeter/delete_performanceTesting_data.py` hardcodes a DB path from a different machine (`c:\Users\Administrator\Documents\trae_projects\test\...`); it will not clean this repo's data until the path is fixed.
- `app.py` runs `debug=os.environ.get("FLASK_DEBUG","0")=="1", use_reloader=False`; the reloader is off on purpose (double-start breaks the executor).
- Source files are UTF-8; the Windows console is GBK, so Chinese in logs/reports often renders as `�?` or blocks. That's display-only — do not re-encode files to "fix" it.
- `python` on PATH here is `C:\Python\python.exe` (3.14). The committed `.venv` exists but is not what a plain `python` resolves to.
- Releases are recorded in `VERSION.md` and the version table at the top of `README.md` (commits are tagged `vX.Y.Z:`). Current: v1.12.0.
- The working tree carries an uncommitted UI + security overhaul (app.py, templates, style.css, several test files). Run `git status`/`git diff` before assuming HEAD matches disk.

## Current focus

Two standing goals for this repo — check these before calling work done:

1. **UI / layout** — landed: `base.html` sidebar/topbar shell, `stat-grid` cards, `.card`/`.table`/`.btn` patterns in `style.css`, `error.html` pages, unified `label + input + .field-hint` field pattern with `.error-text[role=alert]` / `.toast[role=status]` on both auth and index (no JS validation — HTML5 `required`/`minlength` plus server-side `validate_*`), `.empty-state` for zero students vs zero search hits, collapsed pagination window, `.table-wrap` horizontal scroll, breakpoints at 900px and 640px. Still open: a dark-theme toggle, and per-field inline error messages (errors are still page-level banners).
2. **Quality pass** — landed: salted passwords + legacy upgrade, `FLASK_SECRET_KEY` with a random per-process fallback, `SESSION_COOKIE_SECURE` switch, CSRF with same-origin check on the `X-Requested-With` channel, chaos loopback/token guard, route-template metric labels, `validate_student`/`validate_password` on all input, pagination + search with escaped LIKE wildcards, WAL + busy_timeout + request-scoped connection reuse, login rate limiting with 429/Retry-After, error handlers, security headers (`X-Content-Type-Options` etc. in `after_request`). Still open:
   - `/metrics` is unauthenticated (scrape it from an internal network only, or put it behind the proxy).
   - `MIN_PASSWORD_LEN = 5` and no complexity rule — kept because integration fixtures use `pass1`.
   - rate-limit state is per-process; horizontal scaling needs Redis/shared storage.
   - no password reset / account lockout UI — a locked user just waits out the window.
