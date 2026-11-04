"""資料庫設定腳本。sqlcmd 用系統編碼讀檔，UTF-8 中文註解會吃掉下一行，指令被跳過且不報錯（2026-11-04 實測）。"""
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "setup_db.sql"


def test_script_is_ascii_only():
    assert SCRIPT.read_bytes().isascii()


def test_script_stops_on_error_and_never_embeds_a_password():
    text = SCRIPT.read_text(encoding="ascii")
    assert ":On Error exit" in text
    assert "PASSWORD = N'$(APP_PASSWORD)'" in text
    assert text.count("PASSWORD =") == 1
