from pathlib import Path

import pytest

from src.data.download import (
    DATASET_SLUG,
    RAW_FILENAMES,
    download_raw_data,
    ensure_raw_data,
    missing_raw_files,
)


class FakeKaggleApi:
    def __init__(self, files: dict[str, str] | None = None) -> None:
        self.files = files or {name: name for name in RAW_FILENAMES}
        self.calls: list[dict] = []

    def dataset_download_files(
        self,
        dataset: str,
        path: str | Path | None = None,
        **kwargs,
    ) -> None:
        self.calls.append({"dataset": dataset, "path": Path(path), "kwargs": kwargs})
        for name, content in self.files.items():
            target = Path(path) / name
            target.write_text(content, encoding="utf-8")


def test_missing_raw_files_lists_only_absent_files(tmp_path: Path) -> None:
    (tmp_path / RAW_FILENAMES[0]).write_text("present", encoding="utf-8")

    assert missing_raw_files(tmp_path) == [
        tmp_path / name for name in RAW_FILENAMES[1:]
    ]


def test_download_raw_data_copies_all_files(tmp_path: Path) -> None:
    api = FakeKaggleApi()

    downloaded = download_raw_data(tmp_path, api=api)

    assert downloaded == [tmp_path / name for name in RAW_FILENAMES]
    assert all((tmp_path / name).is_file() for name in RAW_FILENAMES)
    assert api.calls[0]["dataset"] == DATASET_SLUG
    assert api.calls[0]["kwargs"]["unzip"] is True


def test_ensure_raw_data_skips_api_when_files_exist(tmp_path: Path) -> None:
    for name in RAW_FILENAMES:
        (tmp_path / name).write_text("present", encoding="utf-8")
    api = FakeKaggleApi()

    ensure_raw_data(tmp_path, api=api)

    assert api.calls == []


def test_download_raw_data_fails_when_dataset_lacks_file(tmp_path: Path) -> None:
    api = FakeKaggleApi(files={RAW_FILENAMES[0]: "only one"})

    with pytest.raises(FileNotFoundError, match=RAW_FILENAMES[1]):
        download_raw_data(tmp_path, api=api)


def test_download_raw_data_requires_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(tmp_path / "config"))

    with pytest.raises(RuntimeError, match="credenciales"):
        download_raw_data(tmp_path / "raw")
