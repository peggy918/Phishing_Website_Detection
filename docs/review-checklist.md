# AI 產生程式核對清單（對應 P3、G7）

> **怎麼用**：每一行確認後打勾，也就是把 `[ ]` 改成 `[x]`。不用讀懂每一行程式，只要確認「它做的事」和你的決定一致。
> - **「打開看」**：打開檔案，看最上面三個引號（`"""`）裡的中文說明。
> - **「在網站試」**：先啟動網站（`.venv/Scripts/flask --app wsgi run`），再用瀏覽器開 `http://127.0.0.1:5000`，在輸入框貼上網址。網址只是交給你自己的系統分析，系統**不會連到**那個網址。
> - 全部勾完後跟 Claude 說，會同步到 `report-notes.md` 的勾選框。
>
> 2026-11-08 由 Claude 整理；每一行的內容都已對照程式與測試確認存在。

## 0. 先做一次（所有測試檔都靠這一步）
- [ ] 跑全部測試：`.venv/Scripts/python -m pytest`，最後出現「389 passed」，沒有 failed。

## 1. 設定檔 `config/rules.yaml`
- [ ] `platform_domains`：裡面都是「任何人都能免費開網站」的服務（github.io、wixsite.com、blogspot.com…）。這些網域底下每個子網域屬於不同的人，所以黑名單只比完整主機名。
- [ ] `shortener_domains`：裡面都是短網址服務（bit.ly、reurl.cc、lihi.cc…）。
- [ ] `suspicious_keywords`：裡面都是詐騙網址常見的英文字（login、verify、wallet、refund…），沒有混進奇怪的字。

## 2. 資料清理（階段 0）
- [ ] `ml/clean_gov.py`：打開看。只讀政府 XML；同一個網址重複通報時只留最早的一筆；7 筆一般網站底下的子網域依完整主機名去重，並放進訓練（你 11/8 的決定）。
- [ ] `ml/clean_kaggle.py`：打開看。只取 Kaggle 的網址和標記兩欄，不使用它預先算好的 87 個特徵（CLAUDE.md「絕對不做」第 2 條）。
- [ ] `ml/build_tw_legit.py`：打開看。台灣正常網域來自品牌官方網域、抽查過的正常網站、`tw_popular_domains.txt` 和 Tranco 排行，並排除出現在政府詐騙清單的網域。
- [ ] `app/config_loader.py`：只負責讀 `config/` 底下的兩個 YAML 檔，沒有別的功能。
- [ ] `tests/unit/test_normalizer_stage0.py`、`tests/unit/test_clean_gov.py`：打開看。測試資料用的是政府清單的真實案例，例如 116 號開頭多一個「;」、1212 號用 @ 偽裝。

## 3. 正規化、品牌、特徵（階段 1）
- [ ] `app/services/normalizer.py`：在網站試兩次。
  - `https://www.Shopee.tw/?fbclid=abc` 和 `https://shopee.tw/` 的結果相同：追蹤參數、大小寫、www 都不影響判斷。
  - `hxxps://example[.]top` 能正常出結果，不出現英文錯誤訊息。
- [ ] `app/services/brand_match.py`：在網站試兩次。
  - `shopee-tw.top`：原因寫「疑似冒用：蝦皮購物」。
  - `onlinetest.tw`：不會被當成冒用 LINE。
- [ ] `app/services/features.py`：打開看「刻意不使用的特徵」。沒有用 http／https、沒有用「是否 .tw」（你 11/1 決定拿掉），也沒有任何要連網才拿得到的資訊。
- [ ] `tests/unit/test_normalizer.py`、`test_brand_match.py`、`test_features.py`：打開看註解。有測「加追蹤參數後結果不變」，也有測「line 不可命中 online」。

## 4. 資料集與訓練（階段 2）
- [ ] `ml/build_dataset.py`：打開看。政府資料依「接獲通報日期」切分，不是隨機；Kaggle 和台灣網域依網域分組切分。
- [ ] `docs/dataset-plan.md`：讀第 3 節，確認資料切分方式是你同意的。
- [ ] `ml/make_variants.py`：打開看。只產生仿冒字串（例如 momoshop.xyz），不連線、不查 DNS；參考 dnstwist 的做法，沒有複製它的程式碼。
- [ ] `ml/train.py`：對照 `docs/results/stage2-evaluation.md`。三個模型都有比較，門檻在驗證集上決定，測試集成績最後才算。
- [ ] `tests/unit/test_build_dataset.py`：打開看函式名稱。有測政府資料依日期切分的邊界，也有測「補純網域版本只加在訓練段」。
- [ ] `app/services/risk.py`：打開看。規則就是你 11/3 的決定：疑似冒用品牌至少中風險，只會提高風險、不會降低。
- [ ] `tests/unit/test_risk.py`：打開看函式名稱。有測門檻邊界值，也有測「沒有冒用品牌時規則不觸發」。
- [ ] `ml/tune_brand.py`：打開看。只用 val_d 和驗證集調整，不看測試集。

## 5. 網站（階段 3）
- [ ] `app/db.py`：資料庫密碼從 `.env` 讀取，程式裡沒有寫死密碼。
- [ ] `app/errors.py`：在網站開 `http://127.0.0.1:5000/abc`，看到中文的「找不到頁面」，沒有程式錯誤細節。
- [ ] `app/cli.py`：`create-admin` 的密碼是跳出提示後才輸入，不是打在指令後面。
- [ ] `app/models/`：對照 `docs/report/figures/erd.png`，資料表名稱和欄位一致。
- [ ] `app/__init__.py`、`app/extensions.py`：網站能正常啟動就算通過。
- [ ] `app/controllers/scan.py`、`app/views/`：在網站試任一個網址。
  - 結果頁的網址是去連結格式（`hxxps://…[.]…`），點不了。
  - 頁面上不說「安全」。
  - 頁尾有 165 反詐騙專線。
- [ ] `app/controllers/admin.py`：用管理者帳號登入，能匯入 XML、看統計、切換模型；啟用中的模型是 `lightgbm-20261108-224947`。
- [ ] `app/static/style.css`：畫面樣式看起來正常就算通過。
- [ ] `app/services/blacklist.py`：在網站試兩次。
  - `niconsortiu.ecpay.com`：高風險，原因寫政府通報。
  - `www.ecpay.com`：不會被黑名單判定。
- [ ] `app/services/gov_import.py`：在管理頁把同一個 XML 檔再匯入一次，會被拒絕。
- [ ] `app/services/predictor.py`：打開看。模型和特徵版本不一致時，拒絕載入模型。
- [ ] `app/services/reasons.py`：結果頁列出 2–3 條原因，你看得懂。
- [ ] `app/services/reference_data.py`：打開看。白名單只收有歸屬佐證的網域（你 11/3、11/6 的決定）。
- [ ] `app/services/scan.py`：打開看。流程順序是「正規化 → 黑名單 → 白名單 → 模型 → 存檔」。
- [ ] `migrations/`、`alembic.ini`、`scripts/setup_db.sql`：你當初照 README 建資料庫成功過，就算通過。
- [ ] `tests/integration/`、`tests/helpers.py`、`tests/unit/test_reference_data.py`：第 0 步通過即可。也可以打開 `test_failure_modes.py`，看到有測「操作中斷、多人同時操作」。

## 6. 紀錄、自動測試、CI（階段 4）
- [ ] `app/logging/`：打開看「隱私原則」。紀錄只記主機名和雜湊，不記完整網址。
- [ ] `wsgi.py`：打開看。網站啟動時先載入模型，第一位使用者不用久等。
- [ ] `app/static/app.js`：在網站連點「檢查」按鈕好幾下，只會送出一次。
- [ ] `tests/e2e/`：第 0 步通過。打開 `test_flows.py`，看到有測訪客檢查、重複送出、異常輸入、管理者匯入。
- [ ] `tests/integration/test_logging.py`：第 0 步通過即可。
- [ ] `README.md`：讀一遍安裝步驟，你看得懂。
- [ ] `.github/workflows/ci.yml`：GitHub 專案的 Actions 頁面最新一次是綠色勾勾。
- [ ] `.mcp.json`：只設定了 chrome-devtools 和 playwright 兩個工具，而且版本是固定的。

## 7. 11/8 重訓的改動
- [ ] `ml/clean_gov.py` 這次的改動：已在第 2 節第一行確認過就算通過。
- [ ] `tests/unit/test_clean_gov.py` 新增的兩項測試：第 0 步通過即可。

## 8. MCP 比較報告
- [ ] 讀 `docs/results/mcp-comparison.md` 第 8 節的結論與第 11 節「2026-11-08 重跑」，看得懂、你同意。
- [ ] 在網站輸入一個中文網域（例如 `蝦皮購物.tw`），確認它沒有被判為冒用品牌，也就是報告說的問題 F2。
- [ ] 在網站輸入 `https://www.ecpay.com/`，確認它是中風險「疑似冒用：綠界科技」，也就是問題 F9（你 11/9 決定維持這個判定）。
- [ ] 文件中 F1–F9 的嚴重程度是 AI 判斷的；你看過後覺得合理。

## 寫進報告 G7 的「本人核對方式」
照你**實際做了的**寫，例如：

> 本人依核對清單逐項確認 AI 產生的程式：閱讀各檔案的說明是否與本人的決定一致，執行全部 389 項自動測試，並在網站實際操作檢查網址、匯入資料與管理功能。
