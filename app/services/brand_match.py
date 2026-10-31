"""品牌近似判斷：網址是否冒用 brands.yaml 中的品牌。

只看主機名（子網域＋註冊網域去掉後綴），不看路徑。比對方式依關鍵字長度決定，避免短字誤中
（Tranco 比對時發現 line 會命中 online）：
- 5 字以上或含數字：主機名任一段包含即算（books → shopingbooksmall、pc24 → onlytoppc24）
- 4 字：某段以關鍵字開頭（line → linerpc，但不含 online）
- 3 字以下：某段拆出的英文詞完全相同（kfc）
近似（未直接包含）：6 字以上的純英文關鍵字，與主機名中英文詞開頭片段的編輯距離（含相鄰字元互換）
差 1 以內；比對前先做同形字正規化（0→o、rn→m 等，rules.yaml 的 homoglyphs）。

主機名屬於該品牌官方或同集團網域時視為 official／related，不算冒用。
"""
import re
from dataclasses import dataclass
from functools import lru_cache

from app.config_loader import load_brands, load_rules
from app.services.normalizer import NormalizedURL, is_platform

NO_MATCH_DISTANCE = 5  # 沒有近似品牌時的距離值（特徵上限）


@dataclass(frozen=True)
class BrandMatch:
    brand_key: str | None
    kind: str          # official／related／contains／similar／none
    distance: int      # contains＝0；similar＝編輯距離；其餘＝NO_MATCH_DISTANCE
    keyword: str | None = None
    with_digits: bool = False  # 品牌名後接數字，例如 newebpay11、shoppe5


NONE = BrandMatch(None, "none", NO_MATCH_DISTANCE)


@lru_cache(maxsize=1)
def _brands() -> tuple[dict, ...]:
    out = []
    for b in load_brands()["brands"]:
        keywords = sorted({str(k).lower() for k in b["keywords"]}, key=len, reverse=True)
        out.append({
            "key": b["key"],
            "official": frozenset(b["domains"]),
            "related": frozenset(b.get("related_domains", [])),
            "keywords": tuple(keywords),
        })
    return tuple(out)


@lru_cache(maxsize=1)
def _homoglyph_table() -> tuple[tuple[str, str], ...]:
    # 多字元規則（rn→m）先套用，再處理單一字元
    pairs = load_rules()["homoglyphs"].items()
    return tuple(sorted(((str(k), str(v)) for k, v in pairs), key=lambda kv: -len(kv[0])))


def homoglyph_normalize(text: str) -> str:
    for src, dst in _homoglyph_table():
        text = text.replace(src, dst)
    return text


def osa_distance(a: str, b: str) -> int:
    """Optimal String Alignment 距離：插入、刪除、替換、相鄰互換各算 1。"""
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = a[i - 1] != b[j - 1]
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[-1]


def _labels(n: NormalizedURL) -> list[str]:
    """主機名中可能放品牌字的片段：子網域各段＋註冊網域去後綴。
    平台型網域（github.io、hinet.net）的註冊網域是平台本身，只看使用者自取的子網域。"""
    parts = [p for p in n.subdomain.split(".") if p]
    if not is_platform(n.registered_domain):
        parts.append(n.sld)
    return [p for p in parts if p]


def _words(label: str) -> list[str]:
    return [w for w in re.split(r"[^a-z]+", label) if w]


def _contains(label: str, kw: str) -> bool:
    if len(kw) >= 5 or re.search(r"\d", kw):  # 含數字的關鍵字（pc24）本身就有辨識度
        return kw in label
    if len(kw) == 4:
        return label.startswith(kw) or any(w.startswith(kw) for w in _words(label))
    return kw in _words(label)


MAX_SIMILAR_DISTANCE = 1


def _similar_distance(label: str, kw: str) -> int:
    """關鍵字與 label 中每個英文詞「開頭」長度相近片段的最小編輯距離。

    限制（依 Kaggle 正常網址的誤中調整）：
    - 只比 6 字以上的純英文關鍵字：5 字時 onlinetest 的 linet 會被當成 hinet；
      mobile01 去掉數字後變成常見字 mobile，會命中 movie、mozilla
    - 只從詞首比、最多差 1 字：容許差 2 字時 easycamp 會被當成 easycard
    """
    if len(kw) < 6 or not kw.isalpha():
        return NO_MATCH_DISTANCE
    best = NO_MATCH_DISTANCE
    for word in _words(homoglyph_normalize(label)):
        for size in (len(kw) - 1, len(kw), len(kw) + 1):
            if len(word) >= size:
                best = min(best, osa_distance(word[:size], kw))
    return best


def match(n: NormalizedURL) -> BrandMatch:
    if n.is_ip:
        return NONE
    for b in _brands():
        if n.registered_domain in b["official"]:
            return BrandMatch(b["key"], "official", NO_MATCH_DISTANCE)
        if n.registered_domain in b["related"]:
            return BrandMatch(b["key"], "related", NO_MATCH_DISTANCE)

    labels = _labels(n)
    best = NONE
    for b in _brands():
        for kw in b["keywords"]:
            for label in labels:
                glyph = homoglyph_normalize(label)
                if _contains(label, kw) or _contains(glyph, kw):
                    digits = bool(re.search(re.escape(kw) + r"\d", label))
                    candidate = BrandMatch(b["key"], "contains", 0, kw, digits)
                else:
                    d = _similar_distance(label, kw)
                    if d > MAX_SIMILAR_DISTANCE:
                        continue
                    candidate = BrandMatch(b["key"], "similar", d, kw, bool(re.search(r"\d", label)))
                # 距離小者優先；同距離時關鍵字長者優先
                if (candidate.distance, -len(kw)) < (best.distance, -len(best.keyword or "")):
                    best = candidate
    return best
