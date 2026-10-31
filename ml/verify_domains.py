"""以 Tranco 排行交叉比對 brands.yaml 與 tw_popular_domains.txt 的網域。

- 出現在 Tranco 前 100 萬名：視為「有外部資料佐證的真實熱門網域」（不代表一定是該品牌官方網域）
- 未出現：列入人工抽查清單 docs/domain-spotcheck.md
- 另檢查：與政府黑名單重疊者、Tranco .tw 網域中含品牌關鍵字但非官方網域者（可能是仿冒或子公司）

輸出：data/processed/domain_verification.csv、docs/domain-spotcheck.md
用法：python -m ml.verify_domains
"""
from pathlib import Path

import pandas as pd

from app.config_loader import load_brands
from app.services.normalizer import is_platform
from ml import domain_reviews
from ml.build_tw_legit import from_brands, from_curated, latest_tranco

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "processed" / "domain_verification.csv"
OUT_MD = ROOT / "docs" / "domain-spotcheck.md"


def lookalike_candidates(tranco: pd.DataFrame) -> pd.DataFrame:
    """Tranco 的 .tw 網域中含品牌關鍵字、但不在該品牌官方網域內者。"""
    rows = []
    tw = tranco[tranco["domain"].str.endswith(".tw")]
    for b in load_brands()["brands"]:
        for kw in b["keywords"]:
            if len(kw) < 4:  # 太短的關鍵字（cht、ltn）誤中太多
                continue
            known = b["domains"] + b.get("related_domains", [])
            hit = tw[tw["domain"].str.contains(kw, regex=False) & ~tw["domain"].isin(known)]
            if kw == "line":  # 「online」內含 line，排除
                hit = hit[hit["domain"].str.replace("online", "", regex=False).str.contains("line", regex=False)]
            rows += [{"brand_key": b["key"], "keyword": kw, "domain": d, "rank": r}
                     for d, r in zip(hit["domain"], hit["rank"])]
    return pd.DataFrame(rows, columns=["brand_key", "keyword", "domain", "rank"]).drop_duplicates("domain")


def main() -> None:
    tranco, tranco_name = latest_tranco()
    ranks = dict(zip(tranco["domain"], tranco["rank"]))
    gov = set(pd.read_csv(ROOT / "data" / "processed" / "gov_records.csv", usecols=["registered_domain"])["registered_domain"])

    df = pd.DataFrame(from_brands() + from_curated())
    df["tranco_rank"] = df["domain"].map(ranks).astype("Int64")
    df["in_tranco"] = df["tranco_rank"].notna()
    df["in_gov_blacklist"] = df["domain"].isin(gov)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    looks = lookalike_candidates(tranco)
    tranco_in_gov = tranco[tranco["domain"].isin(gov)].sort_values("rank")

    # 已記錄在 data/reference/domain_reviews.csv 的網域不再列為待抽查
    reviewed = set(domain_reviews.load()["domain"])
    missing = df[~df["in_tranco"]].sort_values(["source", "category", "domain"])
    missing = missing[~missing["domain"].isin(reviewed)]
    looks = looks[~looks["domain"].isin(reviewed)]
    lines = [
        "# 網域人工抽查清單",
        "",
        f"比對來源：Tranco `{tranco_name}`（前 100 萬名）。由 `python -m ml.verify_domains` 產生，請勿手動改上方統計。",
        "",
        f"- 待比對網域 {len(df)} 個，出現在 Tranco：{int(df['in_tranco'].sum())} 個，"
        f"未出現且尚未抽查：**{len(missing)} 個**",
        f"- 已抽查 {len(reviewed)} 個，結果見 `docs/domain-review.md`；本檔只列尚未判斷者。抽查結果請寫入 `data/reference/domain_reviews.csv`（decision 填 official／related／not_brand／removed）。",
        f"- 與政府黑名單重疊：{int(df['in_gov_blacklist'].sum())} 個",
        "",
        "> 出現在 Tranco 只代表「是真實存在的熱門網域」，不保證屬於該品牌；品牌歸屬仍以 v2fly 來源或官網為準。",
        "",
        "## 一、未出現在 Tranco 的網域（請上官網確認，結果寫入 domain_reviews.csv）",
        "",
        "| 網域 | 來源 | 分類／品牌 | 結果 |",
        "|---|---|---|---|",
        *[f"| {r.domain} | {r.source} | {r.category} | |" for r in missing.itertuples()],
        "",
        "## 二、Tranco .tw 網域中含品牌關鍵字、但不在官方網域的（判斷是否為官方、子公司或仿冒）",
        "",
        "| 網域 | Tranco 排名 | 疑似品牌 | 結果 |",
        "|---|---|---|---|",
        *[f"| {r.domain} | {r.rank} | {r.brand_key} | |" for r in looks.sort_values("rank").itertuples()],
        "",
        "## 三、Tranco（全部 TLD）同時出現在政府黑名單的註冊網域",
        "",
        "平台型網域（github.io 等）出現屬正常；其餘代表 Tranco 也收錄了詐騙網域，因此負例必須先排除黑名單。",
        "",
        "| 網域 | Tranco 排名 | 平台型 |",
        "|---|---|---|",
        *[f"| {r.domain} | {r.rank} | {'✓' if is_platform(r.domain) else ''} |" for r in tranco_in_gov.itertuples()],
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"total {len(df)}, in tranco {int(df['in_tranco'].sum())}, missing {len(missing)}, "
          f"lookalikes {len(looks)}, tranco∩gov {len(tranco_in_gov)}")


if __name__ == "__main__":
    main()
