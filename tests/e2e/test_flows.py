"""完整操作流程：訪客檢查網址、重複送出、異常輸入、管理者匯入。對應報告 p.16 G7。"""
import time

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, expect

from tests.e2e.conftest import ADMIN_PASSWORD, FIXTURE_XML, scan_count

NEW_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<dataset><record><編號>9001</編號><一頁式數位經濟詐騙網站>疑似假冒蝦皮購物網站</一頁式數位經濟詐騙網站><偽冒網址>https://brand-new-fake.top/x</偽冒網址><網域名稱>brand-new-fake.top</網域名稱><詐騙網站創建日期>2026-01-01T00:00:00</詐騙網站創建日期><接獲通報日期>20260102</接獲通報日期><停止解析日期>20260103</停止解析日期></record></dataset>"""


def check(page: Page, server: dict, url: str) -> None:
    page.goto(server["url"])
    page.get_by_label("要檢查的網址").fill(url)
    page.get_by_role("button", name="檢查", exact=True).click()


def login(page: Page, server: dict, password: str = ADMIN_PASSWORD) -> None:
    page.goto(server["url"] + "/admin/login")
    page.get_by_label("帳號").fill("admin")
    page.get_by_label("密碼").fill(password)
    page.get_by_role("button", name="登入").click()


# ---- 訪客流程 ----

def test_blacklisted_url_is_high_risk_and_defanged(page: Page, server):
    check(page, server, "http://tw06.shopeelem.xyz/?fbclid=abc&token=secret")     # 327
    assert "/result/" in page.url
    expect(page.get_by_role("heading", level=1)).to_have_text("高風險")
    expect(page.locator(".defanged")).to_have_text("hxxp://tw06[.]shopeelem[.]xyz/")
    expect(page.get_by_text("已列入政府通報的詐騙網址清單")).to_be_visible()
    expect(page.get_by_text("判定依據：政府通報清單")).to_be_visible()
    assert "secret" not in page.content()
    assert page.locator('a[href*="shopeelem"], a[href*="hxxp"]').count() == 0     # 不可產生可點擊連結


def test_official_domain_never_says_safe(page: Page, server):
    check(page, server, "https://shopee.tw/")
    expect(page.get_by_role("heading", level=1)).to_have_text("未發現明顯風險跡象")
    expect(page.get_by_text("這不代表網站一定沒問題")).to_be_visible()
    expect(page.get_by_text("蝦皮購物的官方網域清單")).to_be_visible()
    assert "安全" not in page.locator("body").inner_text()


def test_impersonation_is_raised_to_medium_with_brand_name(page: Page, server):
    check(page, server, "http://sh0pee-tw.org/")
    expect(page.get_by_role("heading", level=1)).to_have_text("中風險")
    expect(page.get_by_text("疑似冒用：蝦皮購物")).to_be_visible()
    expect(page.get_by_text("判定依據：機器學習模型＋品牌規則")).to_be_visible()


def test_footer_and_165_on_every_visitor_page(page: Page, server):
    check(page, server, "https://shopee.tw/")
    for url in [page.url, server["url"] + "/"]:
        page.goto(url)
        expect(page.get_by_text("學生專題作品，非政府官方服務")).to_be_visible()
        expect(page.locator("footer")).to_contain_text("165")


# ---- 重複送出 ----

def test_second_submit_while_waiting_is_ignored(page: Page, server):
    # 真正的風險：第一次送出後伺服器還沒回應（例如模型載入中），使用者又按一次。
    # 同一瞬間送兩次測不出來，因為瀏覽器會自動合併；所以要讓回應變慢，隔一下再送。
    posts = []
    page.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)

    def slow(route):
        time.sleep(0.4)
        try:
            route.continue_()
        except PlaywrightError:     # 沒有防護時，第一個請求已被第二次送出取消
            pass

    page.route("**/scan", slow)
    page.goto(server["url"])
    page.get_by_label("要檢查的網址").fill("https://shopee.tw/")
    page.evaluate("""() => {
        const form = document.querySelector("form");
        form.requestSubmit();
        setTimeout(() => form.requestSubmit(), 100);
    }""")
    expect(page.get_by_role("heading", level=1)).to_have_text("未發現明顯風險跡象")
    assert len(posts) == 1


def test_button_shows_progress_while_submitting(page: Page, server):
    page.route("**/scan", lambda route: (time.sleep(0.3), route.continue_()))
    page.goto(server["url"])
    page.get_by_label("要檢查的網址").fill("https://shopee.tw/")
    page.get_by_role("button", name="檢查", exact=True).click()
    expect(page.get_by_role("heading", level=1)).to_have_text("未發現明顯風險跡象")
    page.go_back()
    expect(page.get_by_role("button", name="檢查", exact=True)).to_be_visible()   # 回上一頁後按鈕文字要恢復


def test_real_double_click_creates_one_record(page: Page, server):
    page.goto(server["url"])
    page.get_by_label("要檢查的網址").fill("https://shopee.tw/")
    page.get_by_role("button", name="檢查", exact=True).dblclick()
    expect(page.get_by_role("heading", level=1)).to_have_text("未發現明顯風險跡象")
    assert scan_count(server) == 1


def test_reload_result_page_does_not_scan_again(page: Page, server):
    check(page, server, "https://shopee.tw/")
    expect(page.get_by_role("heading", level=1)).to_have_text("未發現明顯風險跡象")
    page.reload()
    expect(page.get_by_role("heading", level=1)).to_have_text("未發現明顯風險跡象")
    assert scan_count(server) == 1


def test_back_button_allows_a_new_scan(page: Page, server):
    check(page, server, "https://shopee.tw/")
    expect(page.get_by_role("heading", level=1)).to_have_text("未發現明顯風險跡象")
    page.go_back()
    expect(page.get_by_role("button", name="檢查", exact=True)).to_be_enabled()
    page.get_by_label("要檢查的網址").fill("http://tw06.shopeelem.xyz/")
    page.get_by_role("button", name="檢查", exact=True).click()
    expect(page.get_by_role("heading", level=1)).to_have_text("高風險")
    assert scan_count(server) == 2


# ---- 異常輸入 ----

@pytest.mark.parametrize("bad", ["not a url", "javascript:alert(1)", "http://a b.com", "localhost"])
def test_invalid_input_shows_message_and_keeps_input(page: Page, server, bad):
    check(page, server, bad)
    expect(page.locator("#url-error")).to_be_visible()
    expect(page.get_by_label("要檢查的網址")).to_have_value(bad)


def test_html_input_is_not_executed(page: Page, server):
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    check(page, server, "<img src=x onerror=alert(1)>")
    expect(page.locator("#url-error")).to_be_visible()
    assert dialogs == [] and page.locator("img[src=x]").count() == 0


def test_empty_input_is_blocked_by_browser(page: Page, server):
    page.goto(server["url"])
    page.get_by_role("button", name="檢查", exact=True).click()
    assert page.url.rstrip("/") == server["url"] and scan_count(server) == 0


def test_tracking_only_difference_gives_same_display(page: Page, server):
    check(page, server, "https://shopee.tw/a?id=1&utm_source=x&fbclid=y")
    expect(page.locator(".defanged")).to_have_text("hxxps://shopee[.]tw/a")


def test_unknown_result_shows_friendly_page_with_trace_id(page: Page, server):
    response = page.goto(server["url"] + "/result/not-a-real-id")
    assert response.status == 404
    expect(page.get_by_role("heading", level=1)).to_have_text("找不到頁面")
    expect(page.get_by_text("追蹤碼")).to_contain_text(response.headers["x-request-id"])


# ---- 版面 ----

@pytest.mark.parametrize("width", [375, 1280])
def test_no_horizontal_scroll(page: Page, server, width):
    page.set_viewport_size({"width": width, "height": 800})
    long_path = "https://shopee.tw/" + "very-long-segment/" * 20
    check(page, server, long_path)
    expect(page.get_by_role("heading", level=1)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_csp_blocks_nothing_on_main_pages(page: Page, server):
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    check(page, server, "https://shopee.tw/")
    page.goto(server["url"] + "/admin/login")
    assert [e for e in errors if "Content Security Policy" in e] == []


# ---- 管理者 ----

def test_wrong_password_is_rejected(page: Page, server):
    login(page, server, password="wrong-password")
    expect(page.get_by_text("帳號或密碼錯誤")).to_be_visible()
    page.goto(server["url"] + "/admin/")
    expect(page.get_by_role("heading", name="管理者登入")).to_be_visible()


def test_admin_import_then_url_is_blacklisted(page: Page, server, tmp_path):
    check(page, server, "https://brand-new-fake.top/")
    expect(page.get_by_role("heading", level=1)).not_to_have_text("高風險")

    login(page, server)
    expect(page.get_by_role("heading", name="管理", exact=True)).to_be_visible()
    xml = tmp_path / "new.xml"
    xml.write_text(NEW_XML, encoding="utf-8")
    page.get_by_label("通報 TWNIC 詐騙網址彙整表").set_input_files(xml)
    page.get_by_role("button", name="匯入", exact=True).click()
    expect(page.get_by_text("匯入 1 筆")).to_be_visible()
    expect(page.get_by_role("cell", name="new.xml")).to_be_visible()

    check(page, server, "https://brand-new-fake.top/")
    expect(page.get_by_role("heading", level=1)).to_have_text("高風險")


def test_admin_duplicate_import_is_refused(page: Page, server):
    login(page, server)
    page.get_by_label("通報 TWNIC 詐騙網址彙整表").set_input_files(FIXTURE_XML)
    page.get_by_role("button", name="匯入", exact=True).click()
    expect(page.get_by_text("這份檔案已經匯入過了")).to_be_visible()


def test_admin_dashboard_shows_all_sections_and_logout(page: Page, server):
    check(page, server, "http://tw06.shopeelem.xyz/")
    login(page, server)
    for name in ["統計", "匯入政府 XML", "匯入紀錄", "模型版本"]:
        expect(page.get_by_role("heading", name=name, exact=True)).to_be_visible()
    expect(page.get_by_text("e2e-model")).to_be_visible()
    expect(page.get_by_text("啟用中")).to_be_visible()
    page.get_by_role("button", name="登出").click()
    page.goto(server["url"] + "/admin/")
    expect(page.get_by_role("heading", name="管理者登入")).to_be_visible()
