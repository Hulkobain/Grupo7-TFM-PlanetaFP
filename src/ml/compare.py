from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config
from .evaluate import evaluate
from .model import build_lightgbm_model, build_model, train, train_lightgbm
from .pipeline import DatasetSplits, prepare_data

CHAMPION = "xgboost"
CHALLENGER = "lightgbm"

LOWER_IS_BETTER = {"log_loss", "brier_score"}


def _best_iteration(model) -> int | None:
    for attribute in ("best_iteration_", "best_iteration"):
        value = getattr(model, attribute, None)
        if value is not None:
            return int(value)
    return None


def _run_experiment(config: dict, splits: DatasetSplits, name: str) -> dict:
    if name == CHAMPION:
        model, early_rounds = build_model(config)
        params = config["model"]["hyperparams"]
        started = time.perf_counter()
        train(
            model,
            splits.X_train,
            splits.y_train,
            splits.X_val,
            splits.y_val,
            early_rounds,
        )
    elif name == CHALLENGER:
        model, early_rounds = build_lightgbm_model(config)
        params = config["lightgbm"]["hyperparams"]
        started = time.perf_counter()
        train_lightgbm(
            model,
            splits.X_train,
            splits.y_train,
            splits.X_val,
            splits.y_val,
            early_rounds,
            config["lightgbm"]["eval_metric"],
        )
    else:
        raise ValueError(f"Modelo desconocido para la comparación: {name}")
    train_seconds = time.perf_counter() - started

    started = time.perf_counter()
    y_prob = model.predict_proba(splits.X_test)[:, 1]
    predict_seconds = time.perf_counter() - started

    metrics = evaluate(splits.y_test, y_prob, config["model"]["threshold"])
    return {
        "metrics": metrics,
        "params": params,
        "best_iteration": _best_iteration(model),
        "train_seconds": round(train_seconds, 3),
        "predict_seconds": round(predict_seconds, 3),
    }


def _build_verdict(
    models: dict,
    primary_metric: str,
    min_improvement: float,
) -> dict:
    champion_score = models[CHAMPION]["metrics"][primary_metric]
    challenger_score = models[CHALLENGER]["metrics"][primary_metric]
    higher_is_better = primary_metric not in LOWER_IS_BETTER

    improvement = (
        challenger_score - champion_score
        if higher_is_better
        else champion_score - challenger_score
    )
    selected = CHALLENGER if improvement > min_improvement else CHAMPION

    champion_seconds = models[CHAMPION]["train_seconds"]
    challenger_seconds = models[CHALLENGER]["train_seconds"]
    time_note = (
        f"Tiempo de entrenamiento: XGBoost {champion_seconds:.3f} s, "
        f"LightGBM {challenger_seconds:.3f} s."
    )
    comparison = (
        f"XGBoost {champion_score:.4f} vs LightGBM {challenger_score:.4f}, "
        f"mejora del retador {improvement:+.4f} "
        f"(mínimo requerido {min_improvement:.4f})"
    )
    if selected == CHALLENGER:
        reason = (
            f"Se recomienda LightGBM: supera a XGBoost en {primary_metric} "
            f"({comparison}). {time_note}"
        )
    else:
        reason = (
            f"Se mantiene XGBoost como modelo principal: LightGBM no aporta "
            f"una mejora material en {primary_metric} ({comparison}). {time_note}"
        )

    return {
        "selected": selected,
        "champion": CHAMPION,
        "challenger": CHALLENGER,
        "primary_metric": primary_metric,
        "higher_is_better": higher_is_better,
        "min_improvement": min_improvement,
        "improvement": improvement,
        "reason": reason,
    }


def run_comparison(
    config_path: Path,
    data_path: Path | None = None,
    output_dir: Path | None = None,
    report_path: Path | None = None,
) -> dict:
    config = load_config(config_path)
    if output_dir is not None:
        config["output"]["model_dir"] = str(output_dir)

    splits = prepare_data(config, data_path)
    models = {
        CHAMPION: _run_experiment(config, splits, CHAMPION),
        CHALLENGER: _run_experiment(config, splits, CHALLENGER),
    }
    primary_metric = config["comparison"]["primary_metric"]

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "cleaned_path": config["data"]["cleaned_path"],
            "target": splits.target_column,
            "n_features": len(splits.feature_names),
            "n_train": len(splits.X_train),
            "n_val": len(splits.X_val),
            "n_test": len(splits.X_test),
        },
        "split": {
            "strategy": "temporal",
            "validation_size": config["validation"]["validation_size"],
            "test_size": config["validation"]["test_size"],
        },
        "primary_metric": primary_metric,
        "min_improvement": config["comparison"]["min_improvement"],
        "models": models,
        "verdict": _build_verdict(
            models,
            primary_metric,
            config["comparison"]["min_improvement"],
        ),
    }

    if report_path is None:
        report_path = (
            Path(config["output"]["model_dir"])
            / config["comparison"]["report_file"]
        )
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compara XGBoost (campeón) con LightGBM (retador) sobre el mismo "
            "split temporal y guarda el informe de decisión."
        )
    )
    parser.add_argument("--config", type=Path, default=Path("src/ml/config.yaml"))
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Ruta del informe JSON; por defecto, model_dir/model_comparison.json.",
    )
    args = parser.parse_args()

    report = run_comparison(
        args.config,
        args.data,
        args.output_dir,
        args.report,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
