# 原始資料（不進 git）

重建時請自行下載下列檔案放到本資料夾，並以 SHA-256 核對。

| 檔案 | 來源 | SHA-256 | 備註 |
|---|---|---|---|
| `通報TWNIC詐騙網址彙整表_20261008.xml` | 政府資料開放平臺：數位產業署「通報 TWNIC 詐騙網址彙整表」 | `fc77d9b244528069edd14336c8ca92181fc7d08164eb19edaa5b7475117caedd` | 1,734 筆，2023-06-29 至 2026-10 |
| `dataset_phishing.csv` | Kaggle：shashwatwork / Web Page Phishing Detection Dataset | `21093e2902e5441c86a6daf95e86e7c332046e477fdf109a579d7bd81e586d6c` | 11,430 筆，phishing／legitimate 各 5,715；只用 `url`、`status` |
| `archive.zip`、`Phishing Website Detection Datasets/` | Kaggle 另一個合輯（6 個資料集） | `970b50dc…68b18c0`（zip） | **不使用（2026-10-31 決定）**，重建時不需下載 |
| `tranco_746VX.csv` | Tranco list `746VX`（2026-10-01～10-30，前 100 萬名）：https://tranco-list.eu/list/746VX/1000000 ，下載：https://tranco-list.eu/download/746VX/1000000 | `6851c471538d3b4e6eddfc6a260e57f671921e8b38ef024fd69d5d462a702da5` | 固定 list ID 以便重現；.tw 網域 2,701 個 |

下載後的處理步驟見專案根目錄的 [README.md](../../README.md) 第 3 節。
