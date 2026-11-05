"""JSON 結構化紀錄：同一次操作共用 request_id，並記錄各階段耗時。

隱私原則：網址只記主機名與雜湊（url_hash），不記完整網址與查詢參數；無效輸入不記內容。
需要追查時，用同一個網址算出的雜湊比對紀錄，或用結果頁／錯誤頁顯示的追蹤碼找 request_id。
"""
import hashlib
import json
import logging
import time
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "phishguard"
logger = logging.getLogger(LOGGER_NAME)

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_stages: ContextVar[dict | None] = ContextVar("stages", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "event": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            entry["exc_type"] = record.exc_info[0].__name__
            entry["traceback"] = "".join(traceback.format_exception(*record.exc_info))
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure(path: str | Path | None) -> None:
    """輸出到標準輸出，並寫入可輪替的檔案。可重複呼叫（測試會建立多個 app）。"""
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handlers = [logging.StreamHandler()]
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(path, maxBytes=5_000_000, backupCount=3, encoding="utf-8"))
    for handler in handlers:
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)


def begin_request(request_id: str) -> None:
    _request_id.set(request_id)
    _stages.set({})


def current_request_id() -> str | None:
    return _request_id.get()


@contextmanager
def stage(name: str):
    """記錄一個階段的耗時（毫秒）。不在請求內時不記錄，所以 ml/ 腳本與 CLI 也能共用 services。"""
    start = time.perf_counter()
    try:
        yield
    finally:
        stages = _stages.get()
        if stages is not None:
            stages[name] = round((time.perf_counter() - start) * 1000, 2)


def stage_timings() -> dict:
    return dict(_stages.get() or {})


def url_hash(url: str) -> str:
    """同一網址得到相同雜湊，可用來追查，但無法從紀錄還原網址。"""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def log_event(event: str, level: int = logging.INFO, exc_info=None, **fields) -> None:
    logger.log(level, event, exc_info=exc_info, extra={"request_id": current_request_id(), "fields": fields})
