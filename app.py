import hashlib
import sqlite3
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST


app = Flask(__name__)
app.secret_key = "student-management-secret"

# 集成混沌测试
try:
    from chaos_test.chaos_api import chaos_bp, chaos_controller
    app.register_blueprint(chaos_bp)
    print("[CHAOS] 混沌测试模块已加载")
except ImportError:
    print("[CHAOS] 混沌测试模块未找到")
    chaos_controller = None

# 全局混沌测试钩子
@app.before_request
def chaos_before_request():
    import random
    from flask import abort, request
    
    # 跳过混沌测试API端点
    if request.path.startswith('/chaos/'):
        return
    
    # 如果混沌控制器未加载，跳过
    if chaos_controller is None:
        return
        
    # 获取当前混沌测试状态
    status = chaos_controller.status()
    if not status.get('enabled', False):
        return
        
    probability = status.get('probability', 0.1)
    
    if random.random() < probability:
        failure_type = random.choice(['latency', 'error'])
        
        if failure_type == 'latency':
            delay = random.uniform(0.1, 3)
            import time
            time.sleep(delay)
            print(f"[CHAOS] 注入延迟: {delay:.2f}s")
            
        elif failure_type == 'error':
            errors = [
                {'code': 500, 'message': 'Internal Server Error (Chaos)'},
                {'code': 503, 'message': 'Service Unavailable (Chaos)'},
                {'code': 408, 'message': 'Request Timeout (Chaos)'}
            ]
            error = random.choice(errors)
            print(f"[CHAOS] 注入错误: {error['code']} - {error['message']}")
            abort(error['code'], description=error['message'])

# Prometheus 监控指标 - 兼容官方 Grafana 模板
metrics = PrometheusMetrics(app)

# 通用指标（兼容官方模板）
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['endpoint', 'method', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request duration', ['endpoint', 'method'])

# 应用特定指标
APP_REQUEST_COUNT = Counter('app_requests_total', 'Total app requests', ['endpoint', 'method', 'status'])
APP_REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'App request latency', ['endpoint'])

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "student_management.db"


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
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
        conn.commit()


def hash_password(password: str):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def is_logged_in():
    return bool(session.get("user"))


@app.get("/register")
def register_page():
    return render_template("auth.html", mode="register", error=None, toast=None, redirect_to=None)


@app.post("/register")
def register_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    print(f"[SERVER DEBUG] 收到注册请求: username={username}, password={password}")

    if not username or not password:
        return render_template(
            "auth.html",
            mode="register",
            error="用户名和密码不能为空",
            toast=None,
            redirect_to=None,
        )

    with get_db_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    print(f"[SERVER DEBUG] 用户 {username} 是否存在: {exists}")
    
    if exists:
        print(f"[SERVER DEBUG] 用户 {username} 已存在，返回错误")
        return render_template(
            "auth.html",
            mode="register",
            error="用户名已存在",
            toast=None,
            redirect_to=None,
        )

    print(f"[SERVER DEBUG] 开始插入用户 {username}")
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hash_password(password)),
        )
        conn.commit()
    print(f"[SERVER DEBUG] 用户 {username} 插入成功")
    
    return render_template(
        "auth.html",
        mode="register",
        error=None,
        toast="注册成功",
        redirect_to=None,
    )


@app.get("/login")
def login_page():
    if is_logged_in():
        return redirect(url_for("index"))
    toast = request.args.get("toast")
    return render_template("auth.html", mode="login", error=None, toast=toast, redirect_to=None)


@app.post("/login")
def login_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT id, username, password FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if not user or user["password"] != hash_password(password):
        return render_template(
            "auth.html",
            mode="login",
            error="用户名或密码错误",
            toast=None,
            redirect_to=None,
        )

    session["user"] = {"id": user["id"], "username": user["username"]}
    return render_template(
        "auth.html",
        mode="login",
        error=None,
        toast="登录成功，正在跳转...",
        redirect_to=url_for("index"),
    )


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.get("/")
def index():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    with get_db_connection() as conn:
        students = conn.execute(
            "SELECT id, name, age, class_name FROM students ORDER BY id DESC"
        ).fetchall()
    return render_template("index.html", students=students, edit_student=None, user=session["user"])


@app.post("/students")
def add_student():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    name = request.form.get("name", "").strip()
    age = int(request.form.get("age", 0) or 0)
    class_name = request.form.get("class_name", "").strip()

    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO students (name, age, class_name) VALUES (?, ?, ?)",
            (name, age, class_name),
        )
        conn.commit()
    return redirect(url_for("index"))


@app.get("/students/<int:student_id>/edit")
def edit_student_page(student_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    with get_db_connection() as conn:
        students = conn.execute(
            "SELECT id, name, age, class_name FROM students ORDER BY id DESC"
        ).fetchall()
        edit_student = conn.execute(
            "SELECT id, name, age, class_name FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
    return render_template("index.html", students=students, edit_student=edit_student, user=session["user"])


@app.post("/students/<int:student_id>")
def edit_student_submit(student_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))

    name = request.form.get("name", "").strip()
    age = int(request.form.get("age", 0) or 0)
    class_name = request.form.get("class_name", "").strip()

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE students SET name = ?, age = ?, class_name = ? WHERE id = ?",
            (name, age, class_name, student_id),
        )
        conn.commit()
    return redirect(url_for("index"))


@app.post("/students/<int:student_id>/delete")
def delete_student(student_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))

    with get_db_connection() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
    return redirect(url_for("index"))


@app.route('/metrics')
def metrics():
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
