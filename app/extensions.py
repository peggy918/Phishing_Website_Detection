"""Flask 擴充套件與每個請求共用的資料庫 Session。"""
from flask import current_app, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)


def db_session():
    """同一個請求共用一個 Session，請求結束時關閉（create_app 的 teardown）。"""
    if "db" not in g:
        g.db = current_app.config["SESSION_FACTORY"]()
    return g.db
