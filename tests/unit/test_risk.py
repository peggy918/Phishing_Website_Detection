"""風險門檻邊界值與品牌規則（PLAN 第 8 節測試優先順序 4）。"""
import pytest

from app.services.brand_match import match
from app.services.normalizer import normalize
from app.services.risk import HIGH, LOW, MEDIUM, assess, model_level

T = {"medium": 0.4, "high": 0.8}


@pytest.mark.parametrize("p, level", [
    (0.0, LOW), (0.3999, LOW), (0.4, MEDIUM), (0.7999, MEDIUM), (0.8, HIGH), (1.0, HIGH),
])
def test_threshold_boundaries(p, level):
    assert model_level(p, T) == level


@pytest.mark.parametrize("kind", ["contains", "similar"])
def test_impersonation_raises_low_to_medium(kind):
    r = assess(0.01, kind, T)
    assert (r.level, r.model_level, r.brand_rule_applied) == (MEDIUM, LOW, True)


@pytest.mark.parametrize("p, level", [(0.5, MEDIUM), (0.9, HIGH)])
def test_rule_never_changes_medium_or_high(p, level):
    r = assess(p, "contains", T)
    assert (r.level, r.brand_rule_applied) == (level, False)


@pytest.mark.parametrize("kind", ["none", "official", "related"])
def test_rule_does_not_fire_without_impersonation(kind):
    r = assess(0.01, kind, T)
    assert (r.level, r.brand_rule_applied) == (LOW, False)


@pytest.mark.parametrize("url, level", [
    ("http://web.books-compy.com", MEDIUM),   # 172：冒用博客來
    ("https://shopee.tw/", LOW),              # 官方網域
    ("https://cathaylife.com.tw/", LOW),      # 同集團
    ("https://ntu.edu.tw/", LOW),             # 無品牌字
])
def test_with_real_brand_match(url, level):
    assert assess(0.01, match(normalize(url)).kind, T).level == level
