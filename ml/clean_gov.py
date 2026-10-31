"""清理數位產業署「通報 TWNIC 詐騙網址彙整表」XML。

輸出：
- data/processed/gov_records.csv：每筆原始紀錄加上解析結果與問題標記（不刪資料）
- data/processed/gov_quality_summary.json：各類問題的筆數與範例編號（報告素材）

用法：python -m ml.clean_gov [xml 路徑]
"""
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pandas as pd

from app.config_loader import load_rules, match_brand
from app.services.normalizer import ensure_scheme, is_platform, match_key, registered_domain, split_host, strip_junk

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_XML = ROOT / "data" / "raw" / "通報TWNIC詐騙網址彙整表_20261008.xml"
OUT_DIR = ROOT / "data" / "processed"

FIELDS = {
    "編號": "record_id",
    "一頁式數位經濟詐騙網站": "brand_text",
    "偽冒網址": "raw_url",
    "網域名稱": "domain_field",
    "詐騙網站創建日期": "created_at",
    "接獲通報日期": "reported_at",
    "停止解析日期": "stopped_at",
}


def parse_xml(path: Path) -> pd.DataFrame:
    root = ET.parse(path).getroot()
    rows = [{FIELDS[c.tag]: (c.text or "").strip() for c in rec} for rec in root]
    df = pd.DataFrame(rows)
    df["record_id"] = df["record_id"].astype(int)
    df["created_at"] = pd.to_datetime(df["created_at"], format="%Y-%m-%dT%H:%M:%S")
    df["reported_at"] = pd.to_datetime(df["reported_at"], format="%Y%m%d")
    df["stopped_at"] = pd.to_datetime(df["stopped_at"], format="%Y%m%d")
    return df.sort_values("record_id").reset_index(drop=True)


def _tracking_keys(url: str) -> list[str]:
    rules = load_rules()["tracking_params"]
    keys = [k.lower() for k, _ in parse_qsl(urlsplit(url).query, keep_blank_values=True)]
    return [k for k in keys if k in rules["exact"] or any(k.startswith(p) for p in rules["prefixes"])]


def annotate(df: pd.DataFrame) -> pd.DataFrame:
    review = set(load_rules()["review_domains"])
    out = []
    for r in df.itertuples(index=False):
        host, userinfo = split_host(r.raw_url)
        field_host, _ = split_host(r.domain_field)
        reg = registered_domain(host)
        level, key = match_key(host)
        out.append({
            "url_fixed": ensure_scheme(r.raw_url),
            "host": host,
            "registered_domain": reg,
            "match_level": level,
            "match_key": key,
            "brand_key": match_brand(r.brand_text),
            "leading_junk": strip_junk(r.raw_url) != r.raw_url,
            "no_scheme": ensure_scheme(r.raw_url) != strip_junk(r.raw_url),
            "has_userinfo": userinfo is not None,
            "domain_mismatch": registered_domain(field_host) != reg,
            "field_host_differs": field_host.removeprefix("www.") != host.removeprefix("www."),
            "is_platform": is_platform(reg),
            "needs_review": reg in review,
            "tracking_params": ",".join(_tracking_keys(ensure_scheme(r.raw_url))),
        })
    df = pd.concat([df, pd.DataFrame(out)], axis=1)

    # 編號不依時間排序：通報日期早於「較小編號中最晚的通報日期」
    running_max = df["reported_at"].cummax().shift(1)
    df["id_out_of_order"] = df["reported_at"] < running_max
    # 創建日期晚於通報日期（不合理）；平台型網域的創建日期是平台本身的日期
    df["created_after_reported"] = df["created_at"].dt.normalize() > df["reported_at"]
    df["created_date_unreliable"] = df["is_platform"] | df["created_after_reported"]

    # 依比對鍵去重：同一鍵保留最早通報（同日取較小編號）的一筆
    order = df.sort_values(["reported_at", "record_id"])
    first = order.groupby("match_key")["record_id"].first()
    df["dup_of"] = df["match_key"].map(first)
    df.loc[df["dup_of"] == df["record_id"], "dup_of"] = pd.NA
    df["dup_of"] = df["dup_of"].astype("Int64")
    df["is_duplicate"] = df["dup_of"].notna()

    df["use_for_training"] = ~df["is_duplicate"] & ~df["needs_review"]
    return df


def summarize(df: pd.DataFrame) -> dict:
    def flag(col):
        ids = df.loc[df[col], "record_id"].tolist()
        return {"count": len(ids), "examples": ids[:15]}

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_records": len(df),
        "report_date_range": [df["reported_at"].min().date().isoformat(), df["reported_at"].max().date().isoformat()],
        "unique_match_keys": int(df["match_key"].nunique()),
        "usable_for_training": int(df["use_for_training"].sum()),
        "issues": {c: flag(c) for c in [
            "leading_junk", "no_scheme", "has_userinfo", "domain_mismatch", "field_host_differs", "is_platform",
            "needs_review", "id_out_of_order", "created_after_reported", "is_duplicate"]},
        "with_tracking_params": int((df["tracking_params"] != "").sum()),
        "brand_unmapped": int(df["brand_key"].isna().sum()),
        "brand_counts": df["brand_key"].fillna("(未對應)").value_counts().to_dict(),
        "platform_counts": df.loc[df["is_platform"], "registered_domain"].value_counts().to_dict(),
        "top_tlds": df["registered_domain"].str.split(".").str[-1].value_counts().head(20).to_dict(),
        "reports_per_month": df["reported_at"].dt.strftime("%Y-%m").value_counts().sort_index().to_dict(),
    }


def main(xml_path: Path = DEFAULT_XML) -> None:
    df = annotate(parse_xml(xml_path))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "gov_records.csv", index=False, encoding="utf-8-sig")
    summary = summarize(df)
    summary["source_file"] = Path(xml_path).name
    with open(OUT_DIR / "gov_quality_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: summary[k] for k in ["total_records", "unique_match_keys", "usable_for_training"]}, ensure_ascii=False))
    for name, v in summary["issues"].items():
        print(f"{name:24s} {v['count']:5d}  {v['examples'][:8]}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XML)
