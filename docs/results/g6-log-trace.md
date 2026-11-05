# G6 紀錄追查演練

> **這是刻意製造的故障**（把模型檔移開），不是實際發生的事故。在全新資料夾重建的環境執行，由程式自動產生。

## 1. 使用者看到的畫面

HTTP 503，頁面顯示「服務暫時無法使用」，並提供追蹤碼 `76cf2f5704194fb98e663cde4b47b18b`。頁面沒有內部錯誤細節。

## 2. 用追蹤碼查紀錄

```json
{"ts": "2026-11-05T13:59:44.527+00:00", "level": "ERROR", "event": "scan_unavailable", "request_id": "76cf2f5704194fb98e663cde4b47b18b", "reason": "找不到模型檔：models_store/lightgbm-20261105-215821/model.joblib"}
{"ts": "2026-11-05T13:59:44.547+00:00", "level": "INFO", "event": "request", "request_id": "76cf2f5704194fb98e663cde4b47b18b", "method": "POST", "route": "/scan", "status": 503, "duration_ms": 112.18}
```

`scan_unavailable` 的 `reason` 直接指出找不到模型檔。紀錄沒有被檢查網址的路徑與查詢參數。

## 3. 修復與確認

把模型檔放回原位後，同一個網址再檢查一次：

```json
{"ts": "2026-11-05T13:59:47.541+00:00", "level": "INFO", "event": "scan_completed", "request_id": "b3584c0833ba45a7a128b4d3df7976b6", "host": "plain-example-site.org", "url_hash": "1b9a53c94d3ffb66", "decided_by": "model", "risk_level": "medium", "brand_rule_applied": false, "probability": 0.6773603562122193, "model_version_id": 1, "rules_version": "2026.10.31-3", "stages_ms": {"normalize": 0.13, "blacklist": 1.63, "whitelist": 0.4, "model": 2907.59, "save": 12.44, "commit": 2.24}}
{"ts": "2026-11-05T13:59:47.542+00:00", "level": "INFO", "event": "request", "request_id": "b3584c0833ba45a7a128b4d3df7976b6", "method": "POST", "route": "/scan", "status": 303, "duration_ms": 2983.2}
```

HTTP 303，流程恢復。紀錄內出現 `secret` 的次數：0。
