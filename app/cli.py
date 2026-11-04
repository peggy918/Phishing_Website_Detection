"""管理指令：flask --app app:create_app <指令>。"""
from pathlib import Path

import click
from flask import current_app
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app.models import AdminUser
from app.services.gov_import import ImportFailed, import_gov_xml
from app.services.predictor import register_model
from app.services.reference_data import seed_reference_data


def register_cli(app) -> None:
    def session():
        return current_app.config["SESSION_FACTORY"]()

    @app.cli.command("seed-reference")
    def seed_reference():
        """依 brands.yaml 與 domain_reviews.csv 重建品牌與白名單。"""
        with session() as db:
            click.echo(seed_reference_data(db))
            db.commit()

    @app.cli.command("import-gov")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    def import_gov(path):
        """匯入政府 XML。"""
        with session() as db:
            try:
                click.echo(import_gov_xml(db, path.name, path.read_bytes()))
            except ImportFailed as e:
                raise click.ClickException(str(e)) from e
            db.commit()

    @app.cli.command("register-model")
    @click.argument("model_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
    def register(model_dir):
        """註冊 ml/train.py 輸出的模型並設為啟用。"""
        with session() as db:
            row = register_model(db, model_dir)
            db.commit()
            click.echo(f"{row.version} 已啟用")

    @app.cli.command("create-admin")
    @click.argument("username")
    def create_admin(username):
        """建立管理者帳號。密碼由指令提示輸入，不經過命令列參數。"""
        password = click.prompt("密碼（至少 12 字）", hide_input=True, confirmation_prompt=True)
        if len(password) < 12:
            raise click.ClickException("密碼至少 12 字")
        with session() as db:
            if db.scalar(select(AdminUser).where(AdminUser.username == username)):
                raise click.ClickException("帳號已存在")
            db.add(AdminUser(username=username, password_hash=generate_password_hash(password)))
            db.commit()
        click.echo("已建立")
