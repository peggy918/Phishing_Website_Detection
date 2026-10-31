"""階段 0 的網域拆解測試。測資取自政府通報清單的真實案例（括號內為原始編號）。"""
import pytest

from app.services.normalizer import ensure_scheme, match_key, registered_domain, split_host, strip_junk


@pytest.mark.parametrize("raw, expected", [
    ("web.books-compy.com", "http://web.books-compy.com"),            # 172 缺 scheme
    ("www.eintph.top", "http://www.eintph.top"),                      # 401
    ("linerpc.com", "http://linerpc.com"),                            # 1136
    ("https://tobuyersepc24.com/57vgaqk#/login", "https://tobuyersepc24.com/57vgaqk#/login"),  # 1
    ("HTTP://Example.top", "HTTP://Example.top"),                     # 大寫 scheme 不重複補
    (";http://colaresearchclub.red/item/PJ1/txy2.html", "http://colaresearchclub.red/item/PJ1/txy2.html"),  # 116 開頭雜字元
    ("  https://a.shop  ", "https://a.shop"),
])
def test_ensure_scheme(raw, expected):
    assert ensure_scheme(raw) == expected


def test_strip_junk_keeps_normal_url():
    assert strip_junk("https://a.top/x") == "https://a.top/x"


@pytest.mark.parametrize("raw, host, userinfo", [
    ("https://help@rakutena-tw.shop", "rakutena-tw.shop", "help"),                       # 1280
    ("https://easywallet.com0165302705@vip.jkpay-officiali.com", "vip.jkpay-officiali.com",
     "easywallet.com0165302705"),                                                         # 1212 用 @ 偽裝成悠遊付
    ("https://WWW.ShopMallBooks.com/wap/#/", "www.shopmallbooks.com", None),             # 318 大小寫
    ("http://tw06.shopeelem.xyz:8080/", "tw06.shopeelem.xyz", None),                     # 連接埠
    ("web.books-compy.com", "web.books-compy.com", None),                                # 172
])
def test_split_host(raw, host, userinfo):
    assert split_host(raw) == (host, userinfo)


@pytest.mark.parametrize("host, expected", [
    ("tw06.shopeelem.xyz", "shopeelem.xyz"),          # 327/330
    ("www.shopmallbooks.com", "shopmallbooks.com"),   # 318/319
    ("rakutentcstore.com.tw", "rakutentcstore.com.tw"),  # 二層 TLD
    ("diptyque-store.com.tw", "diptyque-store.com.tw"),
    ("shopee-tw.github.io", "github.io"),   # 不使用 PSL private 區段，平台改由 rules.yaml 判斷
    ("192.168.0.1", "192.168.0.1"),
])
def test_registered_domain(host, expected):
    assert registered_domain(host) == expected


@pytest.mark.parametrize("host, expected", [
    ("tw06.shopeelem.xyz", ("registered", "shopeelem.xyz")),
    ("www.shopmallbooks.com", ("registered", "shopmallbooks.com")),
    ("abc.carrd.co", ("hostname", "abc.carrd.co")),            # 平台型：比對完整主機名
    ("www.foo.weebly.com", ("hostname", "foo.weebly.com")),
    ("d123.cloudfront.net", ("hostname", "d123.cloudfront.net")),
    # 991/994：出租子網域服務，若比對註冊網域會把兩個不同詐騙站誤判為重複
    ("www.gouwuline-tw-wenjuan.it.com", ("hostname", "gouwuline-tw-wenjuan.it.com")),
    ("einvoice-bss-natgov-tw.eu.cc", ("hostname", "einvoice-bss-natgov-tw.eu.cc")),  # 1391
])
def test_match_key(host, expected):
    assert match_key(host) == expected
