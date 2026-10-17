from src.ml.evaluate import probability_to_percentage


def test_probability_to_percentage() -> None:
    assert probability_to_percentage(0.9234) == 92.34
    assert probability_to_percentage(0.0) == 0.0
    assert probability_to_percentage(1.0) == 100.0
