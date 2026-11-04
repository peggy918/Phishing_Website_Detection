"""SQLAlchemy 資料表（PLAN 第 7 節）。型別需同時相容 SQL Server（正式）與 SQLite（測試）。"""
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Unicode, UnicodeText, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class ImportBatch(Base):
    __tablename__ = "import_batch"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(Unicode(255))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    record_count: Mapped[int] = mapped_column(Integer)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    file_sha256: Mapped[str] = mapped_column(String(64), unique=True)  # 同一份檔案不重複匯入


class Brand(Base):
    __tablename__ = "brand"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(Unicode(100))
    aliases: Mapped[str] = mapped_column(UnicodeText, default="[]")  # JSON 陣列

    domains: Mapped[list["BrandDomain"]] = relationship(back_populates="brand")


class BrandDomain(Base):
    __tablename__ = "brand_domain"

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brand.id"))
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    relation: Mapped[str] = mapped_column(String(20))  # official／related

    brand: Mapped[Brand] = relationship(back_populates="domains")


class BlacklistEntry(Base):
    __tablename__ = "blacklist_entry"
    __table_args__ = (UniqueConstraint("batch_id", "record_no", name="uq_blacklist_batch_record"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batch.id"))
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brand.id"))
    record_no: Mapped[int] = mapped_column(Integer)          # 政府資料的原始編號
    target_text: Mapped[str] = mapped_column(Unicode(255))   # 政府資料記載的冒用對象
    raw_url: Mapped[str] = mapped_column(UnicodeText)
    normalized_url: Mapped[str] = mapped_column(UnicodeText)
    host: Mapped[str] = mapped_column(String(255))
    registered_domain: Mapped[str] = mapped_column(String(255))
    match_level: Mapped[str] = mapped_column(String(20))     # registered／hostname
    match_key: Mapped[str] = mapped_column(String(255), index=True)
    site_created_at: Mapped[datetime | None] = mapped_column(DateTime)
    reported_on: Mapped[date | None] = mapped_column(Date)
    stopped_on: Mapped[date | None] = mapped_column(Date)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)

    batch: Mapped[ImportBatch] = relationship()
    brand: Mapped[Brand | None] = relationship()


class Whitelist(Base):
    __tablename__ = "whitelist"

    id: Mapped[int] = mapped_column(primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brand.id"))
    decision: Mapped[str] = mapped_column(String(20))   # official／related
    evidence: Mapped[str] = mapped_column(String(30))   # manual_website／twnic_whois／v2fly
    reviewer: Mapped[str] = mapped_column(String(20))   # user／claude／v2fly
    note: Mapped[str] = mapped_column(Unicode(255), default="")

    brand: Mapped[Brand | None] = relationship()


class ModelVersion(Base):
    __tablename__ = "model_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(100), unique=True)
    algorithm: Mapped[str] = mapped_column(String(50))
    feature_version: Mapped[str] = mapped_column(String(30))
    rules_version: Mapped[str] = mapped_column(String(30))
    brands_version: Mapped[str] = mapped_column(String(30))
    dataset_sha256: Mapped[str] = mapped_column(String(64))
    seed: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[str] = mapped_column(UnicodeText)   # JSON
    threshold_medium: Mapped[float] = mapped_column(Float)
    threshold_high: Mapped[float] = mapped_column(Float)
    artifact_path: Mapped[str] = mapped_column(Unicode(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ScanRequest(Base):
    __tablename__ = "scan_request"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True)  # 結果頁網址用，不可被循序猜測
    input_type: Mapped[str] = mapped_column(String(20), default="url")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[str] = mapped_column(String(20))     # done／invalid／error
    rules_version: Mapped[str] = mapped_column(String(30))

    result: Mapped["ScanResult | None"] = relationship(back_populates="request", uselist=False)


class ScanResult(Base):
    __tablename__ = "scan_result"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("scan_request.id"), unique=True)
    storage_url: Mapped[str] = mapped_column(UnicodeText)  # 已去除查詢參數與 fragment
    host: Mapped[str] = mapped_column(String(255))
    decided_by: Mapped[str] = mapped_column(String(20))    # blacklist／whitelist／model
    blacklist_entry_id: Mapped[int | None] = mapped_column(ForeignKey("blacklist_entry.id"))
    suspected_brand_id: Mapped[int | None] = mapped_column(ForeignKey("brand.id"))
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_version.id"))
    probability: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(10))    # low／medium／high
    brand_rule_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    reasons: Mapped[str] = mapped_column(UnicodeText, default="[]")  # JSON 陣列

    request: Mapped[ScanRequest] = relationship(back_populates="result")
    blacklist_entry: Mapped[BlacklistEntry | None] = relationship()
    suspected_brand: Mapped[Brand | None] = relationship()
    model_version: Mapped[ModelVersion | None] = relationship()


class AdminUser(Base):
    __tablename__ = "admin_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
