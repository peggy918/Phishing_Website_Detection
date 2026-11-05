"""JSON 紀錄：同一次操作共用 request_id、記錄階段耗時、不外洩網址內容與憑證。"""
import json
import logging
import time

import pytest

from app.logging import JsonFormatter, url_hash
from app.services.predictor import active_model, preload
from tests.integration.conftest import ADMIN_PASSWORD, add_model

SECRET_URL = "https://plain-example-site.org/account?token=secret-token-123&fbclid=abc"


@pytest.fixture
def log_path(tmp_path):
    return tmp_path / "logs" / "app.jsonl"


@pytest.fixture
def logged_app(make_app, log_path, tmp_path):
    app = make_app(LOG_PATH=str(log_path))
    with app.config["SESSION_FACTORY"]() as db:
        add_model(db, tmp_path, probability=0.5)
        db.commit()
    return app


def events(log_path):
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def test_scan_logs_share_request_id_and_stage_timings(logged_app, log_path):
    response = logged_app.test_client().post("/scan", data={"url": SECRET_URL})
    rows = events(log_path)
    scan = next(r for r in rows if r["event"] == "scan_completed")
    access = next(r for r in rows if r["event"] == "request")
    assert scan["request_id"] == access["request_id"] == response.headers["X-Request-ID"]
    assert scan["decided_by"] == "model" and scan["risk_level"] == "medium"
    assert set(scan["stages_ms"]) >= {"normalize", "blacklist", "whitelist", "model", "save"}
    assert all(ms >= 0 for ms in scan["stages_ms"].values())
    assert access["status"] == 303 and access["duration_ms"] > 0


def test_logs_keep_host_and_hash_only(logged_app, log_path):
    logged_app.test_client().post("/scan", data={"url": SECRET_URL})
    text = log_path.read_text(encoding="utf-8")
    assert "secret-token-123" not in text and "fbclid" not in text and "/account" not in text
    scan = next(r for r in events(log_path) if r["event"] == "scan_completed")
    assert scan["host"] == "plain-example-site.org"
    assert scan["url_hash"] == url_hash("https://plain-example-site.org/account")


def test_same_url_with_tracking_params_has_same_hash(logged_app, log_path):
    client = logged_app.test_client()
    client.post("/scan", data={"url": "https://plain-example-site.org/a"})
    client.post("/scan", data={"url": "https://plain-example-site.org/a?utm_source=x"})
    hashes = [r["url_hash"] for r in events(log_path) if r["event"] == "scan_completed"]
    assert len(hashes) == 2 and hashes[0] == hashes[1]


def test_invalid_input_logs_no_content(logged_app, log_path):
    logged_app.test_client().post("/scan", data={"url": "http://secret word.example/"})
    text = log_path.read_text(encoding="utf-8")
    assert "scan_invalid" in text and "secret word" not in text


def test_result_page_path_is_not_logged(logged_app, log_path):
    client = logged_app.test_client()
    location = client.post("/scan", data={"url": "https://plain-example-site.org/"}).headers["Location"]
    client.get(location)
    public_id = location.rsplit("/", 1)[-1]
    assert public_id not in log_path.read_text(encoding="utf-8")   # 結果頁代碼可看到他人查過的網址


def test_unavailable_model_logged_with_reason(make_app, log_path):
    client = make_app(LOG_PATH=str(log_path)).test_client()
    response = client.post("/scan", data={"url": "https://plain-example-site.org/"})
    row = next(r for r in events(log_path) if r["event"] == "scan_unavailable")
    assert response.status_code == 503 and "尚未啟用" in row["reason"]
    assert row["request_id"] in response.get_data(as_text=True)   # 使用者可回報追蹤碼


def test_server_error_is_traceable_without_leaking_details(make_app, log_path, monkeypatch):
    app = make_app(LOG_PATH=str(log_path), TESTING=False)
    monkeypatch.setattr("app.controllers.scan.scan_url", lambda *_: 1 / 0)
    response = app.test_client().post("/scan", data={"url": SECRET_URL})
    html = response.get_data(as_text=True)
    assert response.status_code == 500 and "ZeroDivisionError" not in html
    row = next(r for r in events(log_path) if r["event"] == "unhandled_exception")
    assert row["exc_type"] == "ZeroDivisionError" and row["request_id"] in html
    assert "secret-token-123" not in log_path.read_text(encoding="utf-8")


def test_admin_events_never_log_passwords(make_app, log_path):
    client = make_app(LOG_PATH=str(log_path)).test_client()
    client.post("/admin/login", data={"username": "admin", "password": "typed-wrong-password"})
    client.post("/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD})
    text = log_path.read_text(encoding="utf-8")
    assert "typed-wrong-password" not in text and ADMIN_PASSWORD not in text
    results = [r["success"] for r in events(log_path) if r["event"] == "admin_login"]
    assert results == [False, True]


def test_failed_login_does_not_log_username(make_app, log_path):
    # 使用者可能把密碼打在帳號欄
    client = make_app(LOG_PATH=str(log_path)).test_client()
    client.post("/admin/login", data={"username": "password-in-wrong-field", "password": "x"})
    assert "password-in-wrong-field" not in log_path.read_text(encoding="utf-8")


def test_blocked_admin_access_is_logged(make_app, log_path):
    client = make_app(LOG_PATH=str(log_path)).test_client()
    client.get("/admin/", headers={"CF-Connecting-IP": "203.0.113.5"})
    row = next(r for r in events(log_path) if r["event"] == "admin_blocked")
    assert row["forwarded"] is True and "203.0.113.5" not in log_path.read_text(encoding="utf-8")


def test_rate_limit_is_logged(make_app, log_path):
    client = make_app(LOG_PATH=str(log_path), RATELIMIT_ENABLED=True).test_client()
    for _ in range(6):
        client.post("/admin/login", data={"username": "admin", "password": "x"})
    assert any(r["event"] == "rate_limited" for r in events(log_path))


def test_database_errors_hide_query_parameters(make_app):
    engine = make_app().config["SESSION_FACTORY"].kw["bind"]
    assert engine.hide_parameters is True


def test_formatter_outputs_valid_json_with_traceback():
    try:
        raise ValueError("boom")
    except ValueError:
        record = logging.LogRecord("x", logging.ERROR, __file__, 1, "failed", None, __import__("sys").exc_info())
    row = json.loads(JsonFormatter().format(record))
    assert row["event"] == "failed" and row["exc_type"] == "ValueError" and "boom" in row["traceback"]


# ---- 預先載入模型 ----

def test_preload_loads_active_model(logged_app, log_path):
    start = time.perf_counter()
    assert preload(logged_app.config["SESSION_FACTORY"]) is True
    assert time.perf_counter() - start < 60
    row = next(r for r in events(log_path) if r["event"] == "model_preloaded")
    assert row["version"] == "test-model" and row["duration_ms"] >= 0
    with logged_app.config["SESSION_FACTORY"]() as db:
        assert active_model(db).version == "test-model"


def test_preload_failure_is_logged_not_raised(make_app, log_path):
    app = make_app(LOG_PATH=str(log_path))     # 沒有啟用的模型
    assert preload(app.config["SESSION_FACTORY"]) is False
    assert any(r["event"] == "model_preload_failed" for r in events(log_path))
