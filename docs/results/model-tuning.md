# 三模型參數搜尋與穩定度

> 由 `python -m ml.tune_models` 產生（2026-11-03T22:37:17）。只用訓練集訓練、驗證集（2212 筆）評分，未讀任何測試集，也未更新上線模型。

## 1. 種子穩定度（驗證 PR-AUC，這些種子未參與搜尋）

| 模型 | 搜尋組數 | 目前參數 平均±標準差 | 最佳參數 平均±標準差 | 最佳參數 |
|---|---|---|---|---|
| logistic_regression | 5 | 0.9129 ± 0.0000 | 0.9130 ± 0.0000 | `{'C': 10.0}` |
| random_forest | 12 | 0.9454 ± 0.0006 | 0.9471 ± 0.0005 | `{'min_samples_leaf': 2, 'max_features': 'sqrt', 'max_depth': 20}` |
| lightgbm | 54 | 0.9502 ± 0.0008 | 0.9520 ± 0.0007 | `{'learning_rate': 0.1, 'n_estimators': 200, 'num_leaves': 15, 'min_child_samples': 20}` |

## 2. 模型間差距（最佳參數，依網域分組 bootstrap 驗證集）

| 比較 | PR-AUC 差距平均 | 95% 區間 | 前者勝出比例 |
|---|---|---|---|
| logistic_regression − random_forest | -0.0341 | -0.0512 ～ -0.0205 | 0.0% |
| logistic_regression − lightgbm | -0.0404 | -0.0567 ～ -0.0271 | 0.0% |
| random_forest − lightgbm | -0.0063 | -0.0127 ～ -0.0011 | 1.1% |

## 3. 各模型搜尋結果前 5 名（種子 42）

### logistic_regression

| C | pr_auc |
|---|---|
| 10.0 | 0.9130 |
| 100.0 | 0.9129 |
| 1.0 | 0.9129 |
| 0.1 | 0.9117 |
| 0.01 | 0.9071 |

### random_forest

| min_samples_leaf | max_features | max_depth | pr_auc |
|---|---|---|---|
| 2 | sqrt | 20 | 0.9476 |
| 5 | sqrt | None | 0.9471 |
| 5 | sqrt | 20 | 0.9467 |
| 2 | sqrt | None | 0.9448 |
| 5 | 0.3 | None | 0.9445 |

### lightgbm

| learning_rate | n_estimators | num_leaves | min_child_samples | pr_auc |
|---|---|---|---|---|
| 0.1 | 200 | 15 | 20 | 0.9540 |
| 0.03 | 200 | 63 | 20 | 0.9537 |
| 0.03 | 800 | 15 | 20 | 0.9534 |
| 0.03 | 400 | 15 | 20 | 0.9530 |
| 0.03 | 800 | 15 | 50 | 0.9530 |
