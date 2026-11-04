"""整合測試環境：暫存 SQLite＋假模型。真實資料庫的驗證見 README 的重建步驟。"""
from pathlib import Path

import joblib
import pytest
from sqlalchemy import select
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import AdminUser, Base, ModelVersion
from app.services.features import FEATURE_VERSION
from app.services.gov_import import import_gov_xml
from app.services.reference_data import seed_reference_data
from tests.helpers import ConstantModel

FIXTURE_XML = Path(__file__).resolve().parent.parent / "fixtures" / "gov_sample.xml"
THRESHOLDS = {"medium": 0.4, "high": 0.8}
ADMIN_PASSWORD = "test-only-password"


def add_model(db, tmp_path, probability=0.01, feature_version=FEATURE_VERSION, name="test-model", active=True):
    artifact = tmp_path / f"{name}.joblib"
    joblib.dump(ConstantModel(probability), artifact)
    row = ModelVersion(
        version=name, algorithm="constant", feature_version=feature_version, rules_version="t", brands_version="t",
        dataset_sha256="0" * 64, seed=1, metrics="{}", threshold_medium=THRESHOLDS["medium"],
        threshold_high=THRESHOLDS["high"], artifact_path=str(artifact), is_active=active)
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def make_app(tmp_path):
    def build(**config):
        app = create_app({
            "TESTING": True, "SECRET_KEY": "test-secret", "DATABASE_URL": f"sqlite:///{tmp_path / 'test.db'}",
            "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False, **config,
        })
        factory = app.config["SESSION_FACTORY"]
        Base.metadata.create_all(factory.kw["bind"])
        with factory() as db:
            if db.scalar(select(AdminUser.id).limit(1)) is None:
                seed_reference_data(db)
                import_gov_xml(db, FIXTURE_XML.name, FIXTURE_XML.read_bytes())
                db.add(AdminUser(username="admin", password_hash=generate_password_hash(ADMIN_PASSWORD)))
                db.commit()
        return app
    return build


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def db(app):
    with app.config["SESSION_FACTORY"]() as session:
        yield session


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
    response = client.post("/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD})
    assert response.status_code == 302
    return client
