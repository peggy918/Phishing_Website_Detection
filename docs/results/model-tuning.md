# 三模型參數搜尋與穩定度

> 由 `python -m ml.tune_models` 產生（2026-11-08T22:52:17）。只用訓練集訓練、驗證集（2213 筆）評分，未讀任何測試集，也未更新上線模型。

## 1. 種子穩定度（驗證 PR-AUC，這些種子未參與搜尋）

| 模型 | 搜尋組數 | 目前參數 平均±標準差 | 最佳參數 平均±標準差 | 最佳參數 |
|---|---|---|---|---|
| logistic_regression | 5 | 0.9126 ± 0.0000 | 0.9127 ± 0.0000 | `{'C': 10.0}` |
| random_forest | 12 | 0.9457 ± 0.0007 | 0.9467 ± 0.0007 | `{'min_samples_leaf': 5, 'max_features': 'sqrt', 'max_depth': 20}` |
| lightgbm | 54 | 0.9499 ± 0.0011 | 0.9516 ± 0.0004 | `{'learning_rate': 0.03, 'n_estimators': 800, 'num_leaves': 15, 'min_child_samples': 20}` |

## 2. 模型間差距（最佳參數，依網域分組 bootstrap 驗證集）

| 比較 | PR-AUC 差距平均 | 95% 區間 | 前者勝出比例 |
|---|---|---|---|
| logistic_regression − random_forest | -0.0347 | -0.0516 ～ -0.0200 | 0.0% |
| logistic_regression − lightgbm | -0.0391 | -0.0548 ～ -0.0257 | 0.0% |
| random_forest − lightgbm | -0.0044 | -0.0098 ～ +0.0005 | 4.0% |

## 3. 各模型搜尋結果前 5 名（種子 42）

### logistic_regression

| C | pr_auc |
|---|---|
| 10.0 | 0.9127 |
| 1.0 | 0.9126 |
| 100.0 | 0.9125 |
| 0.1 | 0.9114 |
| 0.01 | 0.9067 |

### random_forest

| min_samples_leaf | max_features | max_depth | pr_auc |
|---|---|---|---|
| 5 | sqrt | 20 | 0.9477 |
| 5 | sqrt | None | 0.9473 |
| 2 | sqrt | 20 | 0.9458 |
| 5 | 0.3 | 20 | 0.9451 |
| 5 | 0.3 | None | 0.9444 |

### lightgbm

| learning_rate | n_estimators | num_leaves | min_child_samples | pr_auc |
|---|---|---|---|---|
| 0.03 | 800 | 15 | 20 | 0.9528 |
| 0.03 | 400 | 31 | 20 | 0.9523 |
| 0.03 | 200 | 31 | 20 | 0.9521 |
| 0.05 | 400 | 15 | 20 | 0.9520 |
| 0.05 | 200 | 31 | 20 | 0.9519 |
