"""PhishGuard Flask 應用程式。ml/ 腳本也會 import app.*，所以 Flask 相關模組都在 create_app 內才載入。

注意：app/logging 載入後會成為本套件的屬性 logging，所以這裡不可用 import logging 再寫 logging.ERROR。
"""
import os
import time
import uuid
from logging import ERROR
from pathlib import Path


def create_app(config: dict | None = None):
    from dotenv import load_dotenv
    from flask import Flask, g, got_request_exception, request
    from sqlalchemy.orm import sessionmaker

    from app.cli import register_cli
    from app.controllers.admin import admin_bp
    from app.controllers.scan import scan_bp
    from app.db import make_engine
    from app.errors import register_error_handlers
    from app.extensions import csrf, limiter
    from app.logging import begin_request, configure, current_request_id, log_event
    from app.services.normalizer import defang

    load_dotenv()
    app = Flask(__name__, template_folder="views", static_folder="static")
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,   # 政府 XML 約 0.9 MB
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        RATELIMIT_STORAGE_URI="memory://",
        LOG_PATH=os.environ.get("LOG_PATH", str(Path(__file__).resolve().parent.parent / "logs" / "app.jsonl")),
    )
    app.config.update(config or {})
    if not app.config["SECRET_KEY"] or app.config["SECRET_KEY"] == "change-me":
        raise RuntimeError("請在 .env 設定 FLASK_SECRET_KEY")

    # 雲端（Cloud Run）前面有一層代理，remote_addr 都是代理的位址，所有人會共用速率限制額度。
    # 設了 TRUSTED_PROXY_HOPS 才信任 X-Forwarded-For 的最後幾段；只取來源 IP，不改 scheme：
    # 改成 https 會讓 Flask-WTF 檢查 Referer，而本站送出 no-referrer，表單會全被擋（F3）。
    hops = int(os.environ.get("TRUSTED_PROXY_HOPS", "0"))
    if hops:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=0, x_host=0, x_port=0, x_prefix=0)

    configure(app.config["LOG_PATH"])
    engine = make_engine(app.config.get("DATABASE_URL"))
    app.config["SESSION_FACTORY"] = sessionmaker(engine, expire_on_commit=False)

    csrf.init_app(app)
    limiter.init_app(app)
    app.register_blueprint(scan_bp)
    app.register_blueprint(admin_bp)
    register_error_handlers(app)
    register_cli(app)
    app.add_template_filter(defang, "defang")

    @app.before_request
    def start_request():
        begin_request(uuid.uuid4().hex)
        g.request_started = time.perf_counter()

    def log_exception(_sender, exception, **_extra):
        log_event("unhandled_exception", level=ERROR,
                  exc_info=(type(exception), exception, exception.__traceback__))

    # weak=False：函式只在這裡被參考，否則訊號連線會被回收
    got_request_exception.connect(log_exception, app, weak=False)

    @app.teardown_appcontext
    def close_session(_exc):
        session = g.pop("db", None)
        if session is not None:
            session.rollback()   # 未 commit 的變更一律放棄
            session.close()

    @app.after_request
    def finish_request(response):
        # 只記路由樣板（/result/<public_id>），不記實際路徑：結果頁代碼可看到他人查過的網址
        rule = request.url_rule.rule if request.url_rule else "(no route)"
        started = g.get("request_started", time.perf_counter())
        log_event("request", method=request.method, route=rule, status=response.status_code,
                  duration_ms=round((time.perf_counter() - started) * 1000, 2))
        if current_request_id():
            response.headers["X-Request-ID"] = current_request_id()
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"   # 結果頁含使用者查過的網址
        return response

    return app
