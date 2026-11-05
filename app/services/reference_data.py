"""把品牌、抽查紀錄與 WHOIS 摘要匯入資料庫，並由資料庫的紀錄決定白名單。

白名單只收有歸屬佐證的網域（本人確認、TWNIC WHOIS、v2fly），並排除 no_whitelist。
沒有佐證或被排除的網域仍是官方網域（不觸發冒用規則），但交給模型判斷（2026-11-03 本人決定）。

佐證以資料庫為準（2026-11-06 本人決定）。repo 裡的 domain_reviews.csv、whois_summary.csv 是遮蔽過的摘要，
只用來讓空資料庫（GitHub Actions、重建環境）建立初始資料；完整 WHOIS 回應含第三方個資，只存本機資料庫
（import_whois_raw），不進 repo。
"""
import csv
import json
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config_loader import load_brands
from app.models import Brand, BrandDomain, DomainReview, Whitelist, WhoisRecord

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEWS = ROOT / "data" / "reference" / "domain_reviews.csv"
WHOIS_SUMMARY = ROOT / "data" / "reference" / "whois_summary.csv"
ACCEPTED_DECISIONS = ("official", "related")


def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sync_reviews(session: Session, path: Path = REVIEWS) -> int:
    existing = {r.domain: r for r in session.scalars(select(DomainReview))}
    rows = _read_csv(path)
    for row in rows:
        record = existing.get(row["domain"]) or DomainReview(domain=row["domain"])
        record.brand_key = row["brand_key"]
        record.decision = row["decision"]
        record.evidence = row["evidence"]
        record.registrant = row["registrant"]
        record.reviewer = row["reviewer"]
        record.reviewed_on = row["reviewed_at"]
        record.note = row["note"]
        session.add(record)
    session.flush()
    return len(rows)


def sync_whois_summary(session: Session, path: Path = WHOIS_SUMMARY) -> int:
    """更新摘要欄位，但不動 raw_response：本機已匯入的完整回應不可被摘要蓋掉。"""
    existing = {r.domain: r for r in session.scalars(select(WhoisRecord))}
    rows = [r for r in _read_csv(path) if r["found"] == "True"]
    for row in rows:
        record = existing.get(row["domain"]) or WhoisRecord(domain=row["domain"])
        record.registrant = row["registrant_zh"] or row["registrant_en"]
        record.record_created_on = row["created"]
        record.queried_on = row["queried_at"]
        session.add(record)
    session.flush()
    return len(rows)


def import_whois_raw(session: Session, folder: Path) -> int:
    """把本機的完整 WHOIS 回應存入資料庫。檔名為 <網域>.txt；資料庫沒有的網域會新增。"""
    existing = {r.domain: r for r in session.scalars(select(WhoisRecord))}
    count = 0
    for path in sorted(Path(folder).glob("*.txt")):
        record = existing.get(path.stem) or WhoisRecord(domain=path.stem, registrant="", record_created_on="", queried_on="")
        record.raw_response = path.read_text(encoding="utf-8")
        session.add(record)
        count += 1
    session.flush()
    return count


def evidence_for(domain: str, brand: dict, reviews: dict[str, DomainReview],
                 whois: dict[str, WhoisRecord]) -> tuple[str, str] | None:
    """回傳 (依據, 確認人)；沒有歸屬佐證時回傳 None。只出現在 Tranco 不算：那只代表網域存在。"""
    review = reviews.get(domain)
    if review and review.decision in ACCEPTED_DECISIONS:
        return review.evidence, review.reviewer
    if domain in whois:
        return "twnic_whois", "claude"
    if brand.get("source") == "v2fly":
        return "v2fly", "v2fly"
    return None


def whitelist_rows(session: Session) -> list[dict]:
    reviews = {r.domain: r for r in session.scalars(select(DomainReview))}
    whois = {r.domain: r for r in session.scalars(select(WhoisRecord))}
    rows = []
    for b in load_brands()["brands"]:
        excluded = set(b.get("no_whitelist", []))
        for field, decision in (("domains", "official"), ("related_domains", "related")):
            for domain in b.get(field, []):
                ev = evidence_for(domain, b, reviews, whois)
                if ev and domain not in excluded:
                    rows.append({"domain": domain, "brand_key": b["key"], "decision": decision,
                                 "evidence": ev[0], "reviewer": ev[1]})
    return rows


def seed_reference_data(session: Session) -> dict:
    """可重複執行。品牌以 key 更新（掃描紀錄會參照）；品牌網域與白名單依資料庫的紀錄重建。"""
    existing = {b.key: b for b in session.scalars(select(Brand))}
    session.execute(delete(BrandDomain))
    session.execute(delete(Whitelist))
    review_count = sync_reviews(session)
    whois_count = sync_whois_summary(session)
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
    rows = whitelist_rows(session)
    for r in rows:
        session.add(Whitelist(domain=r["domain"], brand_id=existing[r["brand_key"]].id, decision=r["decision"],
                              evidence=r["evidence"], reviewer=r["reviewer"]))
    return {"brands": len(existing), "brand_domains": domain_count, "whitelist": len(rows),
            "domain_reviews": review_count, "whois_records": whois_count}
