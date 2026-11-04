"""資料庫連線。正式環境由 .env 的 DB_* 組出 SQL Server 連線；測試用 DATABASE_URL 指向 SQLite。"""
import os

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


def app_database_url() -> str | URL:
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    return URL.create(
        "mssql+pyodbc",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ.get("DB_SERVER", "localhost"),
        database=os.environ.get("DB_NAME", "PhishGuard"),
        query=_odbc_query(),
    )


def migration_database_url() -> str | URL:
    """建表用 Windows 驗證：應用程式帳號只有讀寫權限，不能改資料表結構。"""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    return URL.create(
        "mssql+pyodbc",
        host=os.environ.get("DB_SERVER", "localhost"),
        database=os.environ.get("DB_NAME", "PhishGuard"),
        query={**_odbc_query(), "trusted_connection": "yes"},
    )


def _odbc_query() -> dict:
    return {
        "driver": os.environ.get("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        "TrustServerCertificate": os.environ.get("DB_TRUST_SERVER_CERTIFICATE", "yes"),
    }


def make_engine(url: str | URL | None = None) -> Engine:
    return create_engine(url or app_database_url(), pool_pre_ping=True)
