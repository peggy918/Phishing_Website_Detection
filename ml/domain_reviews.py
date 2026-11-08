"""網域抽查紀錄：data/reference/domain_reviews.csv 為正式資料來源（進 git）。

欄位
- domain       註冊網域
- brand_key    對應 brands.yaml 的品牌 key
- decision     official（列入 domains）／related（同集團，列入 related_domains）／
               not_brand（正常網站但非該品牌，保留為台灣正常網域並標 brand_lookalike）／removed（從 brands.yaml 移除）／
               unconfirmed（仍列在 brands.yaml，但查不到歸屬佐證，不進白名單）
- evidence     manual_website（本人上官網確認）／twnic_whois（TWNIC WHOIS 註冊者）／wikidata（Wikidata 官方網站 P856）／
               rdap（RDAP 註冊者組織）／gov_tw（gov.tw 只能由政府機關註冊）／unverifiable（無法驗證）
- registrant   WHOIS 註冊者（evidence＝twnic_whois 時）；個人註冊者已遮蔽，完整回應只存本機資料庫
- reviewer     user（本人）／claude
- reviewed_at  抽查日期
- trigger      列入抽查的原因：not_in_tranco／brand_keyword_in_tranco／brands_yaml_unverified（brands.yaml 原本沒有佐證的網域）
- tranco_rank  Tranco 排名（若有）
- note         補充說明

docs/domain-review.md 由本模組依 CSV 產生，請勿手動修改；要新增或更正抽查結果請改 CSV。
用法：python -m ml.domain_reviews   （驗證 CSV 並重新產生 Markdown）
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "reference" / "domain_reviews.csv"
MD_PATH = ROOT / "docs" / "domain-review.md"

DECISIONS = {"official": "✓ 官方", "related": "△ 同集團", "not_brand": "○ 非該品牌", "removed": "✗ 移除",
             "unconfirmed": "？ 查無佐證"}
EVIDENCE = {"manual_website": "本人官網確認", "twnic_whois": "TWNIC WHOIS", "wikidata": "Wikidata 官方網站",
            "rdap": "RDAP 註冊者", "gov_tw": "gov.tw 政府網域", "unverifiable": "無法驗證"}
REVIEWERS = {"user", "claude"}


def load(path: Path = CSV_PATH) -> pd.DataFrame:
    """讀取並驗證抽查紀錄；格式錯誤直接拋出例外，避免靜默漏資料。"""
    if not path.exists():
        return pd.DataFrame(columns=["domain", "brand_key", "decision", "evidence", "registrant",
                                     "reviewer", "reviewed_at", "trigger", "tranco_rank", "note"])
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    errors = []
    for col, allowed in [("decision", DECISIONS), ("evidence", EVIDENCE), ("reviewer", REVIEWERS)]:
        bad = df.loc[~df[col].isin(allowed), ["domain", col]]
        errors += [f"{r.domain}: {col}={getattr(r, col)!r} 不在 {sorted(allowed)}" for r in bad.itertuples()]
    dup = df.loc[df["domain"].duplicated(), "domain"].tolist()
    if dup:
        errors.append(f"網域重複：{dup}（同一網域只保留最新一筆結果）")
    if errors:
        raise ValueError(f"{path.name} 格式錯誤：\n" + "\n".join(errors))
    return df


def render_markdown(df: pd.DataFrame) -> str:
    counts = df["decision"].value_counts()
    lines = [
        "# 網域抽查紀錄",
        "",
        "> 由 `python -m ml.domain_reviews` 依 `data/reference/domain_reviews.csv` 產生，請勿手動修改。",
        "> WHOIS 完整回應含第三方個資，只存本機資料庫；此處只列公司名稱，個人已遮蔽。",
        "",
        "圖例：✓ 官方（列入 brands.yaml domains）　△ 同集團或合資（列入 related_domains）　"
        "○ 正常網站但非該品牌（保留為台灣正常網域，標 brand_lookalike）　✗ 移除（從 brands.yaml 移除）　"
        "？ 查無佐證（仍是官方網域清單的一部分，但不進白名單）",
        "",
        "| 判斷 | 筆數 |",
        "|---|---|",
        *[f"| {label} | {int(counts.get(k, 0))} |" for k, label in DECISIONS.items()],
        "",
    ]
    for trigger, title in [("not_in_tranco", "一、品牌網域未出現在 Tranco"),
                           ("brand_keyword_in_tranco", "二、Tranco .tw 網域含品牌關鍵字"),
                           ("brands_yaml_unverified", "三、brands.yaml 原本沒有佐證的網域（2026-11-08 由 Claude 查證）")]:
        part = df[df["trigger"] == trigger]
        if part.empty:
            continue
        lines += [
            f"## {title}",
            "",
            "| 網域 | 品牌 | 判斷 | 依據 | 註冊者 | 確認人 | 日期 | 說明 |",
            "|---|---|---|---|---|---|---|---|",
            *[f"| {r.domain} | {r.brand_key} | {DECISIONS[r.decision]} | {EVIDENCE[r.evidence]} | "
              f"{r.registrant} | {'本人' if r.reviewer == 'user' else 'Claude'} | {r.reviewed_at} | {r.note} |"
              for r in part.itertuples()],
            "",
        ]
    return "\n".join(lines)


if __name__ == "__main__":
    reviews = load()
    MD_PATH.write_text(render_markdown(reviews), encoding="utf-8")
    print(reviews["decision"].value_counts().to_string())
    print(f"→ {MD_PATH.relative_to(ROOT)}")
