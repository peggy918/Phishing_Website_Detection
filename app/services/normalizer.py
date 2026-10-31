"""網址正規化與網域拆解。

訓練與線上預測共用本模組，不可另寫一份。正規化規則：
1. 去除前後空白與開頭雜字元（116 號的「;http://」），缺 scheme 補 http://
2. scheme、主機名轉小寫；主機名去掉開頭 www.、結尾的點；中文網域轉 punycode
3. 去除預設連接埠（http:80、https:443）
4. 去除追蹤參數（rules.yaml 的 tracking_params），其餘參數保留原順序；HTML 跳脫的 &amp; 還原為 &
5. 路徑與參數中的非 ASCII 字元與空白以百分比編碼統一（已編碼者不重複編碼），路徑空白視為「/」；
   主機名含空白則視為無效輸入
6. 保留 fragment（政府資料常見 #/login 這類前端路由），空 fragment 去掉

不變性：加上追蹤參數、改變主機名大小寫、加 www. 後，正規化結果必須相同。
"""
import re
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import quote, urlsplit, urlunsplit

import tldextract

from app.config_loader import load_rules

# 只使用 tldextract 隨附的 Public Suffix List 快照，執行時不下載，確保可重建
_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_LEADING_JUNK = ";,'\"<>()[]（）「」【】 \t"
_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_DEFAULT_PORTS = {"http": 80, "https": 443}
# 百分比編碼時保留的字元（RFC 3986 保留字元＋未保留字元＋%，避免重複編碼）
_SAFE_PATH = "/:@!$&'()*+,;=-._~%"
_SAFE_QUERY = _SAFE_PATH + "?"
MAX_URL_LENGTH = 4096


class InvalidURL(ValueError):
    """無法解析成網址的輸入（空字串、沒有主機名、含空白、過長等）。"""


@dataclass(frozen=True)
class NormalizedURL:
    raw: str                      # 使用者輸入的原始字串
    url: str                      # 正規化後的完整網址（特徵計算用）
    scheme: str
    host: str                     # 小寫、去 www.、punycode
    port: int | None              # 非預設連接埠
    path: str
    query: str                    # 已去除追蹤參數
    fragment: str
    userinfo: str | None          # @ 前的偽裝字串（1212、1280 號）
    registered_domain: str        # eTLD+1；IP 時為 IP 本身
    suffix: str                   # 公開後綴，例如 com.tw
    subdomain: str                # 註冊網域之前的部分（已去 www.）
    had_scheme: bool
    removed_params: tuple[str, ...] = field(default=())

    @property
    def sld(self) -> str:
        """註冊網域去掉後綴的部分，例如 shopee.tw → shopee。"""
        if self.suffix and self.registered_domain.endswith("." + self.suffix):
            return self.registered_domain[: -len(self.suffix) - 1]
        return self.registered_domain

    @property
    def is_ip(self) -> bool:
        return bool(_IPV4_RE.match(self.host)) or self.host.startswith("[")

    @property
    def storage_url(self) -> str:
        """存檔用：去除查詢參數與 fragment（CLAUDE.md：網址存檔前去除查詢參數）。"""
        netloc = self.host + (f":{self.port}" if self.port else "")
        return urlunsplit((self.scheme, netloc, self.path, "", ""))


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
    return reg_domain in _platforms()


@lru_cache(maxsize=1)
def _platforms() -> frozenset[str]:
    return frozenset(load_rules()["platform_domains"])


def match_key(host: str) -> tuple[str, str]:
    """黑名單比對層級與比對鍵：平台型網域用完整主機名，其餘用註冊網域。"""
    reg = registered_domain(host)
    if is_platform(reg):
        return "hostname", host.removeprefix("www.")
    return "registered", reg


def is_tracking_param(name: str) -> bool:
    rules = load_rules()["tracking_params"]
    name = name.lower()
    return name in rules["exact"] or any(name.startswith(p) for p in rules["prefixes"])


def _clean_query(query: str) -> tuple[str, tuple[str, ...]]:
    """去除追蹤參數，保留其餘參數的原始順序與寫法。"""
    query = query.replace("&amp;", "&")  # Kaggle 資料中有 HTML 跳脫的參數分隔符
    kept, removed = [], []
    for part in query.split("&"):
        if not part:
            continue
        name = part.split("=", 1)[0]
        if is_tracking_param(name):
            removed.append(name.lower())
        else:
            kept.append(part)
    return "&".join(kept), tuple(removed)


def _to_ascii_host(host: str) -> str:
    if host.isascii():
        return host
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        return quote(host, safe=".-")


def normalize(raw: str) -> NormalizedURL:
    if not isinstance(raw, str):
        raise InvalidURL("網址必須是字串")
    text = strip_junk(raw)
    if not text:
        raise InvalidURL("網址是空的")
    if len(text) > MAX_URL_LENGTH:
        raise InvalidURL(f"網址超過 {MAX_URL_LENGTH} 字元")
    had_scheme = bool(_SCHEME_RE.match(text))
    try:
        parts = urlsplit(ensure_scheme(text))
    except ValueError as e:  # 例如不合法的 IPv6 方括號
        raise InvalidURL(f"無法解析：{e}") from e
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https"):
        raise InvalidURL(f"不支援的 scheme：{scheme}")

    netloc = parts.netloc
    # 主機名不可含空白；路徑與參數中的空白（資料中 5 筆）比照瀏覽器編碼為 %20
    if any(c.isspace() for c in netloc):
        raise InvalidURL("主機名含有空白")
    userinfo = None
    if "@" in netloc:
        userinfo, netloc = netloc.rsplit("@", 1)
    host, _, port_text = netloc.partition(":") if not netloc.startswith("[") else (netloc, "", "")
    host = _to_ascii_host(host.strip(".").lower()).removeprefix("www.")
    if not host or "." not in host and not host.startswith("["):
        raise InvalidURL("找不到有效的主機名")
    port = int(port_text) if port_text.isdigit() else None
    if port == _DEFAULT_PORTS.get(scheme):
        port = None

    path = quote(parts.path, safe=_SAFE_PATH) or "/"
    query, removed = _clean_query(parts.query)
    query = quote(query, safe=_SAFE_QUERY)
    fragment = quote(parts.fragment, safe=_SAFE_QUERY + "#")

    ext = _extract(host)
    reg = ext.top_domain_under_public_suffix or host
    subdomain = host[: -len(reg)].rstrip(".") if host.endswith(reg) and host != reg else ""

    url = urlunsplit((scheme, host + (f":{port}" if port else ""), path, query, fragment))
    return NormalizedURL(
        raw=raw, url=url, scheme=scheme, host=host, port=port, path=path, query=query,
        fragment=fragment, userinfo=userinfo, registered_domain=reg, suffix=ext.suffix,
        subdomain=subdomain, had_scheme=had_scheme, removed_params=removed,
    )


def defang(url: str) -> str:
    """畫面顯示用的去連結格式：hxxps://example[.]top（不可產生可點擊連結）。"""
    return re.sub(r"^http", "hxxp", url, flags=re.IGNORECASE).replace(".", "[.]")
