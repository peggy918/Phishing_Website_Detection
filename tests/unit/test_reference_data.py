"""白名單收錄規則（2026-11-03 本人決定）。"""
import pytest

from app.config_loader import load_brands
from app.services.reference_data import whitelist_rows


@pytest.fixture(scope="module")
def rows():
    return {r["domain"]: r for r in whitelist_rows()}


@pytest.mark.parametrize("domain", ["live.com", "line.me", "lin.ee", "shp.ee", "dcard.link", "momo.dm", "t.me",
                                    "facebook.com", "instagram.com", "fb.com"])
def test_user_content_and_short_link_domains_excluded(rows, domain):
    assert domain not in rows


@pytest.mark.parametrize("domain", ["newebpay.com", "ctbcbank.com", "hoka.com", "byredo.com"])
def test_domains_without_ownership_evidence_excluded(rows, domain):
    # 只確認存在於 Tranco，或 AI 依常識整理：等核對後才能跳過模型
    assert domain not in rows


@pytest.mark.parametrize("domain, decision, evidence, reviewer", [
    ("momo5188.com", "official", "manual_website", "user"),
    ("momo.com.tw", "official", "twnic_whois", "claude"),
    ("cathaylife.com.tw", "related", "twnic_whois", "claude"),
    ("cathaybk.com.tw", "official", "twnic_whois", "claude"),
    ("shopee.tw", "official", "twnic_whois", "claude"),
    ("dcard.tw", "official", "v2fly", "v2fly"),
])
def test_evidence_is_recorded(rows, domain, decision, evidence, reviewer):
    r = rows[domain]
    assert (r["decision"], r["evidence"], r["reviewer"]) == (decision, evidence, reviewer)


def test_rejected_review_results_never_whitelisted(rows):
    for domain in ["dcard.io", "linefriends.com.tw", "teams.com.tw", "chinapost.com.tw"]:
        assert domain not in rows


def test_no_whitelist_entries_are_real_brand_domains():
    # 打錯字的話，排除會悄悄失效
    for b in load_brands()["brands"]:
        assert set(b.get("no_whitelist", [])) <= set(b["domains"]) | set(b.get("related_domains", []))
