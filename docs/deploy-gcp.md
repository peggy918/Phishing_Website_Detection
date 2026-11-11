# 雲端展示版部署（Google Cloud Run）

本機正式版用 SQL Server（見 README）。雲端展示版讓外部使用者不必等本人開電腦，資料庫改用 SQLite
（2026-11-11 老師同意，報告不需更動）。

## 架構與差異

| 項目 | 本機正式版 | 雲端展示版 |
|---|---|---|
| 資料庫 | SQL Server 2022 | SQLite，Docker 建置時匯入品牌、白名單、政府黑名單、模型紀錄（`scripts/build_sqlite.py`） |
| 檢測紀錄 | 永久保存 | 服務重啟或閒置回收後消失（檔案系統不是永久的） |
| 管理頁 | 只限本機 | 一律 404（帶轉送標頭的請求視為外部） |
| 速率限制 | 依來源 IP | 依 `X-Forwarded-For` 最後一段（`TRUSTED_PROXY_HOPS=1`），每位訪客各自計算 |
| 紀錄檔 | `logs/app.jsonl` | 只輸出到標準輸出，由 Cloud Logging 收集 |
| 對外網址 | Cloudflare Quick Tunnel（每次不同、電腦要開著） | 固定的 `*.run.app` 網址 |

部署時上傳的檔案由 `.gcloudignore` 控制：只放行程式、設定、遷移、參考資料、政府 XML 與上線中的模型。
`.env`（密鑰）、`data/raw/whois`（第三方個資）、`docs`、`tests` 都不上傳。檢查方式：

```bash
gcloud meta list-files-for-upload
```

## 費用設定（2026-11-11 查證）

- Cloud Run 免費額度（依請求計費）：每月 200 萬次請求、180,000 vCPU 秒、360,000 GiB 秒；以帳單帳戶合計。
  台灣機房 `asia-east1` 屬 Tier 1，適用免費額度。來源：https://cloud.google.com/run/pricing
- Cloud Build：每個帳單帳戶每月 2,500 分鐘（e2-standard-2）。來源：https://cloud.google.com/build/pricing
- Artifact Registry：每月 0.5 GiB 免費，超過約每 GiB 每月 0.1 美元；舊映像檔要定期清除。
  來源：https://cloud.google.com/artifact-registry/pricing
- 本服務設定：記憶體 512 MiB（本機實測約 200 MB）、最多 1 個執行個體、沒人用時縮到 0。

## 第一次部署

前置：已有啟用中的帳單帳戶與專案，並安裝 Google Cloud CLI。以下 `<專案ID>` 換成實際值。

```bash
gcloud auth login
```
```bash
gcloud config set project <專案ID>
```
```bash
gcloud config set run/region asia-east1
```
```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

新專案的建置帳號（Compute Engine 預設服務帳戶）預設沒有權限讀取上傳的原始碼，第一次部署會出現
`PERMISSION_DENIED`。依官方說明給它 Cloud Run Builder 角色（2026-11-11 本人同意後設定）：

```bash
gcloud projects add-iam-policy-binding <專案ID> --member="serviceAccount:<專案編號>-compute@developer.gserviceaccount.com" --role="roles/run.builder" --condition=None
```

部署（在專案根目錄執行）。`FLASK_SECRET_KEY` 每次部署用新產生的隨機值，不寫進任何檔案：

```bash
gcloud run deploy netcatch --source . --allow-unauthenticated --memory 512Mi --cpu 1 --min-instances 0 --max-instances 1 --set-env-vars "FLASK_SECRET_KEY=$(.venv/Scripts/python -c 'import secrets; print(secrets.token_hex(32))')"
```

完成後會印出服務網址。目前的網址：`https://netcatch-248530658110.asia-east1.run.app`

### 部署時遇到的問題（2026-11-11）

| 錯誤 | 原因 | 處理 |
|---|---|---|
| `PERMISSION_DENIED`（建置帳號） | 新專案的建置帳號沒有讀取原始碼的權限 | 給 `roles/run.builder`（見上） |
| `COPY failed: ... 通報TWNIC詐騙網址彙整表_20261008.xml: file does not exist` | 從 Windows 上傳時，中文檔名在壓縮檔裡變成亂碼 | `COPY data/raw/*.xml`，匯入時另外指定原檔名 |
| `Container import failed`（`ContainerImageImportFailed`） | 亂碼檔名不是 UTF-8，留在映像檔裡 Cloud Run 無法匯入 | 改成多階段建置：XML 只在建資料庫的階段使用，最後的映像檔只複製建好的資料庫 |

## 部署後要做

1. 舊映像檔只保留最新 2 個，避免超過 Artifact Registry 免費空間：

   ```bash
   gcloud artifacts repositories set-cleanup-policies cloud-run-source-deploy --location asia-east1 --policy docs/deploy/artifact-cleanup.json
   ```

2. 在 Google Cloud 主控台「帳單 → 預算與快訊」建立預算（例如 1 美元，50%／100% 時寄信）。
   預算只會寄信通知，不會自動停止服務。

## 更新

程式或模型更新後，重新執行上面的 `gcloud run deploy` 指令即可。換模型時要同時改 `Dockerfile` 的
`MODEL_VERSION` 與 `.gcloudignore` 放行的模型目錄。

## 暫停對外

```bash
gcloud run services delete netcatch
```
