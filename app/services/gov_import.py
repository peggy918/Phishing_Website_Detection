"""解析與匯入數位產業署「通報 TWNIC 詐騙網址彙整表」XML。資料清理（ml/clean_gov.py）共用同一個解析器。

XML 來自管理者上傳，一律用 defusedxml 解析，拒絕外部實體與實體膨脹攻擊。
"""
import hashlib
from dataclasses import dataclass
from datetime import date, datetime

from defusedxml import ElementTree as SafeET
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config_loader import load_rules, match_brand
from app.models import BlacklistEntry, Brand, ImportBatch
from app.services.normalizer import InvalidURL, match_key, normalize

FIELDS = {
    "編號": "record_id",
    "一頁式數位經濟詐騙網站": "brand_text",
    "偽冒網址": "raw_url",
    "網域名稱": "domain_field",
    "詐騙網站創建日期": "created_at",
    "接獲通報日期": "reported_at",
    "停止解析日期": "stopped_at",
}


class ImportFailed(ValueError):
    """整份檔案無法匯入（格式不符、重複匯入）。訊息可直接顯示給管理者。"""


@dataclass(frozen=True)
class ImportSummary:
    batch_id: int
    imported: int
    skipped: int
    needs_review: int


def parse_gov_xml(content: bytes) -> list[dict]:
    """回傳欄位已對應成英文名稱、值為字串的紀錄。"""
    try:
        root = SafeET.fromstring(content)
    except Exception as e:  # defusedxml 的安全例外與一般解析錯誤都視為檔案無效
        raise ImportFailed(f"XML 無法解析：{e}") from e
    records = []
    for rec in root:
        row = {FIELDS[c.tag]: (c.text or "").strip() for c in rec if c.tag in FIELDS}
        if row:
            records.append(row)
    if not records or "raw_url" not in records[0]:
        raise ImportFailed("檔案內容不是通報 TWNIC 詐騙網址彙整表")
    return records


def _datetime(text: str) -> datetime | None:
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%S")
    except (TypeError, ValueError):
        return None


def _date(text: str) -> date | None:
    try:
        return datetime.strptime(text, "%Y%m%d").date()
    except (TypeError, ValueError):
        return None


def import_gov_xml(session: Session, filename: str, content: bytes) -> ImportSummary:
    """匯入一份 XML。無效網址或重複編號的紀錄略過並計數；呼叫端負責 commit。"""
    digest = hashlib.sha256(content).hexdigest()
    if session.scalar(select(ImportBatch.id).where(ImportBatch.file_sha256 == digest)):
        raise ImportFailed("這份檔案已經匯入過了")
    records = parse_gov_xml(content)

    brand_ids = dict(session.execute(select(Brand.key, Brand.id)).all())
    review = set(load_rules()["review_domains"])
    batch = ImportBatch(filename=filename[:255], record_count=0, file_sha256=digest)
    session.add(batch)
    session.flush()

    seen, entries, skipped, needs_review = set(), [], 0, 0
    for rec in records:
        no = rec.get("record_id", "")
        if not no.isdigit() or int(no) in seen:
            skipped += 1
            continue
        try:
            n = normalize(rec.get("raw_url", ""))
        except InvalidURL:
            skipped += 1
            continue
        seen.add(int(no))
        level, key = match_key(n.host)
        flagged = n.registered_domain in review
        if flagged:  # 疑似遭入侵的一般網站：只比完整主機名，避免把整個網域判成高風險
            level, key, needs_review = "hostname", n.host, needs_review + 1
        target = rec.get("brand_text", "")
        entries.append(BlacklistEntry(
            batch_id=batch.id, brand_id=brand_ids.get(match_brand(target)), record_no=int(no),
            target_text=target[:255], raw_url=rec["raw_url"], normalized_url=n.url, host=n.host,
            registered_domain=n.registered_domain, match_level=level, match_key=key,
            site_created_at=_datetime(rec.get("created_at")), reported_on=_date(rec.get("reported_at")),
            stopped_on=_date(rec.get("stopped_at")), needs_review=flagged,
        ))
    session.add_all(entries)
    batch.record_count = len(entries)
    batch.skipped_count = skipped
    return ImportSummary(batch.id, len(entries), skipped, needs_review)
