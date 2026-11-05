"""抽查紀錄 domain_reviews.csv 與 brands.yaml 的一致性，以及讀取時的格式驗證。"""
import pandas as pd
import pytest

from app.config_loader import load_brands
from ml import domain_reviews


@pytest.fixture(scope="module")
def reviews():
    return domain_reviews.load()


@pytest.fixture(scope="module")
def brands():
    return {b["key"]: b for b in load_brands()["brands"]}


def test_brand_keys_exist(reviews, brands):
    assert set(reviews["brand_key"]) <= set(brands)


@pytest.mark.parametrize("decision, field", [("official", "domains"), ("related", "related_domains")])
def test_accepted_domains_are_in_brands(reviews, brands, decision, field):
    rows = reviews[reviews["decision"] == decision]
    missing = [r.domain for r in rows.itertuples() if r.domain not in brands[r.brand_key].get(field, [])]
    assert missing == []


def test_rejected_domains_not_in_any_brand(reviews, brands):
    listed = {d for b in brands.values() for d in b["domains"] + b.get("related_domains", [])}
    rejected = set(reviews.loc[reviews["decision"].isin(["not_brand", "removed"]), "domain"])
    assert rejected & listed == set()


def test_whois_rows_are_in_public_summary(reviews):
    summary = pd.read_csv(domain_reviews.ROOT / "data" / "reference" / "whois_summary.csv", encoding="utf-8-sig")
    rows = reviews[reviews["evidence"] == "twnic_whois"]
    assert set(rows["domain"]) <= set(summary.loc[summary["found"], "domain"])


def test_invalid_decision_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "domain,brand_key,decision,evidence,registrant,reviewer,reviewed_at,trigger,tranco_rank,note\n"
        "a.com.tw,momo,○,manual_website,,user,2026-10-31,not_in_tranco,,\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="decision"):
        domain_reviews.load(bad)


def test_duplicate_domain_raises(tmp_path):
    bad = tmp_path / "dup.csv"
    row = "a.com.tw,momo,official,manual_website,,user,2026-10-31,not_in_tranco,,\n"
    bad.write_text("domain,brand_key,decision,evidence,registrant,reviewer,reviewed_at,trigger,tranco_rank,note\n"
                   + row + row, encoding="utf-8")
    with pytest.raises(ValueError, match="重複"):
        domain_reviews.load(bad)
