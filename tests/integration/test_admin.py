"""管理者：本機限制、登入、匯入、切換模型。對應報告 G5 未授權存取測試。"""
from io import BytesIO

import pytest
from sqlalchemy import func, select

from app.models import AdminUser, BlacklistEntry, ImportBatch, ModelVersion
from app.services.gov_import import ImportFailed, import_gov_xml, parse_gov_xml
from tests.integration.conftest import ADMIN_PASSWORD, FIXTURE_XML, add_model

VALID_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<dataset>
  <record><編號>9001</編號><一頁式數位經濟詐騙網站>疑似假冒蝦皮購物網站</一頁式數位經濟詐騙網站><偽冒網址>https://new-fake-shop.top/x?fbclid=1</偽冒網址><網域名稱>new-fake-shop.top</網域名稱><詐騙網站創建日期>2026-01-01T00:00:00</詐騙網站創建日期><接獲通報日期>20260102</接獲通報日期><停止解析日期>20260103</停止解析日期></record>
  <record><編號>9001</編號><一頁式數位經濟詐騙網站>重複編號</一頁式數位經濟詐騙網站><偽冒網址>https://dup.top/</偽冒網址><網域名稱>dup.top</網域名稱><詐騙網站創建日期>2026-01-01T00:00:00</詐騙網站創建日期><接獲通報日期>20260102</接獲通報日期><停止解析日期>20260103</停止解析日期></record>
  <record><編號>9002</編號><一頁式數位經濟詐騙網站>無效網址</一頁式數位經濟詐騙網站><偽冒網址>not a url</偽冒網址><網域名稱>x</網域名稱><詐騙網站創建日期>壞掉</詐騙網站創建日期><接獲通報日期>壞掉</接獲通報日期><停止解析日期></停止解析日期></record>
</dataset>""".encode("utf-8")


# ---- 存取限制 ----

@pytest.mark.parametrize("path", ["/admin/", "/admin/login"])
def test_non_local_address_gets_404(client, path):
    assert client.get(path, environ_base={"REMOTE_ADDR": "203.0.113.5"}).status_code == 404


@pytest.mark.parametrize("header", ["CF-Connecting-IP", "CF-Ray", "X-Forwarded-For", "X-Real-IP", "Forwarded"])
def test_tunnel_traffic_from_loopback_gets_404(client, header):
    # cloudflared 跑在本機，remote_addr 是 127.0.0.1，只能靠轉送標頭辨識外部流量
    assert client.get("/admin/login", headers={header: "203.0.113.5"}).status_code == 404


def test_public_pages_stay_available_through_tunnel(client):
    assert client.get("/", headers={"CF-Connecting-IP": "203.0.113.5"}).status_code == 200


@pytest.mark.parametrize("method, path", [
    ("get", "/admin/"), ("post", "/admin/import"), ("post", "/admin/models/1/activate"),
])
def test_requires_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302 and response.headers["Location"].endswith("/admin/login")


# ---- 登入 ----

@pytest.mark.parametrize("username, password", [("admin", "wrong"), ("nobody", ADMIN_PASSWORD), ("", "")])
def test_wrong_credentials_get_same_message(client, username, password):
    response = client.post("/admin/login", data={"username": username, "password": password})
    assert response.status_code == 200 and "帳號或密碼錯誤" in response.get_data(as_text=True)
    assert client.get("/admin/").status_code == 302


def test_password_is_hashed(db):
    assert ADMIN_PASSWORD not in db.scalar(select(AdminUser.password_hash))


def test_login_rate_limit(make_app):
    client = make_app(RATELIMIT_ENABLED=True).test_client()
    codes = [client.post("/admin/login", data={"username": "admin", "password": "x"}).status_code for _ in range(6)]
    assert codes[:5] == [200] * 5 and codes[5] == 429


def test_logout_requires_post_and_clears_session(admin_client):
    assert admin_client.get("/admin/logout").status_code == 405
    admin_client.post("/admin/logout")
    assert admin_client.get("/admin/").status_code == 302


# ---- 匯入 ----

def upload(client, content, name="gov.xml"):
    return client.post("/admin/import", data={"file": (BytesIO(content), name)},
                       content_type="multipart/form-data", follow_redirects=True)


def test_fixture_import_counts_and_levels(db):
    entries = {e.record_no: e for e in db.scalars(select(BlacklistEntry))}
    assert len(entries) == 15
    assert entries[886].needs_review and entries[886].match_level == "hostname"       # ecpay.com 子網域
    assert entries[319].match_key == "shopmallbooks.com"                              # www 與註冊網域
    assert entries[1280].host == "rakutena-tw.shop"                                   # 含 @
    assert entries[116].host == "colaresearchclub.red"                                # 開頭雜字元
    assert entries[1574].match_level == "hostname"                                    # github.io
    assert entries[1].brand.key == "pchome"
    assert "utm_source" not in entries[1373].normalized_url and "utm_source" in entries[1373].raw_url


def test_upload_imports_and_skips_bad_records(admin_client, db):
    html = upload(admin_client, VALID_XML).get_data(as_text=True)
    assert "匯入 1 筆" in html and "略過 2 筆" in html
    row = db.scalar(select(BlacklistEntry).where(BlacklistEntry.record_no == 9001))
    assert row.host == "new-fake-shop.top" and row.brand.key == "shopee"
    assert "fbclid" not in row.normalized_url


def test_imported_url_is_blacklisted_immediately(admin_client):
    upload(admin_client, VALID_XML)
    response = admin_client.post("/scan", data={"url": "https://new-fake-shop.top/"})
    assert "高風險" in admin_client.get(response.headers["Location"]).get_data(as_text=True)


def test_same_file_cannot_be_imported_twice(admin_client, db):
    assert "匯入 1 筆" in upload(admin_client, VALID_XML).get_data(as_text=True)
    assert "已經匯入過" in upload(admin_client, VALID_XML).get_data(as_text=True)
    assert db.scalar(select(func.count()).select_from(ImportBatch)) == 2   # fixture＋第一次


@pytest.mark.parametrize("content", [b"not xml", b"<dataset></dataset>", "<a><b>其他資料</b></a>".encode("utf-8")])
def test_invalid_file_shows_error_and_changes_nothing(admin_client, db, content):
    before = db.scalar(select(func.count()).select_from(ImportBatch))
    assert upload(admin_client, content).status_code == 200
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(ImportBatch)) == before


@pytest.mark.parametrize("attack", [
    b'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]><dataset><record>&b;</record></dataset>',
    b'<?xml version="1.0"?><!DOCTYPE d [<!ENTITY x SYSTEM "file:///c:/windows/win.ini">]><dataset><record>&x;</record></dataset>',
])
def test_xml_entity_attacks_are_rejected(attack):
    with pytest.raises(ImportFailed):
        parse_gov_xml(attack)


def test_entities_in_otherwise_valid_records_are_rejected():
    # 突變測試發現：上面的攻擊字串沒有欄位，換成不安全的解析器也會因為內容無效而被拒絕，測不出解析器。
    # 這裡的紀錄本身有效，只有用安全的解析器才會因為實體定義被拒絕。
    xml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE d [<!ENTITY a \"https://x.top/\">]><dataset><record>"
           "<編號>1</編號><一頁式數位經濟詐騙網站>t</一頁式數位經濟詐騙網站><偽冒網址>&a;</偽冒網址></record></dataset>").encode("utf-8")
    with pytest.raises(ImportFailed, match="無法解析"):
        parse_gov_xml(xml)


def test_oversized_upload_is_rejected(make_app):
    app = make_app(MAX_CONTENT_LENGTH=1024)
    client = app.test_client()
    client.post("/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD})
    assert upload(client, b"x" * 2048).status_code == 413


def test_import_rolls_back_on_duplicate_in_service(db):
    with pytest.raises(ImportFailed):
        import_gov_xml(db, "again.xml", FIXTURE_XML.read_bytes())


def test_cli_reports_duplicate_import_without_traceback(app):
    result = app.test_cli_runner().invoke(args=["import-gov", str(FIXTURE_XML)])
    assert result.exit_code == 1 and "已經匯入過" in result.output and "Traceback" not in result.output


# ---- 模型版本 ----

def test_activate_switches_single_active_model(admin_client, app, tmp_path):
    with app.config["SESSION_FACTORY"]() as s:
        a = add_model(s, tmp_path, name="a", active=True)
        b = add_model(s, tmp_path, name="b", active=False)
        s.commit()
        a_id, b_id = a.id, b.id
    assert admin_client.post(f"/admin/models/{b_id}/activate").status_code == 302
    with app.config["SESSION_FACTORY"]() as s:
        assert s.get(ModelVersion, b_id).is_active and not s.get(ModelVersion, a_id).is_active
    assert admin_client.post("/admin/models/99999/activate").status_code == 404


def test_dashboard_shows_stats(admin_client):
    admin_client.post("/scan", data={"url": "http://tw06.shopeelem.xyz/"})
    html = admin_client.get("/admin/").get_data(as_text=True)
    assert "黑名單命中" in html and "gov_sample.xml" in html
