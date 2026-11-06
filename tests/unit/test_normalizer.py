"""階段 1：完整正規化。測資優先取自政府通報清單（括號內為原始編號）。"""
from dataclasses import replace

import pytest

from app.services.normalizer import InvalidURL, defang, normalize, refang

GOV_URLS = [
    "https://tobuyersepc24.com/57vgaqk#/login",                     # 1
    "https://www.shopmallbooks.com/wap/#/",                         # 318
    "http://tw06.shopeelem.xyz/",                                   # 327
    "web.books-compy.com",                                          # 172
    "https://help@rakutena-tw.shop",                                # 1280
    "https://eadiu.top/item/jzmk/250402.html",                      # 1373（去參數後）
    "https://einvoice-bss-natgov-tw.eu.cc/shopee/verify/binding.html",  # 1391
    "https://laobeibi.shop/products/【現貨供應】dr.gracie",          # 46 中文路徑
]

TRACKING_SUFFIXES = [
    "fbclid=IwAR2ZTIGXo3u7LNd6hyhohghm8v",
    "utm_source=facebook&utm_medium=paid&utm_campaign=1202",
    "gclid=abc&ttclid=def&wbraid=x&mibextid=y&sfnsn=z",
    "campaign_id=1&adset_id=2&ad_id=3&act=4",
    "UTM_Source=FB",  # 參數名稱大小寫
]


# ---- 不變性（CLAUDE.md 關鍵設計原則 2） ----

@pytest.mark.parametrize("url", GOV_URLS)
@pytest.mark.parametrize("tracking", TRACKING_SUFFIXES)
def test_tracking_params_invariance(url, tracking):
    base = normalize(url)
    if "#" in url:
        path, frag = url.split("#", 1)
        tracked = f"{path}?{tracking}#{frag}"
    else:
        tracked = f"{url}?{tracking}"
    assert normalize(tracked).url == base.url


def test_tracking_params_mixed_with_real_params():
    # 1373 號：真實參數與廣告參數混在一起，真實參數保留且順序不變
    n = normalize("https://eadiu.top/item?campaign_id=1&b=2&utm_source=facebook&a=1&fbclid=Iw")
    assert n.query == "b=2&a=1"
    assert n.removed_params == ("campaign_id", "utm_source", "fbclid")


@pytest.mark.parametrize("variant", [
    "https://WWW.ShopMallBooks.COM/wap/#/",
    "https://shopmallbooks.com/wap/#/",
    "https://www.shopmallbooks.com:443/wap/#/",
    "  https://www.shopmallbooks.com/wap/#/  ",
    "https://www.shopmallbooks.com./wap/#/",
])
def test_case_www_port_whitespace_invariance(variant):
    assert normalize(variant).url == "https://shopmallbooks.com/wap/#/"


def test_path_case_is_preserved():
    # 路徑大小寫有意義（短網址代碼），不可轉小寫
    assert normalize("https://a.com/AbC").path == "/AbC"


# ---- 各項規則 ----

def test_missing_scheme_and_leading_junk():
    assert normalize("web.books-compy.com").url == "http://web.books-compy.com/"     # 172
    n = normalize(";http://colaresearchclub.red/item/PJ1/txy2.html")                  # 116
    assert n.host == "colaresearchclub.red" and n.had_scheme


def test_userinfo_is_split_off():
    n = normalize("https://easywallet.com0165302705@vip.jkpay-officiali.com")        # 1212
    assert n.host == "vip.jkpay-officiali.com"
    assert n.userinfo == "easywallet.com0165302705"
    assert n.registered_domain == "jkpay-officiali.com"


def test_domain_parts():
    n = normalize("http://tw06.shopeelem.xyz/")
    assert (n.subdomain, n.registered_domain, n.suffix, n.sld) == ("tw06", "shopeelem.xyz", "xyz", "shopeelem")
    n = normalize("https://rakutentcstore.com.tw/")
    assert (n.suffix, n.sld, n.subdomain) == ("com.tw", "rakutentcstore", "")


def test_non_default_port_kept_and_ip():
    n = normalize("http://192.168.0.1:8080/login")
    assert n.port == 8080 and n.is_ip and n.url == "http://192.168.0.1:8080/login"


def test_unicode_path_percent_encoded_once():
    a = normalize("https://laobeibi.shop/products/【現貨】")
    b = normalize(a.url)  # 已編碼的網址再正規化一次結果相同（冪等）
    assert a.url == b.url and "%E3%80%90" in a.url


def test_unicode_host_to_punycode():
    host = normalize("http://蝦皮.tw/").host
    assert host.startswith("xn--") and host.encode("ascii").decode("idna") == "蝦皮.tw"


def test_space_in_path_or_query_is_encoded():
    # 政府資料 fbclid 值中間斷了一格；Kaggle 路徑含空白
    assert normalize("https://khves.top/item/22105.html?fbclid=IwAR1 Bjh").url == "https://khves.top/item/22105.html"
    assert normalize("http://a.com/x y").path == "/x%20y"


def test_html_escaped_ampersand():
    assert normalize("http://a.com/x?a=1&amp;b=2").query == "a=1&b=2"


def test_storage_url_drops_query_and_fragment():
    n = normalize("https://eadiu.top/item/250402.html?id=7&fbclid=x#top")
    assert n.storage_url == "https://eadiu.top/item/250402.html"


def test_defang():
    assert defang("https://tw06.shopeelem.xyz/") == "hxxps://tw06[.]shopeelem[.]xyz/"


# MCP 比較（docs/results/mcp-comparison.md F1）發現：貼入本站顯示的去連結格式會出現英文錯誤訊息

@pytest.mark.parametrize("url", GOV_URLS + ["http://a.com/x?a=1&b=2#top", "http://127.0.0.1:8080/admin"])
def test_defanged_input_gives_same_result(url):
    n = normalize(url)
    again = normalize(defang(n.url))
    assert replace(again, raw=n.url) == normalize(n.url)     # 除了原始輸入，其餘欄位都相同
    assert normalize(defang(n.storage_url)).storage_url == n.storage_url


@pytest.mark.parametrize("defanged, expected", [
    ("hxxp://tw06[.]shopeelem[.]xyz/", "http://tw06.shopeelem.xyz/"),
    ("HXXPS://shopee[.]tw/", "https://shopee.tw/"),
    ("hxxps[:]//shopee[.]tw/", "https://shopee.tw/"),
    ("tw06[.]shopeelem[.]xyz", "tw06.shopeelem.xyz"),
])
def test_refang(defanged, expected):
    assert refang(defanged) == expected


@pytest.mark.parametrize("url", [
    "http://www.hitsem.com/images/?hxxp:/us.battle.net/login",   # Kaggle 資料：hxxp 不在開頭，不可改動
    "http://[::1]/",                                              # IPv6 方括號不受影響
])
def test_refang_leaves_other_text_alone(url):
    assert refang(url) == url


def test_parse_error_message_is_chinese():
    with pytest.raises(InvalidURL, match="不是有效的網址") as e:
        normalize("http://[bad/")
    assert "Invalid" not in str(e.value)


@pytest.mark.parametrize("url", GOV_URLS + ["http://a.com/x?a=1&amp;b=2", "HTTP://WWW.A.COM"])
def test_idempotent(url):
    once = normalize(url).url
    assert normalize(once).url == once


# ---- 異常輸入（→ G7） ----

@pytest.mark.parametrize("bad", [
    "", "   ", "https://", "not a url", "http://a b.com", "http://a b.com/", "javascript:alert(1)",
    "ftp://example.com/file", "localhost", "https://" + "a" * 5000 + ".com",
])
def test_invalid_input_raises(bad):
    with pytest.raises(InvalidURL):
        normalize(bad)
