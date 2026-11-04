"""資料庫遷移：從空資料庫升級後，結構必須與 SQLAlchemy 模型一致；也要能完整降級。"""
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.models import Base


def _config(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'migrate.db'}")
    return Config("alembic.ini")


def test_upgrade_matches_models_and_downgrade_is_clean(monkeypatch, tmp_path):
    config = _config(monkeypatch, tmp_path)
    command.upgrade(config, "head")
    command.check(config)      # 模型與遷移有差異時會拋例外
    engine = create_engine(f"sqlite:///{tmp_path / 'migrate.db'}")
    assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())
    engine.dispose()
    command.downgrade(config, "base")
    engine = create_engine(f"sqlite:///{tmp_path / 'migrate.db'}")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()


def test_single_head(monkeypatch, tmp_path):
    assert len(ScriptDirectory.from_config(_config(monkeypatch, tmp_path)).get_heads()) == 1
