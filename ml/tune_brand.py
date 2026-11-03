"""調整品牌比對規則用：只看 val_d（調整用仿冒變體）與驗證集的正常網址，不看任何測試集。

輸出：
- val_d 各變形手法被品牌比對抓到（contains 或 similar）的比例
- 驗證集正常網址（Kaggle、台灣熱門網域）被誤判為冒用品牌的比例與例子
用法：python -m ml.tune_brand
"""
from collections import Counter
from pathlib import Path

import pandas as pd

from app.services.brand_match import match
from app.services.normalizer import normalize

ROOT = Path(__file__).resolve().parent.parent


def hit(url: str) -> str:
    return match(normalize(url)).kind


def main() -> None:
    v = pd.read_csv(ROOT / "data" / "processed" / "brand_variants.csv")
    v = v[v["split"] == "val_d"]
    v["kind"] = ("https://" + v["domain"] + "/").map(hit)
    v["hit"] = v["kind"].isin(["contains", "similar"])
    print("val_d 品牌比對抓到率（依手法）")
    print(v.groupby("technique")["hit"].mean().round(3).to_string())
    print(f"合計 {v['hit'].mean():.3f}（{int(v['hit'].sum())}/{len(v)}）")
    print("沒抓到的例子：", v.loc[~v["hit"], "domain"].head(15).tolist())

    d = pd.read_csv(ROOT / "data" / "processed" / "dataset.csv", usecols=["url", "label", "split", "source"])
    legit = d[(d["split"] == "val") & (d["label"] == 0)].copy()
    legit["kind"] = legit["url"].map(hit)
    for src, g in legit.groupby("source"):
        fp = g["kind"].isin(["contains", "similar"])
        print(f"驗證集正常（{src}）誤中率 {fp.mean():.3f}（{int(fp.sum())}/{len(g)}）",
              Counter(g.loc[fp, "kind"]), [normalize(u).host for u in g.loc[g["kind"] == "similar", "url"]][:12])


if __name__ == "__main__":
    main()
