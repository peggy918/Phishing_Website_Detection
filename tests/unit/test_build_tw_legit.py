"""台灣正常網域：brand_lookalike 的訓練／測試集 C 切分。"""
import pandas as pd

from ml.build_tw_legit import assign_lookalike_split


def _frame(rows):
    return pd.DataFrame(rows, columns=["domain", "category", "brand_key"])


def test_half_train_half_test_and_others_blank():
    df = _frame([
        ("a-line.tw", "brand_lookalike", "line"),
        ("b-line.tw", "brand_lookalike", "line"),
        ("c-books.tw", "brand_lookalike", "books"),
        ("d-books.tw", "brand_lookalike", "books"),
        ("ntu.edu.tw", "education", None),
    ])
    split = assign_lookalike_split(df)
    assert sorted(split[:4]) == ["test_c", "test_c", "train", "train"]
    assert split[4] == ""
    # 同品牌兩個網域分到不同邊
    assert set(split[:2]) == {"train", "test_c"} and set(split[2:4]) == {"train", "test_c"}


def test_split_is_deterministic_regardless_of_row_order():
    rows = [(f"x{i}.tw", "brand_lookalike", "line") for i in range(6)]
    a = dict(zip(_frame(rows)["domain"], assign_lookalike_split(_frame(rows))))
    rev = _frame(rows[::-1])
    b = dict(zip(rev["domain"], assign_lookalike_split(rev)))
    assert a == b
