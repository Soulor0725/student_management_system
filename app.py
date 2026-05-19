import hashlib
import sqlite3
import time
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST


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

# Prometheus 监控指标 - 使用原生 prometheus_client
# 自定义请求计数器（按 path 和 status 统计）
REQUEST_COUNT = Counter('flask_http_request_total', 'Total HTTP requests', ['path', 'status'])
REQUEST_LATENCY = Histogram('flask_http_request_duration_seconds', 'HTTP request duration', ['path', 'status'])

# 业务专用指标
REGISTER_REQUESTS = Counter('register_requests_total', 'Total register requests', ['status'])
LOGIN_REQUESTS = Counter('login_requests_total', 'Total login requests', ['status'])
ADD_STUDENT_REQUESTS = Counter('add_student_requests_total', 'Total add student requests', ['status'])

# 正在处理的请求数
IN_FLIGHT_REQUESTS = Gauge('in_flight_requests', 'Number of in-flight requests', ['path'])

# 系统状态指标（持续显示，即使没有请求也有数据）
APP_UP = Gauge('app_up', 'Application is up', [])
TOTAL_USERS = Gauge('total_users', 'Total number of registered users', [])
TOTAL_STUDENTS = Gauge('total_students', 'Total number of students', [])

# 全局监控中间件
@app.before_request
def before_request_monitor():
    request.start_time = time.time()
    IN_FLIGHT_REQUESTS.labels(path=request.path).inc()

@app.after_request
def after_request_monitor(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        path = request.path
        status = str(response.status_code)
        
        REQUEST_COUNT.labels(path=path, status=status).inc()
        REQUEST_LATENCY.labels(path=path, status=status).observe(duration)
        IN_FLIGHT_REQUESTS.labels(path=request.path).dec()
    return response

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
        REGISTER_REQUESTS.labels(status="fail").inc()
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
        REGISTER_REQUESTS.labels(status="fail").inc()
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
    
    REGISTER_REQUESTS.labels(status="success").inc()
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
        LOGIN_REQUESTS.labels(status="fail").inc()
        return render_template(
            "auth.html",
            mode="login",
            error="用户名或密码错误",
            toast=None,
            redirect_to=None,
        )

    session["user"] = {"id": user["id"], "username": user["username"]}
    LOGIN_REQUESTS.labels(status="success").inc()
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

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO students (name, age, class_name) VALUES (?, ?, ?)",
                (name, age, class_name),
            )
            conn.commit()
        ADD_STUDENT_REQUESTS.labels(status="success").inc()
    except Exception as e:
        ADD_STUDENT_REQUESTS.labels(status="fail").inc()
        raise e
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


def update_system_metrics():
    """定期更新系统状态指标"""
    import threading
    import time
    
    def update_loop():
        while True:
            try:
                # 更新应用状态
                APP_UP.set(1)
                
                # 更新用户数量
                with get_db_connection() as conn:
                    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                    TOTAL_USERS.set(user_count)
                    
                    student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
                    TOTAL_STUDENTS.set(student_count)
            except Exception as e:
                print(f"[METRICS] 更新指标失败: {e}")
            
            time.sleep(10)  # 每10秒更新一次
    
    # 启动后台线程
    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()

if __name__ == "__main__":
    init_db()
    
    # 启动指标更新线程
    update_system_metrics()
    
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
