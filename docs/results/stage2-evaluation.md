# 階段 2 評估結果

> 由 `python -m ml.train` 產生（2026-11-03T21:56:25）。模型版本 `lightgbm-20261103-215625`。
> 特徵版本 2026.11.01-3、規則 2026.10.31-3、品牌 2026.11.01-2、資料集 SHA-256 `57f7d974c708…`、隨機種子 42。

## 1. 三個模型在驗證集的比較（選模型用）

| 模型 | 驗證 PR-AUC | 驗證 ROC-AUC | 訓練秒數 |
|---|---|---|---|
| logistic_regression | 0.9129 | 0.9175 | 0.2 |
| random_forest | 0.9448 | 0.9492 | 1.6 |
| lightgbm ✅ | 0.9500 | 0.9524 | 1.0 |

選用：**lightgbm**（驗證 PR-AUC 最高）。

## 2. 門檻（在驗證集上決定）

- 高風險：機率 ≥ **0.797**（驗證集精確率 ≥ 95% 的最低門檻）
- 中風險：機率 ≥ **0.425**（驗證集抓到率 ≥ 90% 的最高門檻）

## 3. 測試集成績（選用模型，門檻定案後才計算）

| 測試集 | 筆數 | 抓到率（中／高） | 誤判率（中／高） | PR-AUC |
|---|---|---|---|---|
| A Kaggle | 1882 | 89.7%／69.4% | 20.8%／5.4% | 0.9250 |
| B 政府最近半年 | 271 | 95.6%／81.5% | — | — |
| C 台灣正常 | 297 | — | 1.3%／0.7% | — |
| D 仿冒變體 | 314 | 61.8%／35.7% | — | — |
| （驗證集） | 2212 | 90.0%／70.1% | 14.6%／3.2% | 0.9500 |
| （仿冒變體調整集 val_d） | 354 | 69.5%／45.2% | — | — |

### 子群

| 子群 | 筆數 | 抓到率（中／高） | 誤判率（中／高） |
|---|---|---|---|
| val:gov_brand | 36 | 94.4%／80.6% | — |
| val:gov_nobrand | 153 | 90.8%／79.7% | — |
| val:tw_popular | 300 | — | 0.0%／0.0% |
| val_d:addition | 60 | 95.0%／90.0% | — |
| val_d:homoglyph | 56 | 85.7%／37.5% | — |
| val_d:omission | 60 | 33.3%／5.0% | — |
| val_d:repetition | 60 | 65.0%／25.0% | — |
| val_d:tld_swap | 58 | 100.0%／100.0% | — |
| val_d:transposition | 60 | 40.0%／15.0% | — |
| test_b:gov_brand | 188 | 100.0%／89.4% | — |
| test_b:gov_nobrand | 83 | 85.5%／63.9% | — |
| test_c:tw_lookalike | 7 | — | 57.1%／28.6% |
| test_c:tw_popular | 290 | — | 0.0%／0.0% |
| test_d:addition | 54 | 100.0%／74.1% | — |
| test_d:homoglyph | 44 | 88.6%／15.9% | — |
| test_d:omission | 54 | 20.4%／5.6% | — |
| test_d:repetition | 54 | 50.0%／11.1% | — |
| test_d:tld_swap | 54 | 100.0%／100.0% | — |
| test_d:transposition | 54 | 16.7%／3.7% | — |

## 3-1. 上線判定：模型＋品牌規則

規則：主機名疑似冒用品牌（非官方、非同集團）者至少中風險（`app/services/risk.py`）。決策依據是 val_d 與驗證集；門檻未因規則重新調整，高風險不受影響。

| 集 | 筆數 | 抓到率：只用模型→加規則 | 誤判率：只用模型→加規則 |
|---|---|---|---|
| val | 2212 | 90.0% → 90.2% | 14.6% → 15.4% |
| val_d | 354 | 69.5% → 92.1% | — |
| test_a | 1882 | 89.7% → 89.7% | 20.8% → 21.2% |
| test_b | 271 | 95.6% → 95.6% | — |
| test_c | 297 | — | 1.3% → 2.0% |
| test_d | 314 | 61.8% → 94.6% | — |
| test_b:gov_brand | 188 | 100.0% → 100.0% | — |
| test_b:gov_nobrand | 83 | 85.5% → 85.5% | — |
| test_c:tw_lookalike | 7 | — | 57.1% → 71.4% |
| test_c:tw_popular | 290 | — | 0.0% → 0.3% |
| test_d:addition | 54 | 100.0% → 100.0% | — |
| test_d:homoglyph | 44 | 88.6% → 100.0% | — |
| test_d:omission | 54 | 20.4% → 88.9% | — |
| test_d:repetition | 54 | 50.0% → 90.7% | — |
| test_d:tld_swap | 54 | 100.0% → 100.0% | — |
| test_d:transposition | 54 | 16.7% → 88.9% | — |
| val:gov_brand | 36 | 94.4% → 100.0% | — |
| val:gov_nobrand | 153 | 90.8% → 90.8% | — |
| val:tw_popular | 300 | — | 0.0% → 0.0% |
| val_d:addition | 60 | 95.0% → 96.7% | — |
| val_d:homoglyph | 56 | 85.7% → 98.2% | — |
| val_d:omission | 60 | 33.3% → 85.0% | — |
| val_d:repetition | 60 | 65.0% → 88.3% | — |
| val_d:tld_swap | 58 | 100.0% → 100.0% | — |
| val_d:transposition | 60 | 40.0% → 85.0% | — |

## 4. 三個模型的測試集成績（參考，選模型時未使用）

| 模型 | A PR-AUC | A 誤判率（中） | B 抓到率（中） | C 誤判率（中） | D 抓到率（中） |
|---|---|---|---|---|---|
| logistic_regression | 0.8661 | 34.2% | 97.4% | 3.7% | 62.4% |
| random_forest | 0.9318 | 16.7% | 95.2% | 1.7% | 60.5% |
| lightgbm | 0.9250 | 20.8% | 95.6% | 1.3% | 61.8% |

（各模型使用自己在驗證集上決定的門檻。）

## 5. 補充檢查一：只用主機名特徵（路徑捷徑）

同一演算法只用主機名 19＋品牌 4 個特徵：

| 版本 | 驗證 PR-AUC | B 抓到率（中） | C 誤判率（中） | D 抓到率（中） |
|---|---|---|---|---|
| 全部特徵 | 0.9500 | 95.6% | 1.3% | 61.8% |
| 只用主機名 | 0.7940 | 98.9% | 21.9% | 81.2% |

## 6. 補充檢查二：.tw 詐騙（排除後重新訓練再預測，非正式測試成績）

> 注意：brands.yaml 第二版加入的國際精品品牌（diptyque、byredo 等）是從這 20 筆找出來的，因此本檢查已不是獨立檢驗，只能說明品牌特徵有發揮作用。

抓到率（中／高）：50.0%／10.0%（20 筆）

| 網址 | 機率 |
|---|---|
| hxxps://maisonmargiela[.]com[.]tw | 0.867 |
| hxxps://www[.]diptyqueshop[.]com[.]tw/ | 0.788 |
| hxxps://www[.]byredo[.]com[.]tw/ | 0.251 |
| hxxps://www[.]maison-margiela[.]com[.]tw/ | 0.555 |
| hxxps://www[.]diptyque-fragrances[.]com[.]tw/ | 0.663 |
| hxxps://www[.]bicycleinn[.]tw/blog/stock-open-account-recommendation/index[.]html | 0.061 |
| hxxps://www[.]mm-replica[.]com[.]tw/ | 0.006 |
| hxxps://www[.]byredo[.]tw/ | 0.457 |
| hxxps://www[.]loewetw[.]com[.]tw/ | 0.413 |
| hxxps://www[.]byredotw[.]com[.]tw/ | 0.369 |
| hxxps://www[.]diptyque-store[.]com[.]tw/ | 0.536 |
| hxxps://www[.]101shop[.]tw/ | 0.044 |
| hxxps://www[.]rakutentcstore[.]com[.]tw | 0.756 |
| hxxps://www[.]diptyque-candle[.]com[.]tw/ | 0.248 |
| hxxps://www[.]thom-browne[.]com[.]tw/returns-and-refunds/ | 0.541 |
| hxxps://www[.]hokatw[.]com[.]tw/ | 0.251 |
| hxxps://www[.]hokashop[.]com[.]tw/ | 0.306 |
| hxxps://www[.]salomontaiwan[.]com[.]tw/ | 0.886 |
| hxxps://www[.]hoka-taiwan[.]com[.]tw/ | 0.5 |
| hxxps://line[.]org[.]tw | 0.095 |

## 6-1. 補充檢查三：測試 B 對未來品牌的依賴（時間切分敏感度分析）

brands.yaml 是看過全部政府資料後整理的。訓練段未出現、之後才被冒用的品牌：foodpanda, friday, newebpay, signal，在測試 B 佔 170／271 筆。

| 情況 | 筆數 | 中風險以上抓到率：只用模型 | 模型＋品牌規則 |
|---|---|---|---|
| 原始（第 3 節的成績） | 271 | 95.6% | 95.6% |
| 品牌表只留訓練段見過的品牌 | 271 | 60.1% | 60.1% |
| 排除未來品牌的網址 | 101 | 88.1% | 88.1% |

## 7. 特徵重要度前 15（選用模型）

| 特徵 | 相對重要度 |
|---|---|
| sld_entropy | 0.121 |
| avg_word_length | 0.103 |
| url_length | 0.083 |
| sld_vowel_ratio | 0.081 |
| path_length | 0.072 |
| host_length | 0.068 |
| url_digit_ratio | 0.063 |
| longest_word_length | 0.061 |
| sld_length | 0.057 |
| url_slash_count | 0.035 |
| url_hyphen_count | 0.027 |
| path_depth | 0.022 |
| subdomain_count | 0.021 |
| url_dot_count | 0.021 |
| host_digit_ratio | 0.020 |

## 8. 預測耗時

單筆（含正規化與特徵計算）平均 **13.95 毫秒**。
