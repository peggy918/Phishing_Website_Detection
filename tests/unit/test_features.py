"""特徵模組。重點是不變性：同一個網址的不同寫法，特徵必須相同。"""
import math

import pytest

from app.services.features import FEATURE_NAMES, entropy, extract, extract_frame

# ---- 不變性 ----

@pytest.mark.parametrize("base, variants", [
    ("https://eadiu.top/item/jzmk/250402.html", [                     # 1373
        "https://eadiu.top/item/jzmk/250402.html?campaign_id=1&utm_source=facebook&fbclid=IwZX",
        "https://EADIU.top/item/jzmk/250402.html?gclid=x",
        "https://www.eadiu.top:443/item/jzmk/250402.html?ttclid=1&mibextid=2",
    ]),
    ("https://www.shopmallbooks.com/wap/#/", [                        # 318/319
        "https://shopmallbooks.com/wap/?utm_medium=paid#/",
    ]),
])
def test_tracking_case_www_invariance(base, variants):
    expected = extract(base)
    for v in variants:
        assert extract(v) == expected, v


@pytest.mark.parametrize("variants", [
    ["emord.top", "http://emord.top", "https://emord.top/"],
    ["web.books-compy.com/a?id=1", "https://web.books-compy.com/a?id=1"],  # 172 缺 scheme
])
def test_scheme_does_not_leak_into_features(variants):
    first = extract(variants[0])
    assert all(extract(v) == first for v in variants[1:])


# ---- 個別特徵（政府真實案例） ----

def f(url):
    return extract(url)


def test_feature_order_and_count():
    assert list(f("https://a.com").keys()) == FEATURE_NAMES
    assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES))


def test_host_features_on_shopee_variant():
    x = f("http://tw06.shopeelem.xyz/")                               # 327
    assert x["subdomain_count"] == 1
    assert x["tld_suspicious"] == 1 and "tld_is_tw" not in x
    assert x["host_has_tw_token"] == 1                                # tw06 → tw
    assert x["brand_contains"] == 1 and x["brand_distance"] == 0


def test_tw_tld_and_official_brand():
    x = f("https://shopee.tw/")
    assert x["tld_suspicious"] == 0
    assert x["brand_contains"] == 0 and x["brand_similar"] == 0 and x["brand_distance"] == 5


def test_userinfo_and_platform():
    assert f("https://help@rakutena-tw.shop")["has_userinfo"] == 1      # 1280
    x = f("https://shopee-tw.github.io/")
    assert x["is_platform"] == 1 and x["brand_contains"] == 1
    assert f("https://abc.it.com/h5/")["is_platform"] == 1              # 991 型


def test_fragment_route():
    x = f("https://tobuyersepc24.com/57vgaqk#/login")                  # 1
    assert x["has_fragment"] == 1 and x["fragment_route"] == 1
    assert x["path_keyword_count"] >= 1                                # login


def test_brand_with_digits_and_digit_ratio():
    x = f("http://newebpay11.com/")
    assert x["brand_with_digits"] == 1 and x["sld_has_digit"] == 1
    assert x["host_digit_ratio"] == pytest.approx(2 / len("newebpay11.com"))


def test_ip_port_punycode_shortener():
    assert f("http://192.168.0.1:8080/login")["is_ip"] == 1
    assert f("http://192.168.0.1:8080/login")["has_port"] == 1
    assert f("http://蝦皮.tw/")["is_punycode"] == 1
    assert f("https://reurl.cc/abc")["is_shortener"] == 1


def test_path_features():
    x = f("http://a.com/wp/login.php?u=http://evil.com&x=1")
    assert x["path_depth"] == 2 and x["path_ext_script"] == 1
    assert x["query_param_count"] == 2 and x["http_in_path"] == 1 and x["tld_in_path"] == 1
    assert f("https://eadiu.top/item/250402.html")["path_ext_html"] == 1


def test_entropy():
    assert entropy("") == 0 and entropy("aaaa") == 0
    assert entropy("ab") == pytest.approx(1.0)
    assert entropy("qsoern") > entropy("shopee")                       # 亂數網域較高


# ---- 批次 ----

def test_extract_frame_marks_invalid_rows():
    df = extract_frame(["https://a.com", "", "http://a b.com"])
    assert list(df["invalid_reason"] != "") == [False, True, True]
    assert math.isnan(df.loc[1, "host_length"]) and df.loc[0, "host_length"] == 5
