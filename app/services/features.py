"""網址特徵：只用網址字串計算，不連線、不查 DNS／WHOIS。訓練與線上預測共用本模組。

特徵分三組，方便階段 2 做分組比較（例如只用主機名特徵，檢查模型是否依賴路徑長度捷徑）：
- HOST：主機名（長度、符號、亂數程度、TLD、平台、短網址…）
- PATH：路徑、參數與整串網址
- BRAND：品牌近似（app/services/brand_match.py）

刻意不使用的特徵：
- scheme（http／https）：政府資料 56 筆缺 scheme、台灣正常網域只有網域，補上的 scheme 是清理時加的，
  不是網址本身的性質，模型會學到資料來源而非詐騙特徵
- 是否為品牌官方網域：官方網域在白名單階段就處理，不會進到模型
- 是否為 .tw：台灣正常網域 97% 是 .tw、政府詐騙只有 1%，模型會學成「.tw＝正常」，
  漏掉政府資料中 20 筆 .tw 詐騙（多為精品仿冒）。2026-11-01 本人決定移除（版本 2026.11.01-2）
- 連網才能取得的資訊（網頁內容、網域年齡、DNS、排名）

修改特徵時必須調整 FEATURE_VERSION，模型版本會記錄它。
"""
import math
import re
from collections import Counter
from functools import lru_cache

import pandas as pd

from app.config_loader import load_rules
from app.services import brand_match
from app.services.normalizer import InvalidURL, NormalizedURL, is_platform, normalize

FEATURE_VERSION = "2026.11.01-3"  # -3：品牌近似加入官方網域名稱與 5 字整詞比對

_VOWELS = set("aeiou")
_TLD_WORDS = {"com", "net", "org", "gov", "edu"}
_SCRIPT_EXT = re.compile(r"\.(php|asp|aspx|jsp|cgi)$", re.IGNORECASE)
_HTML_EXT = re.compile(r"\.(html?|shtml)$", re.IGNORECASE)
_TLD_IN_PATH = re.compile(r"(\.(com|net|org|tw)\b)|(\bwww\.)", re.IGNORECASE)
_URL_CHARS = {".": "dot", "-": "hyphen", "@": "at", "?": "qm", "&": "and", "=": "eq",
              "_": "underscore", "~": "tilde", "%": "percent", "/": "slash"}

HOST_FEATURES = [
    "host_length", "sld_length", "subdomain_count", "host_dot_count", "host_hyphen_count",
    "host_digit_ratio", "sld_entropy", "sld_vowel_ratio", "sld_has_digit",
    "is_ip", "is_punycode", "has_port", "has_userinfo",
    "tld_suspicious", "is_platform", "is_shortener",
    "host_has_tw_token", "tld_word_in_host", "host_keyword_count",
]
PATH_FEATURES = [
    "url_length", "path_length", "path_depth", "query_length", "query_param_count",
    "has_fragment", "fragment_route",
    *[f"url_{name}_count" for name in _URL_CHARS.values()],
    "url_digit_ratio", "path_keyword_count", "tld_in_path", "http_in_path",
    "path_ext_script", "path_ext_html", "longest_word_length", "avg_word_length",
]
BRAND_FEATURES = ["brand_contains", "brand_similar", "brand_distance", "brand_with_digits"]
FEATURE_NAMES = HOST_FEATURES + PATH_FEATURES + BRAND_FEATURES


@lru_cache(maxsize=1)
def _rule_sets() -> dict:
    rules = load_rules()
    return {
        "tlds": frozenset(rules["suspicious_tlds"]),
        "shorteners": frozenset(rules["shortener_domains"]),
        "keywords": tuple(rules["suspicious_keywords"]),
    }


def entropy(text: str) -> float:
    """Shannon 熵（位元／字元）。亂數網域（emord、qsoern）偏高。"""
    if not text:
        return 0.0
    counts = Counter(text)
    return -sum(c / len(text) * math.log2(c / len(text)) for c in counts.values())


def _ratio(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def _host_words(n: NormalizedURL) -> list[str]:
    """子網域與 SLD 拆成英數詞，數字與英文分開（tw06 → tw、06）。"""
    text = f"{n.subdomain}.{n.sld}" if not is_platform(n.registered_domain) else n.subdomain
    return re.findall(r"[a-z]+|\d+", text)


def _host_features(n: NormalizedURL) -> dict:
    rules = _rule_sets()
    sld = n.sld
    letters = [c for c in sld if c.isalpha()]
    words = _host_words(n)
    host_text = f"{n.subdomain}.{sld}"
    return {
        "host_length": len(n.host),
        "sld_length": len(sld),
        "subdomain_count": len([p for p in n.subdomain.split(".") if p]),
        "host_dot_count": n.host.count("."),
        "host_hyphen_count": n.host.count("-"),
        "host_digit_ratio": _ratio(sum(c.isdigit() for c in n.host), len(n.host)),
        "sld_entropy": entropy(sld),
        "sld_vowel_ratio": _ratio(sum(c in _VOWELS for c in letters), len(letters)),
        "sld_has_digit": int(any(c.isdigit() for c in sld)),
        "is_ip": int(n.is_ip),
        "is_punycode": int("xn--" in n.host),
        "has_port": int(n.port is not None),
        "has_userinfo": int(n.userinfo is not None),
        "tld_suspicious": int(n.suffix.split(".")[-1] in rules["tlds"]),
        "is_platform": int(is_platform(n.registered_domain)),
        "is_shortener": int(n.registered_domain in rules["shorteners"] or n.host in rules["shorteners"]),
        "host_has_tw_token": int("tw" in words),
        "tld_word_in_host": int(any(w in _TLD_WORDS for w in words)),
        "host_keyword_count": sum(kw in host_text for kw in rules["keywords"]),
    }


def _path_features(n: NormalizedURL) -> dict:
    # 長度與符號數不含「scheme://」：http 與 https 差一個字，會讓 scheme 從網址長度漏進模型
    url = n.url.split("://", 1)[1]
    rest = n.path + ("?" + n.query if n.query else "") + ("#" + n.fragment if n.fragment else "")
    rest_lower = rest.lower()
    words = re.findall(r"[a-z0-9]+", url.lower())
    feats = {
        "url_length": len(url),
        "path_length": len(n.path),
        "path_depth": len([s for s in n.path.split("/") if s]),
        "query_length": len(n.query),
        "query_param_count": len([p for p in n.query.split("&") if p]),
        "has_fragment": int(bool(n.fragment)),
        "fragment_route": int(n.fragment.startswith("/")),  # 前端路由（#/login），政府資料常見
    }
    feats.update({f"url_{name}_count": url.count(ch) for ch, name in _URL_CHARS.items()})
    feats.update({
        "url_digit_ratio": _ratio(sum(c.isdigit() for c in url), len(url)),
        "path_keyword_count": sum(kw in rest_lower for kw in _rule_sets()["keywords"]),
        "tld_in_path": int(bool(_TLD_IN_PATH.search(rest))),
        "http_in_path": int("http" in rest_lower),
        "path_ext_script": int(bool(_SCRIPT_EXT.search(n.path))),
        "path_ext_html": int(bool(_HTML_EXT.search(n.path))),
        "longest_word_length": max((len(w) for w in words), default=0),
        "avg_word_length": _ratio(sum(len(w) for w in words), len(words)),
    })
    return feats


def _brand_features(n: NormalizedURL) -> dict:
    b = brand_match.match(n)
    return {
        "brand_contains": int(b.kind == "contains"),
        "brand_similar": int(b.kind == "similar"),
        "brand_distance": b.distance,
        "brand_with_digits": int(b.with_digits),
    }


def extract(url: str | NormalizedURL) -> dict[str, float]:
    """單一網址的特徵，鍵的順序固定為 FEATURE_NAMES。無效網址拋出 InvalidURL。"""
    n = url if isinstance(url, NormalizedURL) else normalize(url)
    feats = {**_host_features(n), **_path_features(n), **_brand_features(n)}
    return {name: feats[name] for name in FEATURE_NAMES}


def extract_frame(urls) -> pd.DataFrame:
    """批次計算（訓練用）。無效網址的列全部為 NaN，並在 invalid_reason 欄註明原因。"""
    rows, reasons = [], []
    for u in urls:
        try:
            rows.append(extract(u))
            reasons.append("")
        except InvalidURL as e:
            rows.append(dict.fromkeys(FEATURE_NAMES, float("nan")))
            reasons.append(str(e))
    df = pd.DataFrame(rows, columns=FEATURE_NAMES)
    df["invalid_reason"] = reasons
    return df
