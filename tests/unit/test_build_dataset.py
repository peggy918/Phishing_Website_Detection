"""資料集切分規則（docs/dataset-plan.md）。用小型假資料，不依賴 data/processed 的大檔。"""
from collections import Counter

import pandas as pd
import pytest

from ml.build_dataset import bare_url, group_split, gov_rows, is_bare, tw_rows
from ml.make_variants import addition, homoglyph, omission, transposition


def test_group_split_is_deterministic_and_roughly_70_15_15():
    keys = [f"d{i}.com" for i in range(5000)]
    first = [group_split(k) for k in keys]
    assert first == [group_split(k) for k in keys]
    c = Counter(first)
    assert 0.67 < c["train"] / 5000 < 0.73 and 0.13 < c["val"] / 5000 < 0.17


def test_bare_helpers():
    assert is_bare("https://emord.top") and is_bare("http://emord.top/?fbclid=1")  # 追蹤參數不算路徑
    assert not is_bare("https://eadiu.top/item/1.html")
    assert bare_url("https://www.eadiu.top/item/1.html?id=7#x") == "https://eadiu.top/"


@pytest.fixture
def gov_csv(tmp_path):
    rows = [
        # record_id, url_fixed, reported_at, use_for_training, match_key, registered_domain, brand_key
        (1, "https://a.top/item/1.html", "2024-01-01", True, "a.top", "a.top", "shopee"),
        (2, "https://b.top/", "2025-10-31", True, "b.top", "b.top", None),
        (3, "https://c.top/x", "2025-11-01", True, "c.top", "c.top", None),       # 驗證段第一天
        (4, "https://d.top/x", "2026-04-01", True, "d.top", "d.top", None),       # 測試段第一天
        (5, "https://e.com.tw/x", "2024-05-01", True, "e.com.tw", "e.com.tw", None),
        (6, "https://f.top/x", "2024-05-01", False, "f.top", "f.top", None),      # 重複或待確認
    ]
    df = pd.DataFrame(rows, columns=["record_id", "url_fixed", "reported_at", "use_for_training",
                                     "match_key", "registered_domain", "brand_key"])
    path = tmp_path / "gov.csv"
    df.to_csv(path, index=False)
    return path


def test_gov_time_split_boundaries(gov_csv):
    df = gov_rows(gov_csv)
    orig = df[~df["augmented"]].set_index("record_id")["split"]
    assert orig.to_dict() == {"1": "train", "2": "train", "3": "val", "4": "test_b", "5": "train"}
    assert "6" not in orig.index


def test_gov_augmentation_only_train_and_only_with_path(gov_csv):
    aug = gov_rows(gov_csv).query("augmented")
    assert set(aug["record_id"]) == {"1", "5"}          # 2 本來就是純網域；3、4 不在訓練段
    assert set(aug["url"]) == {"https://a.top/", "https://e.com.tw/"}
    assert (aug["split"] == "train").all() and (aug["label"] == 1).all()


def test_gov_subgroups(gov_csv):
    sub = gov_rows(gov_csv).query("not augmented").set_index("record_id")["subgroup"]
    # 有無品牌字要等特徵算完才分（build），這裡只先標 .tw
    assert sub["1"] == "gov" and sub["2"] == "gov" and sub["5"] == "gov_tw"


def test_tw_rows_rules(tmp_path):
    rows = [
        ("shopee.tw", "shopee.tw", "brand:shopee", ""),
        ("cathaylife.com.tw", "cathaylife.com.tw", "related:cathay", ""),
        ("teams.com.tw", "teams.com.tw", "brand_lookalike", "train"),
        ("chinapost.com.tw", "chinapost.com.tw", "brand_lookalike", "test_c"),
        ("ntu.edu.tw", "ntu.edu.tw", "education", ""),
    ]
    path = tmp_path / "tw.csv"
    pd.DataFrame(rows, columns=["domain", "registered_domain", "category", "split"]).to_csv(path, index=False)
    df = tw_rows(path).set_index("group_key")
    assert df.loc["shopee.tw", "split"] == "train" and df.loc["cathaylife.com.tw", "split"] == "train"
    assert df.loc["teams.com.tw", "split"] == "train" and df.loc["chinapost.com.tw", "split"] == "test_c"
    assert df.loc["ntu.edu.tw", "split"] in {"train", "val", "test_c"}
    assert (df["label"] == 0).all() and df.loc["ntu.edu.tw", "url"] == "https://ntu.edu.tw/"


def test_variant_techniques():
    assert "shope" in omission("shopee")
    assert "rakutne" in transposition("rakuten")
    assert "sh0pee" in homoglyph("shopee") and "rnomo" in homoglyph("momo")
    assert "shopee-tw" in addition("shopee")
