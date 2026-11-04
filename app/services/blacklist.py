"""黑名單比對：一般網域比註冊網域；平台型與待確認紀錄比完整主機名。"""
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import BlacklistEntry
from app.services.normalizer import NormalizedURL


def find(session: Session, n: NormalizedURL) -> BlacklistEntry | None:
    """命中多筆時回傳最新通報的一筆；同時有正式紀錄與待確認紀錄時優先回傳正式紀錄。"""
    stmt = (
        select(BlacklistEntry)
        .where(or_(
            and_(BlacklistEntry.match_level == "registered", BlacklistEntry.match_key == n.registered_domain),
            and_(BlacklistEntry.match_level == "hostname", BlacklistEntry.match_key == n.host),
        ))
        .order_by(BlacklistEntry.needs_review, BlacklistEntry.reported_on.desc(), BlacklistEntry.id.desc())
        .limit(1)
    )
    return session.scalar(stmt)
