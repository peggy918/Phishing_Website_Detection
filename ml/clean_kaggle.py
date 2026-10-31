"""清理 Kaggle「Web Page Phishing Detection Dataset」（shashwatwork）。

只取原始 url 與 status 欄位，Kaggle 預先算好的 87 個特徵一律捨棄，之後由 app/services/features.py 重新計算。

輸出：
- data/processed/kaggle_urls.csv：url、label（1＝釣魚）、主機名、註冊網域、比對鍵、問題標記
- data/processed/kaggle_quality_summary.json

用法：python -m ml.clean_kaggle [csv 路徑]
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.services.normalizer import ensure_scheme, match_key, registered_domain, split_host

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "raw" / "dataset_phishing.csv"
OUT_DIR = ROOT / "data" / "processed"
EXPECTED = {"rows": 11430, "phishing": 5715, "legitimate": 5715}


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=["url", "status"], dtype=str)
    df["label"] = df["status"].map({"phishing": 1, "legitimate": 0})
    if df["label"].isna().any():
        raise ValueError(f"未知的 status：{df.loc[df['label'].isna(), 'status'].unique()}")
    return df.drop(columns="status")


def annotate(df: pd.DataFrame) -> pd.DataFrame:
    df["url"] = df["url"].str.strip()
    hosts = df["url"].map(lambda u: split_host(u)[0])
    df["host"] = hosts
    df["registered_domain"] = hosts.map(registered_domain)
    keys = hosts.map(match_key)
    df["match_level"] = keys.str[0]
    df["match_key"] = keys.str[1]
    df["no_scheme"] = df["url"].map(ensure_scheme) != df["url"]

    df["is_duplicate_url"] = df.duplicated("url", keep="first")
    # 同一比對鍵同時出現在正負例：依網域分組切分時須注意
    labels_per_key = df.groupby("match_key")["label"].nunique()
    df["key_has_both_labels"] = df["match_key"].map(labels_per_key) > 1
    df["use_for_training"] = ~df["is_duplicate_url"]
    return df


def summarize(df: pd.DataFrame, gov_keys: set[str]) -> dict:
    counts = df["label"].value_counts().to_dict()
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "rows": len(df),
        "phishing": int(counts.get(1, 0)),
        "legitimate": int(counts.get(0, 0)),
        "matches_expected": len(df) == EXPECTED["rows"] and counts.get(1) == EXPECTED["phishing"],
        "duplicate_urls": int(df["is_duplicate_url"].sum()),
        "no_scheme": int(df["no_scheme"].sum()),
        "unique_match_keys": int(df["match_key"].nunique()),
        "keys_with_both_labels": int(df.loc[df["key_has_both_labels"], "match_key"].nunique()),
        "rows_in_keys_with_both_labels": int(df["key_has_both_labels"].sum()),
        "overlap_with_gov_keys": sorted(set(df["match_key"]) & gov_keys),
        "top_tlds_by_label": {
            str(lbl): g["registered_domain"].str.split(".").str[-1].value_counts().head(10).to_dict()
            for lbl, g in df.groupby("label")
        },
        "tw_domains_by_label": df[df["registered_domain"].str.endswith(".tw")]["label"].value_counts().to_dict(),
    }


def main(csv_path: Path = DEFAULT_CSV) -> None:
    df = annotate(load(csv_path))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "kaggle_urls.csv", index=False, encoding="utf-8-sig")

    gov_path = OUT_DIR / "gov_records.csv"
    gov_keys = set(pd.read_csv(gov_path, usecols=["match_key"])["match_key"]) if gov_path.exists() else set()
    summary = summarize(df, gov_keys)
    summary["source_file"] = Path(csv_path).name
    with open(OUT_DIR / "kaggle_quality_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV)
