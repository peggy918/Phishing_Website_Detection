"""風險等級判定：模型機率加上品牌規則。訓練評估與線上預測共用本模組。

規則（2026-11-03 本人決定）：主機名疑似冒用品牌（contains／similar）者至少為中風險。
訓練資料中近似品牌的詐騙樣本太少，模型沒有把這個訊號看重（val_d 抓到率：只用模型 69.5%、加規則 92.1%）。
官方與同集團網域的 kind 是 official／related，不會觸發。規則只會提高風險，不會降低。

黑名單與白名單在呼叫本模組之前處理。
"""
from dataclasses import dataclass

LOW, MEDIUM, HIGH = "low", "medium", "high"
_ORDER = {LOW: 0, MEDIUM: 1, HIGH: 2}
IMPERSONATION_KINDS = frozenset({"contains", "similar"})


@dataclass(frozen=True)
class RiskAssessment:
    level: str
    model_level: str          # 只看模型機率的等級
    brand_rule_applied: bool  # 品牌規則是否提高了等級


def model_level(probability: float, thresholds: dict) -> str:
    if probability >= thresholds["high"]:
        return HIGH
    if probability >= thresholds["medium"]:
        return MEDIUM
    return LOW


def assess(probability: float, brand_kind: str, thresholds: dict) -> RiskAssessment:
    base = model_level(probability, thresholds)
    if brand_kind in IMPERSONATION_KINDS and _ORDER[base] < _ORDER[MEDIUM]:
        return RiskAssessment(MEDIUM, base, True)
    return RiskAssessment(base, base, False)
