# 網域抽查紀錄

> 由 `python -m ml.domain_reviews` 依 `data/reference/domain_reviews.csv` 產生，請勿手動修改。
> WHOIS 完整回應含第三方個資，只存本機資料庫；此處只列公司名稱，個人已遮蔽。

圖例：✓ 官方（列入 brands.yaml domains）　△ 同集團或合資（列入 related_domains）　○ 正常網站但非該品牌（保留為台灣正常網域，標 brand_lookalike）　✗ 移除（從 brands.yaml 移除）

| 判斷 | 筆數 |
|---|---|
| ✓ 官方 | 20 |
| △ 同集團 | 8 |
| ○ 非該品牌 | 14 |
| ✗ 移除 | 2 |

## 一、品牌網域未出現在 Tranco

| 網域 | 品牌 | 判斷 | 依據 | 註冊者 | 確認人 | 日期 | 說明 |
|---|---|---|---|---|---|---|---|
| dcard.cc | dcard | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| dcard.io | dcard | ✗ 移除 | 本人官網確認 |  | 本人 | 2026-10-31 | 無法連上這個網站 |
| dcard.link | dcard | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| gogolook.com | gogolook | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| linefriends.com.tw | line | ✗ 移除 | 本人官網確認 |  | 本人 | 2026-10-31 | 無法連上這個網站 |
| linemyshop.com | line | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| mcdonalds.com.tw | mcdonalds | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| momo5188.com | momo | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| pchomeec.tw | pchome | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| pchomeonline.com.tw | pchome | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| pchomepay.com.tw | pchome | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| piapp.com.tw | pchome | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| soft-world.com.tw | softworld | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |

## 二、Tranco .tw 網域含品牌關鍵字

| 網域 | 品牌 | 判斷 | 依據 | 註冊者 | 確認人 | 日期 | 說明 |
|---|---|---|---|---|---|---|---|
| pchomebiz.com.tw | pchome | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| 4gamers.com.tw | bahamut | ○ 非該品牌 | TWNIC WHOIS | 就肆電競股份有限公司 | Claude | 2026-10-31 | WHOIS 註冊者「就肆電競股份有限公司」，非巴哈姆特 |
| hinet.tw | cht | ✓ 官方 | TWNIC WHOIS | Network Technology Group, Chunghwa Telecom Co., Ltd. | Claude | 2026-10-31 | WHOIS 註冊者 Chunghwa Telecom（中華電信） |
| cathaylife.com.tw | cathay | △ 同集團 | TWNIC WHOIS | 國泰人壽保險股份有限公司 | Claude | 2026-10-31 | WHOIS「國泰人壽保險股份有限公司」 |
| chinapost.com.tw | post | ○ 非該品牌 | TWNIC WHOIS | 今日傳媒股份有限公司 | Claude | 2026-10-31 | WHOIS「今日傳媒股份有限公司」（NOWnews），不是中華郵政 |
| cathaysec.com.tw | cathay | △ 同集團 | TWNIC WHOIS | Cathay Securities Corporation | Claude | 2026-10-31 | WHOIS「Cathay Securities Corporation」（國泰證券） |
| momo.com.tw | momo | ✓ 官方 | TWNIC WHOIS | 富邦媒體科技股份有限公司 | Claude | 2026-10-31 | WHOIS「富邦媒體科技股份有限公司」 |
| cathay-cube.com.tw | cathay | ✓ 官方 | TWNIC WHOIS | 國泰世華商業銀行股份有限公司 | Claude | 2026-10-31 | WHOIS「國泰世華商業銀行股份有限公司」 |
| cathay-ins.com.tw | cathay | △ 同集團 | TWNIC WHOIS | 國泰世紀產物保險股份有限公司 | Claude | 2026-10-31 | WHOIS「國泰世紀產物保險股份有限公司」 |
| foodpanda.tw | foodpanda | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| cavesbooks.com.tw | books | ○ 非該品牌 | 本人官網確認 |  | 本人 | 2026-10-31 | 敦煌書局（本人確認為正常網站） |
| linebank.com.tw | line | △ 同集團 | TWNIC WHOIS | LY Corporation | Claude | 2026-10-31 | WHOIS「LY Corporation」（LINE 母公司） |
| yabeline.tw | line | ○ 非該品牌 | TWNIC WHOIS | (個人，已遮蔽) | Claude | 2026-10-31 | WHOIS 註冊者為個人 |
| esunsec.com.tw | esun | △ 同集團 | TWNIC WHOIS | 玉山綜合證券股份有限公司 | Claude | 2026-10-31 | WHOIS「玉山綜合證券股份有限公司」 |
| pchome.tw | pchome | ✓ 官方 | 本人官網確認 |  | 本人 | 2026-10-31 |  |
| shopeepay.tw | shopee | ✓ 官方 | TWNIC WHOIS | ShopeePay Private Limited | Claude | 2026-10-31 | WHOIS「ShopeePay Private Limited」（Sea 集團） |
| postmall.com.tw | post | ✓ 官方 | TWNIC WHOIS | 中華郵政股份有限公司 | Claude | 2026-10-31 | WHOIS「中華郵政股份有限公司」 |
| ebookservice.tw | books | ○ 非該品牌 | 本人官網確認 |  | 本人 | 2026-10-31 | 本人確認為正常網站 |
| lineage182.tw | line | ○ 非該品牌 | TWNIC WHOIS |  | Claude | 2026-10-31 | WHOIS 隱私遮蔽；名稱為遊戲「天堂（Lineage）」私服 |
| familystar.org.tw | family | ○ 非該品牌 | TWNIC WHOIS | 親子觀星會 | Claude | 2026-10-31 | WHOIS「親子觀星會」 |
| rakuten-bank.com.tw | rakuten | △ 同集團 | TWNIC WHOIS | Waterland Financial Holdings | Claude | 2026-10-31 | WHOIS「Waterland Financial Holdings」（國票金控，與樂天合資樂天銀行） |
| cathayhotel.com.tw | cathay | ○ 非該品牌 | TWNIC WHOIS | Cathay Hospitality Management Corporation Limited | Claude | 2026-10-31 | WHOIS「Cathay Hospitality Management」（國泰商旅） |
| cathaysite.com.tw | cathay | △ 同集團 | TWNIC WHOIS | 國泰證券投資信託股份有限公司 | Claude | 2026-10-31 | WHOIS「國泰證券投資信託股份有限公司」 |
| govbooks.com.tw | books | ○ 非該品牌 | 本人官網確認 |  | 本人 | 2026-10-31 | 國家網路書店（本人確認為正常網站） |
| ctbc.edu.tw | ctbc | ○ 非該品牌 | 無法驗證 |  | Claude | 2026-10-31 | .edu.tw 由教育部 TANet 管理；不列入品牌 |
| familyshoes.com.tw | family | ○ 非該品牌 | TWNIC WHOIS | MERCURIES ASSOCIATES | Claude | 2026-10-31 | WHOIS「MERCURIES ASSOCIATES」（三商），非全家 |
| teams.com.tw | microsoft | ○ 非該品牌 | TWNIC WHOIS | HAN LIN EDUCATION TECHNOLOGUY CO.LTD | Claude | 2026-10-31 | WHOIS「HAN LIN EDUCATION TECHNOLOGY」（翰林），非 Microsoft |
| taishinart.org.tw | taishin | △ 同集團 | TWNIC WHOIS | 財團法人台新銀行文化藝術基金會 | Claude | 2026-10-31 | WHOIS「財團法人台新銀行文化藝術基金會」 |
| fast-line.tw | line | ○ 非該品牌 | TWNIC WHOIS |  | Claude | 2026-10-31 | WHOIS 隱私遮蔽，名稱與 LINE 無關 |
| moto-lines.com.tw | line | ○ 非該品牌 | TWNIC WHOIS | Moto-Lines Co., Ltd. | Claude | 2026-10-31 | WHOIS「Moto-Lines Co., Ltd.」 |
| hinetcdn.net.tw | cht | ✓ 官方 | TWNIC WHOIS | Data Communication Business Group | Claude | 2026-10-31 | WHOIS「Data Communication Business Group」，信箱 cht.com.tw（中華電信） |
