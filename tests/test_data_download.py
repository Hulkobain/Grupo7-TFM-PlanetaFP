import pytest
from pathlib import Path
from src.data.download import (
    RAW_FILENAMES,
    download_raw_data,
    ensure_raw_data,
    missing_raw_files,
)


def test_missing_raw_files_lists_only_absent_files(tmp_path: Path) -> None:
    (tmp_path / RAW_FILENAMES[0]).write_text("present", encoding="utf-8")
    assert missing_raw_files(tmp_path) == [tmp_path / name for name in RAW_FILENAMES[1:]]


def test_download_raw_data_copies_all_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_dir = tmp_path / "dataset"
    fake_dir.mkdir()
    for name in RAW_FILENAMES:
        (fake_dir / name).write_text("content", encoding="utf-8")
    def fake_download(force: bool) -> Path:
        return fake_dir
    monkeypatch.setattr("src.data.download._download_dataset", fake_download)
    downloaded = download_raw_data(tmp_path)
    assert downloaded == [tmp_path / name for name in RAW_FILENAMES]
    assert all((tmp_path / name).is_file() for name in RAW_FILENAMES)


def test_ensure_raw_data_skips_download_if_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in RAW_FILENAMES:
        (tmp_path / name).write_text("present", encoding="utf-8")
    def fake_download(force: bool) -> Path:
        fake_dir = tmp_path / "dataset"
        fake_dir.mkdir()
        for name in RAW_FILENAMES:
            (fake_dir / name).write_text("content", encoding="utf-8")
        return fake_dir
    monkeypatch.setattr("src.data.download._download_dataset", fake_download)
    ensure_raw_data(tmp_path)
    # No exception should be raised; _download_dataset should not be called.


def test_download_raw_data_fails_when_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_dir = tmp_path / "dataset"
    fake_dir.mkdir()
    (fake_dir / RAW_FILENAMES[0]).write_text("content", encoding="utf-8")
    def fake_download(force: bool) -> Path:
        return fake_dir
    monkeypatch.setattr("src.data.download._download_dataset", fake_download)
    with pytest.raises(FileNotFoundError, match=RAW_FILENAMES[1]):
        download_raw_data(tmp_path)