# 網域人工抽查清單

比對來源：Tranco `tranco_746VX.csv`（前 100 萬名）。由 `python -m ml.verify_domains` 產生，請勿手動改上方統計。

- 待比對網域 176 個，出現在 Tranco：165 個，未出現且尚未抽查：**0 個**
- 已抽查 44 個，結果見 `docs/domain-review.md`；本檔只列尚未判斷者。抽查結果請寫入 `data/reference/domain_reviews.csv`（decision 填 official／related／not_brand／removed）。
- 與政府黑名單重疊：0 個

> 出現在 Tranco 只代表「是真實存在的熱門網域」，不保證屬於該品牌；品牌歸屬仍以 v2fly 來源或官網為準。

## 一、未出現在 Tranco 的網域（請上官網確認，結果寫入 domain_reviews.csv）

| 網域 | 來源 | 分類／品牌 | 結果 |
|---|---|---|---|

## 二、Tranco .tw 網域中含品牌關鍵字、但不在官方網域的（判斷是否為官方、子公司或仿冒）

| 網域 | Tranco 排名 | 疑似品牌 | 結果 |
|---|---|---|---|

## 三、Tranco（全部 TLD）同時出現在政府黑名單的註冊網域

平台型網域（github.io 等）出現屬正常；其餘代表 Tranco 也收錄了詐騙網域，因此負例必須先排除黑名單。

| 網域 | Tranco 排名 | 平台型 |
|---|---|---|
| cloudfront.net | 27 | ✓ |
| github.io | 136 | ✓ |
| weebly.com | 351 | ✓ |
| vercel.app | 610 | ✓ |
| netlify.app | 831 | ✓ |
| it.com | 990 | ✓ |
| eu.cc | 3495 | ✓ |
| carrd.co | 4592 | ✓ |
| ccaiplatform.com | 17454 | ✓ |
| ooguy.com | 22099 | ✓ |
| pse.is | 36715 | ✓ |
| myfreesites.net | 153097 | ✓ |
| linegames.org | 270291 |  |
| telegram-ios.com | 319365 |  |
| shopex.cn | 380585 |  |
| zifeiji.com | 420129 |  |
| ubpages.com | 629736 | ✓ |
