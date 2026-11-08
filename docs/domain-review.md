# 網域抽查紀錄

> 由 `python -m ml.domain_reviews` 依 `data/reference/domain_reviews.csv` 產生，請勿手動修改。
> WHOIS 完整回應含第三方個資，只存本機資料庫；此處只列公司名稱，個人已遮蔽。

圖例：✓ 官方（列入 brands.yaml domains）　△ 同集團或合資（列入 related_domains）　○ 正常網站但非該品牌（保留為台灣正常網域，標 brand_lookalike）　✗ 移除（從 brands.yaml 移除）　？ 查無佐證（仍是官方網域清單的一部分，但不進白名單）

| 判斷 | 筆數 |
|---|---|
| ✓ 官方 | 51 |
| △ 同集團 | 8 |
| ○ 非該品牌 | 14 |
| ✗ 移除 | 2 |
| ？ 查無佐證 | 4 |

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

## 三、brands.yaml 原本沒有佐證的網域（2026-11-08 由 Claude 查證）

| 網域 | 品牌 | 判斷 | 依據 | 註冊者 | 確認人 | 日期 | 說明 |
|---|---|---|---|---|---|---|---|
| post.gov.tw | post | ✓ 官方 | gov.tw 政府網域 |  | Claude | 2026-11-08 | gov.tw 只能由政府機關註冊 |
| mof.gov.tw | mof | ✓ 官方 | gov.tw 政府網域 |  | Claude | 2026-11-08 | gov.tw 只能由政府機關註冊 |
| nat.gov.tw | mof | ✓ 官方 | gov.tw 政府網域 |  | Claude | 2026-11-08 | gov.tw 只能由政府機關註冊；財政部電子申報繳稅服務網 |
| whoscall.com | gogolook | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q10853310 Whoscall |
| signal.org | signal | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q19718090 Signal |
| microsoft.com | microsoft | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q2283 Microsoft |
| live.com | microsoft | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q219136 Outlook.com（outlook.live.com） |
| meta.com | meta | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q380 Meta Platforms |
| facebook.com | meta | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q355 Facebook |
| instagram.com | meta | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q209330 Instagram |
| telegram.org | telegram | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q15616276 Telegram |
| diptyqueparis.com | diptyque | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q1227345 Diptyque |
| byredo.com | byredo | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q30595852 Byredo |
| maisonmargiela.com | margiela | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q1726925 Maison Margiela |
| loewe.com | loewe | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q966905 Loewe |
| hoka.com | hoka | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q16908664 Hoka |
| salomon.com | salomon | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q2120822 Salomon |
| thombrowne.com | thombrowne | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q3524805 Thom Browne |
| ctbcbank.com | ctbc | ✓ 官方 | Wikidata 官方網站 |  | Claude | 2026-11-08 | Wikidata 官方網站(P856)：Q5100191 CTBC Bank |
| fb.com | meta | ✓ 官方 | RDAP 註冊者 | Meta Platforms, Inc. | Claude | 2026-11-08 | RDAP 註冊者組織 |
| friday.tw | friday | ？ 查無佐證 | TWNIC WHOIS |  | Claude | 2026-11-08 | WHOIS 註冊者已遮蔽，Wikidata 查無；不進白名單 |
| newebpay.com | newebpay | ？ 查無佐證 | 無法驗證 |  | Claude | 2026-11-08 | Wikidata 查無，RDAP 註冊者查不到；不進白名單 |
| esunbank.com | esun | ？ 查無佐證 | 無法驗證 |  | Claude | 2026-11-08 | Wikidata 列的官網是 esunbank.com.tw；RDAP 查不到；不進白名單 |
| t.me | telegram | ？ 查無佐證 | 無法驗證 |  | Claude | 2026-11-08 | .me 沒有 RDAP 資料，Wikidata 查無；本來就不進白名單（no_whitelist） |
| ecpay.com.tw | ecpay | ✓ 官方 | TWNIC WHOIS | 綠界科技股份有限公司 | Claude | 2026-11-08 |  |
| i-pass.com.tw | ipass | ✓ 官方 | TWNIC WHOIS | IPASS CORPORATION | Claude | 2026-11-08 |  |
| easycard.com.tw | easycard | ✓ 官方 | TWNIC WHOIS | Taipei Smart Card Corp. | Claude | 2026-11-08 |  |
| etmall.com.tw | etmall | ✓ 官方 | TWNIC WHOIS | 東森得易購股份有限公司 | Claude | 2026-11-08 |  |
| skm.com.tw | skm | ✓ 官方 | TWNIC WHOIS | 新光三越百貨股份有限公司 | Claude | 2026-11-08 |  |
| kingstone.com.tw | kingstone | ✓ 官方 | TWNIC WHOIS | 金石網絡股份有限公司 | Claude | 2026-11-08 |  |
| kfcclub.com.tw | kfc | ✓ 官方 | TWNIC WHOIS | Jardine Food Services (Taiwan) Co., Ltd. | Claude | 2026-11-08 |  |
| foodpanda.com.tw | foodpanda | ✓ 官方 | TWNIC WHOIS | Delivery Hero SE | Claude | 2026-11-08 |  |
| t-cat.com.tw | tcat | ✓ 官方 | TWNIC WHOIS | 統一速達股份有限公司 | Claude | 2026-11-08 |  |
| 7-11.com.tw | seven | ✓ 官方 | TWNIC WHOIS | 統一超商股份有限公司 | Claude | 2026-11-08 |  |
| bot.com.tw | bot | ✓ 官方 | TWNIC WHOIS | 臺灣銀行股份有限公司 | Claude | 2026-11-08 |  |
