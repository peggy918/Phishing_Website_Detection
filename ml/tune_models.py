"""三個模型的參數搜尋與穩定度檢查：只用 train 訓練、只看 val，不讀任何測試集。

流程：
1. 每個模型依 GRIDS 搜尋（種子固定 SEARCH_SEED），以驗證 PR-AUC 選最佳參數
2. 目前參數與最佳參數各換 STABILITY_SEEDS 重新訓練，看種子造成的變動
   （這些種子沒有參與搜尋，避免只挑到運氣好的組合）
3. 依網域分組 bootstrap 驗證集，看模型間的差距在抽樣變動下是否穩定

本腳本不更新 models_store 與 stage2-evaluation.md；是否換參數由本人決定。
輸出：docs/results/model-tuning.md
用法：python -m ml.tune_models
"""
import time
from datetime import datetime
from itertools import combinations, product
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.services.features import FEATURE_NAMES
from ml.train import DATASET, SEED as SEARCH_SEED

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "docs" / "results" / "model-tuning.md"
STABILITY_SEEDS = [1, 7, 123, 2024, 31415]
BOOTSTRAP_ROUNDS = 2000

GRIDS = {
    "logistic_regression": {"C": [0.01, 0.1, 1.0, 10.0, 100.0]},
    "random_forest": {"min_samples_leaf": [1, 2, 5], "max_features": ["sqrt", 0.3], "max_depth": [None, 20]},
    "lightgbm": {"learning_rate": [0.03, 0.05, 0.1], "n_estimators": [200, 400, 800],
                 "num_leaves": [15, 31, 63], "min_child_samples": [20, 50]},
}
# 目前上線設定（ml/train.py 的 make_models）中，搜尋範圍內的參數值
CURRENT = {
    "logistic_regression": {"C": 1.0},
    "random_forest": {"min_samples_leaf": 2, "max_features": "sqrt", "max_depth": None},
    "lightgbm": {"learning_rate": 0.05, "n_estimators": 400, "num_leaves": 31, "min_child_samples": 20},
}


def build(algo: str, params: dict, seed: int):
    if algo == "logistic_regression":
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, random_state=seed, **params))
    if algo == "random_forest":
        return RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=seed, **params)
    return LGBMClassifier(subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                          random_state=seed, verbose=-1, **params)


def expand(grid: dict) -> list[dict]:
    return [dict(zip(grid, values)) for values in product(*grid.values())]


def group_bootstrap_diff(y, p_a, p_b, groups, rounds: int = BOOTSTRAP_ROUNDS, seed: int = 0) -> dict:
    """PR-AUC(a) − PR-AUC(b) 的分組 bootstrap：同一網域一起抽，避免同網域的網址被當成獨立樣本。"""
    codes, uniques = pd.factorize(np.asarray(groups))
    rng = np.random.default_rng(seed)
    diffs = np.empty(rounds)
    for i in range(rounds):
        counts = np.bincount(rng.integers(0, len(uniques), len(uniques)), minlength=len(uniques))
        w = counts[codes]
        diffs[i] = average_precision_score(y, p_a, sample_weight=w) - average_precision_score(y, p_b, sample_weight=w)
    return {"mean": float(diffs.mean()), "low": float(np.quantile(diffs, 0.025)),
            "high": float(np.quantile(diffs, 0.975)), "a_wins": float((diffs > 0).mean())}


def main() -> None:
    df = pd.read_csv(DATASET, keep_default_na=False)
    train, val = df[df["split"] == "train"], df[df["split"] == "val"]
    X, y = train[FEATURE_NAMES], train["label"]
    X_val, y_val = val[FEATURE_NAMES], val["label"].to_numpy()

    def fit_score(algo, params, seed):
        p = build(algo, params, seed).fit(X, y).predict_proba(X_val)[:, 1]
        return average_precision_score(y_val, p), p

    search, best, stability, preds = {}, {}, {}, {}
    for algo, grid in GRIDS.items():
        start = time.perf_counter()
        # 參數保留原始 dict：放進 DataFrame 時 None 與整數混欄，max_depth 的 20 會變成 20.0 而不合法
        rows = [(fit_score(algo, params, SEARCH_SEED)[0], params) for params in expand(grid)]
        search[algo] = sorted(rows, key=lambda r: -r[0])
        best[algo] = search[algo][0][1]
        print(f"{algo}: {len(rows)} 組，{time.perf_counter() - start:.0f} 秒，最佳 {best[algo]}")

        current, tuned = [], []
        for seed in STABILITY_SEEDS:
            current.append(fit_score(algo, CURRENT[algo], seed)[0])
            score, p = fit_score(algo, best[algo], seed)
            tuned.append(score)
            preds.setdefault(algo, p)   # bootstrap 用第一個穩定度種子的預測
        stability[algo] = {"current": current, "tuned": tuned}

    pairs = {(a, b): group_bootstrap_diff(y_val, preds[a], preds[b], val["group_key"])
             for a, b in combinations(GRIDS, 2)}
    write_report(search, best, stability, pairs, len(val))


def write_report(search, best, stability, pairs, n_val) -> None:
    L = ["# 三模型參數搜尋與穩定度", "",
         f"> 由 `python -m ml.tune_models` 產生（{datetime.now().isoformat(timespec='seconds')}）。"
         f"只用訓練集訓練、驗證集（{n_val} 筆）評分，未讀任何測試集，也未更新上線模型。", "",
         "## 1. 種子穩定度（驗證 PR-AUC，這些種子未參與搜尋）", "",
         "| 模型 | 搜尋組數 | 目前參數 平均±標準差 | 最佳參數 平均±標準差 | 最佳參數 |", "|---|---|---|---|---|"]
    for algo in GRIDS:
        s = stability[algo]
        L.append(f"| {algo} | {len(search[algo])} | {np.mean(s['current']):.4f} ± {np.std(s['current']):.4f} | "
                 f"{np.mean(s['tuned']):.4f} ± {np.std(s['tuned']):.4f} | `{best[algo]}` |")
    L += ["", "## 2. 模型間差距（最佳參數，依網域分組 bootstrap 驗證集）", "",
          "| 比較 | PR-AUC 差距平均 | 95% 區間 | 前者勝出比例 |", "|---|---|---|---|"]
    for (a, b), r in pairs.items():
        L.append(f"| {a} − {b} | {r['mean']:+.4f} | {r['low']:+.4f} ～ {r['high']:+.4f} | {r['a_wins']:.1%} |")
    L += ["", "## 3. 各模型搜尋結果前 5 名（種子 42）", ""]
    for algo, rows in search.items():
        cols = list(GRIDS[algo])
        L += [f"### {algo}", "", "| " + " | ".join(cols) + " | pr_auc |", "|" + "---|" * (len(cols) + 1)]
        L += ["| " + " | ".join(str(params[c]) for c in cols) + f" | {score:.4f} |" for score, params in rows[:5]]
        L.append("")
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print(f"→ {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
