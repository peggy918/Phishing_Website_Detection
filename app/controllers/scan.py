"""訪客：輸入網址、檢視結果。"""
import json
import logging
import uuid

from flask import Blueprint, abort, redirect, render_template, request, url_for
from sqlalchemy import select

from app.config_loader import load_rules
from app.extensions import db_session, limiter
from app.logging import log_event, stage, stage_timings, url_hash
from app.models import ScanRequest
from app.services.normalizer import InvalidURL
from app.services.predictor import ModelUnavailable
from app.services.scan import scan_url

scan_bp = Blueprint("scan", __name__)


@scan_bp.get("/")
def index():
    return render_template("index.html")


@scan_bp.post("/scan")
@limiter.limit("30 per minute")
def scan():
    session = db_session()
    raw = request.form.get("url", "")
    try:
        req = scan_url(session, raw)
    except InvalidURL as e:
        session.rollback()
        # 無效輸入只記狀態，不存輸入內容
        session.add(ScanRequest(public_id=str(uuid.uuid4()), status="invalid", rules_version=load_rules()["version"]))
        session.commit()
        log_event("scan_invalid")
        return render_template("index.html", error=str(e), value=raw[:300]), 400
    except ModelUnavailable as e:
        session.rollback()
        log_event("scan_unavailable", level=logging.ERROR, reason=str(e))
        abort(503)
    with stage("commit"):
        session.commit()
    r = req.result
    log_event("scan_completed", host=r.host, url_hash=url_hash(r.storage_url), decided_by=r.decided_by,
              risk_level=r.risk_level, brand_rule_applied=r.brand_rule_applied,
              probability=r.probability, model_version_id=r.model_version_id,
              rules_version=req.rules_version, stages_ms=stage_timings())
    # 送出後導向結果頁：重新整理不會重複送出
    return redirect(url_for("scan.result", public_id=req.public_id), code=303)


@scan_bp.get("/result/<public_id>")
def result(public_id: str):
    req = db_session().scalar(select(ScanRequest).where(ScanRequest.public_id == public_id))
    if req is None or req.result is None:
        abort(404)
    return render_template("result.html", result=req.result, reasons=json.loads(req.result.reasons))
