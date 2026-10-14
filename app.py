"""学生管理系统 — Flask 应用入口

单文件应用：路由 / 数据访问 / Prometheus 指标 / 混沌测试钩子 / 安全中间件。
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

from flask import (
    Flask,
    abort,
    g,
    has_app_context,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------------------------------------------------------------------
# 应用配置
# ---------------------------------------------------------------------------

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("student_management")

# 会话密钥：优先读环境变量；未配置时每次启动生成随机密钥。
# 随机兜底意味着重启后所有会话失效，但避免了硬编码密钥导致的会话伪造风险。
if os.environ.get("FLASK_SECRET_KEY"):
    app.secret_key = os.environ["FLASK_SECRET_KEY"]
else:
    app.secret_key = secrets.token_hex(32)
    logger.warning(
        "未设置 FLASK_SECRET_KEY，已生成随机密钥（重启后需重新登录）；生产环境请显式配置"
    )

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # 应用走 HTTP 时默认关闭，否则浏览器不会回传 cookie；HTTPS 部署设 SESSION_COOKIE_SECURE=1
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    MAX_CONTENT_LENGTH=1 * 1024 * 1024,  # 1MB，超限返回 413
    STUDENTS_PER_PAGE=20,
    CSRF_ENABLED=os.environ.get("CSRF_ENABLED", "1") == "1",
)

# 业务常量
MAX_NAME_LEN = 12
MAX_CLASS_LEN = 50
MIN_AGE = 0
MAX_AGE = 1000
MIN_PASSWORD_LEN = 5  # 既有集成用例使用 5 位密码（pass1），不可调高
MAX_PASSWORD_LEN = 128
MAX_USERNAME_LEN = 64
SAFE_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")
LIKE_ESCAPE = "\\"  # LIKE ESCAPE 子句使用的转义符

# 登录限流（在线爆破防护）：可用环境变量覆盖；LOGIN_RATE_LIMIT=0 关闭
LOGIN_RATE_LIMIT = os.environ.get("LOGIN_RATE_LIMIT", "1") == "1"
LOGIN_MAX_FAILS_USER = int(os.environ.get("LOGIN_MAX_FAILS_USER", "5"))
LOGIN_MAX_FAILS_IP = int(os.environ.get("LOGIN_MAX_FAILS_IP", "30"))
LOGIN_FAIL_WINDOW = int(os.environ.get("LOGIN_FAIL_WINDOW", "300"))  # 秒
LOGIN_LOCK_SECONDS = int(os.environ.get("LOGIN_LOCK_SECONDS", "60"))
LOGIN_LOCK_MAX_SECONDS = int(os.environ.get("LOGIN_LOCK_MAX_SECONDS", "900"))
LOGIN_ATTEMPT_TTL = 600  # 空闲条目的清理阈值，防止字典无限增长

# 校验错误与成功的提示文案
PAGE_MSG = {
    "added": "学生添加成功",
    "updated": "学生信息已更新",
    "deleted": "学生已删除",
}


# ---------------------------------------------------------------------------
# Prometheus 指标（先注册中间件，保证混沌钩子在其后执行）
# ---------------------------------------------------------------------------

REQUEST_COUNT = Counter("flask_http_request_total", "Total HTTP requests", ["path", "status"])
REQUEST_LATENCY = Histogram(
    "flask_http_request_duration_seconds", "HTTP request duration", ["path", "status"]
)
REGISTER_REQUESTS = Counter("register_requests_total", "Total register requests", ["status"])
LOGIN_REQUESTS = Counter("login_requests_total", "Total login requests", ["status"])
LOGIN_RATE_LIMITED = Counter(
    "login_rate_limited_total", "Login attempts rejected by the rate limiter", ["scope"]
)
ADD_STUDENT_REQUESTS = Counter("add_student_requests_total", "Total add student requests", ["status"])
IN_FLIGHT_REQUESTS = Gauge("in_flight_requests", "Number of in-flight requests", ["path"])
APP_UP = Gauge("app_up", "Application is up", [])
TOTAL_USERS = Gauge("total_users", "Total number of registered users", [])
TOTAL_STUDENTS = Gauge("total_students", "Total number of students", [])


def _metric_path() -> str:
    """指标标签使用路由模板（/students/<int:student_id>/edit），避免按 ID 产生无限标签。"""
    try:
        rule = request.url_rule
        if rule is not None:
            return rule.rule
    except RuntimeError:  # pragma: no cover - 请求上下文缺失
        pass
    return "unmatched"


@app.before_request
def before_request_monitor():
    request.start_time = time.time()
    request.metric_path = _metric_path()
    IN_FLIGHT_REQUESTS.labels(path=request.metric_path).inc()


@app.after_request
def after_request_monitor(response):
    if hasattr(request, "start_time"):
        duration = time.time() - request.start_time
        path = getattr(request, "metric_path", "unmatched")
        status = str(response.status_code)
        REQUEST_COUNT.labels(path=path, status=status).inc()
        REQUEST_LATENCY.labels(path=path, status=status).observe(duration)
        IN_FLIGHT_REQUESTS.labels(path=path).dec()

    # 安全响应头（不覆盖已有值）
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("X-XSS-Protection", "0")
    return response


# ---------------------------------------------------------------------------
# CSRF 防护（注册在混沌钩子之前：先校验，再决定是否注入故障）
# ---------------------------------------------------------------------------


def csrf_token() -> str:
    """返回（必要时生成）当前会话的 CSRF token，供表单渲染。"""
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["_csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


def _csrf_ok() -> bool:
    expected = session.get("_csrf_token")
    if not expected:
        return False
    supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-TOKEN", "")
    if not supplied:
        return False
    return hmac.compare_digest(str(supplied), str(expected))


def _same_origin() -> bool:
    """请求来源是否与本站一致（无 Origin/Referer 视为非浏览器客户端）。"""
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    if not origin:
        return True
    netloc = urlsplit(origin).netloc.lower()
    if not netloc:  # Origin: null 之类
        return False
    return netloc == request.host.lower()


@app.before_request
def csrf_protect():
    """校验不安全方法的 CSRF token。

    放行规则：
    - 测试模式（app.config['TESTING']）下不校验，保证既有用例语义不变；
    - `/chaos/*` 为测试专用控制接口，仅允许本机访问（见 chaos 蓝图）；
    - 携带 `X-Requested-With` 的非浏览器客户端（脚本/压测）走独立通道，
      但要求来源同源：跨站请求即使能带上该头（预检本就通常被拒），
      Origin 也必然对不上，仍会回落到 token 校验。
    """
    if request.method in SAFE_METHODS:
        return None
    if not app.config.get("CSRF_ENABLED", True):
        return None
    if app.config.get("TESTING"):
        return None
    if request.path.startswith("/chaos/"):
        return None
    if request.headers.get("X-Requested-With") and _same_origin():
        return None
    if _csrf_ok():
        return None
    logger.warning("CSRF 校验失败: %s %s", request.method, request.path)
    return render_template(
        "error.html",
        code=400,
        title="请求被拒绝",
        message="CSRF 校验失败，请刷新页面后重试。",
        user=session.get("user"),
    ), 400


# ---------------------------------------------------------------------------
# 混沌测试钩子（注册在 CSRF 之后：被拒绝的请求不再注入故障）
# ---------------------------------------------------------------------------

try:
    from chaos_test.chaos_api import chaos_bp, chaos_controller

    app.register_blueprint(chaos_bp)
    logger.info("混沌测试模块已加载")
except ImportError:  # pragma: no cover - 缺少混沌模块时降级运行
    logger.warning("混沌测试模块未找到")
    chaos_controller = None


@app.before_request
def chaos_before_request():
    """混沌故障注入：仅在启用时按概率注入延迟或错误。"""
    if request.path.startswith("/chaos/"):
        return
    if chaos_controller is None:
        return
    status = chaos_controller.status()
    if not status.get("enabled", False):
        return

    probability = float(status.get("probability", 0.1) or 0.1)
    if secrets.randbelow(1_000_000) / 1_000_000 >= probability:
        return

    failure_type = secrets.choice(["latency", "error"])
    if failure_type == "latency":
        delay = secrets.randbelow(2901) / 1000 + 0.1  # 0.1 ~ 3.0 秒
        time.sleep(delay)
        logger.warning("注入延迟 %.2fs", delay)
    else:
        code, message = secrets.choice(
            [
                (500, "Internal Server Error (Chaos)"),
                (503, "Service Unavailable (Chaos)"),
                (408, "Request Timeout (Chaos)"),
            ]
        )
        logger.warning("注入错误 %s %s", code, message)
        abort(code, description=message)


# ---------------------------------------------------------------------------
# 数据库
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "student_management.db"


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")  # 等锁而非直接抛 database is locked
    try:
        # WAL：读写不互相阻塞，写事务不再卡住指标线程/并发读
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    except sqlite3.Error as exc:  # pragma: no cover - 降级为默认日志模式
        logger.debug("设置 WAL 失败（保持默认模式）: %s", exc)


def get_db_connection():
    """返回一个新的 SQLite 连接（并发测试与脚本直接使用）。"""
    conn = sqlite3.connect(str(DB_FILE), timeout=10)
    _configure_connection(conn)
    return conn


@contextmanager
def db_session():
    """事务边界：自动 commit / rollback。

    在请求（或其它 app 上下文）内，同一线程复用 `g` 上的同一条连接，
    `teardown_appcontext` 统一关闭 —— 一次渲染从 2~3 次开关连接降为 1 次。
    没有 app 上下文时（脚本、后台线程）退化为一次性连接，用完即关。
    """
    if not has_app_context():
        conn = get_db_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return

    conn = getattr(g, "_db_conn", None)
    db_path = str(DB_FILE)
    if conn is not None and getattr(g, "_db_path", None) != db_path:
        # 测试夹具切换了 DB_FILE：旧连接必须立刻关闭，否则句柄指向已删除的临时库
        _close_request_connection()
        conn = None
    if conn is None:
        conn = get_db_connection()
        g._db_conn = conn
        g._db_path = db_path
        g._db_depth = 0

    outermost = g._db_depth == 0
    g._db_depth += 1
    try:
        yield conn
        if outermost:
            conn.commit()
    except Exception:
        if outermost:
            conn.rollback()
        raise
    finally:
        g._db_depth -= 1


def _close_request_connection() -> None:
    conn = getattr(g, "_db_conn", None)
    if conn is None:
        return
    depth = getattr(g, "_db_depth", 0)
    if depth:
        logger.warning("请求结束时仍有 %d 层 db_session 未退出", depth)
    try:
        conn.close()
    except sqlite3.Error:  # pragma: no cover - 关闭失败不应影响响应
        logger.debug("关闭请求级数据库连接失败", exc_info=True)
    g._db_conn = None
    g._db_path = None
    g._db_depth = 0


@app.teardown_appcontext
def _teardown_db(_exception=None):
    if getattr(g, "_db_conn", None) is not None:
        _close_request_connection()


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with db_session() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                class_name TEXT NOT NULL
            )
            """
        )


# ---------------------------------------------------------------------------
# 密码与校验
# ---------------------------------------------------------------------------


HASH_METHOD = os.environ.get("PASSWORD_HASH_METHOD", "pbkdf2:sha256:600000")


def hash_password(password: str) -> str:
    """加盐哈希。

    默认 pbkdf2:sha256:600000：与 scrypt 相比无大块内存分配，
    并发注册时不会触发 OpenSSL 的 malloc failure（本机已复现）。
    可用 PASSWORD_HASH_METHOD 环境变量覆盖。
    """
    return generate_password_hash(password, method=HASH_METHOD)


def _is_legacy_hash(stored: str) -> bool:
    return len(stored) == 64 and all(c in "0123456789abcdef" for c in stored.lower())


def verify_password(stored: str, candidate: str) -> bool:
    """校验密码，兼容历史 SHA-256 记录（无副作用，升级由登录路由负责）。"""
    if not stored or not candidate:
        return False
    if _is_legacy_hash(stored):
        legacy = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy, stored)
    try:
        return check_password_hash(stored, candidate)
    except ValueError:
        return False


def upgrade_password_hash(username: str, candidate: str, old_hash: str) -> None:
    """把旧的 SHA-256 记录升级为加盐哈希（登录成功时静默执行）。"""
    if not username:
        return
    try:
        with db_session() as conn:
            row = conn.execute(
                "SELECT password FROM users WHERE username = ?", (username,)
            ).fetchone()
            if row and row["password"] == old_hash:
                conn.execute(
                    "UPDATE users SET password = ? WHERE username = ?",
                    (hash_password(candidate), username),
                )
    except Exception as exc:  # 升级失败不应阻断登录
        logger.warning("密码哈希升级失败: %s", exc)


def validate_password(password: str) -> str | None:
    if not password:
        return "密码不能为空"
    if len(password) < MIN_PASSWORD_LEN:
        return f"密码长度至少{MIN_PASSWORD_LEN}位"
    if len(password) > MAX_PASSWORD_LEN:
        return f"密码长度不能超过{MAX_PASSWORD_LEN}位"
    return None


def validate_student(name: str, age_raw, class_name: str) -> tuple[int, str | None]:
    """返回 (age, error)。age 仅在校验通过时有效。"""
    if not name:
        return 0, "姓名不能为空"
    if len(name) > MAX_NAME_LEN:
        return 0, f"姓名长度不能超过{MAX_NAME_LEN}个字符"
    if not class_name:
        return 0, "班级不能为空"
    if len(class_name) > MAX_CLASS_LEN:
        return 0, f"班级长度不能超过{MAX_CLASS_LEN}个字符"
    try:
        age = int(str(age_raw).strip())
    except (TypeError, ValueError):
        return 0, "年龄必须是整数"
    if age < MIN_AGE:
        return 0, "年龄不能为负数"
    if age > MAX_AGE:
        return 0, f"年龄必须在{MIN_AGE}~{MAX_AGE}之间"
    return age, None


def is_logged_in() -> bool:
    return bool(session.get("user"))


def require_login():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    return None


# ---------------------------------------------------------------------------
# 页面渲染辅助
# ---------------------------------------------------------------------------


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符，使 % 和 _ 按字面量匹配（配合 ESCAPE '\'）。"""
    esc = LIKE_ESCAPE
    return value.replace(esc, esc * 2).replace("%", f"{esc}%").replace("_", f"{esc}_")


def _list_students(q: str, page: int):
    """分页 + 关键字查询（姓名/班级模糊匹配，通配符按字面量处理）。"""
    per_page = int(app.config["STUDENTS_PER_PAGE"])
    where, params = "", []
    if q:
        where = " WHERE name LIKE ? ESCAPE '\\' OR class_name LIKE ? ESCAPE '\\'"
        like = f"%{_escape_like(q)}%"
        params = [like, like]

    with db_session() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM students{where}", params).fetchone()[0]
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        rows = conn.execute(
            f"SELECT id, name, age, class_name FROM students{where}"
            " ORDER BY id DESC LIMIT ? OFFSET ?",
            [*params, per_page, (page - 1) * per_page],
        ).fetchall()
    return rows, {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "pages": _page_window(page, total_pages),
    }


def _page_window(page: int, total_pages: int, radius: int = 2) -> list:
    """生成带省略号的页码序列，避免页数多时渲染成一长串链接。

    例：_page_window(7, 20) -> [1, '…', 5, 6, 7, 8, 9, '…', 20]
    """
    if total_pages <= 1:
        return [page]
    candidates = {1, total_pages, *range(page - radius, page + radius + 1)}
    ordered = sorted(n for n in candidates if 1 <= n <= total_pages)
    window: list = []
    prev = 0
    for num in ordered:
        if prev and num - prev > 1:
            window.append("…")
        window.append(num)
        prev = num
    return window


def _count_totals() -> dict:
    with db_session() as conn:
        students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    return {"students": students, "users": users}


def render_index(
    error: str | None = None,
    msg: str | None = None,
    status: int = 200,
    edit_student=None,
):
    """渲染学生列表页（新增/编辑/校验失败共用）。"""
    q = (request.args.get("q") or "").strip()
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    students, pagination = _list_students(q, page)
    return (
        render_template(
            "index.html",
            students=students,
            edit_student=edit_student,
            user=session["user"],
            error=error,
            msg=PAGE_MSG.get(msg or ""),
            q=q,
            pagination=pagination,
            stats=_count_totals(),
        ),
        status,
    )


# ---------------------------------------------------------------------------
# 登录限流（进程内存态：单进程部署够用，多进程需换成共享存储）
# ---------------------------------------------------------------------------

_login_attempts: dict[str, dict[str, float]] = {}
_login_attempts_lock = threading.Lock()


def _attempt_limit(key: str) -> int:
    return LOGIN_MAX_FAILS_USER if key.startswith("user:") else LOGIN_MAX_FAILS_IP


def _login_keys(username: str) -> list[str]:
    return [f"user:{username.lower()}", f"ip:{request.remote_addr or 'unknown'}"]


def _prune_attempts(now: float) -> None:
    """清理长时间无活动且未锁定的条目，避免字典被爆破脚本撑大。"""
    if len(_login_attempts) < 1024:
        return
    stale = [
        key
        for key, entry in _login_attempts.items()
        if now - entry["last"] > LOGIN_ATTEMPT_TTL and entry["locked_until"] <= now
    ]
    for key in stale:
        _login_attempts.pop(key, None)


def _login_lock_remaining(keys: list[str]) -> tuple[int, str] | None:
    """返回 (剩余秒数, 触发限流的作用域)，未被锁定时返回 None。"""
    if not LOGIN_RATE_LIMIT:
        return None
    now = time.time()
    with _login_attempts_lock:
        _prune_attempts(now)
        worst = None
        for key in keys:
            entry = _login_attempts.get(key)
            if not entry:
                continue
            remaining = entry["locked_until"] - now
            if remaining > 0:
                scope = key.split(":", 1)[0]
                if worst is None or remaining > worst[0]:
                    worst = (int(remaining) + 1, scope)
        return worst


def _record_login_failure(keys: list[str]) -> None:
    if not LOGIN_RATE_LIMIT:
        return
    now = time.time()
    with _login_attempts_lock:
        _prune_attempts(now)
        for key in keys:
            entry = _login_attempts.get(key)
            if entry is None or now - entry["last"] > LOGIN_FAIL_WINDOW:
                entry = {"fails": 0.0, "last": now, "locked_until": 0.0}
                _login_attempts[key] = entry
            entry["fails"] += 1
            entry["last"] = now
            limit = _attempt_limit(key)
            if entry["fails"] >= limit:
                overshoot = int(entry["fails"]) - limit
                lock_for = min(LOGIN_LOCK_SECONDS * (2**overshoot), LOGIN_LOCK_MAX_SECONDS)
                entry["locked_until"] = now + lock_for
                logger.warning(
                    "登录限流触发 %s: 连续失败 %d 次，锁定 %d 秒", key, int(entry["fails"]), lock_for
                )


def _clear_login_failures(username: str) -> None:
    """登录成功后清掉该用户的失败计数（IP 维度保留，防止换号继续爆破）。"""
    with _login_attempts_lock:
        _login_attempts.pop(f"user:{username.lower()}", None)


def _reset_login_attempts() -> None:
    """测试夹具用：清空限流状态。"""
    with _login_attempts_lock:
        _login_attempts.clear()


# ---------------------------------------------------------------------------
# 认证路由
# ---------------------------------------------------------------------------


@app.get("/register")
def register_page():
    return render_template(
        "auth.html",
        mode="register",
        error=None,
        toast=None,
        redirect_to=None,
        user=session.get("user"),
    )


@app.post("/register")
def register_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    def page(error: str | None, toast: str | None = None):
        return render_template(
            "auth.html",
            mode="register",
            error=error,
            toast=toast,
            redirect_to=None,
            user=session.get("user"),
        )

    if not username or not password:
        REGISTER_REQUESTS.labels(status="fail").inc()
        return page("用户名和密码不能为空")
    if len(username) > MAX_USERNAME_LEN:
        REGISTER_REQUESTS.labels(status="fail").inc()
        return page(f"用户名长度不能超过{MAX_USERNAME_LEN}个字符")
    pwd_error = validate_password(password)
    if pwd_error:
        REGISTER_REQUESTS.labels(status="fail").inc()
        return page(pwd_error)

    try:
        with db_session() as conn:
            exists = conn.execute(
                "SELECT 1 FROM users WHERE username = ?", (username,)
            ).fetchone()
            if exists:
                REGISTER_REQUESTS.labels(status="fail").inc()
                return page("用户名已存在")
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hash_password(password)),
            )
    except sqlite3.IntegrityError:
        REGISTER_REQUESTS.labels(status="fail").inc()
        return page("用户名已存在")
    except sqlite3.Error:
        REGISTER_REQUESTS.labels(status="fail").inc()
        logger.exception("注册失败")
        return page("系统繁忙，请稍后重试")

    logger.info("注册成功: %s", username)
    REGISTER_REQUESTS.labels(status="success").inc()
    return page(None, toast="注册成功")


@app.get("/login")
def login_page():
    if is_logged_in():
        return redirect(url_for("index"))
    toast = request.args.get("toast")
    return render_template(
        "auth.html",
        mode="login",
        error=None,
        toast=toast,
        redirect_to=None,
        user=session.get("user"),
    )


@app.post("/login")
def login_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    def page(error: str | None, toast: str | None = None, redirect_to=None, status: int = 200):
        response = make_response(
            render_template(
                "auth.html",
                mode="login",
                error=error,
                toast=toast,
                redirect_to=redirect_to,
                user=session.get("user"),
            ),
            status,
        )
        return response

    if not username or not password:
        LOGIN_REQUESTS.labels(status="fail").inc()
        return page("用户名和密码不能为空")

    # 在线爆破防护：先判断是否处于锁定窗口，再校验凭证
    lock = _login_lock_remaining(_login_keys(username))
    if lock is not None:
        seconds, scope = lock
        LOGIN_RATE_LIMITED.labels(scope=scope).inc()
        LOGIN_REQUESTS.labels(status="limited").inc()
        logger.warning("登录被限流: user=%s scope=%s 剩余 %ds", username, scope, seconds)
        response = page(
            f"登录尝试过于频繁，请 {seconds} 秒后再试", status=429
        )
        response.headers["Retry-After"] = str(seconds)
        return response

    with db_session() as conn:
        user = conn.execute(
            "SELECT id, username, password FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    stored_hash = user["password"] if user else None
    if not stored_hash or not verify_password(stored_hash, password):
        LOGIN_REQUESTS.labels(status="fail").inc()
        _record_login_failure(_login_keys(username))
        logger.info("登录失败: %s", username)
        return page("用户名或密码错误")

    # 旧算法（legacy SHA-256 / scrypt）在登录成功后平滑迁移到当前算法
    if stored_hash.split("$", 1)[0] != HASH_METHOD:
        upgrade_password_hash(username, password, stored_hash)

    # 防止会话固定：登录前清空旧会话
    session.clear()
    session["user"] = {"id": user["id"], "username": user["username"]}
    _clear_login_failures(username)
    LOGIN_REQUESTS.labels(status="success").inc()
    logger.info("登录成功: %s", username)
    return page(None, toast="登录成功，正在跳转...", redirect_to=url_for("index"))


@app.post("/logout")
def logout():
    guard = require_login()
    if guard is not None:
        return guard
    session.clear()
    return redirect(url_for("login_page"))


# ---------------------------------------------------------------------------
# 学生管理路由
# ---------------------------------------------------------------------------


@app.get("/")
def index():
    guard = require_login()
    if guard is not None:
        return guard
    return render_index()[0]


@app.post("/students")
def add_student():
    guard = require_login()
    if guard is not None:
        return guard

    name = request.form.get("name", "").strip()
    class_name = request.form.get("class_name", "").strip()
    age, error = validate_student(name, request.form.get("age", ""), class_name)
    if error:
        ADD_STUDENT_REQUESTS.labels(status="fail").inc()
        return render_index(error=error)

    try:
        with db_session() as conn:
            conn.execute(
                "INSERT INTO students (name, age, class_name) VALUES (?, ?, ?)",
                (name, age, class_name),
            )
    except sqlite3.Error:
        ADD_STUDENT_REQUESTS.labels(status="fail").inc()
        logger.exception("添加学生失败")
        return render_index(error="系统繁忙，请稍后重试")

    ADD_STUDENT_REQUESTS.labels(status="success").inc()
    return redirect(url_for("index", msg="added"))


@app.get("/students/<int:student_id>/edit")
def edit_student_page(student_id: int):
    guard = require_login()
    if guard is not None:
        return guard

    with db_session() as conn:
        edit_student = conn.execute(
            "SELECT id, name, age, class_name FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
    if edit_student is None:
        abort(404)

    return render_index(edit_student=edit_student)


@app.post("/students/<int:student_id>")
def edit_student_submit(student_id: int):
    guard = require_login()
    if guard is not None:
        return guard

    name = request.form.get("name", "").strip()
    class_name = request.form.get("class_name", "").strip()
    age, error = validate_student(name, request.form.get("age", ""), class_name)
    if error:
        return render_index(error=error)

    with db_session() as conn:
        exists = conn.execute(
            "SELECT 1 FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if not exists:
            return render_index(error="学生不存在或已被删除")
        conn.execute(
            "UPDATE students SET name = ?, age = ?, class_name = ? WHERE id = ?",
            (name, age, class_name, student_id),
        )
    return redirect(url_for("index", msg="updated"))


@app.post("/students/<int:student_id>/delete")
def delete_student(student_id: int):
    guard = require_login()
    if guard is not None:
        return guard

    with db_session() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return redirect(url_for("index", msg="deleted"))


# ---------------------------------------------------------------------------
# 监控与错误页
# ---------------------------------------------------------------------------


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.errorhandler(404)
def not_found(_error):
    return (
        render_template(
            "error.html",
            code=404,
            title="页面不存在",
            message="您访问的页面不存在或已被删除。",
            user=session.get("user"),
        ),
        404,
    )


@app.errorhandler(400)
def bad_request(_error):
    return (
        render_template(
            "error.html",
            code=400,
            title="请求错误",
            message="请求参数不合法。",
            user=session.get("user"),
        ),
        400,
    )


@app.errorhandler(413)
def too_large(_error):
    return (
        render_template(
            "error.html",
            code=413,
            title="请求内容过大",
            message="提交的内容超过大小限制。",
            user=session.get("user"),
        ),
        413,
    )


@app.errorhandler(500)
def internal_error(_error):
    return (
        render_template(
            "error.html",
            code=500,
            title="服务器繁忙",
            message="服务器开小差了，请稍后重试。",
            user=session.get("user"),
        ),
        500,
    )


# ---------------------------------------------------------------------------
# 后台指标线程（仅直接启动时运行）
# ---------------------------------------------------------------------------


def update_system_metrics():
    """定期更新系统状态指标。"""

    def update_loop():
        while True:
            try:
                APP_UP.set(1)
                with db_session() as conn:
                    TOTAL_USERS.set(
                        conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                    )
                    TOTAL_STUDENTS.set(
                        conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
                    )
            except Exception as exc:
                logger.warning("更新指标失败: %s", exc)
            time.sleep(10)

    thread = threading.Thread(target=update_loop, daemon=True, name="metrics-updater")
    thread.start()


if __name__ == "__main__":
    # ---- SkyWalking APM 接入（仅直接启动时启用，pytest 导入 app.py 不受影响） ----
    try:
        from skywalking import agent as sw_agent, config as sw_config

        sw_config.init(
            agent_collector_backend_services="127.0.0.1:11800",
            agent_name="student-management",
            agent_instance_name="sm-5000",
        )
        sw_agent.start()
        logger.info("SkyWalking agent 已启动 -> 127.0.0.1:11800")
    except Exception as exc:
        logger.warning("SkyWalking agent 启动失败（不影响业务）: %s", exc)

    init_db()
    update_system_metrics()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        use_reloader=False,
    )
