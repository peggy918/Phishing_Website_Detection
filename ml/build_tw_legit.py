"""彙整台灣正常網域：brands.yaml 官方網域 + data/reference/domain_reviews.csv 中 not_brand 的網域
+ data/reference/tw_popular_domains.txt + （選用）Tranco 清單。

用途：訓練負例與測試集 C（誤判率）。避免模型學成「台灣網址＝詐騙」。
category＝brand_lookalike 者（例如 teams.com.tw、chinapost.com.tw）網址含品牌字卻是正常網站，
用來檢查品牌近似特徵是否造成誤判；一半放訓練、一半留給測試集 C（split 欄）。

Tranco：若 data/raw/ 下有 tranco*.csv（格式：rank,domain），取出 .tw 結尾的網域，前 N 名加入。

輸出：data/processed/tw_legit_domains.csv（domain、registered_domain、source、category、rank、brand_key、split）
用法：python -m ml.build_tw_legit [--tranco-top 2000]
"""
import argparse
import hashlib
from pathlib import Path

import pandas as pd

from app.config_loader import load_brands
from app.services.normalizer import registered_domain
from ml import domain_reviews

ROOT = Path(__file__).resolve().parent.parent
CURATED = ROOT / "data" / "reference" / "tw_popular_domains.txt"
OUT = ROOT / "data" / "processed" / "tw_legit_domains.csv"


def from_brands() -> list[dict]:
    rows = []
    for b in load_brands()["brands"]:
        rows += [{"domain": d, "source": "brands.yaml", "category": f"brand:{b['key']}", "rank": None}
                 for d in b["domains"]]
        rows += [{"domain": d, "source": "brands.yaml", "category": f"related:{b['key']}", "rank": None}
                 for d in b.get("related_domains", [])]
    return rows


def from_curated(path: Path = CURATED) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        domain, *rest = line.split()
        rows.append({"domain": domain.lower(), "source": "curated", "category": rest[0] if rest else "", "rank": None})
    return rows


def latest_tranco() -> tuple[pd.DataFrame, str]:
    files = sorted((ROOT / "data" / "raw").glob("tranco*.csv"))
    if not files:
        return pd.DataFrame(columns=["rank", "domain"]), ""
    df = pd.read_csv(files[-1], names=["rank", "domain"], dtype={"rank": int, "domain": str})
    return df, files[-1].name


def from_tranco(top: int) -> list[dict]:
    df, name = latest_tranco()
    tw = df[df["domain"].str.endswith(".tw")].head(top)
    return [{"domain": d, "source": name, "category": "tranco", "rank": r} for r, d in zip(tw["rank"], tw["domain"])]


def from_review() -> list[dict]:
    """抽查結果為 not_brand 者：網址含品牌字但屬正常網站，是測試品牌誤判的關鍵負例。
    不受 Tranco 前 N 名限制，一律納入。"""
    tranco = latest_tranco()[0]
    ranks = dict(zip(tranco["domain"], tranco["rank"]))
    reviews = domain_reviews.load()
    rows = reviews[reviews["decision"] == "not_brand"]
    return [{"domain": d, "source": "domain_reviews.csv", "category": "brand_lookalike", "rank": ranks.get(d),
             "brand_key": b} for d, b in zip(rows["domain"], rows["brand_key"])]


def assign_lookalike_split(df: pd.DataFrame) -> pd.Series:
    """brand_lookalike 一半訓練、一半留給測試集 C（2026-11-01 本人決定）。

    依（疑似品牌, 網域 SHA-256）排序後輪流分配，讓同一品牌的網域盡量分到兩邊，且每次重建結果相同。
    其餘網域的切分留到階段 2 依網域分組決定，此處留空。
    """
    split = pd.Series("", index=df.index)
    looks = df[df["category"] == "brand_lookalike"].copy()
    looks["_h"] = looks["domain"].map(lambda d: hashlib.sha256(d.encode()).hexdigest())
    order = looks.sort_values(["brand_key", "_h"]).index
    split[order] = ["train" if i % 2 == 0 else "test_c" for i in range(len(order))]
    return split


def build(tranco_top: int = 2000) -> pd.DataFrame:
    # 順序決定去重時保留哪個來源：品牌 > 抽查 > 人工整理 > Tranco
    df = pd.DataFrame(from_brands() + from_review() + from_curated() + from_tranco(tranco_top))
    df["registered_domain"] = df["domain"].map(registered_domain)
    # Tranco 也收錄詐騙網域（例如 linegames.org、telegram-ios.com），排除政府黑名單
    gov_path = ROOT / "data" / "processed" / "gov_records.csv"
    if gov_path.exists():
        gov = set(pd.read_csv(gov_path, usecols=["registered_domain"])["registered_domain"])
        df = df[~df["registered_domain"].isin(gov)]
    df = df.drop_duplicates("domain", keep="first").reset_index(drop=True)
    df["split"] = assign_lookalike_split(df)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tranco-top", type=int, default=2000)
    df = build(ap.parse_args().tranco_top)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(df["source"].value_counts().to_string())
    print(f"total {len(df)} → {OUT.relative_to(ROOT)}")
