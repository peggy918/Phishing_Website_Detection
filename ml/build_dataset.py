"""依 docs/dataset-plan.md 組合訓練／驗證／測試資料並計算特徵。

輸出：
- data/processed/dataset.csv：每列一個網址，含 label、split、來源、分組鍵、子群標記與全部特徵
- data/processed/dataset_manifest.json：來源檔 SHA-256、特徵與規則版本、各段筆數（寫入 ModelVersion 用）

split 值：train／val／test_a（Kaggle）／test_b（政府最近半年）／test_c（台灣正常）／
        val_d、test_d（仿冒變體，依品牌對半：val_d 調整品牌比對用，test_d 正式測試）
用法：python -m ml.build_dataset
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.config_loader import load_brands, load_rules
from app.services.features import FEATURE_NAMES, FEATURE_VERSION, extract_frame
from app.services.normalizer import normalize

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
SOURCES = {
    "gov": PROCESSED / "gov_records.csv",
    "kaggle": PROCESSED / "kaggle_urls.csv",
    "tw_legit": PROCESSED / "tw_legit_domains.csv",
    "variants": PROCESSED / "brand_variants.csv",
}
OUT = PROCESSED / "dataset.csv"
MANIFEST = PROCESSED / "dataset_manifest.json"

# 政府資料依「接獲通報日期」切分（dataset-plan.md 3.1）
GOV_VAL_START = pd.Timestamp("2025-11-01")
GOV_TEST_START = pd.Timestamp("2026-04-01")

COLUMNS = ["url", "label", "split", "source", "group_key", "record_id",
           "augmented", "subgroup"]


def group_split(key: str) -> str:
    """依分組鍵的 SHA-256 決定 70／15／15。結果固定，日後加資料不會打亂原分組。"""
    bucket = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16) % 100
    return "train" if bucket < 70 else ("val" if bucket < 85 else "test")


def is_bare(url: str) -> bool:
    n = normalize(url)
    return n.path == "/" and not n.query and not n.fragment


def bare_url(url: str) -> str:
    n = normalize(url)
    return f"https://{n.host}/"


def gov_rows(path: Path) -> pd.DataFrame:
    g = pd.read_csv(path, parse_dates=["reported_at"])
    g = g[g["use_for_training"]].copy()
    split = pd.Series("train", index=g.index)
    split[g["reported_at"] >= GOV_VAL_START] = "val"
    split[g["reported_at"] >= GOV_TEST_START] = "test_b"
    tw = g["registered_domain"].str.endswith(".tw")
    out = pd.DataFrame({
        "url": g["url_fixed"], "label": 1, "split": split, "source": "gov",
        "group_key": g["match_key"], "record_id": g["record_id"].astype(str), "augmented": False,
        # .tw 詐騙另列子群；其餘在 build() 算完特徵後，依主機名是否命中品牌分 gov_brand／gov_nobrand
        "subgroup": ["gov_tw" if t else "gov" for t in tw],
    })
    # 補純網域版本：只對政府訓練段、有路徑者（dataset-plan.md 第 4 節）
    aug = out[(out["split"] == "train") & ~out["url"].map(is_bare)].copy()
    aug["url"] = aug["url"].map(bare_url)
    aug["augmented"] = True
    return pd.concat([out, aug], ignore_index=True)


def kaggle_rows(path: Path) -> pd.DataFrame:
    k = pd.read_csv(path)
    k = k[k["use_for_training"]]
    split = k["match_key"].map(group_split).replace({"test": "test_a"})
    return pd.DataFrame({
        "url": k["url"], "label": k["label"].astype(int), "split": split, "source": "kaggle",
        "group_key": k["match_key"], "record_id": "", "augmented": False, "subgroup": "",
    })


def tw_rows(path: Path) -> pd.DataFrame:
    t = pd.read_csv(path, keep_default_na=False)
    rows = []
    for r in t.itertuples():
        if r.category.startswith(("brand:", "related:")):
            split, sub = "train", "tw_brand"          # 白名單會先放行，只放訓練集
        elif r.category == "brand_lookalike":
            split, sub = ("test_c" if r.split == "test_c" else "train"), "tw_lookalike"
        else:
            split, sub = group_split(r.registered_domain).replace("test", "test_c"), "tw_popular"
        rows.append({"url": f"https://{r.domain}/", "label": 0, "split": split, "source": "tw_legit",
                     "group_key": r.registered_domain, "record_id": "", "augmented": False, "subgroup": sub})
    return pd.DataFrame(rows, columns=COLUMNS)


def variant_rows(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    v = pd.read_csv(path)
    return pd.DataFrame({
        "url": "https://" + v["domain"] + "/", "label": 1, "split": v["split"], "source": "variant",
        "group_key": v["domain"], "record_id": "", "augmented": False, "subgroup": v["technique"],
    })


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def build() -> tuple[pd.DataFrame, dict]:
    df = pd.concat([gov_rows(SOURCES["gov"]), kaggle_rows(SOURCES["kaggle"]),
                    tw_rows(SOURCES["tw_legit"]), variant_rows(SOURCES["variants"])], ignore_index=True)
    feats = extract_frame(df["url"])
    invalid = feats["invalid_reason"] != ""
    if invalid.any():
        raise ValueError(f"{int(invalid.sum())} 筆網址無法計算特徵：{df.loc[invalid, 'url'].head().tolist()}")
    df = pd.concat([df, feats[FEATURE_NAMES]], axis=1)
    # 不可用冒用對象文字（brand_key）分：測試 B 有 269 筆有文字，但主機名真的含品牌字的只有 188 筆
    hit = (df["brand_contains"] == 1) | (df["brand_similar"] == 1)
    df.loc[(df["subgroup"] == "gov") & hit, "subgroup"] = "gov_brand"
    df.loc[df["subgroup"] == "gov", "subgroup"] = "gov_nobrand"

    counts = df.groupby(["split", "label"]).size().unstack(fill_value=0)
    manifest = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "feature_version": FEATURE_VERSION,
        "rules_version": load_rules()["version"],
        "brands_version": load_brands()["version"],
        "source_sha256": {k: sha256_file(p) for k, p in SOURCES.items()},
        "rows": len(df),
        "counts": {s: {str(lbl): int(n) for lbl, n in row.items()} for s, row in counts.iterrows()},
        "augmented_rows": int(df["augmented"].sum()),
    }
    return df, manifest


if __name__ == "__main__":
    df, manifest = build()
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    manifest["dataset_sha256"] = sha256_file(OUT)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False))
    print(f"rows {len(df)}, augmented {manifest['augmented_rows']} → {OUT.relative_to(ROOT)}")
