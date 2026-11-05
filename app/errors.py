"""錯誤頁。不顯示內部錯誤細節。"""
from flask import render_template
from flask_wtf.csrf import CSRFError

from app.logging import current_request_id, log_event

MESSAGES = {
    400: ("請求無效", "請回到上一頁重新送出。"),
    404: ("找不到頁面", "這個頁面不存在或已失效。"),
    413: ("檔案太大", "上傳的檔案超過大小限制。"),
    429: ("送出太頻繁", "請稍候一分鐘再試。"),
    500: ("系統發生錯誤", "請稍後再試。"),
    503: ("服務暫時無法使用", "偵測模型尚未就緒，請稍後再試。"),
}


def _page(code: int):
    if code == 429:
        log_event("rate_limited")
    title, message = MESSAGES[code]
    return render_template("error.html", title=title, message=message, request_id=current_request_id()), code


def register_error_handlers(app) -> None:
    for code in MESSAGES:
        app.register_error_handler(code, lambda _e, c=code: _page(c))
    app.register_error_handler(CSRFError, lambda _e: _page(400))
