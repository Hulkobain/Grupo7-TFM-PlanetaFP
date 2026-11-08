import json
from pathlib import Path

from src.api.inference import load_inference_service
from src.data.clean import ORDER_CATEGORICAL_COLUMNS, ORDER_LEVEL_FEATURES

ARTIFACT_DIR = Path("src/ml/artifacts")


def _committed_metadata() -> dict:
    path = ARTIFACT_DIR / "model_metadata.json"
    assert path.is_file(), (
        "Falta el artefacto de referencia versionado en src/ml/artifacts/; "
        "regenéralo con `python -m src.ml.train`."
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_committed_artifact_matches_feature_contract() -> None:
    features = _committed_metadata()["features"]

    assert set(ORDER_LEVEL_FEATURES) <= set(features)
    for column in ORDER_CATEGORICAL_COLUMNS:
        assert any(name.startswith(f"{column}_") for name in features), column
    assert any(name.startswith("category_") for name in features)

    # Valida además que el booster y el metadata declaran las mismas features.
    assert load_inference_service(ARTIFACT_DIR) is not None
