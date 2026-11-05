# 測試佐證摘要（初審定版）

> 實際執行結果的摘要，供報告 p.7、p.12、p.16 引用。日期 2026-11-05 至 11-06。

## 1. 自動化測試

- 363 項全部通過（`tests/unit`、`tests/integration`、`tests/e2e`）。使用暫存 SQLite 與假模型。
- 覆蓋率：全專案 69%（`app/` 主要偵測模組見下）。`ml/` 較低是因為資料清理與訓練腳本靠實際執行驗證（見重建預演），不靠單元測試。

| 模組 | 覆蓋率 | 未執行的部分 |
|---|---|---|
| scan、blacklist、risk、features、reference_data、logging | 100% | — |
| brand_match | 99% | |
| admin | 98% | 少數分支 |
| normalizer | 96% | 少數例外分支 |
| gov_import | 94% | 少數例外分支 |
| reasons | 80% | IP、punycode、亂數等部分原因文字 |
| predictor | 68% | register_model（靠實際註冊驗證） |
| db | 67% | SQL Server 連線字串（靠 check_db.py 與實測驗證） |
| cli | 61% | 管理指令（靠實際操作驗證） |

覆蓋率只代表程式有被執行，不代表判斷正確；後者看下方的刻意改錯。

## 2. 刻意改錯（手動突變測試）

在專案副本改壞 20 個重要判斷，看測試能否發現。第一輪抓到 18 個，**2 個沒抓到**；補測試後再驗證這 2 個，都抓到。

| 改動 | 第一輪 | 發現的測試 |
|---|---|---|
| 高風險門檻邊界 >= 改成 > | 抓到 | `test_threshold_boundaries[0.8-high]` |
| 品牌規則不處理「近似」 | 抓到 | `test_impersonation_raises_low_to_medium[similar]` |
| 不再去除追蹤參數 | 抓到 | `test_bare_helpers` |
| 不再統一 www | 抓到 | `test_bare_helpers` |
| 存檔網址保留查詢參數 | 抓到 | `test_storage_url_drops_query_and_fragment` |
| 黑名單主機名層級改比註冊網域 | 抓到 | `test_blacklist_platform_matches_full_hostname_only` |
| 待確認通報改比整個網域 | 抓到 | `test_fixture_import_counts_and_levels` |
| 平台網域可被白名單放行 | **沒抓到**，補測試後抓到 | `test_platform_domain_cannot_be_whitelisted` |
| 品牌近似容許差 2 字 | 抓到 | `test_not_detected[https://shopping.com/]` |
| 網址長度包含 scheme | 抓到 | `test_scheme_does_not_leak_into_features[variants0]` |
| 使用者內容網域進白名單 | 抓到 | `test_user_content_and_short_link_domains_excluded[line.me]` |
| 模型版本不符仍載入 | 抓到 | `test_feature_version_mismatch_refuses_model` |
| 管理頁不檢查 Tunnel 標頭 | 抓到 | `test_tunnel_traffic_from_loopback_gets_404[CF-Connecting-IP]` |
| 管理頁不用登入 | 抓到 | `test_requires_login[get-/admin/]` |
| 紀錄寫入完整網址 | 抓到 | `test_logs_keep_host_and_hash_only` |
| 低風險文字改成「安全」 | 抓到 | `test_low_risk_page_never_says_safe` |
| 結果頁網址不去連結 | 抓到 | `test_post_redirects_then_result_page_is_defanged` |
| XML 改用不安全的解析器 | **沒抓到**，補測試後抓到 | `test_entities_in_otherwise_valid_records_are_rejected` |
| 防重複送出失效 | 抓到 | `test_second_submit_while_waiting_is_ignored[chromium]` |
| 結果頁改成可點擊連結 | 抓到 | `test_blacklisted_url_is_high_risk_and_defanged[chromium]` |

- 沒抓到的原因：XML 攻擊字串的紀錄本身無欄位，換成不安全的解析器也會因內容無效被拒絕；白名單目前沒有平台型網域，防護從未被執行。
- 限制：這 20 處是人工挑選的重要判斷，不是全面的突變測試，不能推論其他地方改錯也都抓得到。

## 3. 效能與同時操作（本機 SQL Server 2022、真實 LightGBM）

| 情況 | 請求數 | 中位數 | 最大 | 結果 |
|---|---|---|---|---|
| 單人依序 | 20 | 42 毫秒 | 291 毫秒 | 全部成功 |
| 20 人同時（模型 10、黑名單 5、白名單 5） | 20 | 513 毫秒 | 610 毫秒 | 全部成功，結果頁各自獨立，判定無錯置 |

- 第一次同時測試的中位數是 6.4 秒，當時背景正在跑突變測試，CPU 被占用，不採用。
- 這是在程式內同時送 20 個請求，不是 20 位真人，也沒有經過網路。

## 4. 操作中斷（自動化測試）

| 情況 | 結果 |
|---|---|
| 資料庫在存檔時失敗 | 顯示錯誤頁與追蹤碼，不存任何資料；恢復後重試成功 |
| 送出時斷線 | 伺服器沒收到，不留紀錄；恢復後重新操作成功 |
| 伺服器已存檔、回應途中斷線 | 使用者看不到結果；重查會多一筆紀錄，判定不受影響 |
| 伺服器未回應時再按一次 | 只送出一次（瀏覽器端防護；關閉 JavaScript 或直接送請求時仍可重複） |

## 5. 程式複雜度（radon，循環複雜度 11 以上者）

| 函式 | 複雜度 | 說明 |
|---|---|---|
| `normalizer.normalize` | 20 | 判斷分支最多 |
| `reasons.model_reasons` | 18 | 原因種類多，但彼此獨立 |
| `brand_match.match` | 13 | 比對規則多 |
| `features._path_features` | 12 | |
| `features._host_features` | 11 | |

最難修改的是正規化：有 21 個程式與測試檔引用，訓練和線上都依賴它；改了之後特徵可能跟著變，模型要重新訓練。
