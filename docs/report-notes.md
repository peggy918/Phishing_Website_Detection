# 報告素材紀錄

每完成一個階段在此記錄可寫進報告的素材，註明對應頁碼。
標示「AI 產生」的程式與測試需由本人核對後勾選。

---

## 階段 0（2026-10-31）環境建立與資料清理

### 環境（→ p.13 G4）
- Windows 10、Python 3.14.2、`.venv`；套件版本鎖定於 `requirements.txt`／`requirements.lock.txt`。
- 本機 SQL Server 2022（MSSQLSERVER 服務運作中）、ODBC Driver 18 已安裝。
- 原始資料不進 git，`data/raw/README.md` 記錄來源與 SHA-256，供乾淨環境重建時核對。

### 政府通報資料品質（→ p.3–5 G1、p.8–12 G3）
來源：`通報TWNIC詐騙網址彙整表_20261008.xml`，1,734 筆，通報日期 2023-06-29～2026-10。
清理腳本 `ml/clean_gov.py`，完整數字見 `data/processed/gov_quality_summary.json`。
**原則：不刪原始資料，只加標記**，訓練用 `use_for_training` 篩選。

| 問題 | 筆數 | 例 | 處理 |
|---|---|---|---|
| 同網址拆成多筆（www／子網域） | 100 筆重複 | 318/319、327/330 | 依比對鍵去重，保留最早通報者 |
| 網址欄與網域欄註冊網域不一致 | 2 | 46（laobeibi／aobeibi）、1207（jkpay-officiald.com／ezywalletc.net） | 以網址欄為準，標記 `domain_mismatch` |
| 網域欄與網址主機名不同（多為子網域） | 214 | 328、330 | 僅標記 |
| 缺少 scheme | 56 | 172、401、1136–1187（LINE／Telegram 仿冒） | 補 `http://` |
| 開頭雜字元 | 1 | 116（`;http://colaresearchclub.red/…`） | 去除開頭標點（**清理時新發現**，PLAN 未列） |
| 含 @（userinfo 偽裝） | 3 | 1280、1281、1212（`easywallet.com0165302705@vip.jkpay-officiali.com`，偽裝成悠遊付網址）| 主機名取 @ 之後（1212 為**新發現**） |
| 編號不依時間排序 | 54 | 1320–1373（通報日期回到 2025-03/04） | 時間切分依「接獲通報日期」 |
| 平台型網域 | 49 | github.io 32、carrd.co 7、其他 10 | 比對完整主機名；創建日期不可靠 |
| 疑似一般／遭入侵網站 | 7 | 882 shopex.cn、886/889/893 ecpay.com、906 amsdi.com.ph、1284 hsblood.org.cn、1320 googleinvest.com | 標記待確認，不作為訓練正例 |
| 含廣告追蹤參數 | 533 | 1373（fbclid + 10 個 utm／廣告參數） | 階段 1 正規化去除；**fbclid 捷徑素材（→ p.6–7 G2）** |

- 去重後 1,634 個比對鍵，可用於訓練 1,629 筆。
- 創建日期晚於通報日期：0 筆（日期欄位本身一致）。
- 冒用對象：可對應到 brands.yaml 的 1,305 筆；未對應 429 筆（其中 393 筆是「偽冒電商一頁式詐騙」未指明品牌）。
- 常見 TLD：.com 515、.top 288、.shop 170、.store 82、.online 66、.xyz 50。
- 「LINE 帳號詐騙」類別中有大量 Telegram 仿冒網域（telegrambcn.com、telegrm.net…）→ 冒用對象描述與網域品牌不一定相符。

### Kaggle 資料（→ p.8–12 G3）
- `dataset_phishing.csv`：11,430 筆，phishing／legitimate 各 5,715，**與資料集說明相符**。
- 只取 `url`、`status`，其餘 87 個預算特徵捨棄（其中包含 web_traffic、dns_record、google_index、page_rank 等需連網的特徵，與本系統「不連線」原則衝突）。
- 重複網址 1 筆；20 個比對鍵同時有正負例（386 列）→ 依網域分組切分時要注意。
- 與政府資料的比對鍵**沒有重疊**。
- .tw 網域只有 11 筆（正常 7、釣魚 4）→ **證實需要另外補台灣正常網域**，否則模型沒看過台灣網址。
- 另一個下載的合輯 `archive.zip` 中 dataset3.csv 與本檔 url／status 完全相同；其餘資料集目前不使用。

### 第二組 Kaggle 合輯評估（`Phishing Website Detection Datasets/`，→ p.8–12 G3 資料取捨）
| 檔案 | 有原始網址？ | 評估 |
|---|---|---|
| dataset1（11,055） | 無 | 只有預算特徵，含 SSL、網域年齡等連網特徵 → 不可用 |
| dataset2（88,647） | 無 | 只有預算特徵 → 不可用 |
| dataset3（11,430） | 有 | 與 `dataset_phishing.csv` 的 url／status 完全相同 → 重複 |
| dataset4（235,795，PhiUSIIL） | 有 | **label 1＝正常、0＝釣魚（與直覺相反）**；正常網址 100% 只有首頁、釣魚 80% → 長度／路徑捷徑嚴重 |
| dataset5（95,993） | 有（無 scheme） | label 1＝釣魚；正負例都有路徑，但網址年代較舊，第 18259 列後格式有誤 |
| dataset6（10,000） | 無 | 只有預算特徵 → 不可用 |

**決定（2026-10-31，本人）**：第二組合輯全部不使用，只用 shashwatwork 的 `dataset_phishing.csv`。

### 台灣正常網域（→ p.8–12 G3、測試集 C）
- 品牌網域補充自 GitHub [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)（MIT 授權）：momo、PChome、蝦皮、樂天、博客來、LINE，並新增露天、Dcard、PTT、巴哈姆特、Mobile01、KKBOX、聯合、自由、中華電信、TWCA。該專案沒有台灣分類清單（只有 cn、ir、ru 等），只能逐品牌取。
- **設計發現**：v2fly 的 hinet.net、pixnet.net、xuite.net 允許使用者自建子網域，若整個註冊網域列入白名單，攻擊者可用 `xxx.pixnet.net` 繞過 → 改列入 rules.yaml 平台型網域，比對完整主機名。
- `ml/build_tw_legit.py` 彙整：brands.yaml 90 個 + 人工整理 62 個 + Tranco 前 2,000 個 .tw 中的 1,915 個（扣除重複與黑名單），共 **2,067 個**。

### Tranco 交叉比對（→ p.8–12 G3 資料驗證、p.6–7 G2 測試發現）
- Tranco list `746VX`（2026-10-30，前 100 萬名，固定 ID 可重現）。`ml/verify_domains.py` 產生 `docs/domain-spotcheck.md`。
- brands.yaml＋人工清單 161 個網域中 **148 個出現在 Tranco**，只剩 13 個需人工抽查（多為 PChome、LINE、Dcard 的次要網域）。人工整理的 62 個熱門網域全部有出現在 Tranco。
- **發現 1：漏列的出租子網域平台**。政府黑名單中的 it.com（Tranco 第 990 名）、eu.cc、ooguy.com、ccaiplatform.com 都是出租或免費子網域服務，原本被當成一般網域：
  - 黑名單會整個封鎖 it.com，造成大量誤判；
  - 991 `gouwuline-tw-wenjuan.it.com` 與 994 `gouwuvoom-wenjuan.it.com` 兩個不同詐騙站被誤判成重複。
  - 修正：加入 rules.yaml 平台清單（版本 2026.10.31-3），補測試。去重後比對鍵 1,634 → 1,635，可訓練 1,629 → 1,630。
- **發現 2：Tranco 不等於安全**。linegames.org、telegram-ios.com、zifeiji.com、shopex.cn 是黑名單網域，卻也在 Tranco 前 100 萬名 → 負例建立時先排除政府黑名單。
- **發現 3：品牌關鍵字誤中**。關鍵字 `line` 會命中 `online`、`lineage`，`books` 會命中 `cavesbooks`、`govbooks` → 階段 1 品牌近似特徵不能只用子字串，需考慮詞邊界或編輯距離。
- 發現 4：v2fly 沒收的官方網域，例如 momo.com.tw、pchome.tw、shopeepay.tw、linebank.com.tw、foodpanda.tw，列入抽查清單第二節。

### 網域抽查（2026-10-31，→ p.17 P3 AI 產出核對、p.8–12 G3）
紀錄：`data/reference/domain_reviews.csv`（正式資料來源）→ `docs/domain-review.md`（由 CSV 產生）；WHOIS 原始回應：`data/reference/whois/`；摘要：`data/reference/whois_summary.csv`。
- **第一節（不在 Tranco 的 13 個）：本人上官網逐一確認**。11 個 ✓；dcard.io、linefriends.com.tw 無法連線 → 從 brands.yaml 移除。
- **第二節（31 個含品牌字的 .tw 網域）**：本人確認 7 個，其餘 24 個由 Claude 以 TWNIC WHOIS（whois.twnic.net.tw:43，`ml/whois_check.py`）查註冊者，並查 9 個已知官方網域的註冊者作為對照：
  - 官方 6 個（momo.com.tw、shopeepay.tw、cathay-cube.com.tw、postmall.com.tw、hinet.tw、hinetcdn.net.tw）→ 加入 domains
  - 同集團／合資 8 個（國泰人壽、國泰產險、國泰證券、國泰投信、玉山證券、台新基金會、LINE Bank、樂天銀行）→ 新增 `related_domains` 欄位：列入白名單，但不是官方網域
  - 無關 10 個；ctbc.edu.tw 無法驗證（.edu.tw 由教育部 TANet 管理，TWNIC 查不到）
- **最佳反例**：`chinapost.com.tw` 名稱像中華郵政，WHOIS 註冊者卻是「今日傳媒（NOWnews）」；`teams.com.tw` 是翰林，不是 Microsoft。只靠網域字面判斷品牌會誤判，這說明品牌對照表必須以註冊者佐證。
- WHOIS 遇到的問題：TWNIC 有查詢頻率限制，間隔 1.5 秒會被拒絕連線，改成 8 秒間隔並快取結果；有些紀錄的註冊者中文名稱欄位是空行，解析程式一開始漏抓，已修正。
- 原則說明：WHOIS 只在開發時用來驗證參考資料，系統執行時仍然**不對使用者輸入的網址查 WHOIS**。
- brands.yaml 版本 2026.10.31-3：47 個品牌、105 個網域（含 related）。
- **「含品牌字的正常網域」（brand_lookalike）**：抽查結果為「○ 非該品牌」的 14 個網域（teams.com.tw、chinapost.com.tw、cavesbooks.com.tw 等）不列入品牌，但保留為台灣正常網域，並另外標記 `category=brand_lookalike`，且不受 Tranco 前 2,000 名限制（fast-line.tw、moto-lines.com.tw 原本因排名較後被漏掉）。
  - 用途：測試集 C 單獨報告這組的誤判率，檢查品牌近似特徵會不會「看到品牌字就判詐騙」（→ p.8–12 G3、p.16 G7 異常輸入）。
  - **切分決定（2026-11-01，本人）**：14 個一半訓練、一半測試。同一批資料不能同時用來訓練和評估，否則誤判率會偏低。
    依（疑似品牌, 網域 SHA-256）排序後輪流分配，同品牌盡量分到兩邊，重建結果固定。
    訓練 7：4gamers、cavesbooks、cathayhotel、familyshoes、fast-line、moto-lines、teams；
    測試 7：ebookservice、govbooks、ctbc.edu.tw、familystar、yabeline、lineage182、chinapost。
  - 限制：測試只有 7 個，誤判率的統計意義有限，報告需如實說明；階段 2 可再用 dnstwist 規則產生的變體補充。
  - 抽查圖例原本把「無法連線、刪除」和「正常但非該品牌」都標 ✗，容易混淆，改成 ✗＝刪除、○＝保留為正常但非品牌。
- 台灣正常網域共 2,069 個（品牌 105＋抽查 14＋人工 62＋Tranco 1,888）。
- **設計修正：抽查紀錄從 Markdown 改成 CSV**（2026-11-01，本人提出）。
  - 原本程式直接解析人工填寫的 Markdown 表格，靠「結果欄以 ○ 開頭」判斷。表格格式一變就會**不報錯、靜默漏資料**，而且判斷、證據、確認人擠在同一格文字裡。
  - 改成 `data/reference/domain_reviews.csv`（domain、brand_key、decision、evidence、registrant、reviewer、reviewed_at…）為正式資料來源：讀取時驗證欄位值與重複，錯誤直接報錯；Markdown 改由程式產生，只給人看。
  - 新增一致性測試：official／related 必須在 brands.yaml，not_brand／removed 不可在 brands.yaml，WHOIS 紀錄必須有原始回應檔。
  - 為什麼不直接寫進資料庫：訓練資料要能在沒有 SQL Server 的環境（GitHub Actions、乾淨環境）重建，並計算資料雜湊寫入 ModelVersion。資料庫留到階段 3，由 CSV 匯入 Brand／BrandDomain／Whitelist，供系統執行時查詢（Whitelist 欄位需配合調整，屆時確認）。（→ p.8–12 G3 設計比較、p.13 G4）
- 與政府黑名單無重疊。
- **待辦**：加入 Tranco 熱門 .tw 網域；正常資料目前只有網域，沒有路徑，階段 2 需注意「網址長短」造成的捷徑。

### AI 產生內容（待本人核對）
- [ ] `config/brands.yaml`：官方網域由 AI 依常識整理，全部標記 `verified: false`，需逐一上官網確認；樂信創意、美無痕、客林國際、華麗熊的官方網域留空。
- [ ] `config/rules.yaml`：可疑 TLD 依政府資料統計整理；平台、短網址、關鍵字清單由 AI 整理。
- [ ] `data/reference/tw_popular_domains.txt`：AI 整理，需核對。
- [ ] `app/services/normalizer.py`、`app/config_loader.py`、`ml/clean_gov.py`、`ml/clean_kaggle.py`、`ml/build_tw_legit.py`
- [ ] `tests/unit/test_normalizer_stage0.py`、`tests/unit/test_clean_gov.py`（fixture `tests/fixtures/gov_sample.xml` 為原始 XML 的 15 筆真實紀錄）

### 開發中發現（→ p.6–7 G2 或 p.15 G6 素材）
- tldextract 預設不使用 PSL private 區段，`shopee-tw.github.io` 的註冊網域是 `github.io`。原本的測試預期錯誤，修正後確認改由 `rules.yaml` 的平台清單統一判斷比對層級。
