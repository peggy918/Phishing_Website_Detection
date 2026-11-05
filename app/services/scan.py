"""偵測主流程：正規化 → 黑名單 → 白名單 → 模型＋品牌規則 → 存檔。全程不連線被檢查的網址。"""
import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config_loader import load_rules
from app.logging import stage
from app.models import Brand, ScanRequest, ScanResult, Whitelist
from app.services import blacklist, brand_match, predictor, reasons, risk
from app.services.features import extract
from app.services.normalizer import NormalizedURL, is_platform, normalize


def _save(session: Session, n: NormalizedURL, **fields) -> ScanRequest:
    request = ScanRequest(public_id=str(uuid.uuid4()), status="done", rules_version=load_rules()["version"])
    request.result = ScanResult(storage_url=n.storage_url, host=n.host, **fields)
    with stage("save"):
        session.add(request)
        session.flush()
    return request


def _brand_id(session: Session, key: str | None) -> int | None:
    return session.scalar(select(Brand.id).where(Brand.key == key)) if key else None


def scan_url(session: Session, raw: str) -> ScanRequest:
    """無效網址拋 InvalidURL；沒有可用模型時拋 ModelUnavailable（黑名單與白名單仍可判定）。呼叫端負責 commit。"""
    with stage("normalize"):
        n = normalize(raw)

    with stage("blacklist"):
        entry = blacklist.find(session, n)
    if entry:
        return _save(session, n, decided_by="blacklist", blacklist_entry_id=entry.id, risk_level=risk.HIGH,
                     suspected_brand_id=entry.brand_id, reasons=json.dumps(_blacklist_reasons(entry), ensure_ascii=False))

    # 平台型網域的註冊網域是平台本身，不能因此放行底下的所有子網域
    with stage("whitelist"):
        white = None if is_platform(n.registered_domain) else session.scalar(
            select(Whitelist).where(Whitelist.domain == n.registered_domain))
    if white:
        relation = "官方" if white.decision == "official" else "同集團"
        why = [f"網域列於{white.brand.name if white.brand else ''}的{relation}網域清單"]
        return _save(session, n, decided_by="whitelist", risk_level=risk.LOW, reasons=json.dumps(why, ensure_ascii=False))

    with stage("model"):
        model = predictor.active_model(session)
        match = brand_match.match(n)
        probability = model.probability(n)
        assessment = risk.assess(probability, match.kind, model.thresholds)
    why = reasons.model_reasons(n, extract(n), match, assessment.level)
    suspected = match.brand_key if match.kind in risk.IMPERSONATION_KINDS else None
    return _save(session, n, decided_by="model", model_version_id=model.id, probability=probability,
                 risk_level=assessment.level, brand_rule_applied=assessment.brand_rule_applied,
                 suspected_brand_id=_brand_id(session, suspected), reasons=json.dumps(why, ensure_ascii=False))


def _blacklist_reasons(entry) -> list[str]:
    date_text = entry.reported_on.strftime("%Y-%m-%d") if entry.reported_on else "日期不詳"
    first = f"已列入政府通報的詐騙網址清單（通報日期 {date_text}）"
    if entry.needs_review:
        first += "；此筆通報疑似遭入侵的網站，尚待人工確認"
    return [first, f"通報的冒用對象：{entry.target_text}"]
