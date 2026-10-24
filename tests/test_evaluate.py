import numpy as np
import pytest

from src.ml.evaluate import evaluate, probability_to_percentage


def test_evaluate_returns_binary_classification_metrics() -> None:
    metrics = evaluate([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8], threshold=0.5)

    assert metrics == {
        "roc_auc": 0.75,
        "average_precision": 0.8333333333333333,
        "log_loss": pytest.approx(0.47229, abs=1e-4),
        "brier_score": pytest.approx(0.158125),
        "threshold": 0.5,
        "confusion_matrix": [[2, 0], [1, 1]],
    }


@pytest.mark.parametrize(
    ("y_true", "y_prob", "threshold", "message"),
    [
        ([1, 1], [0.2, 0.8], 0.5, "ambas clases"),
        ([0, 1], [0.2, float("nan")], 0.5, "probabilidades finitas"),
        ([0, 1], [-0.1, 0.8], 0.5, "probabilidades finitas"),
        ([0, 1], [0.2, 1.1], 0.5, "probabilidades finitas"),
        ([0, 1], [0.2], 0.5, "mismo tamaño"),
        ([0, 1], [0.2, 0.8], 1.1, "threshold"),
        ([0, 2], [0.2, 0.8], 0.5, "únicamente 0 o 1"),
    ],
)
def test_evaluate_rejects_invalid_inputs(
    y_true: list[int],
    y_prob: list[float],
    threshold: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        evaluate(y_true, y_prob, threshold)


def test_probability_to_percentage() -> None:
    assert probability_to_percentage(0.9234) == 92.34
    assert probability_to_percentage(0.0) == 0.0
    assert probability_to_percentage(1.0) == 100.0


@pytest.mark.parametrize("probability", [-0.1, 1.1, np.nan, np.inf])
def test_probability_to_percentage_rejects_invalid_probabilities(
    probability: float,
) -> None:
    with pytest.raises(ValueError, match="entre 0 y 1"):
        probability_to_percentage(probability)
