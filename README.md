# 一網打詐 NetCatch

輸入網址，檢查是否有可疑跡象，並說明原因。結合政府通報的詐騙網址、品牌官方網域與機器學習模型。

資訊管理實務專題作品（系統代號 PhishGuard），非政府官方服務。系統只分析網址文字，**不會連線到被檢查的網址**；結果只代表可疑跡象，不保證網站沒有問題。

```
輸入網址 → 正規化 → 黑名單 → 白名單 → 模型＋品牌規則 → 風險與原因 → 存檔
```

## 環境需求

| 項目 | 版本 |
|---|---|
| 作業系統 | Windows 10／11（其他系統未驗證） |
| Python | 3.14 |
| 資料庫 | SQL Server 2022（Developer 版即可），開啟混合驗證模式 |
| 驅動程式 | ODBC Driver 18 for SQL Server |
| 工具 | Git、sqlcmd（或 SSMS） |

以下指令都在專案根目錄執行，可用 PowerShell 或 Git Bash。

## 1. 安裝

```bash
git clone <repo 網址> phishguard
```
```bash
cd phishguard
```
```bash
py -3.14 -m venv .venv
```
```bash
.venv/Scripts/python -m pip install -r requirements.txt
```

## 2. 準備原始資料

原始資料不放在 git。依 [data/raw/README.md](data/raw/README.md) 下載 3 個檔案到 `data/raw/`，並核對 SHA-256：政府通報 XML、Kaggle `dataset_phishing.csv`、Tranco 清單。

## 3. 清理資料並訓練模型

依序執行（前面的輸出是後面的輸入）：

```bash
.venv/Scripts/python -m ml.clean_gov
```
```bash
.venv/Scripts/python -m ml.clean_kaggle
```
```bash
.venv/Scripts/python -m ml.build_tw_legit
```
```bash
.venv/Scripts/python -m ml.make_variants
```
```bash
.venv/Scripts/python -m ml.build_dataset
```
```bash
.venv/Scripts/python -m ml.train
```

模型會輸出到 `models_store/<模型版本>/`，評估結果寫入 `docs/results/stage2-evaluation.md`。資料切分不用隨機抽樣、隨機種子固定，指標應與 repo 內的評估結果相同；模型版本名稱含時間，每次不同。

## 4. 建立設定檔

```bash
cp .env.example .env
```

產生密鑰和資料庫密碼：

```bash
.venv/Scripts/python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32)); print('DB_PASSWORD=Pg-7' + secrets.token_urlsafe(18))"
```

把印出的兩行填入 `.env`，取代原本的 `change-me`。`.env` 不可提交。

## 5. 建立資料庫

用 Windows 驗證建立資料庫與應用程式專用帳號。把 `你的密碼` 換成 `DB_PASSWORD` 的值，**路徑要用反斜線並加引號**：

```bash
sqlcmd -S localhost -E -C -i "scripts\setup_db.sql" -v APP_PASSWORD="你的密碼"
```

也可以改用 SSMS：建立資料庫 `PhishGuard`；建立 SQL 登入 `phishguard_app`（取消「使用者必須在下次登入時變更密碼」與密碼逾期），只對應 `PhishGuard` 並給 `db_datareader`、`db_datawriter`。

確認連線與權限：

```bash
.venv/Scripts/python scripts/check_db.py
```

建立資料表（以 Windows 驗證執行，應用程式帳號沒有改結構的權限）：

```bash
.venv/Scripts/alembic upgrade head
```

## 6. 匯入資料與註冊模型

```bash
.venv/Scripts/flask --app app:create_app seed-reference
```
```bash
.venv/Scripts/flask --app app:create_app import-gov "data/raw/通報TWNIC詐騙網址彙整表_20261008.xml"
```

`seed-reference` 會把 repo 內遮蔽過的抽查紀錄與 WHOIS 摘要存入資料庫，白名單由資料庫的紀錄決定。完整 WHOIS 回應含第三方個資，不在 repo；本機若有，可用 `import-whois <資料夾>` 存入資料庫，沒有也不影響運作。

把 `<模型版本>` 換成第 3 步產生的目錄名稱：

```bash
.venv/Scripts/flask --app app:create_app register-model models_store/<模型版本>
```

建立管理者帳號（會提示輸入密碼，至少 12 字）：

```bash
.venv/Scripts/flask --app app:create_app create-admin admin
```

## 7. 啟動

```bash
.venv/Scripts/flask --app wsgi run
```

- 偵測頁：<http://127.0.0.1:5000/>
- 管理頁：<http://127.0.0.1:5000/admin/>（只允許本機存取）

啟動時會在背景載入模型，載入完成前的第一次模型判斷可能要等幾秒。

紀錄寫在 `logs/app.jsonl`（JSON 格式）。錯誤頁會顯示追蹤碼，對應紀錄的 `request_id`。

## 測試

測試使用暫存 SQLite 與假模型，不需要 SQL Server、原始資料或模型檔。

```bash
.venv/Scripts/python -m playwright install chromium
```
```bash
.venv/Scripts/python -m pytest
```

| 目錄 | 內容 |
|---|---|
| `tests/unit` | 正規化、特徵、品牌比對、風險判定、資料切分 |
| `tests/integration` | 偵測流程、管理頁權限、匯入、紀錄、資料庫遷移 |
| `tests/e2e` | 用瀏覽器操作完整流程、重複送出、異常輸入 |

## 目錄

```
app/          Flask 應用程式：controllers、models、views、services、logging
config/       rules.yaml（規則）、brands.yaml（品牌對照表）
ml/           資料清理、訓練、評估
data/         raw、processed（不進 git）；reference（抽查紀錄與 WHOIS 佐證）
migrations/   資料庫遷移
scripts/      資料庫設定與連線檢查
tests/        自動化測試
docs/         規劃、評估結果、報告素材
```

## 已知限制

- 模型對新出現的被冒用品牌抓得較差，品牌表需要持續維護；評估細節見 `docs/results/stage2-evaluation.md`。
- 短網址無法判斷實際目的地；4 字品牌（如 line）的拼字變形抓不到；含品牌字的正常網站可能被判中風險。
- 目前的頻率限制以來源 IP 計算，透過 Cloudflare Tunnel 對外前需要調整。
