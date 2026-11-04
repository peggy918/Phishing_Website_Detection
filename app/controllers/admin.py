"""管理者：登入、匯入政府 XML、檢視統計、切換模型版本。只允許本機存取。"""
from functools import wraps
from pathlib import Path

from flask import Blueprint, abort, flash, redirect, render_template, request, session as cookie, url_for
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db_session, limiter
from app.models import AdminUser, BlacklistEntry, ImportBatch, ModelVersion, ScanRequest, ScanResult, Whitelist
from app.services.gov_import import ImportFailed, import_gov_xml
from app.services.predictor import activate_model

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

LOOPBACK = {"127.0.0.1", "::1"}
# Cloudflare Tunnel 的 cloudflared 跑在本機，對 Flask 來說來源也是 127.0.0.1，
# 所以只看 remote_addr 不夠：帶轉送標頭的請求一律視為外部。
FORWARD_HEADERS = ("CF-Connecting-IP", "CF-Ray", "X-Forwarded-For", "X-Real-IP", "Forwarded")
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def is_local_request() -> bool:
    return request.remote_addr in LOOPBACK and not any(h in request.headers for h in FORWARD_HEADERS)


@admin_bp.before_request
def local_only():
    if not is_local_request():
        abort(404)   # 不透露管理頁面存在


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "admin_id" not in cookie:
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        user = db_session().scalar(select(AdminUser).where(AdminUser.username == request.form.get("username", "")))
        # 帳號不存在時也驗一次雜湊，避免從回應時間猜出帳號
        ok = check_password_hash(user.password_hash if user else _DUMMY_HASH, request.form.get("password", ""))
        if user and ok:
            cookie.clear()
            cookie["admin_id"] = user.id
            return redirect(url_for("admin.dashboard"))
        flash("帳號或密碼錯誤", "error")
    return render_template("admin/login.html")


@admin_bp.post("/logout")
def logout():
    cookie.clear()
    return redirect(url_for("admin.login"))


@admin_bp.get("/")
@login_required
def dashboard():
    db = db_session()
    levels = dict(db.execute(select(ScanResult.risk_level, func.count()).group_by(ScanResult.risk_level)).all())
    deciders = dict(db.execute(select(ScanResult.decided_by, func.count()).group_by(ScanResult.decided_by)).all())
    return render_template(
        "admin/dashboard.html",
        levels=levels, deciders=deciders,
        scan_total=db.scalar(select(func.count()).select_from(ScanRequest)),
        invalid_total=db.scalar(select(func.count()).select_from(ScanRequest).where(ScanRequest.status == "invalid")),
        blacklist_total=db.scalar(select(func.count()).select_from(BlacklistEntry)),
        whitelist_total=db.scalar(select(func.count()).select_from(Whitelist)),
        batches=db.scalars(select(ImportBatch).order_by(ImportBatch.imported_at.desc()).limit(10)).all(),
        models=db.scalars(select(ModelVersion).order_by(ModelVersion.registered_at.desc())).all(),
    )


@admin_bp.post("/import")
@login_required
def import_xml():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        flash("請選擇 XML 檔案", "error")
        return redirect(url_for("admin.dashboard"))
    db = db_session()
    try:
        summary = import_gov_xml(db, Path(upload.filename).name, upload.read())
        db.commit()
    except ImportFailed as e:
        db.rollback()
        flash(str(e), "error")
    else:
        flash(f"匯入 {summary.imported} 筆（略過 {summary.skipped} 筆，待確認 {summary.needs_review} 筆）", "ok")
    return redirect(url_for("admin.dashboard"))


@admin_bp.post("/models/<int:model_id>/activate")
@login_required
def activate(model_id: int):
    db = db_session()
    if db.get(ModelVersion, model_id) is None:
        abort(404)
    activate_model(db, model_id)
    db.commit()
    flash("已切換模型版本", "ok")
    return redirect(url_for("admin.dashboard"))
