"""開發時以 TWNIC WHOIS（whois.twnic.net.tw:43）驗證參考網域的註冊者。

僅用於驗證 brands.yaml／抽查清單等「參考資料」，不屬於系統執行流程；
系統本身仍遵守「不對被檢查的網址做 WHOIS」原則。

原始回應存於 data/reference/whois/<domain>.txt（報告佐證），摘要輸出至 data/reference/whois_summary.csv。
用法：python -m ml.whois_check domain1 domain2 ...
"""
import csv
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "reference" / "whois"
SUMMARY = ROOT / "data" / "reference" / "whois_summary.csv"
SERVER = ("whois.twnic.net.tw", 43)


def query(domain: str, retries: int = 2) -> str:
    for attempt in range(retries + 1):
        try:
            with socket.create_connection(SERVER, timeout=30) as s:
                s.sendall(domain.encode("ascii") + b"\r\n")
                chunks = []
                while chunk := s.recv(4096):
                    chunks.append(chunk)
            return b"".join(chunks).decode("utf-8", "replace")
        except TimeoutError:
            if attempt == retries:
                raise
            time.sleep(5)


def parse(text: str) -> dict:
    """取 Registrant 區塊前兩行（中、英文名稱）、聯絡信箱網域與建立日期。"""
    lines = [l.strip() for l in text.splitlines()]
    info = {"registrant_zh": "", "registrant_en": "", "email_domain": "", "created": ""}
    if "Registrant:" in lines:
        block = []
        for l in lines[lines.index("Registrant:") + 1:]:
            if l.endswith(":") or l.startswith("Record "):
                break
            if l:  # 部分紀錄中文名稱留空，第一行是空白
                block.append(l)
        names = [l for l in block if "@" not in l and len(l) > 2 and l != "(Redacted for privacy)"]
        info["registrant_zh"] = names[0] if names else ""
        info["registrant_en"] = names[1] if len(names) > 1 else ""
        info["email_domain"] = next((l.split("@", 1)[1] for l in block if "@" in l), "")
    info["created"] = next((l.split("on", 1)[1].split()[0] for l in lines if l.startswith("Record created on")), "")
    return info


def main(domains: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for d in domains:
        if (OUT_DIR / f"{d}.txt").exists():  # 已查過的不重查
            continue
        try:
            text = query(d)
        except OSError as e:
            print(f"{d}: 查詢失敗（{e}），稍後重跑")
            time.sleep(30)
            continue
        (OUT_DIR / f"{d}.txt").write_text(text, encoding="utf-8")
        print(d, "ok")
        time.sleep(8)  # TWNIC 有頻率限制，查太快會被拒絕連線

    # 摘要由所有快取檔重建
    rows = []
    for p in sorted(OUT_DIR.glob("*.txt")):
        text = p.read_text(encoding="utf-8")
        found = "No Found" not in text and "Domain Name:" in text
        rows.append({"domain": p.stem, "found": found, **(parse(text) if found else {}),
                     "queried_at": time.strftime("%Y-%m-%d", time.localtime(p.stat().st_mtime))})
    with open(SUMMARY, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["domain", "found", "registrant_zh", "registrant_en",
                                          "email_domain", "created", "queried_at"])
        w.writeheader()
        w.writerows(rows)
    missing = [d for d in domains if not (OUT_DIR / f"{d}.txt").exists()]
    print(f"{len(rows)} cached, missing: {missing}")


if __name__ == "__main__":
    main(sys.argv[1:])
