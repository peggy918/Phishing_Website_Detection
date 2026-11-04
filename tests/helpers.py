"""測試共用：不依賴 models_store 的假模型（GitHub Actions 上沒有模型檔）。"""
import numpy as np


class ConstantModel:
    """永遠回傳固定機率，讓測試能精準控制風險等級。必須放在可 import 的模組，joblib 才能載入。"""

    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, x):
        return np.tile([1 - self.probability, self.probability], (len(x), 1))
