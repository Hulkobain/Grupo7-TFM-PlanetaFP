from __future__ import annotations

import argparse
import shutil
from pathlib import Path

DATASET_SLUG = "shashwatwork/dataco-smart-supply-chain-for-big-data-analysis"
RAW_FILENAMES = (
    "DataCoSupplyChainDataset.csv",
    "DescriptionDataCoSupplyChain.csv",
    "tokenized_access_logs.csv",
)
DEFAULT_RAW_DIR = Path("data/raw")


def _download_dataset(force: bool) -> Path:
    import kagglehub

    return Path(kagglehub.dataset_download(DATASET_SLUG, force_download=force))


def missing_raw_files(destination: Path = DEFAULT_RAW_DIR) -> list[Path]:
    destination = Path(destination)
    return [
        destination / name
        for name in RAW_FILENAMES
        if not (destination / name).is_file()
    ]


def download_raw_data(
    destination: Path = DEFAULT_RAW_DIR,
    force: bool = False,
) -> list[Path]:
    destination = Path(destination)
    if not force and not missing_raw_files(destination):
        return [destination / name for name in RAW_FILENAMES]

    dataset_path = _download_dataset(force)
    destination.mkdir(parents=True, exist_ok=True)
    for name in RAW_FILENAMES:
        matches = list(dataset_path.rglob(name))
        if not matches:
            raise FileNotFoundError(
                f"El dataset de Kaggle no contiene el fichero {name}"
            )
        shutil.copy2(matches[0], destination / name)

    return [destination / name for name in RAW_FILENAMES]


def ensure_raw_data(
    destination: Path = DEFAULT_RAW_DIR,
    force: bool = False,
) -> list[Path]:
    return download_raw_data(destination, force=force)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga los tres CSV de DataCo desde Kaggle."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Vuelve a descargar los ficheros aunque ya existan.",
    )
    args = parser.parse_args()

    missing = set(missing_raw_files(args.output))
    files = download_raw_data(args.output, force=args.force)
    for path in files:
        status = "Descargado" if args.force or path in missing else "Ya existía"
        print(f"{status}: {path}")


if __name__ == "__main__":
    main()
