"""雲端展示版（Cloud Run＋SQLite）的設定：代理標頭與建置時產生的資料庫。"""
import json
import sqlite3
from pathlib import Path

import joblib
import pytest

from app.services.features import FEATURE_VERSION
from tests.helpers import ConstantModel

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_XML = ROOT / "tests" / "fixtures" / "gov_sample.xml"


def _scan(client, ip):
    return client.post("/scan", data={"url": "http://tw06.shopeelem.xyz/"},
                       headers={"X-Forwarded-For": ip}).status_code


def test_without_trusted_proxy_everyone_shares_one_limit(make_app, monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)
    client = make_app(RATELIMIT_ENABLED=True).test_client()
    codes = [_scan(client, f"203.0.113.{i}") for i in range(31)]
    assert codes[30] == 429   # 不信任轉送標頭：換 IP 也沒用，避免偽造標頭繞過限制


def test_trusted_proxy_limits_each_visitor_separately(make_app, monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    client = make_app(RATELIMIT_ENABLED=True).test_client()
    codes = [_scan(client, "203.0.113.7") for _ in range(31)]
    assert codes[:30] == [303] * 30 and codes[30] == 429
    assert _scan(client, "203.0.113.8") == 303


def test_trusted_proxy_uses_last_hop_so_spoofed_header_does_not_help(make_app, monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    client = make_app(RATELIMIT_ENABLED=True).test_client()
    codes = [_scan(client, f"10.0.0.{i}, 203.0.113.7") for i in range(31)]
    assert codes[30] == 429


@pytest.mark.parametrize("ip", ["127.0.0.1", "203.0.113.7"])
def test_trusted_proxy_keeps_admin_hidden(make_app, monkeypatch, ip):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    client = make_app().test_client()
    assert client.get("/admin/login", headers={"X-Forwarded-For": ip}).status_code == 404


def test_trusted_proxy_does_not_switch_to_https(make_app, monkeypatch):
    """改成 https 會觸發 Flask-WTF 的 Referer 檢查，而本站送出 no-referrer，表單會全被擋（F3）。"""
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    client = make_app(WTF_CSRF_ENABLED=True).test_client()
    page = client.get("/", headers={"X-Forwarded-Proto": "https"}).get_data(as_text=True)
    token = page.split('name="csrf_token" value="')[1].split('"')[0]
    response = client.post("/scan", data={"url": "http://tw06.shopeelem.xyz/", "csrf_token": token},
                           headers={"X-Forwarded-For": "203.0.113.7", "X-Forwarded-Proto": "https"})
    assert response.status_code == 303


def _fake_model_dir(tmp_path: Path) -> Path:
    model_dir = tmp_path / "fake-model"
    model_dir.mkdir(parents=True)
    joblib.dump(ConstantModel(0.01), model_dir / "model.joblib")
    (model_dir / "metadata.json").write_text(json.dumps({
        "model_version": "fake-model", "algorithm": "constant", "feature_version": FEATURE_VERSION,
        "rules_version": "t", "brands_version": "t", "dataset_sha256": "0" * 64, "seed": 1, "metrics": {},
        "thresholds": {"medium": 0.4, "high": 0.8},
    }), encoding="utf-8")
    return model_dir


def test_build_sqlite_creates_ready_database(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    monkeypatch.setenv("DATABASE_URL", "sqlite://")   # 讓 monkeypatch 在測試後還原 build 設定的值
    from build_sqlite import build

    db_path = tmp_path / "cloud" / "netcatch.db"
    summary = build(db_path, FIXTURE_XML, _fake_model_dir(tmp_path))
    assert summary["model"] == "fake-model" and summary["gov_imported"] > 0

    con = sqlite3.connect(db_path)
    try:
        assert con.execute("select count(*) from model_version where is_active = 1").fetchone()[0] == 1
        assert con.execute("select count(*) from blacklist_entry").fetchone()[0] == summary["gov_imported"]
        assert con.execute("select count(*) from whitelist").fetchone()[0] > 0
        assert con.execute("select version_num from alembic_version").fetchone() is not None
    finally:
        con.close()

    with pytest.raises(SystemExit):   # 不覆蓋既有資料庫
        build(db_path, FIXTURE_XML, _fake_model_dir(tmp_path / "again"))
