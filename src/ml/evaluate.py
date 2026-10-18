from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)


def evaluate(y_true, y_prob, threshold: float) -> dict:
    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "average_precision": float(average_precision_score(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "threshold": float(threshold),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def probability_to_percentage(probability: float) -> float:
    return round(100.0 * float(probability), 2)
