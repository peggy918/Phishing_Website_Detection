"""E2E 測試環境：真的啟動伺服器（開啟 CSRF），用瀏覽器操作。暫存 SQLite＋固定機率的假模型。"""
import socket
import threading
from pathlib import Path

import joblib
import pytest
from sqlalchemy import select
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

from app import create_app
from app.models import AdminUser, Base, ModelVersion
from app.services.features import FEATURE_VERSION
from app.services.gov_import import import_gov_xml
from app.services.reference_data import seed_reference_data
from tests.helpers import ConstantModel

FIXTURE_XML = Path(__file__).resolve().parent.parent / "fixtures" / "gov_sample.xml"
ADMIN_PASSWORD = "e2e-only-password"
LOW_PROBABILITY = 0.01      # 沒有其他線索時判為低風險，方便分辨黑名單、白名單與品牌規則


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def server(tmp_path):
    artifact = tmp_path / "model.joblib"
    joblib.dump(ConstantModel(LOW_PROBABILITY), artifact)
    app = create_app({
        "SECRET_KEY": "e2e-secret", "DATABASE_URL": f"sqlite:///{tmp_path / 'e2e.db'}",
        "LOG_PATH": str(tmp_path / "app.jsonl"), "RATELIMIT_ENABLED": False,
    })
    factory = app.config["SESSION_FACTORY"]
    Base.metadata.create_all(factory.kw["bind"])
    with factory() as db:
        seed_reference_data(db)
        import_gov_xml(db, FIXTURE_XML.name, FIXTURE_XML.read_bytes())
        db.add(AdminUser(username="admin", password_hash=generate_password_hash(ADMIN_PASSWORD)))
        db.add(ModelVersion(
            version="e2e-model", algorithm="constant", feature_version=FEATURE_VERSION, rules_version="t",
            brands_version="t", dataset_sha256="0" * 64, seed=1, metrics="{}", threshold_medium=0.4,
            threshold_high=0.8, artifact_path=str(artifact), is_active=True))
        db.commit()

    port = _free_port()
    httpd = make_server("127.0.0.1", port, app, threaded=True)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield {"url": f"http://127.0.0.1:{port}", "sessions": factory, "log": tmp_path / "app.jsonl"}
    httpd.shutdown()
    thread.join(timeout=5)
    factory.kw["bind"].dispose()


def scan_count(server) -> int:
    from sqlalchemy import func

    from app.models import ScanRequest
    with server["sessions"]() as db:
        return db.scalar(select(func.count()).select_from(ScanRequest))
