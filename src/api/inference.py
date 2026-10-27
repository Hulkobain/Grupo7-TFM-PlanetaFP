from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
import xgboost as xgb

from src.data.clean import build_shipment_features

from .schemas import PredictionResponse

logger = logging.getLogger(__name__)
DEFAULT_MODEL_ARTIFACT_DIR = Path("src/ml/artifacts")
MODEL_METADATA_FILE = "model_metadata.json"
DEFAULT_MODEL_FILE = "delay_risk_xgb.json"


class InferenceService:
    def __init__(
        self,
        model: xgb.XGBClassifier,
        feature_names: list[str],
        threshold: float,
    ) -> None:
        self._model = model
        self._feature_names = feature_names
        self._threshold = threshold

    def predict(self, shipment: dict[str, Any]) -> PredictionResponse:
        features = build_shipment_features(shipment, self._feature_names)
        probabilities = np.asarray(self._model.predict_proba(features), dtype=float)
        if probabilities.shape != (1, 2):
            raise RuntimeError(
                f"El modelo devolvió probabilidades con forma inesperada: {probabilities.shape}"
            )

        probability = float(probabilities[0, 1])
        if not np.isfinite(probability) or not 0 <= probability <= 1:
            raise RuntimeError("El modelo devolvió una probabilidad inválida")

        return PredictionResponse(
            delay_risk=probability >= self._threshold,
            delay_probability=probability,
            threshold=self._threshold,
        )


def load_inference_service(
    artifact_dir: Path | None = None,
) -> InferenceService | None:
    artifact_dir = artifact_dir or Path(
        os.getenv("MODEL_ARTIFACT_DIR", str(DEFAULT_MODEL_ARTIFACT_DIR))
    )
    metadata_path = artifact_dir / MODEL_METADATA_FILE
    if not metadata_path.is_file():
        logger.warning(
            "No se encuentra el metadata del modelo en %s; la inferencia no está disponible",
            metadata_path,
        )
        return None

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("El metadata del modelo debe ser un objeto JSON")
    model_file = metadata.get("model_file", DEFAULT_MODEL_FILE)
    if not isinstance(model_file, str) or Path(model_file).name != model_file:
        raise ValueError(
            "model_file debe ser un nombre de fichero dentro del directorio de artefactos"
        )
    model_path = artifact_dir / model_file
    if not model_path.is_file():
        logger.warning(
            "No se encuentra el artefacto del modelo en %s; la inferencia no está disponible",
            model_path,
        )
        return None

    feature_names = metadata.get("features")
    threshold = metadata.get("threshold")
    if (
        not isinstance(feature_names, list)
        or not feature_names
        or not all(isinstance(name, str) for name in feature_names)
        or len(set(feature_names)) != len(feature_names)
    ):
        raise ValueError("El metadata debe incluir una lista válida de features únicas")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not np.isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("El metadata debe incluir un threshold entre 0 y 1")

    model = xgb.XGBClassifier()
    model.load_model(str(model_path))
    model_feature_names = model.get_booster().feature_names
    if model_feature_names is not None and model_feature_names != feature_names:
        raise ValueError(
            "Las features del modelo no coinciden con las del metadata"
        )

    logger.info("Modelo de inferencia cargado desde %s", model_path)
    return InferenceService(model, feature_names, float(threshold))
