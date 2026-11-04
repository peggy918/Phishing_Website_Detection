"""Alembic 環境。連線不寫在 alembic.ini：正式環境用 Windows 驗證，測試用 DATABASE_URL。"""
from alembic import context
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

from app.db import migration_database_url
from app.models import Base

load_dotenv()
target_metadata = Base.metadata


def run_offline() -> None:
    url = migration_database_url()
    context.configure(url=url.render_as_string(hide_password=True) if isinstance(url, URL) else url,
                      target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    with create_engine(migration_database_url()).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_offline() if context.is_offline_mode() else run_online()
