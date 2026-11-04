"""偵測流程：黑名單 → 白名單 → 模型＋品牌規則 → 存檔 → 結果頁。測資來自政府清單真實案例。"""
import json
import re
import socket

import pytest
from sqlalchemy import func, select

from app.models import BlacklistEntry, ScanRequest, ScanResult
from app.services.predictor import ModelUnavailable
from app.services.scan import scan_url
from tests.integration.conftest import add_model


@pytest.fixture
def low_model(db, tmp_path):
    add_model(db, tmp_path, probability=0.01)
    db.commit()


def scan(db, url):
    return scan_url(db, url).result


# ---- 黑名單兩種比對層級 ----

@pytest.mark.parametrize("url", [
    "http://tw06.shopeelem.xyz/",                    # 327 原網址
    "https://other.shopeelem.xyz/any/path",          # 同一註冊網域的其他子網域
    "http://tw06.shopeelem.xyz/?fbclid=abc",         # 追蹤參數不影響
    "https://www.shopmallbooks.com/wap/#/",          # 318
])
def test_blacklist_matches_registered_domain(db, url):
    r = scan(db, url)   # 不需要模型：黑名單直接判定
    assert (r.decided_by, r.risk_level) == ("blacklist", "high")


def test_blacklist_platform_matches_full_hostname_only(db, low_model):
    gh = db.scalar(select(BlacklistEntry.host).where(BlacklistEntry.registered_domain == "github.io"))
    assert scan(db, f"https://{gh}/").decided_by == "blacklist"
    other = scan(db, "https://someone-else.github.io/")
    assert other.decided_by == "model"     # 同平台的其他使用者不受牽連


def test_needs_review_matches_hostname_only(db, low_model):
    hit = scan(db, "https://niconsortiu.ecpay.com/")           # 886
    assert hit.decided_by == "blacklist"
    assert any("尚待人工確認" in reason for reason in _reasons(hit))
    assert scan(db, "https://www.ecpay.com/").decided_by == "model"


def test_blacklist_outranks_whitelist_and_shows_date_and_target(db):
    r = scan(db, "https://tobuyersepc24.com/57vgaqk#/login")   # 1
    reasons = _reasons(r)
    assert "2023-06-29" in reasons[0] and "PChome" in reasons[1]


# ---- 白名單 ----

@pytest.mark.parametrize("url", ["https://shopee.tw/", "https://mall.shopee.tw/x", "https://www.momo.com.tw/"])
def test_whitelist_skips_model(db, url):
    r = scan(db, url)   # 沒有註冊模型也能判定
    assert (r.decided_by, r.risk_level, r.probability) == ("whitelist", "low", None)


@pytest.mark.parametrize("url", ["https://onedrive.live.com/view?id=1", "https://line.me/ti/p/abc", "https://t.me/abc"])
def test_user_content_official_domains_go_to_model_without_impersonation_rule(db, low_model, url):
    r = scan(db, url)
    assert (r.decided_by, r.risk_level, r.brand_rule_applied) == ("model", "low", False)


def test_official_without_evidence_goes_to_model(db, low_model):
    assert scan(db, "https://www.newebpay.com/").decided_by == "model"


def test_official_domain_flagged_by_model_keeps_neutral_reason(db, tmp_path):
    add_model(db, tmp_path, probability=0.9)
    db.commit()
    r = scan(db, "https://onedrive.live.com/view?id=1")
    assert r.risk_level == "high" and "網域屬於" in _reasons(r)[0]


# ---- 模型與品牌規則 ----

@pytest.mark.parametrize("probability, level", [(0.01, "low"), (0.5, "medium"), (0.9, "high")])
def test_model_thresholds(db, tmp_path, probability, level):
    add_model(db, tmp_path, probability=probability)
    db.commit()
    r = scan(db, "https://plain-example-site.org/")
    assert (r.decided_by, r.risk_level) == ("model", level)
    assert r.probability == pytest.approx(probability)


def test_brand_rule_raises_low_to_medium_and_names_brand(db, low_model):
    r = scan(db, "http://sh0pee-tw.org/")
    assert (r.risk_level, r.brand_rule_applied) == ("medium", True)
    assert r.suspected_brand.key == "shopee" and "蝦皮" in _reasons(r)[0]


def test_low_risk_lists_no_reasons(db, low_model):
    assert _reasons(scan(db, "https://plain-example-site.org/")) == []


def test_medium_without_clear_clue_has_generic_reason(db, tmp_path):
    add_model(db, tmp_path, probability=0.5)
    db.commit()
    assert "模型綜合" in _reasons(scan(db, "https://plain-example-site.org/"))[0]


def test_shortener_reason_does_not_blame_its_tld(db, tmp_path):
    add_model(db, tmp_path, probability=0.9)
    db.commit()
    reasons = _reasons(scan(db, "https://reurl.cc/abc123"))
    assert any("短網址" in reason for reason in reasons) and not any("結尾" in reason for reason in reasons)


def test_tracking_params_do_not_change_result(db, tmp_path):
    add_model(db, tmp_path, probability=0.5)
    db.commit()
    a = scan(db, "https://plain-example-site.org/a?id=1")
    b = scan(db, "https://plain-example-site.org/a?id=1&fbclid=x&utm_source=y")
    assert (a.risk_level, a.probability, a.storage_url) == (b.risk_level, b.probability, b.storage_url)


# ---- 模型不可用 ----

def test_no_active_model_raises_but_blacklist_still_works(db):
    assert scan(db, "http://tw06.shopeelem.xyz/").risk_level == "high"
    with pytest.raises(ModelUnavailable):
        scan(db, "https://plain-example-site.org/")


def test_feature_version_mismatch_refuses_model(db, tmp_path):
    add_model(db, tmp_path, feature_version="old-version")
    db.commit()
    with pytest.raises(ModelUnavailable, match="不一致"):
        scan(db, "https://plain-example-site.org/")


# ---- 存檔與隱私 ----

def test_storage_drops_query_and_fragment(db, low_model):
    r = scan(db, "https://plain-example-site.org/a/b?token=secret#frag")
    assert r.storage_url == "https://plain-example-site.org/a/b"
    assert "secret" not in r.storage_url


def test_rules_version_recorded(db, low_model):
    req = scan_url(db, "https://plain-example-site.org/")
    assert req.rules_version and req.status == "done"


def test_scan_never_opens_a_network_connection(db, low_model, monkeypatch):
    # CLAUDE.md：不連線被檢查的網址。任何對外連線或 DNS 查詢都讓測試失敗。
    def forbidden(*_a, **_k):
        raise AssertionError("偵測流程不可連線")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    for url in ["https://plain-example-site.org/login", "http://tw06.shopeelem.xyz/", "https://shopee.tw/"]:
        scan(db, url)


# ---- 網頁 ----

def test_post_redirects_then_result_page_is_defanged(client, app, tmp_path):
    with app.config["SESSION_FACTORY"]() as s:
        add_model(s, tmp_path, probability=0.5)
        s.commit()
    response = client.post("/scan", data={"url": "https://plain-example-site.org/a?token=secret"})
    assert response.status_code == 303                    # 重新整理不會重複送出
    html = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "hxxps://plain-example-site[.]org/a" in html
    assert "secret" not in html
    assert "plain-example-site.org" not in html           # 不可出現可複製點擊的原網址
    assert not re.search(r'href="[^"]*(plain-example|hxxp)', html)
    assert "中風險" in html and "165" in html


def test_low_risk_page_never_says_safe(client, app, tmp_path):
    with app.config["SESSION_FACTORY"]() as s:
        add_model(s, tmp_path, probability=0.01)
        s.commit()
    response = client.post("/scan", data={"url": "https://plain-example-site.org/"})
    html = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "未發現明顯風險跡象" in html and "安全" not in html


@pytest.mark.parametrize("bad", ["", "javascript:alert(1)", "http://a b.com", "<script>alert(1)</script>"])
def test_invalid_input_shows_error_and_stores_no_content(client, app, bad):
    response = client.post("/scan", data={"url": bad})
    html = response.get_data(as_text=True)
    assert response.status_code == 400 and "<script>alert(1)" not in html   # 跳脫，不可注入
    with app.config["SESSION_FACTORY"]() as s:
        req = s.scalar(select(ScanRequest).order_by(ScanRequest.id.desc()).limit(1))
        assert req.status == "invalid" and req.result is None


def test_oversized_input_is_rejected(client):
    assert client.post("/scan", data={"url": "https://a.com/" + "x" * 5000}).status_code == 400


def test_no_model_shows_503_page(client):
    response = client.post("/scan", data={"url": "https://plain-example-site.org/"})
    assert response.status_code == 503 and "暫時無法使用" in response.get_data(as_text=True)


def test_unknown_result_is_404(client):
    assert client.get("/result/not-a-real-id").status_code == 404


@pytest.mark.parametrize("path", ["/", "/admin/login", "/result/not-a-real-id"])
def test_footer_says_not_a_government_service(client, path):
    assert "學生專題作品，非政府官方服務" in client.get(path).get_data(as_text=True)


def test_security_headers(client):
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff" and headers["Cache-Control"] == "no-store"


def test_csrf_is_required_when_enabled(make_app):
    client = make_app(WTF_CSRF_ENABLED=True).test_client()
    assert client.post("/scan", data={"url": "https://a.com"}).status_code == 400


def test_csrf_token_from_form_is_accepted(make_app):
    client = make_app(WTF_CSRF_ENABLED=True).test_client()
    token = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/").get_data(as_text=True)).group(1)
    response = client.post("/scan", data={"url": "http://tw06.shopeelem.xyz/", "csrf_token": token})
    assert response.status_code == 303


def test_scan_rate_limit(make_app):
    client = make_app(RATELIMIT_ENABLED=True).test_client()
    codes = [client.post("/scan", data={"url": "http://tw06.shopeelem.xyz/"}).status_code for _ in range(31)]
    assert codes[:30] == [303] * 30 and codes[30] == 429


def test_each_submit_creates_one_record(client, app):
    client.post("/scan", data={"url": "http://tw06.shopeelem.xyz/"})
    with app.config["SESSION_FACTORY"]() as s:
        assert s.scalar(select(func.count()).select_from(ScanResult)) == 1


def _reasons(result):
    return json.loads(result.reasons)
