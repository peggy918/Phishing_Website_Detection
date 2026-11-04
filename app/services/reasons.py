"""判斷原因：列出 2–3 項使用者看得懂的網址特徵（PLAN 第 4 節）。

這些是規則整理出的線索，不是模型內部的解釋：模型依 48 個特徵綜合判斷，這裡只挑可以直接指給使用者看的部分。
"""
from app.config_loader import load_brands
from app.services.brand_match import BrandMatch
from app.services.normalizer import NormalizedURL

MAX_REASONS = 3
RANDOM_ENTROPY = 3.0        # SLD 熵高於此值且母音比例低，看起來像亂數字串
RANDOM_VOWEL_RATIO = 0.25


def brand_name(key: str | None) -> str | None:
    for b in load_brands()["brands"]:
        if b["key"] == key:
            return b["name"]
    return None


def model_reasons(n: NormalizedURL, features: dict, brand: BrandMatch, level: str) -> list[str]:
    """低風險不列原因：只顯示「未發現明顯風險跡象」，避免把零星特徵講成風險。"""
    if level == "low":
        return []
    out = []
    name = brand_name(brand.brand_key)
    if brand.kind == "contains":
        out.append(f"疑似冒用：{name}（網域含品牌字，但不是官方網域）")
    elif brand.kind == "similar":
        out.append(f"疑似冒用：{name}（網域與官方名稱只差一個字）")
    elif brand.kind in ("official", "related"):
        # 走到模型的官方網域：使用者內容服務或尚無歸屬佐證，不預設是哪一種
        out.append(f"網域屬於{name}，但網址本身有可疑特徵，官方服務上也可能出現他人放置的內容")
    if features["brand_with_digits"]:
        out.append("品牌名稱後面接數字，是大量產生仿冒網域的常見手法")
    if features["has_userinfo"]:
        out.append(f"網址含 @，實際連到的是 @ 後面的 {n.host}")
    if features["tld_suspicious"] and not features["is_shortener"]:  # 短網址的 TLD 是服務本身的，不是線索
        out.append(f"使用 .{n.suffix.split('.')[-1]} 等常見詐騙網域結尾")
    if features["is_ip"]:
        out.append("網址直接使用 IP 位址，而不是網域名稱")
    if features["is_punycode"]:
        out.append("網域含特殊編碼字元（punycode），可能用相似文字偽裝")
    if features["is_shortener"]:
        out.append("這是短網址，無法從網址看出實際目的地")
    if features["is_platform"]:
        out.append(f"架設在 {n.registered_domain} 平台上，任何人都能建立這類子網域")
    if features["sld_entropy"] >= RANDOM_ENTROPY and features["sld_vowel_ratio"] <= RANDOM_VOWEL_RATIO:
        out.append("網域名稱看起來像隨機字串")
    if features["path_keyword_count"] or features["host_keyword_count"]:
        out.append("網址含 login、verify 等常見於釣魚網站的字眼")
    return out[:MAX_REASONS] or ["模型綜合網址特徵後，判斷與已知詐騙網址相似"]
