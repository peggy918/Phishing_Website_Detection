# 階段 2 評估結果

> 由 `python -m ml.train` 產生（2026-11-08T22:49:47）。模型版本 `lightgbm-20261108-224947`。
> 特徵版本 2026.11.01-3、規則 2026.10.31-3、品牌 2026.11.08-1、資料集 SHA-256 `5fddafad8ebe…`、隨機種子 42。

## 1. 三個模型在驗證集的比較（選模型用）

| 模型 | 驗證 PR-AUC | 驗證 ROC-AUC | 訓練秒數 |
|---|---|---|---|
| logistic_regression | 0.9126 | 0.9169 | 0.5 |
| random_forest | 0.9444 | 0.9484 | 1.6 |
| lightgbm ✅ | 0.9495 | 0.9519 | 1.1 |

選用：**lightgbm**（驗證 PR-AUC 最高）。

## 2. 門檻（在驗證集上決定）

- 高風險：機率 ≥ **0.786**（驗證集精確率 ≥ 95% 的最低門檻）
- 中風險：機率 ≥ **0.444**（驗證集抓到率 ≥ 90% 的最高門檻）

## 3. 測試集成績（選用模型，門檻定案後才計算）

| 測試集 | 筆數 | 抓到率（中／高） | 誤判率（中／高） | PR-AUC |
|---|---|---|---|---|
| A Kaggle | 1882 | 90.1%／70.7% | 17.6%／4.2% | 0.9301 |
| B 政府最近半年 | 271 | 94.8%／84.1% | — | — |
| C 台灣正常 | 297 | — | 1.3%／0.7% | — |
| D 仿冒變體 | 314 | 62.4%／37.9% | — | — |
| （驗證集） | 2213 | 90.0%／71.9% | 13.2%／3.3% | 0.9495 |
| （仿冒變體調整集 val_d） | 354 | 68.4%／47.2% | — | — |

### 子群

| 子群 | 筆數 | 抓到率（中／高） | 誤判率（中／高） |
|---|---|---|---|
| val:gov_brand | 36 | 94.4%／77.8% | — |
| val:gov_nobrand | 154 | 90.3%／81.2% | — |
| val:tw_popular | 300 | — | 0.0%／0.0% |
| val_d:addition | 60 | 95.0%／90.0% | — |
| val_d:homoglyph | 56 | 83.9%／39.3% | — |
| val_d:omission | 60 | 33.3%／6.7% | — |
| val_d:repetition | 60 | 63.3%／33.3% | — |
| val_d:tld_swap | 58 | 100.0%／100.0% | — |
| val_d:transposition | 60 | 36.7%／15.0% | — |
| test_b:gov_brand | 188 | 100.0%／90.4% | — |
| test_b:gov_nobrand | 83 | 83.1%／69.9% | — |
| test_c:tw_lookalike | 7 | — | 57.1%／28.6% |
| test_c:tw_popular | 290 | — | 0.0%／0.0% |
| test_d:addition | 54 | 100.0%／72.2% | — |
| test_d:homoglyph | 44 | 90.9%／15.9% | — |
| test_d:omission | 54 | 22.2%／11.1% | — |
| test_d:repetition | 54 | 50.0%／18.5% | — |
| test_d:tld_swap | 54 | 100.0%／100.0% | — |
| test_d:transposition | 54 | 16.7%／5.6% | — |

## 3-1. 上線判定：模型＋品牌規則

規則：主機名疑似冒用品牌（非官方、非同集團）者至少中風險（`app/services/risk.py`）。決策依據是 val_d 與驗證集；門檻未因規則重新調整，高風險不受影響。

| 集 | 筆數 | 抓到率：只用模型→加規則 | 誤判率：只用模型→加規則 |
|---|---|---|---|
| val | 2213 | 90.0% → 90.2% | 13.2% → 14.0% |
| val_d | 354 | 68.4% → 92.1% | — |
| test_a | 1882 | 90.1% → 90.1% | 17.6% → 18.0% |
| test_b | 271 | 94.8% → 94.8% | — |
| test_c | 297 | — | 1.3% → 2.0% |
| test_d | 314 | 62.4% → 94.6% | — |
| test_b:gov_brand | 188 | 100.0% → 100.0% | — |
| test_b:gov_nobrand | 83 | 83.1% → 83.1% | — |
| test_c:tw_lookalike | 7 | — | 57.1% → 71.4% |
| test_c:tw_popular | 290 | — | 0.0% → 0.3% |
| test_d:addition | 54 | 100.0% → 100.0% | — |
| test_d:homoglyph | 44 | 90.9% → 100.0% | — |
| test_d:omission | 54 | 22.2% → 88.9% | — |
| test_d:repetition | 54 | 50.0% → 90.7% | — |
| test_d:tld_swap | 54 | 100.0% → 100.0% | — |
| test_d:transposition | 54 | 16.7% → 88.9% | — |
| val:gov_brand | 36 | 94.4% → 100.0% | — |
| val:gov_nobrand | 154 | 90.3% → 90.3% | — |
| val:tw_popular | 300 | — | 0.0% → 0.0% |
| val_d:addition | 60 | 95.0% → 96.7% | — |
| val_d:homoglyph | 56 | 83.9% → 98.2% | — |
| val_d:omission | 60 | 33.3% → 85.0% | — |
| val_d:repetition | 60 | 63.3% → 88.3% | — |
| val_d:tld_swap | 58 | 100.0% → 100.0% | — |
| val_d:transposition | 60 | 36.7% → 85.0% | — |

## 4. 三個模型的測試集成績（參考，選模型時未使用）

| 模型 | A PR-AUC | A 誤判率（中） | B 抓到率（中） | C 誤判率（中） | D 抓到率（中） |
|---|---|---|---|---|---|
| logistic_regression | 0.8661 | 33.8% | 97.4% | 3.7% | 62.4% |
| random_forest | 0.9323 | 16.5% | 95.6% | 1.7% | 61.5% |
| lightgbm | 0.9301 | 17.6% | 94.8% | 1.3% | 62.4% |

（各模型使用自己在驗證集上決定的門檻。）

## 5. 補充檢查一：只用主機名特徵（路徑捷徑）

同一演算法只用主機名 19＋品牌 4 個特徵：

| 版本 | 驗證 PR-AUC | B 抓到率（中） | C 誤判率（中） | D 抓到率（中） |
|---|---|---|---|---|
| 全部特徵 | 0.9495 | 94.8% | 1.3% | 62.4% |
| 只用主機名 | 0.7980 | 98.9% | 23.2% | 79.0% |

## 6. 補充檢查二：.tw 詐騙（排除後重新訓練再預測，非正式測試成績）

> 注意：brands.yaml 第二版加入的國際精品品牌（diptyque、byredo 等）是從這 20 筆找出來的，因此本檢查已不是獨立檢驗，只能說明品牌特徵有發揮作用。

抓到率（中／高）：45.0%／15.0%（20 筆）

| 網址 | 機率 |
|---|---|
| hxxps://maisonmargiela[.]com[.]tw | 0.87 |
| hxxps://www[.]diptyqueshop[.]com[.]tw/ | 0.823 |
| hxxps://www[.]byredo[.]com[.]tw/ | 0.224 |
| hxxps://www[.]maison-margiela[.]com[.]tw/ | 0.689 |
| hxxps://www[.]diptyque-fragrances[.]com[.]tw/ | 0.644 |
| hxxps://www[.]bicycleinn[.]tw/blog/stock-open-account-recommendation/index[.]html | 0.059 |
| hxxps://www[.]mm-replica[.]com[.]tw/ | 0.007 |
| hxxps://www[.]byredo[.]tw/ | 0.476 |
| hxxps://www[.]loewetw[.]com[.]tw/ | 0.336 |
| hxxps://www[.]byredotw[.]com[.]tw/ | 0.46 |
| hxxps://www[.]diptyque-store[.]com[.]tw/ | 0.405 |
| hxxps://www[.]101shop[.]tw/ | 0.076 |
| hxxps://www[.]rakutentcstore[.]com[.]tw | 0.748 |
| hxxps://www[.]diptyque-candle[.]com[.]tw/ | 0.295 |
| hxxps://www[.]thom-browne[.]com[.]tw/returns-and-refunds/ | 0.648 |
| hxxps://www[.]hokatw[.]com[.]tw/ | 0.224 |
| hxxps://www[.]hokashop[.]com[.]tw/ | 0.385 |
| hxxps://www[.]salomontaiwan[.]com[.]tw/ | 0.825 |
| hxxps://www[.]hoka-taiwan[.]com[.]tw/ | 0.369 |
| hxxps://line[.]org[.]tw | 0.101 |

## 6-1. 補充檢查三：測試 B 對未來品牌的依賴（時間切分敏感度分析）

brands.yaml 是看過全部政府資料後整理的。訓練段未出現、之後才被冒用的品牌：foodpanda, friday, newebpay, signal，在測試 B 佔 170／271 筆。

| 情況 | 筆數 | 中風險以上抓到率：只用模型 | 模型＋品牌規則 |
|---|---|---|---|
| 原始（第 3 節的成績） | 271 | 94.8% | 94.8% |
| 品牌表只留訓練段見過的品牌 | 271 | 56.8% | 56.8% |
| 排除未來品牌的網址 | 101 | 86.1% | 86.1% |

## 7. 特徵重要度前 15（選用模型）

| 特徵 | 相對重要度 |
|---|---|
| sld_entropy | 0.114 |
| avg_word_length | 0.105 |
| sld_vowel_ratio | 0.084 |
| url_length | 0.082 |
| path_length | 0.071 |
| host_length | 0.068 |
| url_digit_ratio | 0.065 |
| longest_word_length | 0.061 |
| sld_length | 0.058 |
| url_slash_count | 0.036 |
| url_hyphen_count | 0.028 |
| path_depth | 0.023 |
| subdomain_count | 0.020 |
| host_digit_ratio | 0.019 |
| url_dot_count | 0.018 |

## 8. 預測耗時

單筆（含正規化與特徵計算）平均 **12.35 毫秒**。
