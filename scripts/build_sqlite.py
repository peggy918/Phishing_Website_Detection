"""雲端展示版：建立內含參考資料、政府黑名單與模型紀錄的 SQLite 資料庫。

在 Docker 建置時執行一次（見 Dockerfile），啟動時就不用再匯入。雲端的檔案系統不是永久的，
執行期間新增的檢測紀錄在服務重啟後會消失；本機正式版仍用 SQL Server（2026-11-11 老師同意雲端改用 SQLite）。

用法：python scripts/build_sqlite.py <SQLite 檔案路徑> <政府 XML> <模型目錄> [匯入紀錄顯示的檔名]
（從 Windows 上傳到 Cloud Build 時中文檔名會變亂碼，所以可另外指定原檔名）
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def build(db_path: Path, gov_xml: Path, model_dir: Path, gov_name: str | None = None) -> dict:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.services.gov_import import import_gov_xml
    from app.services.predictor import register_model
    from app.services.reference_data import seed_reference_data

    if db_path.exists():
        raise SystemExit(f"{db_path} 已存在，請先刪除")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path.resolve().as_posix()}"
    os.environ["DATABASE_URL"] = url   # alembic 的 env.py 由這個變數取得連線

    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    engine = create_engine(url)
    with Session(engine) as db:
        reference = seed_reference_data(db)
        gov = import_gov_xml(db, gov_name or gov_xml.name, gov_xml.read_bytes())
        model = register_model(db, model_dir)
        db.commit()
        summary = {"reference": reference, "gov_imported": gov.imported, "model": model.version}
    engine.dispose()
    return summary


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        raise SystemExit(__doc__)
    print(build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4] if len(sys.argv) == 5 else None))
