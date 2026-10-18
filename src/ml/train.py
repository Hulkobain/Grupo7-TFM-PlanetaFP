from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Entrena el modelo XGBoost de riesgo de retraso."
    )
    parser.add_argument("--config", type=Path, default=Path("src/ml/config.yaml"))
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    metrics = run(args.config, args.data, args.output_dir)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
