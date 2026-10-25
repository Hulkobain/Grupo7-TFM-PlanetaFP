from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

DATASET_SLUG = "shashwatwork/dataco-smart-supply-chain-for-big-data-analysis"
RAW_FILENAMES = (
    "DataCoSupplyChainDataset.csv",
    "DescriptionDataCoSupplyChain.csv",
    "tokenized_access_logs.csv",
)
DEFAULT_RAW_DIR = Path("data/raw")

AUTH_HELP = (
    "Faltan credenciales de Kaggle. Descarga kaggle.json desde "
    "https://www.kaggle.com/settings/account y guárdalo en ~/.kaggle/kaggle.json, "
    "o define KAGGLE_USERNAME y KAGGLE_KEY (también se admite KAGGLE_API_TOKEN)."
)


def _has_credentials() -> bool:
    if os.getenv("KAGGLE_USERNAME") and os.getenv("KAGGLE_KEY"):
        return True
    if os.getenv("KAGGLE_API_TOKEN"):
        return True
    config_dir = Path(os.getenv("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle"))
    if any(
        (config_dir / name).is_file()
        for name in ("kaggle.json", "access_token", "access_token.txt")
    ):
        return True
    return (Path.home() / ".kaggle" / "credentials.json").is_file()


def _build_api() -> Any:
    if not _has_credentials():
        raise RuntimeError(AUTH_HELP)
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi

        enable_oauth = os.getenv("KAGGLE_ENABLE_OAUTH") in ("1", "true", "yes")
        api = KaggleApi(enable_oauth=enable_oauth)
        api.authenticate()
    except SystemExit as exc:
        raise RuntimeError(AUTH_HELP) from exc
    return api


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
    api: Any = None,
) -> list[Path]:
    destination = Path(destination)
    if not force and not missing_raw_files(destination):
        return [destination / name for name in RAW_FILENAMES]

    api = api or _build_api()
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        api.dataset_download_files(
            DATASET_SLUG,
            path=tmp,
            unzip=True,
            force=force,
            quiet=True,
        )
        for name in RAW_FILENAMES:
            matches = list(Path(tmp).rglob(name))
            if not matches:
                raise FileNotFoundError(
                    f"El dataset de Kaggle no contiene el fichero {name}"
                )
            shutil.copy2(matches[0], destination / name)

    return [destination / name for name in RAW_FILENAMES]


def ensure_raw_data(
    destination: Path = DEFAULT_RAW_DIR,
    force: bool = False,
    api: Any = None,
) -> list[Path]:
    return download_raw_data(destination, force=force, api=api)


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
