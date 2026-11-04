"""確認 .env 的資料庫設定可以連線，且應用程式帳號只有讀寫權限。不顯示密碼，不改動資料。

用法：.venv/Scripts/python scripts/check_db.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db import make_engine

PLACEHOLDER = "change-me"


def main() -> int:
    if not Path(".env").exists():
        print("找不到 .env：請先在專案資料夾複製 .env.example 成 .env")
        return 1
    load_dotenv(".env")
    for name in ("FLASK_SECRET_KEY", "DB_USER", "DB_PASSWORD"):
        if os.environ.get(name, PLACEHOLDER) in ("", PLACEHOLDER):
            print(f".env 的 {name} 還沒填")
            return 1
    try:
        with make_engine().connect() as conn:
            database, user, reader, writer, owner = conn.execute(text(
                "SELECT DB_NAME(), SUSER_SNAME(), IS_ROLEMEMBER('db_datareader'), "
                "IS_ROLEMEMBER('db_datawriter'), IS_ROLEMEMBER('db_owner')")).one()
    except DBAPIError as e:
        print("無法連線。SQL Server 回應：")
        print(str(e.orig))
        return 1
    print(f"連線成功：資料庫 {database}，帳號 {user}")
    print(f"可讀取：{bool(reader)}　可寫入：{bool(writer)}　擁有者權限：{bool(owner)}（應為 False）")
    return 0 if reader and writer and not owner else 1


if __name__ == "__main__":
    raise SystemExit(main())
