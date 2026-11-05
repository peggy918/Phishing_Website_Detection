# PhishGuard：結合政府開放資料與機器學習之可疑釣魚網址特徵檢測系統

> 給 Claude Code 的專案說明。每次開始工作前先讀本檔與 `docs/PLAN.md`。
> 回覆使用者時一律使用**繁體中文**。

## 專案背景

- 資訊管理實務專題，**單人作業**（評分文件中只填組員 1 的個人頁，其餘留白）。
- 初審（期中報告）：**2026-11-11 繳交**；複審（期末報告）：學期末。
- 評分依「115 年資訊管理實務專題學生公版 v26」初審、複審文件（放在 `docs/rubric/`）。
- 系統必須包含 ML 模型。
- 開發過程要留下可寫進報告的證據：測試結果、錯誤案例、設計比較、紀錄截取等。

## 已確定的決策（變更前先與使用者討論）

| 項目 | 決定 |
|---|---|
| 框架 | Flask，MVC 分層：controllers / models / views，加 services 層 |
| 資料庫 | 使用者本機 SQL Server 2022，SQLAlchemy 2 + Alembic + pyodbc（ODBC Driver 18） |
| ML 特徵 | **只用網址字串可計算的特徵**（方案 A），不抓網頁、不查 DNS/WHOIS |
| 候選模型 | Logistic Regression、Random Forest、LightGBM，三者比較後擇一上線 |
| 初審範圍 | 網址輸入 → 正規化 → 黑名單 → 白名單／品牌 → ML → 風險與原因 → 存檔；管理者匯入政府 XML |
| 複審新增 | 截圖 OCR（Tesseract chi_tra+eng，不佳再評估 PaddleOCR）、165 話術規則、品牌交叉比對、外部使用者測試 |
| 外部連線 | 複審使用者測試時以 Cloudflare Quick Tunnel 對外 |
| 風險判定 | 模型兩個門檻（在驗證集決定）＋品牌規則：疑似冒用品牌至少中風險（`app/services/risk.py`） |

## 絕對不做

- 系統**不連線任何被檢查的網址**（不 fetch、不 DNS 查詢、不 WHOIS）。避免惡意內容與 SSRF。
- 不使用 Kaggle 預先算好的特徵欄位，只取原始 `url` 欄位，用本專案的特徵程式重新計算。
- 不使用隨機切分評估模型。依「接獲通報日期」做時間切分，並依註冊網域分組。
- 截圖與簡訊原文不存檔；網址存檔前去除查詢參數。
- 密碼、連線字串不進 repo，使用 `.env`（只提交 `.env.example`）。
- 不複製 GPL 授權專案的程式碼（例如 phishing_catcher），只參考做法。
- 網址在畫面上一律以去連結格式顯示（`hxxps://example[.]top`），不可產生可點擊連結。

## 關鍵設計原則

1. **訓練與線上預測共用同一個特徵模組** `app/services/features.py`。
2. **正規化先行**：去除追蹤參數（fbclid、utm_*、gclid、ttclid、wbraid、mibextid、sfnsn 等），統一 scheme、大小寫與 www。
   不變性測試：加上追蹤參數後，特徵與預測結果不得改變。
3. **黑名單兩種比對層級**：一般網域比對註冊網域（eTLD+1）；平台型網域（github.io、carrd.co、netlify.app、weebly.com、cloudfront.net、vercel.app、pse.is 等）比對完整主機名。
4. **品牌對照表** `config/brands.yaml`：品牌名稱、別名、官方網域。品牌近似特徵、白名單與判斷原因都從這裡取。
5. **規則外部化** `config/rules.yaml`：可疑 TLD、關鍵字等，檔內附 `version`，偵測結果要記錄當時的規則版本。
6. **模型版本**：每次訓練記錄資料雜湊、特徵版本、隨機種子、指標與兩個門檻（中／高風險），寫入 `ModelVersion` 資料表。
7. 結果文字不說「安全」，改說「未發現明顯風險跡象」，並附 165 反詐騙諮詢管道。
8. tldextract 使用隨附的 Public Suffix List 快照，不在執行時下載，確保可以重建。

## 目錄結構

```
phishguard/
├─ app/
│  ├─ controllers/   # Flask Blueprint：scan、admin
│  ├─ models/        # SQLAlchemy 資料表
│  ├─ views/         # Jinja2 模板
│  ├─ services/      # normalizer、features、blacklist、brand_match、predictor
│  └─ logging/       # JSON 結構化紀錄（request_id）
├─ config/           # rules.yaml、brands.yaml
├─ ml/               # 資料清理、訓練、評估腳本（notebook 只做探索）
├─ data/             # raw / processed（大檔不進 git）
├─ migrations/       # Alembic
├─ tests/            # unit / integration / e2e
├─ docs/             # PLAN.md、rubric/、報告素材
└─ .env.example
```

## 開發慣例

- 先寫正規化與特徵的單元測試，測資優先取自政府清單的真實案例。
- 測試工具：pytest、pytest-cov；特徵模組可用 mutmut 做突變測試；整套流程用 Playwright。
- 每完成一個階段，更新下方「目前進度」，並在 `docs/report-notes.md` 記下可寫進報告的素材，註明對應頁碼。
- 遇到需要使用者決定的事（資料取捨、範圍變更），先問再做。
- 由 AI 產生的程式與測試，須在 report-notes 註明，並由使用者核對（對應 P3 的要求）。

## 目前進度

- [x] 規劃完成（2026-10-31）
- [x] 階段 0：環境建立、資料清理（政府 XML、Kaggle CSV）、台灣正常網域、brands.yaml（2026-10-31；Tranco 待補、brands.yaml 待本人核對）
- [x] 階段 1：normalizer + brand_match + features + 單元測試（2026-11-01；169 項測試）
- [x] 階段 2：三模型訓練與評估、決定門檻（2026-11-03；LightGBM，中 0.425／高 0.797；結果見 `docs/results/stage2-evaluation.md`）
- [x] 階段 3：Flask MVC + 資料庫 + 偵測頁 + 管理者匯入（2026-11-05；已在 SQL Server 驗證；網站品牌「一網打詐 NetCatch」，程式內部維持 PhishGuard）
- [x] 階段 4：紀錄、安全、E2E、重建驗證（2026-11-05；356 項測試；GitHub Actions 通過；本人決定不另做乾淨環境重建，p.13 需如實說明）
- [ ] 階段 5：初審文件撰寫（11/9–11/10；評分版本標籤 v1.0-review）

## 待解決事項

- **G1 使用者證據**：目前沒有受訪者。以 165 話術與政府通報資料作為問題依據，並盡量找 1–2 人做簡短訪談。
- **G4 重建驗證（單人）**：本人決定（2026-11-05）不另外做乾淨環境重建。報告 p.13 須如實回答「誰照文件重新安裝過」：由 AI 在同一台電腦的全新資料夾預演（資料庫用 SQLite），未由他人或在另一台電腦驗證；另以 GitHub Actions 在全新環境安裝與跑測試。
- **G7「撰寫測試以外的人核對」**：單人作業，說明由 AI 協助審查的部分與本人核對方式。
