"""Offline tests for the BTS downloader: a fake opener stands in for the network."""

from __future__ import annotations

import io
import urllib.error
import zipfile
from pathlib import Path
from typing import BinaryIO

import pytest

from aom.ml import bts_download as bts


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("T_ONTIME_REPORTING.csv", "FlightDate,Origin\n2025-01-01,JFK\n")
    return buffer.getvalue()


class FakeNetwork:
    """Returns a valid zip, after failing the first ``failures`` calls."""

    def __init__(self, failures: int = 0, payload: bytes | None = None) -> None:
        self.failures = failures
        self.payload = _zip_bytes() if payload is None else payload
        self.urls: list[str] = []

    def __call__(self, url: str, timeout: float) -> BinaryIO:
        self.urls.append(url)
        if len(self.urls) <= self.failures:
            raise urllib.error.URLError("connection reset")
        return io.BytesIO(self.payload)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bts.time, "sleep", lambda _s: None)


def test_url_has_unpadded_month() -> None:
    assert bts.month_url(2025, 1) == (
        "https://transtats.bts.gov/PREZIP/"
        "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2025_1.zip"
    )
    assert bts.file_name(2025, 12).endswith("_2025_12.zip")
    with pytest.raises(ValueError):
        bts.file_name(2025, 13)


def test_parse_months() -> None:
    assert bts.parse_months("1-12") == list(range(1, 13))
    assert bts.parse_months("3, 1-2, 7") == [1, 2, 3, 7]
    with pytest.raises(ValueError):
        bts.parse_months("0-2")


def test_downloads_and_validates(tmp_path: Path) -> None:
    net = FakeNetwork()
    path = bts.download_month(2025, 4, tmp_path, opener=net, log=lambda _m: None)
    assert path.name.endswith("_2025_4.zip")
    assert bts.is_valid_zip(path)
    assert not list(tmp_path.glob("*.part"))


def test_skips_existing_valid_file(tmp_path: Path) -> None:
    net = FakeNetwork()
    bts.download_month(2025, 4, tmp_path, opener=net, log=lambda _m: None)
    bts.download_month(2025, 4, tmp_path, opener=net, log=lambda _m: None)
    assert len(net.urls) == 1
    bts.download_month(2025, 4, tmp_path, opener=net, force=True, log=lambda _m: None)
    assert len(net.urls) == 2


def test_replaces_a_corrupt_existing_file(tmp_path: Path) -> None:
    (tmp_path / bts.file_name(2025, 5)).write_bytes(b"half a download")
    net = FakeNetwork()
    path = bts.download_month(2025, 5, tmp_path, opener=net, log=lambda _m: None)
    assert bts.is_valid_zip(path)
    assert len(net.urls) == 1


def test_retries_then_succeeds(tmp_path: Path) -> None:
    net = FakeNetwork(failures=2)
    bts.download_month(2025, 6, tmp_path, opener=net, retries=3, log=lambda _m: None)
    assert len(net.urls) == 3


def test_gives_up_and_leaves_no_partial_file(tmp_path: Path) -> None:
    net = FakeNetwork(payload=b"<html>maintenance</html>")
    with pytest.raises(RuntimeError, match="giving up"):
        bts.download_month(2025, 7, tmp_path, opener=net, retries=2, log=lambda _m: None)
    assert list(tmp_path.iterdir()) == []


def test_main_reports_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download(year: int, month: int, out: Path, **_: object) -> Path:
        if month == 2:
            raise RuntimeError("down")
        return out / bts.file_name(year, month)

    monkeypatch.setattr(bts, "download_month", fake_download)
    assert bts.main(["--months", "1-2", "--out", str(tmp_path)]) == 1
    assert bts.main(["--months", "1", "--out", str(tmp_path)]) == 0
