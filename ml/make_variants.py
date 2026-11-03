"""測試集 D：由 brands.yaml 官方網域產生仿冒網域字串。

參考 dnstwist 的網域變形手法（本專案自行實作，未複製其程式碼），只產生字串，不查 DNS、不連線。
每個品牌取第一個官方網域為基準，每種手法依雜湊值固定挑最多 3 個，結果可重現。
已存在於訓練來源（政府、Kaggle、台灣正常網域、brands.yaml）的網域一律排除，避免與訓練資料重疊。

輸出：data/processed/brand_variants.csv（brand_key、base、technique、domain、split）
品牌依 brand_split 對半分成 val_d（調整用）與 test_d（正式測試）。
用法：python -m ml.make_variants
"""
import hashlib
from pathlib import Path

import pandas as pd

from app.config_loader import load_brands, load_rules
from app.services.normalizer import registered_domain

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed" / "brand_variants.csv"
PER_TECHNIQUE = 3
SWAP_TLDS = ["top", "shop", "xyz", "cyou", "vip"]   # 政府資料最常見的可疑 TLD
GLYPHS = {"o": "0", "l": "1", "i": "1", "e": "3", "a": "4", "s": "5", "m": "rn", "w": "vv", "d": "cl"}


def split_domain(domain: str) -> tuple[str, str]:
    reg = registered_domain(domain)
    sld = reg.split(".", 1)[0]
    return sld, reg[len(sld) + 1:]


def omission(s):
    return {s[:i] + s[i + 1:] for i in range(len(s))}


def repetition(s):
    return {s[:i] + s[i] + s[i:] for i in range(len(s)) if s[i].isalpha()}


def transposition(s):
    return {s[:i] + s[i + 1] + s[i] + s[i + 2:] for i in range(len(s) - 1) if s[i] != s[i + 1]}


def homoglyph(s):
    return {s[:i] + GLYPHS[c] + s[i + 1:] for i, c in enumerate(s) if c in GLYPHS}


def addition(s):
    return {f"{s}-tw", f"tw-{s}", f"{s}tw", f"{s}-login", f"{s}-service", f"{s}shop", f"{s}88", f"my{s}"}


TECHNIQUES = {
    "omission": omission,           # 少一個字：shopee → shope
    "repetition": repetition,       # 多一個字：shopee → shoppee
    "transposition": transposition,  # 相鄰互換：rakuten → rakutne
    "homoglyph": homoglyph,         # 同形字：shopee → sh0pee
    "addition": addition,           # 加字：shopee-tw、shopee88
}


def _pick(candidates: set[str], k: int) -> list[str]:
    return sorted(candidates, key=lambda d: hashlib.sha256(d.encode()).hexdigest())[:k]


def known_domains() -> set[str]:
    processed = ROOT / "data" / "processed"
    known = set()
    for b in load_brands()["brands"]:
        known |= set(b["domains"]) | set(b.get("related_domains", []))
    known |= set(pd.read_csv(processed / "gov_records.csv", usecols=["registered_domain"])["registered_domain"])
    known |= set(pd.read_csv(processed / "kaggle_urls.csv", usecols=["registered_domain"])["registered_domain"])
    known |= set(pd.read_csv(processed / "tw_legit_domains.csv", usecols=["registered_domain"])["registered_domain"])
    return known


def brand_split(brand_key: str) -> str:
    """品牌對半分：val_d 的變體用來調整品牌比對規則，test_d 的變體留作正式測試（2026-11-01）。
    看著測試集調規則會讓測試成績失真，所以調整只能看 val_d。"""
    return "val_d" if int(hashlib.sha256(brand_key.encode()).hexdigest(), 16) % 2 == 0 else "test_d"


def generate() -> pd.DataFrame:
    known = known_domains()
    rows = []
    for b in load_brands()["brands"]:
        if not b["domains"]:
            continue
        base = b["domains"][0]
        sld, suffix = split_domain(base)
        if len(sld) < 4 or not sld.isalpha():   # 太短或含數字（7-11）的品牌變形意義不大
            continue
        for name, fn in TECHNIQUES.items():
            cands = {f"{v}.{suffix}" for v in fn(sld) if v != sld and len(v) >= 3}
            cands = {d for d in cands if registered_domain(d) not in known}
            rows += [{"brand_key": b["key"], "base": base, "technique": name, "domain": d}
                     for d in _pick(cands, PER_TECHNIQUE)]
        # 換成可疑 TLD：shopee.tw → shopee.top
        swaps = {f"{sld}.{t}" for t in SWAP_TLDS} - known
        rows += [{"brand_key": b["key"], "base": base, "technique": "tld_swap", "domain": d}
                 for d in _pick(swaps, PER_TECHNIQUE)]
    df = pd.DataFrame(rows).drop_duplicates("domain").reset_index(drop=True)
    df["split"] = df["brand_key"].map(brand_split)
    return df


if __name__ == "__main__":
    df = generate()
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(pd.crosstab(df["technique"], df["split"]).to_string())
    print(df.groupby("split")["brand_key"].unique().to_dict())
    print(f"{len(df)} variants from {df['brand_key'].nunique()} brands → {OUT.relative_to(ROOT)}")
    print(df.groupby("technique").head(2).to_string())
