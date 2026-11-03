# 階段 2 評估結果（第一版，2026-11-01）

> **已被第二版取代。** 第一版的測試集 D 包含全部 31 個品牌的變體（尚未對半切分），與第二版不能直接比較；品牌比對規則與 brands.yaml 也是舊版。保留作為改善前的紀錄。

> 由 `python -m ml.train` 產生（2026-11-01T22:44:51）。模型版本 `lightgbm-20261101-224451`。
> 特徵版本 2026.11.01-2、規則 2026.10.31-3、品牌 2026.11.01-1、資料集 SHA-256 `a74d3b52cbb1…`、隨機種子 42。

## 1. 三個模型在驗證集的比較（選模型用）

| 模型 | 驗證 PR-AUC | 驗證 ROC-AUC | 訓練秒數 |
|---|---|---|---|
| logistic_regression | 0.9132 | 0.9175 | 0.4 |
| random_forest | 0.9449 | 0.9492 | 1.7 |
| lightgbm ✅ | 0.9498 | 0.9515 | 1.2 |

選用：**lightgbm**（驗證 PR-AUC 最高）。

## 2. 門檻（在驗證集上決定）

- 高風險：機率 ≥ **0.773**（驗證集精確率 ≥ 95% 的最低門檻）
- 中風險：機率 ≥ **0.441**（驗證集抓到率 ≥ 90% 的最高門檻）

## 3. 測試集成績（選用模型，門檻定案後才計算）

| 測試集 | 筆數 | 抓到率（中／高） | 誤判率（中／高） | PR-AUC |
|---|---|---|---|---|
| A Kaggle | 1882 | 89.0%／70.6% | 19.3%／4.5% | 0.9250 |
| B 政府最近半年 | 271 | 94.5%／87.1% | — | — |
| C 台灣正常 | 297 | — | 1.3%／0.7% | — |
| D 仿冒變體 | 543 | 55.6%／41.1% | — | — |
| （驗證集） | 2212 | 90.0%／72.3% | 14.4%／3.3% | 0.9498 |

### 子群

| 子群 | 筆數 | 抓到率（中／高） | 誤判率（中／高） |
|---|---|---|---|
| val:gov_brand | 181 | 91.7%／81.8% | — |
| val:gov_nobrand | 8 | 87.5%／62.5% | — |
| val:tw_popular | 300 | — | 0.0%／0.0% |
| test_b:gov_brand | 269 | 94.4%／87.0% | — |
| test_b:gov_nobrand | 2 | 100.0%／100.0% | — |
| test_c:tw_lookalike | 7 | — | 57.1%／28.6% |
| test_c:tw_popular | 290 | — | 0.0%／0.0% |
| test_d:addition | 93 | 89.2%／74.2% | — |
| test_d:homoglyph | 80 | 40.0%／18.8% | — |
| test_d:omission | 93 | 26.9%／12.9% | — |
| test_d:repetition | 93 | 49.5%／26.9% | — |
| test_d:tld_swap | 91 | 100.0%／100.0% | — |
| test_d:transposition | 93 | 26.9%／11.8% | — |

## 4. 三個模型的測試集成績（參考，選模型時未使用）

| 模型 | A PR-AUC | A 誤判率（中） | B 抓到率（中） | C 誤判率（中） | D 抓到率（中） |
|---|---|---|---|---|---|
| logistic_regression | 0.8649 | 33.7% | 97.4% | 3.7% | 79.4% |
| random_forest | 0.9343 | 17.3% | 95.6% | 1.3% | 54.5% |
| lightgbm | 0.9250 | 19.3% | 94.5% | 1.3% | 55.6% |

（各模型使用自己在驗證集上決定的門檻。）

## 5. 補充檢查一：只用主機名特徵（路徑捷徑）

同一演算法只用主機名 19＋品牌 4 個特徵：

| 版本 | 驗證 PR-AUC | B 抓到率（中） | C 誤判率（中） | D 抓到率（中） |
|---|---|---|---|---|
| 全部特徵 | 0.9498 | 94.5% | 1.3% | 55.6% |
| 只用主機名 | 0.7977 | 98.9% | 22.9% | 84.3% |

## 6. 補充檢查二：.tw 詐騙（排除後重新訓練再預測，非正式測試成績）

抓到率（中／高）：10.0%／0.0%（20 筆）

| 網址 | 機率 |
|---|---|
| hxxps://maisonmargiela[.]com[.]tw | 0.028 |
| hxxps://www[.]diptyqueshop[.]com[.]tw/ | 0.021 |
| hxxps://www[.]byredo[.]com[.]tw/ | 0.006 |
| hxxps://www[.]maison-margiela[.]com[.]tw/ | 0.041 |
| hxxps://www[.]diptyque-fragrances[.]com[.]tw/ | 0.154 |
| hxxps://www[.]bicycleinn[.]tw/blog/stock-open-account-recommendation/index[.]html | 0.061 |
| hxxps://www[.]mm-replica[.]com[.]tw/ | 0.008 |
| hxxps://www[.]byredo[.]tw/ | 0.037 |
| hxxps://www[.]loewetw[.]com[.]tw/ | 0.013 |
| hxxps://www[.]byredotw[.]com[.]tw/ | 0.01 |
| hxxps://www[.]diptyque-store[.]com[.]tw/ | 0.045 |
| hxxps://www[.]101shop[.]tw/ | 0.08 |
| hxxps://www[.]rakutentcstore[.]com[.]tw | 0.72 |
| hxxps://www[.]diptyque-candle[.]com[.]tw/ | 0.018 |
| hxxps://www[.]thom-browne[.]com[.]tw/returns-and-refunds/ | 0.562 |
| hxxps://www[.]hokatw[.]com[.]tw/ | 0.006 |
| hxxps://www[.]hokashop[.]com[.]tw/ | 0.007 |
| hxxps://www[.]salomontaiwan[.]com[.]tw/ | 0.023 |
| hxxps://www[.]hoka-taiwan[.]com[.]tw/ | 0.018 |
| hxxps://line[.]org[.]tw | 0.119 |

## 7. 特徵重要度前 15（選用模型）

| 特徵 | 相對重要度 |
|---|---|
| sld_entropy | 0.118 |
| avg_word_length | 0.108 |
| url_length | 0.084 |
| sld_vowel_ratio | 0.079 |
| path_length | 0.073 |
| host_length | 0.067 |
| url_digit_ratio | 0.062 |
| longest_word_length | 0.060 |
| sld_length | 0.057 |
| url_slash_count | 0.035 |
| url_hyphen_count | 0.027 |
| subdomain_count | 0.022 |
| host_digit_ratio | 0.021 |
| path_depth | 0.020 |
| url_dot_count | 0.020 |

## 8. 預測耗時

單筆（含正規化與特徵計算）平均 **7.14 毫秒**。
