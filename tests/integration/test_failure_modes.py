"""操作中斷與多人同時操作（報告 p.5、p.9、p.16）。"""
import threading

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models import ScanRequest, ScanResult
from tests.integration.conftest import add_model


@pytest.fixture
def ready_app(make_app, tmp_path):
    app = make_app(TESTING=False)
    with app.config["SESSION_FACTORY"]() as db:
        add_model(db, tmp_path, probability=0.5)
        db.commit()
    return app


def counts(app) -> tuple[int, int]:
    with app.config["SESSION_FACTORY"]() as db:
        return (db.scalar(select(func.count()).select_from(ScanRequest)),
                db.scalar(select(func.count()).select_from(ScanResult)))


def test_database_failure_shows_error_and_saves_nothing(ready_app, monkeypatch):
    def broken_commit(self):
        raise OperationalError("COMMIT", {}, Exception("connection lost"))

    client = ready_app.test_client()
    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", broken_commit)
        response = client.post("/scan", data={"url": "https://plain-example-site.org/"})
    assert response.status_code == 500
    html = response.get_data(as_text=True)
    assert "系統發生錯誤" in html and "追蹤碼" in html and "connection lost" not in html
    assert counts(ready_app) == (0, 0)           # 沒有只存一半的資料
    # 資料庫恢復後可以直接重試
    assert client.post("/scan", data={"url": "https://plain-example-site.org/"}).status_code == 303
    assert counts(ready_app) == (1, 1)


def test_failure_after_request_row_does_not_leave_half_record(ready_app, monkeypatch):
    # 寫入中途失敗：request 與 result 要一起成功或一起失敗
    def broken_flush(self, *_a, **_k):
        raise OperationalError("INSERT", {}, Exception("disk full"))

    client = ready_app.test_client()
    with monkeypatch.context() as patch:
        patch.setattr("app.services.scan.Session.flush", broken_flush)
        response = client.post("/scan", data={"url": "https://plain-example-site.org/"})
    assert response.status_code == 500 and counts(ready_app) == (0, 0)


def test_concurrent_scans_each_get_own_correct_result(ready_app):
    urls = [(f"https://site-{i}-example.org/", "medium") for i in range(10)] + \
           [("http://tw06.shopeelem.xyz/", "high")] * 5 + [("https://shopee.tw/", "low")] * 5
    results, barrier = [None] * len(urls), threading.Barrier(len(urls))

    def worker(index, url):
        client = ready_app.test_client()
        barrier.wait()
        response = client.post("/scan", data={"url": url})
        results[index] = (response.status_code, response.headers.get("Location", "").rsplit("/", 1)[-1])

    threads = [threading.Thread(target=worker, args=(i, u)) for i, (u, _) in enumerate(urls)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert all(r and r[0] == 303 for r in results), results
    public_ids = [r[1] for r in results]
    assert len(set(public_ids)) == len(urls)     # 每人拿到自己的結果頁
    with ready_app.config["SESSION_FACTORY"]() as db:
        for (url, level), public_id in zip(urls, public_ids):
            row = db.scalar(select(ScanRequest).where(ScanRequest.public_id == public_id)).result
            assert row.risk_level == level and row.host in url   # 結果沒有互相串到
    assert counts(ready_app) == (len(urls), len(urls))
