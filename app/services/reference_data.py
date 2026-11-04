"""把 brands.yaml 與 data/reference/domain_reviews.csv 匯入資料庫（Brand、BrandDomain、Whitelist）。

白名單只收有歸屬佐證的網域（本人確認、TWNIC WHOIS、v2fly），並排除 no_whitelist。
沒有佐證或被排除的網域仍是官方網域（不觸發冒用規則），但交給模型判斷（2026-11-03 本人決定）。
檔案是正式資料來源，可在沒有資料庫的環境重建與計算雜湊；資料庫只供系統執行時查詢。
"""
import csv
import json
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config_loader import load_brands
from app.models import Brand, BrandDomain, Whitelist

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEWS = ROOT / "data" / "reference" / "domain_reviews.csv"
WHOIS_DIR = ROOT / "data" / "reference" / "whois"


def _reviews() -> dict[str, dict]:
    with open(REVIEWS, encoding="utf-8-sig", newline="") as f:
        return {r["domain"]: r for r in csv.DictReader(f)}


def evidence_for(domain: str, brand: dict, reviews: dict[str, dict]) -> tuple[str, str] | None:
    """回傳 (依據, 確認人)；沒有歸屬佐證時回傳 None。只出現在 Tranco 不算：那只代表網域存在。"""
    review = reviews.get(domain)
    if review and review["decision"] in ("official", "related"):
        return review["evidence"], review["reviewer"]
    if (WHOIS_DIR / f"{domain}.txt").exists():
        return "twnic_whois", "claude"
    if brand.get("source") == "v2fly":
        return "v2fly", "v2fly"
    return None


def whitelist_rows() -> list[dict]:
    reviews = _reviews()
    rows = []
    for b in load_brands()["brands"]:
        excluded = set(b.get("no_whitelist", []))
        for field, decision in (("domains", "official"), ("related_domains", "related")):
            for domain in b.get(field, []):
                ev = evidence_for(domain, b, reviews)
                if ev and domain not in excluded:
                    rows.append({"domain": domain, "brand_key": b["key"], "decision": decision,
                                 "evidence": ev[0], "reviewer": ev[1]})
    return rows


def seed_reference_data(session: Session) -> dict:
    """可重複執行。品牌以 key 更新（掃描紀錄會參照）；白名單與品牌網域完全依檔案重建。"""
    existing = {b.key: b for b in session.scalars(select(Brand))}
    session.execute(delete(BrandDomain))
    session.execute(delete(Whitelist))
    domain_count = 0
    for data in load_brands()["brands"]:
        brand = existing.get(data["key"]) or Brand(key=data["key"])
        brand.name = data["name"]
        brand.aliases = json.dumps(data["aliases"], ensure_ascii=False)
        session.add(brand)
        session.flush()
        existing[data["key"]] = brand
        for field, relation in (("domains", "official"), ("related_domains", "related")):
            for domain in data.get(field, []):
                session.add(BrandDomain(brand_id=brand.id, domain=domain, relation=relation))
                domain_count += 1
    rows = whitelist_rows()
    for r in rows:
        session.add(Whitelist(domain=r["domain"], brand_id=existing[r["brand_key"]].id, decision=r["decision"],
                              evidence=r["evidence"], reviewer=r["reviewer"]))
    return {"brands": len(existing), "brand_domains": domain_count, "whitelist": len(rows)}
