"""政府資料清理測試：fixture 取自原始 XML 的 15 筆真實紀錄。"""
from pathlib import Path

import pandas as pd
import pytest

from app.config_loader import match_brand
from ml.clean_gov import annotate, parse_xml

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "gov_sample.xml"


@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    return annotate(parse_xml(FIXTURE)).set_index("record_id")


def test_parse_types(df):
    assert len(df) == 15
    assert df.loc[1, "reported_at"] == pd.Timestamp("2023-06-29")


def test_www_and_subdomain_duplicates(df):
    # 318/319：含 www 與不含；327/330：子網域與註冊網域
    assert df.loc[319, "dup_of"] == 318 and not df.loc[318, "is_duplicate"]
    assert df.loc[330, "dup_of"] == 327
    assert not df.loc[319, "use_for_training"]


def test_domain_field_mismatch(df):
    assert df.loc[46, "domain_mismatch"]      # laobeibi / aobeibi
    assert df.loc[1207, "domain_mismatch"]    # jkpay-officiald.com / ezywalletc.net
    assert not df.loc[1, "domain_mismatch"]


def test_scheme_userinfo_and_junk(df):
    assert df.loc[172, "no_scheme"] and df.loc[172, "url_fixed"] == "http://web.books-compy.com"
    assert df.loc[1280, "has_userinfo"] and df.loc[1280, "host"] == "rakutena-tw.shop"
    assert df.loc[116, "leading_junk"] and df.loc[116, "host"] == "colaresearchclub.red"


def test_out_of_order_ids(df):
    # 1320 號之後的通報日期回到 2025-03/04
    assert df.loc[1320, "id_out_of_order"] and df.loc[1373, "id_out_of_order"]
    assert not df.loc[1319, "id_out_of_order"]


def test_platform_and_review(df):
    gh = df[df["registered_domain"] == "github.io"].iloc[0]
    assert gh["is_platform"] and gh["match_level"] == "hostname" and gh["created_date_unreliable"]
    # ecpay.com 子網域：只比完整主機名；政府通報為準，也作為訓練正例（2026-11-08）
    assert df.loc[886, "needs_review"] and df.loc[886, "use_for_training"]
    assert (df.loc[886, "match_level"], df.loc[886, "match_key"]) == ("hostname", "niconsortiu.ecpay.com")


def test_review_subdomains_are_not_duplicates_of_each_other():
    # 886／889／893 都是 ecpay.com 子網域：依註冊網域去重會只剩 886，依主機名則三筆都保留
    raw = parse_xml(FIXTURE)
    row = raw[raw["record_id"] == 886]
    other = row.assign(record_id=893, raw_url="http://retailpark.ecpay.com", domain_field="retailpark.ecpay.com")
    out = annotate(pd.concat([row, other], ignore_index=True)).set_index("record_id")
    assert not out["is_duplicate"].any() and out["use_for_training"].all()


def test_tracking_params_detected(df):
    assert "fbclid" in df.loc[1373, "tracking_params"]
    assert "utm_source" in df.loc[1373, "tracking_params"]


@pytest.mark.parametrize("text, key", [
    ("連至PChome 24H購物網站首頁", "pchome"),
    ("疑似假冒富邦媒體 momo購物網站", "momo"),
    ("疑似假冒新加坡商蝦皮娛樂電商有限公司台灣分公司", "shopee"),
    ("疑似假冒藍新科技股份有限公司", "newebpay"),
    ("偽冒電商一頁式詐騙", None),
])
def test_match_brand(text, key):
    assert match_brand(text) == key
