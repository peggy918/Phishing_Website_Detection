"""品牌近似判斷。測資取自政府通報清單、Tranco 抽查與 Kaggle 中觀察到的真實網域。"""
import pytest

from app.services.brand_match import NO_MATCH_DISTANCE, homoglyph_normalize, match, osa_distance
from app.services.normalizer import normalize


def m(url):
    return match(normalize(url))


@pytest.mark.parametrize("url, brand, kind", [
    # 官方與同集團：不算冒用
    ("https://shopee.tw/", "shopee", "official"),
    ("https://www.momo.com.tw/", "momo", "official"),
    ("https://cathaylife.com.tw/", "cathay", "related"),
    # 直接包含品牌字（政府資料）
    ("http://tw06.shopeelem.xyz/", "shopee", "contains"),          # 327
    ("https://onlytoppc24.com/x#/login", "pchome", "contains"),    # 2：含數字的關鍵字任意位置
    ("https://rakutenz-tw.shop", "rakuten", "contains"),           # 1281
    ("http://web.books-compy.com", "books", "contains"),           # 172
    ("http://linerpc.com", "line", "contains"),                    # 1136：4 字關鍵字在開頭
    ("https://shopee-tw.github.io/", "shopee", "contains"),        # 平台子網域
    # 同形字
    ("http://sh0pee-tw.top/", "shopee", "contains"),
    ("http://rnomoshop.top/", "momo", "contains"),                 # rn → m
    # 近似
    ("https://rakutsenaffilike.com/", "rakuten", "similar"),
    ("http://telegrm.net/", "telegram", "similar"),                # 1146 一帶
    ("http://mlcr0sof7-off1c017.typeform.com/", "microsoft", "similar"),  # Kaggle 釣魚
    # 第二版：官方網域名稱當近似候選、5 字整詞比對（依 val_d 調整）
    ("https://momsohop.com.tw/", "momo", "similar"),              # momoshop 相鄰互換
    ("https://ecpya.com.tw/", "ecpay", "similar"),                 # 5 字整詞
    ("https://fcclub.com.tw/", "kfc", "similar"),                  # cl→d 不可破壞 club
    ("https://kfcc1ub.com.tw/", "kfc", "similar"),                 # 同形字 1→l 後才出現 cl
    # 國際精品（政府資料 .tw 仿冒）
    ("https://www.diptyqueshop.com.tw/", "diptyque", "contains"),
    ("https://www.hokashop.com.tw/", "hoka", "contains"),
])
def test_detected(url, brand, kind):
    r = m(url)
    assert (r.brand_key, r.kind) == (brand, kind)


@pytest.mark.parametrize("url", [
    "https://onlinetest.tw/",          # line 不可命中 online；也不可近似 hinet
    "https://chinapost.com.tw/",       # 4 字的 post 只看開頭
    "https://shopping.com/",           # 不放 shoppe 關鍵字
    "https://developer.mozilla.org/",  # mobile01 不做近似
    "https://easycamp.com.tw/",        # 只容許差 1 字
    "https://ntu.edu.tw/",
    "http://192.168.0.1/login",
    "https://abc.hinet.net/",          # 平台本身名稱不算品牌
    "https://hokkaido.jp/",            # 4 字的 hoka 只看開頭
    "https://hookah.com/",
    "https://lin.me/",                 # 4 字品牌不做近似（已知限制，val_d 中 line 變形抓不到）
])
def test_not_detected(url):
    r = m(url)
    assert r.kind == "none" and r.distance == NO_MATCH_DISTANCE


def test_brand_with_digits():
    assert m("http://newebpay11.com/").with_digits         # PLAN 3.2 newebpay* 變體
    assert not m("http://newebpay-tw.cc/").with_digits


def test_known_false_positive_is_documented():
    # 抽查確認為正常網站、但含品牌字：模型要靠其他特徵分辨（測試集 C 的 brand_lookalike）
    assert m("https://teams.com.tw/").kind == "contains"
    assert m("https://lineage182.tw/").kind == "contains"


@pytest.mark.parametrize("a, b, d", [
    ("shopee", "shopee", 0), ("shoppe", "shopee", 1), ("rakutne", "rakuten", 1),  # 相鄰互換算 1
    ("telegrm", "telegram", 1), ("abc", "", 3), ("", "", 0),
])
def test_osa_distance(a, b, d):
    assert osa_distance(a, b) == d


def test_homoglyph_multi_char_first():
    assert homoglyph_normalize("rnicr0soft") == "microsoft"
