"""白名單收錄規則（2026-11-03 本人決定）與佐證來源（2026-11-06：以資料庫為準）。"""
import csv
import re

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config_loader import load_brands
from app.models import Base, WhoisRecord
from app.services.reference_data import (
    REVIEWS,
    WHOIS_SUMMARY,
    import_whois_raw,
    seed_reference_data,
    sync_whois_summary,
    whitelist_rows,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        seed_reference_data(s)
        yield s
    engine.dispose()


@pytest.fixture
def rows(session):
    return {r["domain"]: r for r in whitelist_rows(session)}


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


# ---- 佐證以資料庫為準 ----

def test_evidence_comes_from_database_not_files(session):
    # cathaybk.com.tw 的佐證只有 WHOIS 紀錄：從資料庫刪掉後就不能再進白名單
    assert "cathaybk.com.tw" in {r["domain"] for r in whitelist_rows(session)}
    session.delete(session.scalar(select(WhoisRecord).where(WhoisRecord.domain == "cathaybk.com.tw")))
    session.flush()
    assert "cathaybk.com.tw" not in {r["domain"] for r in whitelist_rows(session)}


def test_reseed_keeps_local_raw_response(session, tmp_path):
    (tmp_path / "shopee.tw.txt").write_text("完整回應", encoding="utf-8")
    assert import_whois_raw(session, tmp_path) == 1
    seed_reference_data(session)
    assert session.scalar(select(WhoisRecord.raw_response).where(WhoisRecord.domain == "shopee.tw")) == "完整回應"


def test_import_raw_adds_unknown_domain(session, tmp_path):
    (tmp_path / "new-domain.tw.txt").write_text("回應", encoding="utf-8")
    import_whois_raw(session, tmp_path)
    assert session.scalar(select(WhoisRecord.raw_response).where(WhoisRecord.domain == "new-domain.tw")) == "回應"


def test_summary_alone_gives_no_raw_response(session):
    # GitHub Actions 與重建環境只有摘要，資料庫不會有完整回應
    assert session.scalars(select(WhoisRecord.raw_response).where(WhoisRecord.raw_response.is_not(None))).first() is None


def test_not_found_summary_rows_are_not_evidence(session, tmp_path):
    path = tmp_path / "summary.csv"
    path.write_text("domain,found,registrant_zh,registrant_en,created,queried_at\nghost.tw,False,,,,2026-11-06\n",
                    encoding="utf-8")
    sync_whois_summary(session, path)
    assert session.scalar(select(WhoisRecord).where(WhoisRecord.domain == "ghost.tw")) is None


# ---- repo 公開：摘要不可含第三方個資 ----

@pytest.mark.parametrize("path", [REVIEWS, WHOIS_SUMMARY])
def test_public_reference_files_have_no_email_or_phone(path):
    text = path.read_text(encoding="utf-8-sig")
    assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    assert not re.search(r"\+\d{3}\.\d{6,}", text)


def test_public_summary_drops_email_domain_column():
    with open(WHOIS_SUMMARY, encoding="utf-8-sig", newline="") as f:
        assert "email_domain" not in csv.DictReader(f).fieldnames


def test_individual_registrant_is_masked():
    with open(REVIEWS, encoding="utf-8-sig", newline="") as f:
        row = next(r for r in csv.DictReader(f) if r["domain"] == "yabeline.tw")
    assert row["registrant"] == "(個人，已遮蔽)"
