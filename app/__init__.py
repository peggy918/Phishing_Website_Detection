"""PhishGuard Flask 應用程式。ml/ 腳本也會 import app.*，所以 Flask 相關模組都在 create_app 內才載入。"""
import os


def create_app(config: dict | None = None):
    from dotenv import load_dotenv
    from flask import Flask, g
    from sqlalchemy.orm import sessionmaker

    from app.cli import register_cli
    from app.controllers.admin import admin_bp
    from app.controllers.scan import scan_bp
    from app.db import make_engine
    from app.errors import register_error_handlers
    from app.extensions import csrf, limiter
    from app.services.normalizer import defang

    load_dotenv()
    app = Flask(__name__, template_folder="views", static_folder="static")
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,   # 政府 XML 約 0.9 MB
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        RATELIMIT_STORAGE_URI="memory://",
    )
    app.config.update(config or {})
    if not app.config["SECRET_KEY"] or app.config["SECRET_KEY"] == "change-me":
        raise RuntimeError("請在 .env 設定 FLASK_SECRET_KEY")

    engine = make_engine(app.config.get("DATABASE_URL"))
    app.config["SESSION_FACTORY"] = sessionmaker(engine, expire_on_commit=False)

    csrf.init_app(app)
    limiter.init_app(app)
    app.register_blueprint(scan_bp)
    app.register_blueprint(admin_bp)
    register_error_handlers(app)
    register_cli(app)
    app.add_template_filter(defang, "defang")

    @app.teardown_appcontext
    def close_session(_exc):
        session = g.pop("db", None)
        if session is not None:
            session.rollback()   # 未 commit 的變更一律放棄
            session.close()

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"   # 結果頁含使用者查過的網址
        return response

    return app
