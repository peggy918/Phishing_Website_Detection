"""參數搜尋的輔助函式。"""
import numpy as np
import pytest

from ml.tune_models import CURRENT, GRIDS, expand, group_bootstrap_diff


def test_expand_is_full_product():
    combos = expand({"a": [1, 2], "b": ["x", "y", "z"]})
    assert len(combos) == 6 and {"a": 2, "b": "z"} in combos


def test_current_settings_are_inside_the_search_grid():
    # 目前參數必須在搜尋範圍內，否則「最佳」不一定不輸目前設定
    for algo, params in CURRENT.items():
        assert params in expand(GRIDS[algo])


@pytest.fixture
def scored():
    y = np.array([1, 1, 1, 0, 0, 0] * 5)
    good = np.array([0.9, 0.8, 0.7, 0.3, 0.2, 0.1] * 5)
    bad = np.array([0.4, 0.2, 0.6, 0.5, 0.7, 0.3] * 5)
    return y, good, bad, np.arange(len(y))


def test_bootstrap_identical_predictions_have_zero_difference(scored):
    y, good, _, groups = scored
    r = group_bootstrap_diff(y, good, good, groups, rounds=50)
    assert r["mean"] == 0 and r["low"] == 0 and r["high"] == 0 and r["a_wins"] == 0


def test_bootstrap_detects_a_better_model_and_is_reproducible(scored):
    y, good, bad, groups = scored
    r = group_bootstrap_diff(y, good, bad, groups, rounds=50)
    assert r["low"] > 0 and r["a_wins"] == 1
    assert r == group_bootstrap_diff(y, good, bad, groups, rounds=50)
