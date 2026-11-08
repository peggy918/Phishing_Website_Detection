"""產生初審文件的三張技術圖（p.8 架構圖、p.9 資料流程圖、p.10 ERD）。

中文標楷體、英文 Times New Roman（評分文件規定）。
用法：python docs/report/make_diagrams.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

plt.rcParams["font.family"] = ["Times New Roman", "DFKai-SB"]
plt.rcParams["axes.unicode_minus"] = False

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

INK = "#1d1d1f"
MUTED = "#55555a"
OURS = ("#e8f1fb", "#1f5fa8")       # 本專案開發
EXTERNAL = ("#f2f2f4", "#6e6e73")   # 外部服務、套件、資料
STORE = ("#fdf3df", "#a56a00")      # 資料保存
BAD = ("#fbe9e7", "#b3261e")        # 失敗路徑
GOOD = ("#e7f3ec", "#1f7a4d")


def canvas(width, height):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, lines=(), style=OURS, size=11, title_size=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08",
                                facecolor=style[0], edgecolor=style[1], linewidth=1.3))
    if lines:
        gap = size * 0.0205
        top = y + h / 2 + gap * len(lines) / 2
        ax.text(x + w / 2, top, title, ha="center", va="center", fontsize=title_size or size + 0.5,
                color=INK)
        for i, line in enumerate(lines):
            ax.text(x + w / 2, top - gap * (i + 1), line, ha="center", va="center", fontsize=size - 1, color=MUTED)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=size, color=INK)


def arrow(ax, start, end, label=None, color=INK, offset=(0, 0), both=False, size=9.5, ls="-"):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="<|-|>" if both else "-|>", mutation_scale=12,
                                 color=color, linewidth=1.2, linestyle=ls, shrinkA=0, shrinkB=0))
    if label:
        ax.text((start[0] + end[0]) / 2 + offset[0], (start[1] + end[1]) / 2 + offset[1], label, ha="center",
                va="center", fontsize=size, color=color,
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2})


def legend(ax, x, y, items):
    for label, style in items:
        ax.add_patch(FancyBboxPatch((x, y), 0.26, 0.17, boxstyle="round,pad=0,rounding_size=0.03",
                                    facecolor=style[0], edgecolor=style[1], linewidth=1.1))
        ax.text(x + 0.33, y + 0.085, label, va="center", fontsize=10, color=INK)
        x += 0.5 + 0.17 * len(label)


def save(fig, name):
    fig.savefig(OUT / name, dpi=220, bbox_inches="tight", pad_inches=0.05, facecolor="white")
    plt.close(fig)


def architecture():
    fig, ax = canvas(9.4, 7.5)
    box(ax, 0.2, 6.55, 2.7, 0.75, "訪客（瀏覽器）", ["貼網址、看結果"], EXTERNAL)
    box(ax, 6.5, 6.55, 2.7, 0.75, "管理者（本機瀏覽器）", ["匯入 XML、切換模型"], EXTERNAL)

    ax.add_patch(FancyBboxPatch((0.2, 2.72), 9.0, 3.45, boxstyle="round,pad=0,rounding_size=0.1",
                                facecolor="none", edgecolor=OURS[1], linewidth=1.2, linestyle="--"))
    ax.text(3.1, 5.98, "Flask 應用程式（本專案開發，MVC＋services）", fontsize=11, color=OURS[1], va="center")
    box(ax, 0.5, 4.86, 3.35, 0.92, "Controller：scan", ["表單、頻率限制、CSRF、結果頁"])
    box(ax, 5.55, 4.86, 3.35, 0.92, "Controller：admin", ["本機限制、登入、匯入、切換模型"])
    box(ax, 3.98, 4.98, 1.45, 0.68, "Views", ["Jinja2 模板"])

    box(ax, 0.5, 2.92, 1.6, 1.42, "偵測流程", ["scan", "normalizer", "risk、reasons"], size=10.5)
    box(ax, 2.2, 2.92, 1.6, 1.42, "比對", ["blacklist", "brand_match", "白名單查詢"], size=10.5)
    box(ax, 3.9, 2.92, 1.6, 1.42, "模型預測", ["features", "predictor"], size=10.5)
    box(ax, 5.6, 2.92, 1.6, 1.42, "資料匯入", ["gov_import", "reference_data"], size=10.5)
    box(ax, 7.3, 2.92, 1.6, 1.42, "紀錄", ["app/logging", "JSON、request_id"], size=10.5)

    box(ax, 0.5, 1.15, 3.3, 1.0, "SQL Server 2022", ["11 張資料表", "帳號只有資料讀寫權限"], STORE)
    box(ax, 3.9, 1.15, 1.6, 1.0, "模型檔", ["LightGBM", "models_store/"], STORE)
    box(ax, 5.6, 1.15, 1.6, 1.0, "設定檔", ["rules.yaml", "brands.yaml"], STORE)
    box(ax, 7.3, 1.15, 1.6, 1.0, "紀錄檔", ["logs/app.jsonl", "主機名與雜湊"], STORE)

    box(ax, 0.2, 0.05, 9.0, 0.78, "外部套件", ["Flask、SQLAlchemy、Alembic、pyodbc、ODBC Driver 18、tldextract（隨附快照）、LightGBM、defusedxml"],
        style=EXTERNAL, size=10.5)

    arrow(ax, (1.55, 6.55), (1.55, 5.78), "HTTP", both=True)
    arrow(ax, (7.85, 6.55), (7.85, 5.78), "HTTP（只限本機）", both=True)
    arrow(ax, (3.85, 5.32), (3.98, 5.32))
    arrow(ax, (5.55, 5.32), (5.43, 5.32))
    arrow(ax, (1.3, 4.86), (1.3, 4.34))
    arrow(ax, (6.4, 4.86), (6.4, 4.34))
    arrow(ax, (1.3, 2.92), (1.3, 2.15), both=True)
    arrow(ax, (3.0, 2.92), (3.0, 2.15), both=True)
    arrow(ax, (4.7, 2.92), (4.7, 2.15))
    arrow(ax, (6.4, 2.92), (6.4, 2.15), "讀取", offset=(0.3, 0))
    arrow(ax, (8.1, 2.92), (8.1, 2.15), "寫入", offset=(0.3, 0))
    ax.plot([6.0, 6.0, 3.5], [2.92, 2.42, 2.42], color=MUTED, linewidth=1.2)
    arrow(ax, (3.5, 2.42), (3.5, 2.15), color=MUTED)
    ax.text(4.7, 7.05, "不連線被檢查的網址：\n系統沒有抓網頁、DNS、WHOIS 的路徑", ha="center", va="center", fontsize=10.5, color=BAD[1])
    legend(ax, 3.3, 6.38, [("本專案開發", OURS), ("外部", EXTERNAL)])
    save(fig, "architecture.png")


def data_flow():
    fig, ax = canvas(9.4, 9.25)
    x, w = 1.9, 3.9
    steps = [
        (8.3, "1. 輸入：訪客貼上網址並送出", ["檢查：CSRF、頻率限制（30 次／分）"], EXTERNAL),
        (7.2, "2. 正規化", ["去追蹤參數、統一大小寫與 www"], OURS),
        (6.1, "3. 黑名單比對（資料庫）", ["一般比註冊網域；平台與指定子網域比主機名"], OURS),
        (5.0, "4. 白名單比對（資料庫）", ["平台型網域不適用；只收有佐證的官方網域"], OURS),
        (3.9, "5. 模型預測", ["48 個特徵，只用網址字串 → LightGBM 機率"], OURS),
        (2.8, "6. 風險判定", ["兩個門檻＋品牌規則（疑似冒用至少中風險）"], OURS),
        (1.7, "7. 保存（資料庫交易）", ["請求與結果一起成功或失敗；去除查詢參數"], STORE),
        (0.6, "8. 導向結果頁（重新整理不會重送）", ["去連結顯示網址、風險等級、原因、165 管道"], GOOD),
    ]
    for y, title, lines, style in steps:
        box(ax, x, y, w, 0.82, title, lines, style, size=10.5)
    for (y, *_rest), (next_y, *_r) in zip(steps, steps[1:]):
        arrow(ax, (x + w / 2, y), (x + w / 2, next_y + 0.82))

    ax.text(x + w / 2 + 0.12, 6.0, "未命中", fontsize=9.5, color=MUTED, va="center")
    ax.text(x + w / 2 + 0.12, 4.9, "未命中", fontsize=9.5, color=MUTED, va="center")

    # 右側：命中直接跳到保存
    box(ax, 6.55, 6.14, 2.65, 0.74, "命中：高風險", ["顯示通報日期與冒用對象"], GOOD, size=10)
    box(ax, 6.55, 5.04, 2.65, 0.74, "命中：未發現明顯風險跡象", ["顯示所屬品牌，不說安全"], GOOD, size=10)
    arrow(ax, (x + w, 6.51), (6.55, 6.51))
    arrow(ax, (x + w, 5.41), (6.55, 5.41))
    ax.plot([9.0, 9.0], [5.04, 2.11], color=INK, linewidth=1.2)
    ax.plot([9.0, 9.0], [6.14, 5.78], color=INK, linewidth=1.2)
    arrow(ax, (9.0, 2.11), (x + w, 2.11))

    # 左側：失敗路徑
    box(ax, 0.05, 7.22, 1.55, 0.78, "網址無效", ["400，留在首頁", "只記狀態"], BAD, size=9.5, title_size=10)
    arrow(ax, (x, 7.61), (1.6, 7.61), color=BAD[1])
    box(ax, 0.05, 3.92, 1.55, 0.78, "沒有可用模型", ["503＋追蹤碼", "不存結果"], BAD, size=9.5, title_size=10)
    arrow(ax, (x, 4.31), (1.6, 4.31), color=BAD[1])
    box(ax, 0.05, 1.72, 1.55, 0.78, "資料庫失敗", ["500＋追蹤碼", "全部復原"], BAD, size=9.5, title_size=10)
    arrow(ax, (x, 2.11), (1.6, 2.11), color=BAD[1])

    # 紀錄
    box(ax, 6.55, 0.6, 2.65, 0.82, "紀錄（logs/app.jsonl）", ["request_id、各階段耗時", "主機名與雜湊，不含完整網址"], STORE, size=10)
    arrow(ax, (x + w, 1.0), (6.55, 1.0), color=MUTED, ls="--")
    save(fig, "data_flow.png")


def erd():
    fig, ax = canvas(9.5, 8.6)

    def table(x, y, name, fields, w=2.28):
        row = 0.215
        h = 0.3 + row * len(fields) + 0.05
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05",
                                    facecolor="white", edgecolor=OURS[1], linewidth=1.2))
        ax.add_patch(FancyBboxPatch((x, y + h - 0.3), w, 0.3, boxstyle="round,pad=0,rounding_size=0.05",
                                    facecolor=OURS[0], edgecolor=OURS[1], linewidth=1.2))
        ax.text(x + w / 2, y + h - 0.15, name, ha="center", va="center", fontsize=10.5, color=INK)
        for i, f in enumerate(fields):
            color = "#a56a00" if f.startswith("FK") else (OURS[1] if f.startswith("PK") else INK)
            ax.text(x + 0.08, y + h - 0.3 - row * (i + 0.5) - 0.02, f, va="center", fontsize=8.8, color=color)

    table(0.1, 6.9, "import_batch", ["PK id", "filename", "UQ file_sha256", "record_count、skipped_count", "imported_at"])
    table(3.5, 5.75, "blacklist_entry", ["PK id", "FK batch_id", "FK brand_id（可空）", "UQ(batch_id, record_no)", "target_text、raw_url", "normalized_url、host",
                                         "match_level、match_key", "reported_on、stopped_on", "needs_review"])
    table(7.0, 7.1, "brand", ["PK id", "UQ key", "name", "aliases"])
    table(7.0, 5.45, "brand_domain", ["PK id", "FK brand_id", "UQ domain", "relation"])
    table(7.0, 3.72, "whitelist", ["PK id", "FK brand_id（可空）", "UQ domain", "decision、evidence", "reviewer、note"])
    table(0.1, 3.72, "scan_request", ["PK id", "UQ public_id", "input_type", "created_at、status", "rules_version"])
    table(3.5, 2.4, "scan_result", ["PK id", "FK、UQ request_id", "FK blacklist_entry_id（可空）", "FK suspected_brand_id（可空）", "FK model_version_id（可空）",
                                    "storage_url、host", "decided_by、risk_level", "probability、brand_rule_applied", "reasons"], w=2.75)
    table(0.1, 0.72, "model_version", ["PK id", "UQ version", "algorithm、feature_version", "rules_version、brands_version", "dataset_sha256、seed", "metrics",
                                       "threshold_medium、threshold_high", "artifact_path、is_active"], w=2.55)
    table(7.0, 2.15, "domain_review", ["PK id", "UQ domain", "brand_key、decision", "evidence、reviewer", "note"])
    table(7.0, 0.58, "whois_record", ["PK id", "UQ domain", "registrant", "queried_on", "raw_response（只存本機）"])
    table(3.5, 0.72, "admin_user", ["PK id", "UQ username", "password_hash", "created_at"], w=2.75)

    def link(points, label=None, at=None):
        xs, ys = zip(*points)
        ax.plot(xs[:-1], ys[:-1], color=MUTED, linewidth=1.2)
        arrow(ax, points[-2], points[-1], color=MUTED)
        if label:
            ax.text(at[0], at[1], label, fontsize=9, ha="center", va="center", color=MUTED,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.6})

    link([(2.38, 7.2), (3.5, 7.2)], "1 對多", (2.94, 7.2))
    link([(7.0, 7.65), (5.78, 7.65)], "0..1 對多", (6.39, 7.65))
    link([(8.14, 7.1), (8.14, 6.66)], "1 對多", (8.14, 6.88))
    link([(9.28, 7.7), (9.42, 7.7), (9.42, 4.4), (9.28, 4.4)], "0..1\n對多", (9.27, 5.9))
    link([(7.0, 7.3), (6.62, 7.3), (6.62, 4.2), (6.25, 4.2)], "0..1 對多", (6.62, 5.2))
    link([(4.6, 5.75), (4.6, 4.7)], "0..1 對多", (4.6, 5.22))
    link([(2.38, 4.3), (3.5, 4.3)], "1 對 0..1", (2.94, 4.3))
    link([(2.65, 2.55), (3.5, 2.55)], "0..1 對多", (3.07, 2.55))
    ax.text(0.1, 0.42, "PK 主鍵　FK 外鍵　UQ 唯一", fontsize=9.5, color=MUTED)
    ax.text(0.1, 0.17, "domain_review、whois_record、admin_user 沒有外鍵；前兩者以網域對應，白名單由它們決定", fontsize=9.5, color=MUTED)
    save(fig, "erd.png")


if __name__ == "__main__":
    architecture()
    data_flow()
    erd()
    print(sorted(p.name for p in OUT.glob("*.png")))
