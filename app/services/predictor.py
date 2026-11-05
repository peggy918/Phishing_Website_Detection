"""載入啟用中的模型並預測機率。

模型與特徵版本不一致時拒絕載入：同名特徵的算法可能已改變，預測會失真且不易察覺。
"""
import json
import logging
import threading
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.logging import log_event
from app.models import ModelVersion
from app.services.features import FEATURE_NAMES, FEATURE_VERSION, extract
from app.services.normalizer import NormalizedURL, normalize

ROOT = Path(__file__).resolve().parent.parent.parent


class ModelUnavailable(RuntimeError):
    """沒有可用模型。"""


@dataclass(frozen=True)
class ActiveModel:
    id: int
    version: str
    thresholds: dict
    estimator: object

    def probability(self, n: NormalizedURL) -> float:
        x = pd.DataFrame([extract(n)], columns=FEATURE_NAMES)
        return float(self.estimator.predict_proba(x)[0, 1])


@lru_cache(maxsize=4)
def _load_artifact(path: str):
    full = Path(path) if Path(path).is_absolute() else ROOT / path
    if not full.exists():
        raise ModelUnavailable(f"找不到模型檔：{path}")
    return joblib.load(full)


def active_model(session: Session) -> ActiveModel:
    row = session.scalar(select(ModelVersion).where(ModelVersion.is_active).limit(1))
    if row is None:
        raise ModelUnavailable("尚未啟用任何模型")
    if row.feature_version != FEATURE_VERSION:
        raise ModelUnavailable(f"模型特徵版本 {row.feature_version} 與程式 {FEATURE_VERSION} 不一致，需重新訓練")
    return ActiveModel(row.id, row.version, {"medium": row.threshold_medium, "high": row.threshold_high},
                       _load_artifact(row.artifact_path))


def preload(session_factory) -> bool:
    """先載入啟用中的模型並預測一次，讓第一位使用者不用等。失敗只記錄：黑名單與白名單仍可運作。"""
    start = time.perf_counter()
    try:
        with session_factory() as session:
            model = active_model(session)
            model.probability(normalize("https://example.com/"))
    except Exception as e:
        log_event("model_preload_failed", level=logging.WARNING, reason=str(e))
        return False
    log_event("model_preloaded", version=model.version, duration_ms=round((time.perf_counter() - start) * 1000, 1))
    return True


def preload_in_background(session_factory) -> threading.Thread:
    thread = threading.Thread(target=preload, args=(session_factory,), name="model-preload", daemon=True)
    thread.start()
    return thread


def register_model(session: Session, model_dir: Path, activate: bool = True) -> ModelVersion:
    """讀取 ml/train.py 輸出的 metadata.json，寫入 ModelVersion。重複註冊時更新既有紀錄。"""
    meta = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    row = session.scalar(select(ModelVersion).where(ModelVersion.version == meta["model_version"]))
    if row is None:
        row = ModelVersion(version=meta["model_version"])
        session.add(row)
    artifact = (model_dir / "model.joblib").resolve()
    row.algorithm = meta["algorithm"]
    row.feature_version = meta["feature_version"]
    row.rules_version = meta["rules_version"]
    row.brands_version = meta["brands_version"]
    row.dataset_sha256 = meta["dataset_sha256"]
    row.seed = meta["seed"]
    row.metrics = json.dumps({"test": meta["metrics"], "with_brand_rule": meta.get("metrics_with_brand_rule"),
                              "future_brand_check": meta.get("future_brand_check")}, ensure_ascii=False)
    row.threshold_medium = meta["thresholds"]["medium"]
    row.threshold_high = meta["thresholds"]["high"]
    row.artifact_path = artifact.relative_to(ROOT).as_posix() if artifact.is_relative_to(ROOT) else str(artifact)
    session.flush()
    if activate:
        activate_model(session, row.id)
    return row


def activate_model(session: Session, model_id: int) -> None:
    """同一時間只有一個啟用中的模型。"""
    session.execute(update(ModelVersion).values(is_active=False))
    session.execute(update(ModelVersion).where(ModelVersion.id == model_id).values(is_active=True))
