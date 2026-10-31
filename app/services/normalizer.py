"""網址正規化與網域拆解。

階段 0 只提供資料清理需要的部分（補 scheme、取主機名、註冊網域、平台判斷）；
完整正規化（去追蹤參數、大小寫、www）於階段 1 補上。
訓練與線上預測共用本模組，不可另寫一份。
"""
import re
from functools import lru_cache
from urllib.parse import urlsplit

import tldextract

from app.config_loader import load_rules

# 只使用 tldextract 隨附的 Public Suffix List 快照，執行時不下載，確保可重建
_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_LEADING_JUNK = ";,'\"<>()[]（）「」【】 \t"


def strip_junk(url: str) -> str:
    """去除前後空白與開頭的標點（複製貼上常帶入的 ; , 引號、括號）。"""
    return url.strip().lstrip(_LEADING_JUNK).strip()


def ensure_scheme(url: str) -> str:
    """去除開頭雜字元（116 號的「;http://」），缺少 scheme 時補上 http://（172、401、1136 號等）。"""
    url = strip_junk(url)
    if not _SCHEME_RE.match(url):
        return "http://" + url
    return url


def split_host(url: str) -> tuple[str, str | None]:
    """回傳 (小寫主機名, userinfo)。含 @ 的網址（1280、1281 號）主機名取 @ 之後。"""
    parts = urlsplit(ensure_scheme(url))
    netloc = parts.netloc
    userinfo = None
    if "@" in netloc:
        userinfo, netloc = netloc.rsplit("@", 1)
    host = netloc.split(":", 1)[0].strip(".").lower()
    return host, userinfo


@lru_cache(maxsize=65536)
def registered_domain(host: str) -> str:
    """註冊網域（eTLD+1）；IP 或無法判斷時回傳主機名本身。"""
    ext = _extract(host)
    return ext.top_domain_under_public_suffix or host


def is_platform(reg_domain: str) -> bool:
    return reg_domain in set(load_rules()["platform_domains"])


def match_key(host: str) -> tuple[str, str]:
    """黑名單比對層級與比對鍵：平台型網域用完整主機名，其餘用註冊網域。"""
    reg = registered_domain(host)
    if is_platform(reg):
        return "hostname", host.removeprefix("www.")
    return "registered", reg
