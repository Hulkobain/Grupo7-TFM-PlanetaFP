from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data.clean import clean_csv

from .config import load_config
from .pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Entrena el modelo XGBoost de riesgo de retraso."
    )
    parser.add_argument("--config", type=Path, default=Path("src/ml/config.yaml"))
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument(
        "--raw-data",
        type=Path,
        default=None,
        help="Limpia este CSV antes de entrenar y guarda el resultado en la ruta configurada.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    if args.raw_data is not None:
        config = load_config(args.config)
        cleaned_path = args.data or Path(config["data"]["cleaned_path"])
        clean_csv(args.raw_data, cleaned_path)

    metrics = run(args.config, args.data, args.output_dir)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
