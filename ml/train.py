"""階段 2：訓練三個模型、在驗證集上選模型與門檻，最後用測試集 A／B／C／D 報告成績。

流程（docs/dataset-plan.md 第 7 節）：
1. Logistic Regression、Random Forest、LightGBM 只用 train 訓練
2. 在 val 上比較 PR-AUC，選一個
3. 在 val 上決定門檻：高風險＝精確率 ≥ 95% 的最低機率；中風險＝抓到率 ≥ 90% 的最高機率
4. 門檻定案後才計算測試集成績
5. 補充檢查：只用主機名特徵的模型（路徑捷徑）、排除 .tw 詐騙重新訓練（留一組驗證）、
   測試 B 對未來品牌的依賴（時間切分敏感度分析）

輸出：
- models_store/<模型版本>/model.joblib、metadata.json（ModelVersion 用）
- docs/results/stage2-evaluation.md（報告素材，由程式產生）
用法：python -m ml.train
"""
import json
import time
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.services import brand_match
from app.services.features import BRAND_FEATURES, FEATURE_NAMES, HOST_FEATURES, extract
from app.services.normalizer import normalize
from app.services.risk import IMPERSONATION_KINDS, LOW, assess

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "processed" / "dataset.csv"
MANIFEST = ROOT / "data" / "processed" / "dataset_manifest.json"
MODEL_DIR = ROOT / "models_store"
REPORT = ROOT / "docs" / "results" / "stage2-evaluation.md"
SEED = 42
HIGH_PRECISION = 0.95
MEDIUM_RECALL = 0.90


def make_models() -> dict:
    return {
        "logistic_regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, random_state=SEED)),
        "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=2, n_jobs=-1, random_state=SEED),
        "lightgbm": LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31, subsample=0.8,
                                   subsample_freq=1, colsample_bytree=0.8, random_state=SEED, verbose=-1),
    }


def choose_thresholds(y: np.ndarray, p: np.ndarray) -> dict:
    precision, recall, thr = precision_recall_curve(y, p)
    precision, recall = precision[:-1], recall[:-1]   # 與 thr 對齊
    ok_high = precision >= HIGH_PRECISION
    high = float(thr[ok_high].min()) if ok_high.any() else float(thr.max())
    ok_med = recall >= MEDIUM_RECALL
    medium = float(thr[ok_med].max()) if ok_med.any() else float(thr.min())
    return {"medium": min(medium, high), "high": high}


def rates(y: np.ndarray, p: np.ndarray, t: dict) -> dict:
    """各門檻下的抓到率（詐騙中被判到該級以上的比例）與誤判率（正常中被判到該級以上的比例）。"""
    out = {}
    for level, thr in t.items():
        pred = p >= thr
        if (y == 1).any():
            out[f"recall_{level}"] = float(pred[y == 1].mean())
        if (y == 0).any():
            out[f"fpr_{level}"] = float(pred[y == 0].mean())
        if (y == 1).any() and pred.any():
            out[f"precision_{level}"] = float(y[pred].mean())
    if len(set(y)) == 2:
        out["pr_auc"] = float(average_precision_score(y, p))
        out["roc_auc"] = float(roc_auc_score(y, p))
    out["n"] = int(len(y))
    return out


def evaluate(df: pd.DataFrame, p: np.ndarray, t: dict) -> dict:
    """各測試集與子群的成績。"""
    res = {}
    for split in ["val", "val_d", "test_a", "test_b", "test_c", "test_d"]:
        m = (df["split"] == split).to_numpy()
        res[split] = rates(df.loc[m, "label"].to_numpy(), p[m], t)
        for sub, g in df[m].groupby("subgroup"):
            if sub:
                idx = g.index.to_numpy()
                res[f"{split}:{sub}"] = rates(g["label"].to_numpy(), p[idx], t)
    return res


def rule_rates(df: pd.DataFrame, p: np.ndarray, t: dict) -> dict:
    """模型＋品牌規則（app/services/risk.py）下，判為中風險以上的比例。高風險不受規則影響。"""
    kinds = np.where(df["brand_contains"] == 1, "contains", np.where(df["brand_similar"] == 1, "similar", "none"))
    flagged = np.array([assess(float(x), k, t).level != LOW for x, k in zip(p, kinds)])
    model_flagged = p >= t["medium"]
    res = {}
    groups = [(s, df["split"] == s) for s in ["val", "val_d", "test_a", "test_b", "test_c", "test_d"]]
    groups += [(f"{s}:{sub}", (df["split"] == s) & (df["subgroup"] == sub)) for s, sub in sorted(
        set(zip(df["split"], df["subgroup"]))) if sub and s != "train"]
    for name, mask in groups:
        m = mask.to_numpy()
        y = df.loc[m, "label"].to_numpy()
        row = {"n": int(m.sum())}
        if (y == 1).any():
            row["recall_model"] = float(model_flagged[m][y == 1].mean())
            row["recall_rule"] = float(flagged[m][y == 1].mean())
        if (y == 0).any():
            row["fpr_model"] = float(model_flagged[m][y == 0].mean())
            row["fpr_rule"] = float(flagged[m][y == 0].mean())
        res[name] = row
    return res


def future_brand_check(df: pd.DataFrame, model, t: dict) -> dict:
    """時間切分的敏感度分析：brands.yaml 是看過全部政府資料後整理的，含訓練段之後才被冒用的品牌。

    比較測試 B 在三種情況的成績：原始、品牌表只留訓練段見過的品牌（模擬當時不知道未來品牌）、
    排除未來品牌的網址。模型不重新訓練；訓練段特徵本來就不含這些品牌的詐騙樣本。
    """
    gov = df[(df["source"] == "gov") & ~df["augmented"]]
    hit_brands = {u: brand_match.match(normalize(u)) for u in gov["url"]}
    brand_of = gov["url"].map(lambda u: hit_brands[u].brand_key if hit_brands[u].kind in IMPERSONATION_KINDS else None)
    seen = set(brand_of[gov["split"] == "train"].dropna())
    future = sorted(set(brand_of.dropna()) - seen)

    test = gov[gov["split"] == "test_b"]
    is_future = brand_of[test.index].isin(future).to_numpy()

    def flagged(rows: pd.DataFrame, removed: set[str]) -> tuple[np.ndarray, np.ndarray]:
        original = brand_match._brands
        filtered = tuple(b for b in original() if b["key"] not in removed)
        brand_match._brands = lambda: filtered
        try:
            x = pd.DataFrame([extract(u) for u in rows["url"]])[FEATURE_NAMES]
            kinds = [brand_match.match(normalize(u)).kind for u in rows["url"]]
        finally:
            brand_match._brands = original
        prob = model.predict_proba(x)[:, 1]
        return prob >= t["medium"], np.array([assess(float(a), k, t).level != LOW for a, k in zip(prob, kinds)])

    out = {"future_brands": future, "future_rows": int(is_future.sum())}
    for name, rows, removed in [("original", test, set()), ("known_brands_only", test, set(future)),
                                ("excluding_future_rows", test[~is_future], set())]:
        by_model, by_rule = flagged(rows, removed)
        out[name] = {"n": len(rows), "recall_model": float(by_model.mean()), "recall_rule": float(by_rule.mean())}
    return out


def importance(model, names: list[str]) -> list[tuple[str, float]]:
    est = model[-1] if hasattr(model, "steps") else model
    vals = np.abs(est.coef_[0]) if hasattr(est, "coef_") else est.feature_importances_.astype(float)
    vals = vals / vals.sum()
    return sorted(zip(names, vals.round(4).tolist()), key=lambda kv: -kv[1])[:15]


def latency_ms(model, urls: list[str], names: list[str]) -> float:
    """單筆預測耗時（含正規化與特徵計算），模擬線上一次查一個網址。"""
    start = time.perf_counter()
    for u in urls:
        x = pd.DataFrame([extract(u)])[names]
        model.predict_proba(x)
    return (time.perf_counter() - start) / len(urls) * 1000


def train_eval(df: pd.DataFrame, names: list[str], algo: str) -> tuple:
    train = df["split"] == "train"
    model = make_models()[algo].fit(df.loc[train, names], df.loc[train, "label"])
    p = model.predict_proba(df[names])[:, 1]
    val = (df["split"] == "val").to_numpy()
    t = choose_thresholds(df.loc[val, "label"].to_numpy(), p[val])
    return model, p, t


def tw_leave_out(df: pd.DataFrame, names: list[str], algo: str, t: dict) -> dict:
    """.tw 詐騙全在訓練段：排除它們（含補的純網域版本）重新訓練，再預測這 20 筆。"""
    tw = df["subgroup"] == "gov_tw"
    train = (df["split"] == "train") & ~tw
    model = make_models()[algo].fit(df.loc[train, names], df.loc[train, "label"])
    target = tw & ~df["augmented"]
    p = model.predict_proba(df.loc[target, names])[:, 1]
    r = rates(np.ones(len(p), dtype=int), p, t)
    r["urls"] = [(u, round(float(s), 3)) for u, s in zip(df.loc[target, "url"], p)]
    return r


def fmt(v) -> str:
    return f"{v * 100:.1f}%" if isinstance(v, float) and v <= 1 else str(v)


def write_report(meta: dict, results: dict, host_only: dict, tw_check: dict, rule: dict, future: dict) -> None:
    sel, t = meta["algorithm"], meta["thresholds"]
    L = [
        "# 階段 2 評估結果", "",
        f"> 由 `python -m ml.train` 產生（{meta['trained_at']}）。模型版本 `{meta['model_version']}`。",
        f"> 特徵版本 {meta['feature_version']}、規則 {meta['rules_version']}、品牌 {meta['brands_version']}、"
        f"資料集 SHA-256 `{meta['dataset_sha256'][:12]}…`、隨機種子 {SEED}。", "",
        "## 1. 三個模型在驗證集的比較（選模型用）", "",
        "| 模型 | 驗證 PR-AUC | 驗證 ROC-AUC | 訓練秒數 |", "|---|---|---|---|",
        *[f"| {a}{' ✅' if a == sel else ''} | {r['eval']['val']['pr_auc']:.4f} | {r['eval']['val']['roc_auc']:.4f} | {r['train_seconds']:.1f} |"
          for a, r in results.items()],
        "", f"選用：**{sel}**（驗證 PR-AUC 最高）。", "",
        "## 2. 門檻（在驗證集上決定）", "",
        f"- 高風險：機率 ≥ **{t['high']:.3f}**（驗證集精確率 ≥ {HIGH_PRECISION:.0%} 的最低門檻）",
        f"- 中風險：機率 ≥ **{t['medium']:.3f}**（驗證集抓到率 ≥ {MEDIUM_RECALL:.0%} 的最高門檻）", "",
        "## 3. 測試集成績（選用模型，門檻定案後才計算）", "",
        "| 測試集 | 筆數 | 抓到率（中／高） | 誤判率（中／高） | PR-AUC |", "|---|---|---|---|---|",
    ]
    ev = results[sel]["eval"]
    labels = {"test_a": "A Kaggle", "test_b": "B 政府最近半年", "test_c": "C 台灣正常", "test_d": "D 仿冒變體", "val": "（驗證集）", "val_d": "（仿冒變體調整集 val_d）"}
    for key, name in labels.items():
        r = ev[key]
        rec = f"{fmt(r['recall_medium'])}／{fmt(r['recall_high'])}" if "recall_medium" in r else "—"
        fpr = f"{fmt(r['fpr_medium'])}／{fmt(r['fpr_high'])}" if "fpr_medium" in r else "—"
        pr_auc = f"{r['pr_auc']:.4f}" if "pr_auc" in r else "—"
        L.append(f"| {name} | {r['n']} | {rec} | {fpr} | {pr_auc} |")
    L += ["", "### 子群", "", "| 子群 | 筆數 | 抓到率（中／高） | 誤判率（中／高） |", "|---|---|---|---|"]
    for key, r in ev.items():
        if ":" in key:
            rec = f"{fmt(r['recall_medium'])}／{fmt(r['recall_high'])}" if "recall_medium" in r else "—"
            fpr = f"{fmt(r['fpr_medium'])}／{fmt(r['fpr_high'])}" if "fpr_medium" in r else "—"
            L.append(f"| {key} | {r['n']} | {rec} | {fpr} |")
    L += ["", "## 3-1. 上線判定：模型＋品牌規則", "",
          "規則：主機名疑似冒用品牌（非官方、非同集團）者至少中風險（`app/services/risk.py`）。"
          "決策依據是 val_d 與驗證集；門檻未因規則重新調整，高風險不受影響。", "",
          "| 集 | 筆數 | 抓到率：只用模型→加規則 | 誤判率：只用模型→加規則 |", "|---|---|---|---|"]
    for key, r in rule.items():
        rec = f"{fmt(r['recall_model'])} → {fmt(r['recall_rule'])}" if "recall_rule" in r else "—"
        fpr = f"{fmt(r['fpr_model'])} → {fmt(r['fpr_rule'])}" if "fpr_rule" in r else "—"
        L.append(f"| {key} | {r['n']} | {rec} | {fpr} |")
    L += ["", "## 4. 三個模型的測試集成績（參考，選模型時未使用）", "",
          "| 模型 | A PR-AUC | A 誤判率（中） | B 抓到率（中） | C 誤判率（中） | D 抓到率（中） |", "|---|---|---|---|---|---|"]
    for a, r in results.items():
        e = r["eval"]
        L.append(f"| {a} | {e['test_a']['pr_auc']:.4f} | {fmt(e['test_a']['fpr_medium'])} | {fmt(e['test_b']['recall_medium'])} | "
                 f"{fmt(e['test_c']['fpr_medium'])} | {fmt(e['test_d']['recall_medium'])} |")
    L += ["", "（各模型使用自己在驗證集上決定的門檻。）", "",
          "## 5. 補充檢查一：只用主機名特徵（路徑捷徑）", "",
          f"同一演算法只用主機名 {len(HOST_FEATURES)}＋品牌 {len(BRAND_FEATURES)} 個特徵：", "",
          "| 版本 | 驗證 PR-AUC | B 抓到率（中） | C 誤判率（中） | D 抓到率（中） |", "|---|---|---|---|---|",
          f"| 全部特徵 | {ev['val']['pr_auc']:.4f} | {fmt(ev['test_b']['recall_medium'])} | {fmt(ev['test_c']['fpr_medium'])} | {fmt(ev['test_d']['recall_medium'])} |",
          f"| 只用主機名 | {host_only['val']['pr_auc']:.4f} | {fmt(host_only['test_b']['recall_medium'])} | {fmt(host_only['test_c']['fpr_medium'])} | {fmt(host_only['test_d']['recall_medium'])} |",
          "", "## 6. 補充檢查二：.tw 詐騙（排除後重新訓練再預測，非正式測試成績）", "",
          "> 注意：brands.yaml 第二版加入的國際精品品牌（diptyque、byredo 等）是從這 20 筆找出來的，"
          "因此本檢查已不是獨立檢驗，只能說明品牌特徵有發揮作用。", "",
          f"抓到率（中／高）：{fmt(tw_check['recall_medium'])}／{fmt(tw_check['recall_high'])}（{tw_check['n']} 筆）", "",
          "| 網址 | 機率 |", "|---|---|",
          *[f"| {u.replace('.', '[.]').replace('http', 'hxxp')} | {s} |" for u, s in tw_check["urls"]],
          "", "## 6-1. 補充檢查三：測試 B 對未來品牌的依賴（時間切分敏感度分析）", "",
          f"brands.yaml 是看過全部政府資料後整理的。訓練段未出現、之後才被冒用的品牌：{', '.join(future['future_brands'])}，"
          f"在測試 B 佔 {future['future_rows']}／{future['original']['n']} 筆。", "",
          "| 情況 | 筆數 | 中風險以上抓到率：只用模型 | 模型＋品牌規則 |", "|---|---|---|---|",
          *[f"| {label} | {future[k]['n']} | {fmt(future[k]['recall_model'])} | {fmt(future[k]['recall_rule'])} |"
            for k, label in [("original", "原始（第 3 節的成績）"),
                             ("known_brands_only", "品牌表只留訓練段見過的品牌"),
                             ("excluding_future_rows", "排除未來品牌的網址")]],
          "", "## 7. 特徵重要度前 15（選用模型）", "",
          "| 特徵 | 相對重要度 |", "|---|---|",
          *[f"| {n} | {v:.3f} |" for n, v in meta["top_features"]],
          "", f"## 8. 預測耗時", "", f"單筆（含正規化與特徵計算）平均 **{meta['latency_ms']:.2f} 毫秒**。", ""]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(L), encoding="utf-8")


def main() -> None:
    df = pd.read_csv(DATASET, keep_default_na=False)
    df["subgroup"] = df["subgroup"].astype(str)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    results = {}
    for algo in make_models():
        start = time.perf_counter()
        model, p, t = train_eval(df, FEATURE_NAMES, algo)
        results[algo] = {"model": model, "thresholds": t, "eval": evaluate(df, p, t),
                         "train_seconds": time.perf_counter() - start}
        print(algo, "val PR-AUC", round(results[algo]["eval"]["val"]["pr_auc"], 4), t)

    sel = max(results, key=lambda a: results[a]["eval"]["val"]["pr_auc"])
    model, t = results[sel]["model"], results[sel]["thresholds"]

    host_names = HOST_FEATURES + BRAND_FEATURES
    _, p_host, t_host = train_eval(df, host_names, sel)
    host_only = evaluate(df, p_host, t_host)
    tw_check = tw_leave_out(df, FEATURE_NAMES, sel, t)

    rule = rule_rates(df, model.predict_proba(df[FEATURE_NAMES])[:, 1], t)
    future = future_brand_check(df, model, t)

    sample = df[df["split"].isin(["test_a", "test_b", "test_c"])].sample(300, random_state=SEED)["url"].tolist()
    version = f"{sel}-{datetime.now():%Y%m%d-%H%M%S}"
    meta = {
        "model_version": version, "algorithm": sel, "trained_at": datetime.now().isoformat(timespec="seconds"),
        "feature_version": manifest["feature_version"], "rules_version": manifest["rules_version"],
        "brands_version": manifest["brands_version"], "dataset_sha256": manifest["dataset_sha256"],
        "source_sha256": manifest["source_sha256"], "seed": SEED, "feature_names": FEATURE_NAMES,
        "thresholds": t, "metrics": results[sel]["eval"], "metrics_with_brand_rule": rule, "future_brand_check": future,
        "top_features": importance(model, FEATURE_NAMES),
        "latency_ms": latency_ms(model, sample, FEATURE_NAMES),
    }
    out_dir = MODEL_DIR / version
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / "model.joblib")
    (out_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(meta, results, host_only, tw_check, rule, future)
    print(f"selected {sel}, thresholds {t} → {out_dir.relative_to(ROOT)}, report {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
