"""讀取 config/ 下的 YAML 設定（rules.yaml、brands.yaml）。"""
from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@lru_cache(maxsize=None)
def load_rules(path: Path = CONFIG_DIR / "rules.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=None)
def load_brands(path: Path = CONFIG_DIR / "brands.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def match_brand(text: str) -> str | None:
    """依 aliases 將文字（例如政府資料的冒用對象描述）對應到品牌 key，找不到回傳 None。"""
    lowered = text.lower()
    for brand in load_brands()["brands"]:
        if any(alias.lower() in lowered for alias in brand["aliases"]):
            return brand["key"]
    return None
